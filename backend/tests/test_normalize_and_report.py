"""Tests for normalisation helpers and report rendering."""

from __future__ import annotations

from datetime import datetime, timezone

from citeproof.normalize import (
    case_name_similarity,
    citation_string_key,
    normalize_case_name,
    normalize_cite_key,
    normalize_court,
    normalize_quote,
    quote_is_distinctive,
    split_case_name,
)
from citeproof.report import to_json, to_markdown
from citeproof.schemas import (
    AuditCounts,
    AuditReport,
    ErrorClass,
    ExtractedCitation,
    Finding,
    Verdict,
)


# -- citation keys ---------------------------------------------------------


def test_citation_keys_ignore_spacing_capitalisation_and_periods():
    assert normalize_cite_key("905", "F. Supp. 2d", "121") == citation_string_key(
        "905 F. Supp. 2d 121"
    )
    assert normalize_cite_key("516", "U.S.", "217") == citation_string_key("516 U.S. 217")
    assert normalize_cite_key("925", "F.3d", "1339") == citation_string_key("925 F.3d 1339")


def test_different_citations_do_not_collide():
    assert normalize_cite_key("516", "U.S.", "217") != normalize_cite_key("516", "U.S.", "218")
    assert normalize_cite_key("516", "U.S.", "217") != normalize_cite_key("925", "F.3d", "1339")


def test_missing_parts_yield_no_key():
    assert normalize_cite_key(None, "U.S.", "217") is None
    assert normalize_cite_key("516", None, "217") is None


# -- case names ------------------------------------------------------------


def test_case_name_split():
    assert split_case_name("Zicherman v. Korean Air Lines Co.") == (
        "Zicherman",
        "Korean Air Lines Co.",
    )
    assert split_case_name("No separator here") is None


def test_case_name_similarity_accepts_a_longer_recorded_name():
    """The corpus records fuller party names than the document writes."""

    score = case_name_similarity(
        "Zicherman v. Korean Air Lines Co.",
        "Zicherman Ex Rel. Estate of Kole v. Korean Air Lines Co.",
    )
    assert score == 1.0


def test_case_name_similarity_rejects_a_shared_defendant():
    """A case that shares only the defendant is a different case.

    "Martinez v. Delta Air Lines" against the real "Lorme v. Delta Air Lines"
    must not be accepted on the strength of the shared defendant, because that is
    exactly how a fabricated case name is made to look plausible.
    """

    score = case_name_similarity("Martinez v. Delta Air Lines", "Lorme v. Delta Air Lines, Inc.")
    assert score == 0.0


def test_case_name_similarity_is_case_and_punctuation_insensitive():
    assert case_name_similarity("Bell Atl. Corp. v. Twombly", "BELL ATLANTIC CORP. v. TWOMBLY") == 1.0


def test_normalize_case_name_strips_punctuation():
    assert normalize_case_name("Monell v. Dep't of Soc. Servs.") == "monell v dep t of soc servs"


# -- quotations ------------------------------------------------------------


def test_quote_normalisation_removes_typography_and_bracketed_edits():
    assert normalize_quote("\u201cWe [so] hold\u2026 that it applies.\u201d") == "we hold that it applies"


def test_short_quotations_are_not_searched():
    assert not quote_is_distinctive('"we hold"')
    assert quote_is_distinctive('"the Warsaw Convention does not preempt state law claims"')


# -- courts ----------------------------------------------------------------


def test_court_normalisation_maps_reporters_and_written_names_together():
    assert normalize_court("11th Cir.") == normalize_court("ca11")
    assert normalize_court("9th Cir.") == "ca9"
    assert normalize_court("U.S.") == "scotus"


# -- report rendering ------------------------------------------------------


def _finding(verdict: Verdict, error: ErrorClass, name: str) -> Finding:
    return Finding(
        citation=ExtractedCitation(
            index=0,
            verbatim=f"{name}, 925 F.3d 1339 (11th Cir. 2019)",
            matched_text="925 F.3d 1339",
            case_name=name,
            volume="925",
            reporter="F.3d",
            page="1339",
            cite_key="925f3d1339",
        ),
        verdict=verdict,
        error_class=error,
        confidence=0.9,
        explanation="No case matching this name was found in the corpus.",
        advisories=["A note about the evidence."],
    )


def _report(findings: list[Finding]) -> AuditReport:
    counts = AuditCounts()
    for finding in findings:
        setattr(counts, finding.verdict.value, getattr(counts, finding.verdict.value) + 1)
    return AuditReport(
        audit_id="abc123",
        created_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
        document_title="Motion to dismiss",
        counts=counts,
        integrity_score=0.0,
        check_coverage=100.0,
        findings=findings,
        duration_ms=1234,
        api_requests=4,
        cache_hits=8,
        notes=["Method note."],
    )


def test_markdown_report_states_the_verdict_and_the_queries():
    report = _report([_finding(Verdict.FABRICATED, ErrorClass.FABRICATED_CITE, "Varghese v. China")])
    markdown = to_markdown(report)
    assert "# Citation audit: Motion to dismiss" in markdown
    assert "Not found" in markdown
    assert "the reporter citation does not exist" in markdown
    assert "A note about the evidence." in markdown
    assert "Method note." in markdown
    assert "Upstream requests: 4 made, 8 served from cache" in markdown


def test_markdown_report_escapes_pipes_in_case_names():
    report = _report([_finding(Verdict.VERIFIED, ErrorClass.NONE, "Smith | Jones v. Acme")])
    markdown = to_markdown(report)
    assert "Smith \\| Jones v. Acme" in markdown
    # The table row must still have the expected number of columns.
    row = next(line for line in markdown.splitlines() if line.startswith("| 1 |"))
    # The escaped pipe must not be counted as a column separator.
    assert row.count("|") - row.count("\\|") == 6
    assert "Smith \\| Jones" in row


def test_markdown_report_handles_a_document_with_no_citations():
    markdown = to_markdown(_report([]))
    assert "No case citations were found in this document." in markdown


def test_json_report_is_serialisable():
    payload = to_json(_report([_finding(Verdict.MISCITED, ErrorClass.WRONG_SLOT, "Ehrlich v. AA")]))
    assert payload["audit_id"] == "abc123"
    assert payload["findings"][0]["verdict"] == "miscited"
    assert isinstance(payload["created_at"], str)
