"""Client for the CourtListener REST API (Free Law Project).

Two access modes are supported. With ``COURTLISTENER_TOKEN`` set, requests are
paced quickly and the ``citation-lookup`` endpoint and opinion-text endpoints
are available. Without a token, only ``search`` works, it is paced at roughly
one request per 3.6 seconds to stay inside the anonymous allowance, and requests
for opinion text fail with 401 and are reported as such.

Every response is cached in SQLite. Re-auditing the same document, or auditing a
second document that cites the same authorities, therefore performs no upstream
requests.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx


class CourtListenerError(RuntimeError):
    """Raised when the upstream API cannot answer a request."""

    def __init__(self, message: str, status: int | None = None, retry_after: float | None = None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


class AuthenticationRequired(CourtListenerError):
    """Raised for endpoints that need an API token."""


@dataclass
class ClientStats:
    """Counters describing what an audit actually did against the upstream API."""

    requests: int = 0
    cache_hits: int = 0
    throttle_waits: int = 0
    throttle_seconds: float = 0.0
    retries: int = 0
    errors: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "requests": self.requests,
            "cache_hits": self.cache_hits,
            "throttle_waits": self.throttle_waits,
            "throttle_seconds": round(self.throttle_seconds, 2),
            "retries": self.retries,
            "errors": self.errors,
        }


class ResponseCache:
    """SQLite-backed cache of upstream responses, keyed by request URL."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS responses (
                key TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                status INTEGER NOT NULL,
                body TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        self._conn.commit()

    @staticmethod
    def key_for(method: str, url: str, body: str | None) -> str:
        payload = f"{method}\n{url}\n{body or ''}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def get(self, key: str, max_age: float | None = None) -> Any | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT status, body, created_at FROM responses WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        status, body, created_at = row
        if max_age is not None and (time.time() - created_at) > max_age:
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None

    def put(self, key: str, url: str, status: int, payload: Any) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO responses (key, url, status, body, created_at) VALUES (?, ?, ?, ?, ?)",
                (key, url, status, json.dumps(payload), time.time()),
            )
            self._conn.commit()

    def count(self) -> int:
        with self._lock:
            return int(self._conn.execute("SELECT COUNT(*) FROM responses").fetchone()[0])

    def close(self) -> None:
        with self._lock:
            self._conn.close()


@dataclass
class CourtListenerClient:
    """Paced, cached, retrying client for the CourtListener v4 REST API."""

    token: str | None = None
    base_url: str = "https://www.courtlistener.com/api/rest/v4"
    min_interval: float = 3.6
    max_retries: int = 4
    timeout: float = 30.0
    cache: ResponseCache | None = None
    user_agent: str = "CiteProof/0.1 (+https://github.com/)"
    stats: ClientStats = field(default_factory=ClientStats)

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _last_request_at: float = field(default=0.0, repr=False)
    _client: httpx.Client | None = field(default=None, repr=False)

    # -- transport ---------------------------------------------------------

    @property
    def has_token(self) -> bool:
        return bool(self.token)

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout, follow_redirects=True)
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _throttle(self) -> None:
        """Block until at least ``min_interval`` has elapsed since the last request."""

        with self._lock:
            now = time.monotonic()
            wait = self.min_interval - (now - self._last_request_at)
            if wait > 0:
                self.stats.throttle_waits += 1
                self.stats.throttle_seconds += wait
                time.sleep(wait)
            self._last_request_at = time.monotonic()

    def request(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        json_body: Any | None = None,
        use_cache: bool = True,
    ) -> Any:
        """Perform one API request, using the cache when possible.

        Raises AuthenticationRequired for 401 and CourtListenerError for other
        failures that survive the retry budget.
        """

        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        body_json = json.dumps(json_body) if json_body is not None else None
        cache_key = ResponseCache.key_for(method, url, body_json)

        if use_cache and self.cache is not None:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self.stats.cache_hits += 1
                return cached

        headers = {"Accept": "application/json", "User-Agent": self.user_agent}
        if self.token:
            headers["Authorization"] = f"Token {self.token}"

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                if method == "POST":
                    post_headers = dict(headers)
                    if body_json is not None:
                        post_headers["Content-Type"] = "application/json"
                    response = self._http().post(url, headers=post_headers, content=body_json)
                else:
                    response = self._http().get(url, headers=headers)
            except httpx.HTTPError as exc:
                self.stats.errors += 1
                last_error = CourtListenerError(f"transport error: {exc}")
                if attempt < self.max_retries:
                    self.stats.retries += 1
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise last_error from exc

            self.stats.requests += 1

            if response.status_code == 401:
                self.stats.errors += 1
                raise AuthenticationRequired(
                    f"{path} requires an API token (HTTP 401)", status=401
                )
            if response.status_code == 429:
                retry_after = _retry_after_seconds(response)
                self.stats.errors += 1
                if attempt < self.max_retries:
                    self.stats.retries += 1
                    time.sleep(retry_after)
                    continue
                raise CourtListenerError(
                    "rate limited (HTTP 429)", status=429, retry_after=retry_after
                )
            if response.status_code >= 400:
                self.stats.errors += 1
                raise CourtListenerError(
                    f"HTTP {response.status_code} for {path}", status=response.status_code
                )

            try:
                payload = response.json()
            except ValueError as exc:
                self.stats.errors += 1
                raise CourtListenerError(f"response was not JSON for {path}") from exc

            if use_cache and self.cache is not None:
                self.cache.put(cache_key, url, response.status_code, payload)
            return payload

        raise last_error or CourtListenerError("request failed")

    # -- endpoints ---------------------------------------------------------

    def search_opinions(self, query: str, **filters: Any) -> dict[str, Any]:
        """Search the opinion corpus. Works with and without a token."""

        params: dict[str, Any] = {"q": query, "type": "o"}
        for key, value in filters.items():
            if value is not None:
                params[key] = value
        return self.request("search/", params=params)

    def citation_lookup(self, text: str) -> list[dict[str, Any]]:
        """Resolve many citations in one request. Requires a token."""

        if not self.has_token:
            raise AuthenticationRequired("citation-lookup requires an API token")
        result = self.request("citation-lookup/", method="POST", json_body={"text": text})
        if isinstance(result, list):
            return result
        return []

    def get_opinion(self, opinion_id: int | str) -> dict[str, Any]:
        """Fetch one opinion record, including its text. Requires a token."""

        if not self.has_token:
            raise AuthenticationRequired("opinion detail requires an API token")
        return self.request(f"opinions/{opinion_id}/")

    def get_cluster(self, cluster_id: int | str) -> dict[str, Any]:
        """Fetch one case cluster record. Requires a token."""

        if not self.has_token:
            raise AuthenticationRequired("cluster detail requires an API token")
        return self.request(f"clusters/{cluster_id}/")


def _retry_after_seconds(response: httpx.Response, default: float = 36.0) -> float:
    raw = response.headers.get("Retry-After")
    if not raw:
        return default
    try:
        return max(0.5, float(raw))
    except ValueError:
        return default
