"""Shared test fixtures.

The verification engine is tested against a stub corpus rather than the live
CourtListener API, so the tests are deterministic, run without network access,
and can assert on the exact queries the engine issued.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from citeproof.courtlistener import AuthenticationRequired, CourtListenerError  # noqa: E402
from citeproof.extract import extract_citations  # noqa: E402


class FakeStats:
    def __init__(self) -> None:
        self.requests = 0
        self.cache_hits = 0
        self.throttle_waits = 0
        self.throttle_seconds = 0.0
        self.retries = 0
        self.errors = 0


class FakeCorpus:
    """A stub CourtListener client holding canned search results.

    ``responses`` maps a query string to the list of result dictionaries it
    returns. A query may also be keyed by ``(query, court)`` to model the
    court-filtered search. Queries absent from the mapping return no results,
    which is how the stub models a case that does not exist.
    """

    def __init__(
        self,
        responses: dict[Any, list[dict[str, Any]]] | None = None,
        token: str | None = None,
        failing: set[str] | None = None,
    ) -> None:
        self.responses = responses or {}
        self.token = token
        self.failing = failing or set()
        self.stats = FakeStats()
        self.queries: list[tuple[str, dict[str, Any]]] = []

    @property
    def has_token(self) -> bool:
        return bool(self.token)

    def search_opinions(self, query: str, **filters: Any) -> dict[str, Any]:
        self.queries.append((query, dict(filters)))
        self.stats.requests += 1
        if query in self.failing:
            raise CourtListenerError("stub corpus failure")
        court = filters.get("court")
        if (query, court) in self.responses:
            return {"results": self.responses[(query, court)]}
        if query in self.responses:
            return {"results": self.responses[query]}
        # A key ending in '*' matches any query that starts with the key's stem.
        # The passage-retrieval query appends terms taken from the citing
        # sentence, so its exact text is not known before the engine builds it.
        for key, results in self.responses.items():
            if isinstance(key, str) and key.endswith("*") and query.startswith(key[:-1]):
                return {"results": results}
        return {"results": []}

    def get_cluster(self, cluster_id: int | str) -> dict[str, Any]:
        raise AuthenticationRequired("the stub corpus holds no opinion text")

    def get_opinion(self, opinion_id: int | str) -> dict[str, Any]:
        raise AuthenticationRequired("the stub corpus holds no opinion text")

    def close(self) -> None:
        return None


def case_result(
    cluster_id: int,
    name: str,
    citations: list[str],
    court: str | None = None,
    date_filed: str | None = None,
    snippet: str | None = None,
) -> dict[str, Any]:
    """Build one search result in the shape the real API returns."""

    return {
        "cluster_id": cluster_id,
        "caseName": name,
        "caseNameFull": name,
        "citation": citations,
        "court_citation_string": court,
        "court": court,
        "dateFiled": date_filed,
        "absolute_url": f"/opinion/{cluster_id}/x/",
        "opinions": [{"snippet": snippet or ""}],
    }


@pytest.fixture
def extract():
    def _extract(text: str):
        return extract_citations(text)

    return _extract


class FakeLanguageModel:
    """A stub model that records what it was asked to judge."""

    def __init__(self, result=None) -> None:
        from citeproof.schemas import FidelityCheck, SupportLevel

        self.calls: list[dict[str, Any]] = []
        self.enabled = True
        self.model = "stub-model"
        self._result = result or FidelityCheck(
            support=SupportLevel.SUPPORTED, confidence=0.9, rationale="stub rationale"
        )

    def assess_support(self, sentence: str, case_name: str | None, passage: str | None, citation: str | None = None):
        self.calls.append(
            {"sentence": sentence, "case_name": case_name, "passage": passage, "citation": citation}
        )
        return self._result
