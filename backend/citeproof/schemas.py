"""Data models shared by the extraction engine, the verification engine, and the API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class CitationKind(str, Enum):
    """What kind of authority a citation string refers to."""

    CASE = "case"
    STATUTE = "statute"
    REGULATION = "regulation"
    JOURNAL = "journal"
    OTHER = "other"


class Verdict(str, Enum):
    """Outcome of checking one citation against the case-law corpus."""

    VERIFIED = "verified"
    FABRICATED = "fabricated"
    MISCITED = "miscited"
    UNVERIFIABLE = "unverifiable"


class ErrorClass(str, Enum):
    """Specific defect, used to explain a non-verified verdict."""

    NONE = "none"
    FABRICATED_CITE = "fabricated_cite"
    FABRICATED_CASE_NAME = "fabricated_case_name"
    WRONG_SLOT = "wrong_slot"
    WRONG_COURT = "wrong_court"
    WRONG_YEAR = "wrong_year"
    QUOTE_NOT_FOUND = "quote_not_found"
    MISCHARACTERIZED = "mischaracterized"
    NOT_CHECKED = "not_checked"


class QuoteStatus(str, Enum):
    """Outcome of checking quoted language attributed to an authority.

    ``verbatim``, ``variant`` and ``not_found`` mean the quotation was compared
    against the text of the cited authority itself. ``corpus_hit`` and
    ``corpus_miss`` mean only a corpus-wide phrase search was possible, which
    establishes whether the phrase occurs anywhere in the indexed corpus but not
    whether it comes from the cited authority.
    """

    VERBATIM = "verbatim"
    VARIANT = "variant"
    NOT_FOUND = "not_found"
    CORPUS_HIT = "corpus_hit"
    CORPUS_MISS = "corpus_miss"
    SKIPPED = "skipped"


class SupportLevel(str, Enum):
    """Whether the cited authority supports the proposition it is cited for."""

    SUPPORTED = "supported"
    PARTIAL = "partial"
    NOT_SUPPORTED = "not_supported"
    CONTRADICTED = "contradicted"
    UNKNOWN = "unknown"


class ResolvedCase(BaseModel):
    """A case record returned by the upstream case-law corpus."""

    case_name: str
    cluster_id: int | None = None
    court: str | None = None
    date_filed: str | None = None
    citations: list[str] = Field(default_factory=list)
    absolute_url: str | None = None
    snippet: str | None = None
    source: Literal["cite_search", "name_search", "citation_lookup", "opinion_text"] = "cite_search"


class Evidence(BaseModel):
    """One upstream query and what it returned. Kept so every verdict is inspectable."""

    strategy: str
    query: str
    result_count: int
    matched: bool = False
    top: ResolvedCase | None = None
    note: str | None = None


class QuoteCheck(BaseModel):
    """Result of checking a quotation attributed to a cited authority."""

    text: str
    status: QuoteStatus
    hits: int | None = None
    matched_case: str | None = None
    detail: str | None = None


class FidelityCheck(BaseModel):
    """Result of asking an LLM whether the cited authority supports the proposition."""

    support: SupportLevel
    confidence: float | None = None
    rationale: str | None = None
    model: str | None = None
    passage: str | None = None


class ExtractedCitation(BaseModel):
    """One distinct authority referenced by the document, with its positions."""

    index: int
    verbatim: str = Field(description="The citation as written, including the case name.")
    matched_text: str = Field(description="The reporter citation portion, e.g. '925 F.3d 1339'.")
    kind: CitationKind = CitationKind.CASE
    volume: str | None = None
    reporter: str | None = None
    page: str | None = None
    pin_cite: str | None = None
    court: str | None = None
    court_id: str | None = Field(
        default=None,
        description=(
            "CourtListener court identifier resolved from the reporter abbreviation, such as "
            "'scotus' or 'ca11'. Usable as a search filter."
        ),
    )
    court_source: Literal["document", "reporter"] | None = Field(
        default=None,
        description=(
            "'document' when the court was written on the citation, 'reporter' when it was "
            "inferred from the reporter abbreviation. Only a written court can disagree with "
            "the corpus record."
        ),
    )
    year: str | None = None
    case_name: str | None = None
    plaintiff: str | None = None
    defendant: str | None = None
    parenthetical: str | None = None
    cite_key: str | None = Field(
        default=None, description="Normalised 'volume reporter page' used for exact slot matching."
    )
    spans: list[tuple[int, int]] = Field(default_factory=list)
    occurrence_count: int = 1
    context: str = Field(default="", description="Sentence containing the citation, plus the one before.")
    extraction_notes: list[str] = Field(
        default_factory=list,
        description="Disagreements between the citation parser and the document text, recorded so they stay visible.",
    )


class Finding(BaseModel):
    """Verification result for one extracted citation."""

    citation: ExtractedCitation
    verdict: Verdict
    error_class: ErrorClass
    confidence: float = 0.0
    explanation: str = ""
    resolved_case: ResolvedCase | None = None
    slot_owner: ResolvedCase | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    quote_check: QuoteCheck | None = None
    fidelity: FidelityCheck | None = None
    suggestion: str | None = None
    advisories: list[str] = Field(
        default_factory=list,
        description="Secondary observations that do not change the verdict, such as a year mismatch.",
    )


class AuditCounts(BaseModel):
    """Aggregate tallies for one audit."""

    verified: int = 0
    fabricated: int = 0
    miscited: int = 0
    unverifiable: int = 0

    @property
    def total(self) -> int:
        return self.verified + self.fabricated + self.miscited + self.unverifiable

    @property
    def checkable(self) -> int:
        """Citations the corpus could actually adjudicate."""

        return self.verified + self.fabricated + self.miscited


class AuditReport(BaseModel):
    """Complete output of auditing one document."""

    audit_id: str
    created_at: datetime
    document_title: str | None = None
    access_mode: Literal["token", "anonymous"] = "anonymous"
    counts: AuditCounts = Field(default_factory=AuditCounts)
    statute_count: int = 0
    integrity_score: float | None = Field(
        default=None,
        description="Percentage of checkable citations that resolved correctly. None when nothing was checkable.",
    )
    check_coverage: float | None = Field(
        default=None,
        description="Percentage of extracted citations the corpus could adjudicate.",
    )
    findings: list[Finding] = Field(default_factory=list)
    duration_ms: int = 0
    api_requests: int = 0
    cache_hits: int = 0
    notes: list[str] = Field(default_factory=list)


class AuditRequest(BaseModel):
    """Request body for POST /api/audits."""

    text: str | None = None
    document_title: str | None = None
    deep: bool = Field(
        default=False,
        description="Also run the quotation check and the LLM proposition-fidelity check.",
    )


class AuditSummary(BaseModel):
    """Progress record for an audit job, polled by the client."""

    audit_id: str
    status: Literal["queued", "extracting", "verifying", "checking", "done", "failed"]
    progress: float = 0.0
    message: str = ""
    citations_total: int = 0
    citations_done: int = 0
    error: str | None = None
    report: AuditReport | None = None
