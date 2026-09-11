"""Render an audit report as Markdown or JSON.

The Markdown form is the artifact a reviewer reads. It states the verdict for
every citation together with the queries that produced it, so a reader can
reproduce the check rather than take the verdict on trust.
"""

from __future__ import annotations

from typing import Any

from .schemas import AuditReport, ErrorClass, Finding, QuoteStatus, Verdict

_VERDICT_LABEL = {
    Verdict.VERIFIED: "Verified",
    Verdict.FABRICATED: "Not found",
    Verdict.MISCITED: "Miscited",
    Verdict.UNVERIFIABLE: "Not checked",
}

_ERROR_LABEL = {
    ErrorClass.NONE: "none",
    ErrorClass.FABRICATED_CITE: "the reporter citation does not exist",
    ErrorClass.FABRICATED_CASE_NAME: "the case name does not exist",
    ErrorClass.WRONG_SLOT: "the reporter citation belongs to another case",
    ErrorClass.WRONG_COURT: "court does not match the record",
    ErrorClass.WRONG_YEAR: "year does not match the record",
    ErrorClass.QUOTE_NOT_FOUND: "the quoted language is not in the source",
    ErrorClass.MISCHARACTERIZED: "the authority does not support the proposition",
    ErrorClass.NOT_CHECKED: "not checked",
}

_QUOTE_LABEL = {
    QuoteStatus.VERBATIM: "appears in the cited authority",
    QuoteStatus.VARIANT: "similar wording only",
    QuoteStatus.NOT_FOUND: "does not appear in the cited authority",
    QuoteStatus.CORPUS_HIT: "found elsewhere in the corpus",
    QuoteStatus.CORPUS_MISS: "not found anywhere in the corpus",
    QuoteStatus.SKIPPED: "not checked",
}

_SUPPORT_LABEL = {
    "supported": "the authority supports the proposition",
    "partial": "the authority supports the proposition in part",
    "not_supported": "the authority does not support the proposition",
    "contradicted": "the authority states the opposite",
    "unknown": "not determined",
}


def _escape(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _citation_label(finding: Finding) -> str:
    citation = finding.citation
    return _escape(citation.case_name or citation.verbatim or citation.matched_text)


def _counts_line(report: AuditReport) -> str:
    counts = report.counts
    return (
        f"{counts.total} case citation(s): {counts.verified} verified, "
        f"{counts.fabricated} not found, {counts.miscited} miscited, "
        f"{counts.unverifiable} not checked"
    )


def to_markdown(report: AuditReport) -> str:
    """Render the full report as Markdown."""

    lines: list[str] = []
    lines.append(f"# Citation audit: {report.document_title or 'untitled document'}")
    lines.append("")
    lines.append(f"- Audit id: `{report.audit_id}`")
    lines.append(f"- Run at: {report.created_at.isoformat(timespec='seconds')}")
    lines.append(
        f"- Case-law access: {'authenticated' if report.access_mode == 'token' else 'anonymous'}"
    )
    lines.append(
        f"- Results: {_counts_line(report)}"
        + (f", {report.statute_count} non-case citation(s) listed but not checked" if report.statute_count else "")
    )
    if report.integrity_score is not None:
        lines.append(
            f"- Citation integrity: **{report.integrity_score}%** of the "
            f"{report.counts.checkable} citation(s) the corpus could adjudicate"
        )
    if report.check_coverage is not None:
        lines.append(f"- Coverage: {report.check_coverage}% of extracted citations were adjudicable")
    lines.append(
        f"- Upstream requests: {report.api_requests} made, {report.cache_hits} served from cache, "
        f"{report.duration_ms} ms elapsed"
    )
    lines.append("")

    if not report.findings:
        lines.append("No case citations were found in this document.")
        return "\n".join(lines) + "\n"

    lines.append("## Findings")
    lines.append("")
    lines.append("| # | Citation | Verdict | Issue | Confidence |")
    lines.append("|---|----------|---------|-------|------------|")
    for position, finding in enumerate(report.findings, start=1):
        lines.append(
            f"| {position} | {_citation_label(finding)} {_escape(finding.citation.matched_text)} "
            f"| {_VERDICT_LABEL[finding.verdict]} "
            f"| {_ERROR_LABEL[finding.error_class]} "
            f"| {finding.confidence:.2f} |"
        )
    lines.append("")

    lines.append("## Detail")
    lines.append("")
    for position, finding in enumerate(report.findings, start=1):
        citation = finding.citation
        lines.append(f"### {position}. {_citation_label(finding)}")
        lines.append("")
        lines.append(f"- As written: `{citation.verbatim}`")
        if citation.occurrence_count > 1:
            lines.append(f"- References: {citation.occurrence_count}")
        lines.append(f"- Verdict: **{_VERDICT_LABEL[finding.verdict]}** ({_ERROR_LABEL[finding.error_class]})")
        lines.append(f"- {finding.explanation}")
        if finding.resolved_case:
            resolved = finding.resolved_case
            recorded = "".join(
                f"\n  - {value}"
                for value in [
                    f"Case: {resolved.case_name}",
                    f"Citations recorded by the corpus: {', '.join(resolved.citations) or 'none'}",
                    f"Court: {resolved.court or 'unknown'}",
                    f"Decided: {resolved.date_filed or 'unknown'}",
                    f"Source: {resolved.absolute_url}" if resolved.absolute_url else "",
                ]
                if value
            )
            lines.append(f"- Resolved to:{recorded}")
        if finding.slot_owner:
            lines.append(
                f"- The cited reporter citation belongs to: {finding.slot_owner.case_name}"
            )
        if finding.suggestion:
            lines.append(f"- Likely correct citation: {finding.suggestion}")
        if finding.quote_check:
            quote = finding.quote_check
            lines.append(
                f"- Quotation: {_QUOTE_LABEL[quote.status]}"
                + (f" ({quote.hits} corpus matches)" if quote.hits is not None else "")
            )
            if quote.detail:
                lines.append(f"  - {quote.detail}")
        if finding.fidelity:
            fidelity = finding.fidelity
            lines.append(
                f"- Support for the proposition: {_SUPPORT_LABEL.get(fidelity.support.value, fidelity.support.value)}"
                + (f" (confidence {fidelity.confidence:.2f})" if fidelity.confidence is not None else "")
            )
            if fidelity.rationale:
                lines.append(f"  - {fidelity.rationale}")
            if fidelity.passage:
                lines.append(f"  - Passage relied on: \u201c{fidelity.passage}\u201d")
        for advisory in finding.advisories:
            lines.append(f"- Note: {advisory}")
        if finding.evidence:
            lines.append("- Queries run:")
            for item in finding.evidence:
                lines.append(
                    f"  - `{item.query}` returned {item.result_count} result(s)"
                    + (f"; {item.note}" if item.note else "")
                )
        lines.append("")

    if report.notes:
        lines.append("## Method and limitations")
        lines.append("")
        for note in report.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)


def to_json(report: AuditReport) -> dict[str, Any]:
    """Render the report as a JSON-serialisable dictionary."""

    return report.model_dump(mode="json")
