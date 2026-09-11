"""Runtime configuration, read from environment variables.

Every setting has a working default so the application starts with no
configuration at all. The two settings that change behaviour materially are
``COURTLISTENER_TOKEN`` (upstream rate limit and access to opinion text) and
``CITEPROOF_LLM_API_KEY`` (enables the proposition-fidelity check).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Anonymous CourtListener requests were measured at roughly 10 requests per
# 36-second window, after which the API answers 429 with Retry-After: 36.
DEFAULT_ANON_INTERVAL = 3.6
# Authenticated requests are not throttled at that level; this pacing only
# exists to stay well inside the documented daily allowance.
DEFAULT_TOKEN_INTERVAL = 0.15


def _load_dotenv(path: Path) -> None:
    """Populate os.environ from a .env file without overriding real env vars."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_float(name: str, default: float) -> float:
    raw = _env(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass
class Settings:
    courtlistener_token: str = ""
    courtlistener_base_url: str = "https://www.courtlistener.com/api/rest/v4"
    cache_path: Path = field(default_factory=lambda: REPO_ROOT / "data" / "cache" / "cache.sqlite")
    min_interval_token: float = DEFAULT_TOKEN_INTERVAL
    min_interval_anon: float = DEFAULT_ANON_INTERVAL
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    request_timeout: float = 30.0
    max_retries: int = 4

    @property
    def has_token(self) -> bool:
        return bool(self.courtlistener_token)

    @property
    def has_llm(self) -> bool:
        return bool(self.llm_api_key)

    @property
    def access_mode(self) -> str:
        return "token" if self.has_token else "anonymous"

    @property
    def min_interval(self) -> float:
        return self.min_interval_token if self.has_token else self.min_interval_anon


def load_settings(env_file: Path | None = None) -> Settings:
    _load_dotenv(env_file or (REPO_ROOT / ".env"))
    cache_raw = _env("CITEPROOF_CACHE_PATH")
    cache_path = Path(cache_raw) if cache_raw else REPO_ROOT / "data" / "cache" / "cache.sqlite"
    if not cache_path.is_absolute():
        cache_path = REPO_ROOT / cache_path
    return Settings(
        courtlistener_token=_env("COURTLISTENER_TOKEN"),
        courtlistener_base_url=_env(
            "COURTLISTENER_BASE_URL", "https://www.courtlistener.com/api/rest/v4"
        ).rstrip("/"),
        cache_path=cache_path,
        min_interval_token=_env_float("CITEPROOF_MIN_INTERVAL_TOKEN", DEFAULT_TOKEN_INTERVAL),
        min_interval_anon=_env_float("CITEPROOF_MIN_INTERVAL_ANON", DEFAULT_ANON_INTERVAL),
        llm_api_key=_env("CITEPROOF_LLM_API_KEY"),
        llm_base_url=_env("CITEPROOF_LLM_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        llm_model=_env("CITEPROOF_LLM_MODEL", "deepseek-chat"),
    )
