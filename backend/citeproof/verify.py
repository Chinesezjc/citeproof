"""Verify extracted citations against the case-law corpus.

The verdict for each citation is decided primarily by whether the case *name* is
present in the corpus, because the corpus indexes case names for every opinion
it holds. The reporter citation is used as corroboration, because the corpus
does not record a reporter citation for every opinion: public-domain and neutral
citations such as "2013 IL App (1st) 111279-U" are frequently absent from the
citation field even when the case is present. Where the citation format is one
the corpus indexes unreliably, the slot check is not allowed to decide the
verdict on its own and the reduced confidence is stated in the finding.

A case that cannot be found is not automatically reported as fabricated. Every
finding carries the queries that were run and their result counts, so a reader
can see which evidence produced the verdict.
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from .courtlistener import AuthenticationRequired, CourtListenerClient, CourtListenerError
from .extract import extract_citations, quote_from, split_by_kind
from .llm import LLMClient
from .normalize import (
    case_name_similarity,
    citation_string_key,
    normalize_court,
    normalize_quote,
    quote_is_distinctive,
)
from .schemas import (
    AuditCounts,
    AuditReport,
    CitationKind,
    ErrorClass,
    Evidence,
    ExtractedCitation,
    FidelityCheck,
    Finding,
    QuoteCheck,
    QuoteStatus,
    ResolvedCase,
    SupportLevel,
    Verdict,
)

# A case name matching this well on both parties is treated as the cited case.
NAME_MATCH_THRESHOLD = 0.8
# A weaker name match is still accepted when the cited reporter slot resolves to
# the same case, because name variance in the document then explains the gap.
NAME_ACCEPT_WITH_CITE_THRESHOLD = 0.5

# Citation formats the corpus does not record reliably in its citation field.
_REPORTERS_WITH_PARTIAL_COVERAGE = {"WL", "LEXIS", "US App Lexis"}

_PUBLIC_DOMAIN_VOLUME = re.compile(r"^(19|20)\d{2}$")
_HTML_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]{2,}")
_STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "under", "which",
    "court", "case", "held", "holding", "shall", "have", "been", "were", "was",
    "are", "not", "but", "its", "any", "all", "such", "than", "then", "them",
    "there", "their", "these", "those", "into", "upon", "over", "also", "may",
    "must", "does", "did", "has", "had", "would", "could", "should", "state",
    "states", "united", "section", "plaintiff", "defendant",
}


@dataclass
class VerifierOptions:
    """What the audit should attempt beyond the existence check."""

    check_quotes: bool = True
    check_support: bool = False
    progress: Callable[[str, float], None] | None = None


@dataclass
class _SearchOutcome:
    query: str
    results: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    @property
    def failed(self) -> bool:
        return self.error is not None


def _strip_html(value: str) -> str:
    return _WS.sub(" ", _HTML_TAG.sub(" ", value)).strip()


def _resolved_from(result: dict[str, Any], source: str) -> ResolvedCase:
    raw_citations = result.get("citation") or []
    if isinstance(raw_citations, str):
        raw_citations = [raw_citations]
    snippet = None
    opinions = result.get("opinions") or []
    if opinions and isinstance(opinions, list):
        snippet = opinions[0].get("snippet")
    if snippet:
        snippet = _WS.sub(" ", str(snippet)).strip()
    absolute = result.get("absolute_url")
    if absolute and absolute.startswith("/"):
        absolute = f"https://www.courtlistener.com{absolute}"
    return ResolvedCase(
        case_name=(result.get("caseNameFull") or result.get("caseName") or "").strip(),
        cluster_id=result.get("cluster_id"),
        court=result.get("court_citation_string") or result.get("court") or None,
        date_filed=result.get("dateFiled") or None,
        citations=[str(c) for c in raw_citations],
        absolute_url=absolute,
        snippet=snippet,
        source=source,  # type: ignore[arg-type]
    )


def _slot_check_reliable(citation: ExtractedCitation) -> tuple[bool, str | None]:
    """Whether absence of a reporter citation is meaningful for this format.

    CourtListener records reporter citations for the standard federal, regional
    and state reporters, but not for public-domain and neutral citations whose
    volume is a year ("2013 IL App (1st) 111279-U") or for Westlaw-only
    citations, whose coverage is partial.
    """

    if not citation.cite_key:
        return False, "the document gives no reporter citation to check"
    reporter = (citation.reporter or "").strip()
    # The Westlaw and Lexis reporters are checked before the year-volume test
    # below, because their volume number is the year of decision and would
    # otherwise be mistaken for a public-domain citation.
    if reporter in _REPORTERS_WITH_PARTIAL_COVERAGE:
        return False, (
            f"{reporter} citations are only partially indexed by the corpus, so the absence of "
            "this citation is weak evidence; the case name is the primary evidence"
        )
    if citation.volume and _PUBLIC_DOMAIN_VOLUME.match(citation.volume):
        return False, (
            f"'{citation.matched_text}' uses a public-domain citation format, which the "
            "corpus does not record in its citation field; the case name is the only evidence available"
        )
    return True, None


def _year_from_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(19|20)\d{2}", value)
    return match.group(0) if match else None


def _select_passage(full_text: str, sentence: str, max_chars: int = 3500) -> str | None:
    """Pick the passages of an authority most likely to address the sentence.

    Retrieval is lexical: paragraphs are scored by the number of distinct content
    words they share with the citing sentence. The highest scoring paragraphs are
    returned in document order.
    """

    if not full_text:
        return None
    terms = {t.lower() for t in _WORD.findall(sentence)} - _STOPWORDS
    paragraphs = [p for p in re.split(r"\n{2,}|(?<=\.)\s{2,}", full_text) if p.strip()]
    if not paragraphs:
        paragraphs = [full_text]
    if not terms:
        return full_text[:max_chars]

    scored: list[tuple[float, int, str]] = []
    for position, paragraph in enumerate(paragraphs):
        if len(paragraph) < 60:
            continue
        words = {t.lower() for t in _WORD.findall(paragraph)}
        overlap = len(terms & words)
        if overlap == 0:
            continue
        scored.append((overlap / max(1, len(terms)), position, paragraph.strip()))
    if not scored:
        return full_text[:max_chars]

    scored.sort(key=lambda item: (-item[0], item[1]))
    chosen = sorted(scored[:3], key=lambda item: item[1])
    passage = "\n\n".join(text for _, _, text in chosen)
    return passage[:max_chars]


class CitationVerifier:
    """Runs an audit over a document and produces findings for each citation."""

    def __init__(
        self,
        client: CourtListenerClient,
        llm: LLMClient | None = None,
        options: VerifierOptions | None = None,
    ) -> None:
        self.client = client
        self.llm = llm
        self.options = options or VerifierOptions()

    # -- upstream helpers --------------------------------------------------

    def _search(self, query: str, **filters: Any) -> _SearchOutcome:
        try:
            payload = self.client.search_opinions(query, **filters)
        except AuthenticationRequired:
            return _SearchOutcome(query=query, error="authentication required")
        except CourtListenerError as exc:
            return _SearchOutcome(query=query, error=str(exc))
        results = payload.get("results") if isinstance(payload, dict) else None
        return _SearchOutcome(query=query, results=list(results or []))

    def _case_text(self, cluster_id: int | None) -> tuple[str | None, str | None]:
        """Full text of a case and the reason it was unavailable, if it was."""

        if cluster_id is None:
            return None, "no case record was resolved"
        try:
            cluster = self.client.get_cluster(cluster_id)
        except AuthenticationRequired:
            return None, "reading opinion text requires an API token"
        except CourtListenerError as exc:
            return None, f"the case record could not be read: {exc}"

        texts: list[str] = []
        for url in (cluster.get("sub_opinions") or [])[:4]:
            match = re.search(r"/opinions/(\d+)/", str(url))
            if not match:
                continue
            try:
                opinion = self.client.get_opinion(match.group(1))
            except (AuthenticationRequired, CourtListenerError):
                continue
            for key in ("plain_text", "html_with_citations", "html", "html_lawbox", "xml_harvard"):
                value = opinion.get(key)
                if value:
                    texts.append(_strip_html(str(value[:400000])))
                    break
        if not texts:
            return None, "the corpus holds no text for this case"
        return "\n\n".join(texts), None

    # -- checks ------------------------------------------------------------

    def check_quote(
        self,
        citation: ExtractedCitation,
        resolved: ResolvedCase | None,
    ) -> QuoteCheck | None:
        """Check the quoted language attributed to a cited authority."""

        quote = quote_from(citation)
        if not quote:
            return None
        if not quote_is_distinctive(quote):
            return QuoteCheck(
                text=citation.parenthetical or "",
                status=QuoteStatus.SKIPPED,
                detail="The quotation is too short for a search to distinguish it from ordinary wording.",
            )

        if resolved is not None and self.client.has_token:
            full_text, reason = self._case_text(resolved.cluster_id)
            if full_text:
                normalized_source = normalize_quote(full_text)
                if quote in normalized_source:
                    return QuoteCheck(
                        text=citation.parenthetical or "",
                        status=QuoteStatus.VERBATIM,
                        matched_case=resolved.case_name,
                        detail="The quoted language appears in the text of the cited authority.",
                    )
                variant = self._closest_window(normalized_source, quote)
                if variant is not None:
                    return QuoteCheck(
                        text=citation.parenthetical or "",
                        status=QuoteStatus.VARIANT,
                        matched_case=resolved.case_name,
                        detail=(
                            "The cited authority contains similar wording, but not the quotation as written: "
                            f"\u201c{variant}\u201d"
                        ),
                    )
                return QuoteCheck(
                    text=citation.parenthetical or "",
                    status=QuoteStatus.NOT_FOUND,
                    matched_case=resolved.case_name,
                    detail="The quoted language does not appear in the text of the cited authority.",
                )
            detail = reason or "the text of the cited authority was unavailable"
        else:
            detail = "the text of the cited authority could not be read, so the quotation was only searched across the corpus"

        words = (citation.parenthetical or "").strip().strip('"\u201c\u201d').split()
        phrase = " ".join(words[:12])
        outcome = self._search(f'"{phrase}"')
        if outcome.failed:
            return QuoteCheck(
                text=citation.parenthetical or "",
                status=QuoteStatus.SKIPPED,
                detail=f"The quotation could not be searched: {outcome.error}",
            )
        if not outcome.results:
            return QuoteCheck(
                text=citation.parenthetical or "",
                status=QuoteStatus.CORPUS_MISS,
                hits=0,
                detail=(
                    "No opinion in the indexed corpus contains this phrase. " + detail
                ),
            )
        top = _resolved_from(outcome.results[0], "cite_search")
        return QuoteCheck(
            text=citation.parenthetical or "",
            status=QuoteStatus.CORPUS_HIT,
            hits=len(outcome.results),
            matched_case=top.case_name,
            detail=(
                f"The phrase occurs in the corpus ({len(outcome.results)} matching opinions), "
                "but it was not compared against the cited authority's own text. " + detail
            ),
        )

    @staticmethod
    def _closest_window(source: str, quote: str) -> str | None:
        """The part of the source that best resembles a quotation, if any does."""

        quote_words = quote.split()
        if len(quote_words) < 5:
            return None
        width = len(quote_words)
        source_words = source.split()
        if len(source_words) < width:
            return None
        anchor = " ".join(quote_words[:6])
        position = source.find(anchor)
        if position == -1:
            anchor = " ".join(quote_words[:4])
            position = source.find(anchor)
            if position == -1:
                return None
        window = " ".join(source[position:].split()[:width])
        return window or None

    def check_support(
        self,
        citation: ExtractedCitation,
        resolved: ResolvedCase | None,
    ) -> FidelityCheck | None:
        """Ask the model whether the cited authority supports the proposition."""

        if self.llm is None or not self.llm.enabled:
            return None
        if resolved is None:
            return FidelityCheck(
                support=SupportLevel.UNKNOWN,
                rationale="No case record was resolved for this citation, so no passage could be reviewed.",
                model=self.llm.model,
            )

        passage: str | None = None
        if self.client.has_token:
            full_text, _ = self._case_text(resolved.cluster_id)
            if full_text:
                passage = _select_passage(full_text, citation.context)

        if not passage:
            terms = " ".join(
                sorted({t for t in _WORD.findall(citation.context) if t.lower() not in _STOPWORDS})[:8]
            )
            query = f'"{resolved.case_name}" AND ({terms})' if terms else f'"{resolved.case_name}"'
            outcome = self._search(query)
            if not outcome.failed and outcome.results:
                candidate = _resolved_from(outcome.results[0], "cite_search")
                passage = candidate.snippet

        if not passage:
            return FidelityCheck(
                support=SupportLevel.UNKNOWN,
                rationale="No passage from the cited authority was available to review.",
                model=self.llm.model,
            )
        return self.llm.assess_support(
            sentence=citation.context,
            case_name=resolved.case_name or citation.case_name,
            passage=passage,
            citation=citation.matched_text,
        )

    # -- verification ------------------------------------------------------

    def verify_citation(self, citation: ExtractedCitation) -> Finding:
        advisories = list(citation.extraction_notes)
        evidence: list[Evidence] = []

        slot_reliable, slot_note = _slot_check_reliable(citation)
        if slot_note:
            advisories.append(slot_note)

        name_outcome = _SearchOutcome(query="")
        if citation.case_name:
            name_outcome = self._search(f'"{citation.case_name}"')
            best_overall: ResolvedCase | None = None
            best_score = 0.0
            for result in name_outcome.results:
                candidate = _resolved_from(result, "name_search")
                score = case_name_similarity(citation.case_name, candidate.case_name)
                if score > best_score:
                    best_score, best_overall = score, candidate
            evidence.append(
                Evidence(
                    strategy="case_name_search",
                    query=name_outcome.query,
                    result_count=len(name_outcome.results),
                    matched=best_score >= NAME_MATCH_THRESHOLD,
                    top=best_overall,
                    note=name_outcome.error
                    or (f"closest name match scored {best_score:.2f}" if name_outcome.results else "no results"),
                )
            )
        else:
            advisories.append("The document gives no case name for this citation, so only the reporter citation was checked.")

        cite_outcome = _SearchOutcome(query="")
        cite_evidence_index: int | None = None
        if citation.cite_key and citation.matched_text:
            cite_outcome = self._search(f'"{citation.matched_text}"')
            evidence.append(
                Evidence(
                    strategy="reporter_citation_search",
                    query=cite_outcome.query,
                    result_count=len(cite_outcome.results),
                    matched=False,
                    top=None,
                    note=cite_outcome.error
                    or "results were cross-checked against their recorded citation lists",
                )
            )
            cite_evidence_index = len(evidence) - 1

        # A case holds the cited reporter citation when any record returned by
        # either query lists that citation. Both result sets are used, because a
        # phrase search for a citation returns the opinions that cite the
        # authority as well as the authority itself, and because one dispute can
        # produce several records whose citation lists differ: a certiorari grant
        # and the later decision on the merits are separate records with separate
        # citations ("429 U.S. 1071" and "436 U.S. 658" for Monell, for example).
        # Reading only the citation search would miss the record that actually
        # holds the citation.
        slot_owners: list[ResolvedCase] = []
        if citation.cite_key:
            seen_owners: set[Any] = set()
            for result in list(name_outcome.results) + list(cite_outcome.results):
                candidate = _resolved_from(result, "cite_search")
                if candidate.cluster_id in seen_owners:
                    continue
                if any(citation_string_key(c) == citation.cite_key for c in candidate.citations):
                    seen_owners.add(candidate.cluster_id)
                    slot_owners.append(candidate)
            if cite_evidence_index is not None:
                entry = evidence[cite_evidence_index]
                entry.matched = bool(slot_owners)
                entry.top = slot_owners[0] if slot_owners else None
                entry.note = (
                    f"{len(slot_owners)} case record(s) list this exact reporter citation"
                    if slot_owners
                    else cite_outcome.error
                    or "no case record returned by either query lists this exact reporter citation"
                )

        # Every record the name search returned that matches the cited name. One
        # dispute produces several records with different reporter citations: a
        # district decision, a circuit decision, a certiorari grant and the
        # decision on the merits are separate records with separate citations
        # ("429 U.S. 1071" and "436 U.S. 658" for Monell, for example). All of
        # them are collected, because the document may mean any of them.
        litigation_records: list[ResolvedCase] = []
        if citation.case_name:
            for result in name_outcome.results:
                candidate = _resolved_from(result, "name_search")
                if (
                    case_name_similarity(citation.case_name, candidate.case_name)
                    >= NAME_MATCH_THRESHOLD
                ):
                    litigation_records.append(candidate)

        slot_name_match: ResolvedCase | None = None
        slot_name_score = 0.0
        if citation.case_name:
            for owner in slot_owners:
                score = case_name_similarity(citation.case_name, owner.case_name)
                if score >= NAME_ACCEPT_WITH_CITE_THRESHOLD and score > slot_name_score:
                    slot_name_match, slot_name_score = owner, score

        if slot_name_match is not None and slot_name_score < NAME_MATCH_THRESHOLD:
            advisories.append(
                f"The cited name {citation.case_name!r} differs from the name the corpus "
                f"records for this citation ({slot_name_match.case_name!r})."
            )

        # The record of this case that best agrees with the court and year the
        # document asserts. It is used for display and for the court comparison.
        def _affinity(record: ResolvedCase) -> int:
            score = 0
            if citation.court_source == "document" and citation.court and record.court:
                if normalize_court(citation.court) == normalize_court(record.court):
                    score += 2
            record_year = _year_from_date(record.date_filed)
            if citation.year and record_year and citation.year == record_year:
                score += 1
            return score

        name_match: ResolvedCase | None = None
        if litigation_records:
            name_match = max(litigation_records, key=_affinity)
        elif slot_name_match is not None:
            name_match = slot_name_match

        # The citation is confirmed only when a record that also carries the cited
        # case's name lists it. A record that holds the citation but names a
        # different case does not confirm anything: that is the pattern of a
        # citation number borrowed from an unrelated authority.
        #
        # The search endpoint cannot resolve a reporter citation to the case that
        # holds it: a phrase search for a citation returns the opinions that
        # mention it, ranked by relevance, and the case itself need not appear.
        # CourtListener provides a citation-lookup endpoint for that purpose, and
        # it requires an API token. Without a token the citation is confirmed
        # from the case's own recorded citation lists, and when those do not
        # contain it a court-filtered search is attempted before the citation is
        # left unverified.
        name_matching_records = (
            ([slot_name_match] if slot_name_match is not None else []) + litigation_records
        )

        def _record_lists_cite(record: ResolvedCase | None) -> bool:
            if record is None or not citation.cite_key:
                return False
            return any(
                citation_string_key(c) == citation.cite_key for c in record.citations
            )

        confirming_record: ResolvedCase | None = None
        for record in name_matching_records:
            if _record_lists_cite(record):
                confirming_record = record
                break

        if confirming_record is None and name_matching_records and citation.court_id:
            # The corpus records a court for this reporter, so the citation search
            # is repeated restricted to that court. The case itself is then far
            # more likely to appear among the results, and with it its own
            # citation list.
            filtered = self._search(
                f'"{citation.matched_text}"', court=citation.court_id
            )
            if not filtered.failed:
                filtered_owners: list[ResolvedCase] = []
                for result in filtered.results:
                    candidate = _resolved_from(result, "cite_search")
                    if _record_lists_cite(candidate):
                        filtered_owners.append(candidate)
                        if (
                            case_name_similarity(citation.case_name, candidate.case_name)
                            >= NAME_ACCEPT_WITH_CITE_THRESHOLD
                        ):
                            confirming_record = candidate
                            break
                evidence.append(
                    Evidence(
                        strategy="reporter_citation_search_in_court",
                        query=f'"{citation.matched_text}" court={citation.court_id}',
                        result_count=len(filtered.results),
                        matched=confirming_record is not None,
                        top=confirming_record or (filtered_owners[0] if filtered_owners else None),
                        note=(
                            "restricted to the court recorded for this reporter"
                            + (
                                "; a matching record was found"
                                if confirming_record is not None
                                else "; no matching record was found"
                            )
                        ),
                    )
                )

        if citation.case_name is None and slot_owners:
            return self._with_advisories(
                Finding(
                    citation=citation,
                    verdict=Verdict.VERIFIED,
                    error_class=ErrorClass.NONE,
                    confidence=0.75,
                    explanation=(
                        f"The reporter citation {citation.matched_text} is held by "
                        f"{slot_owners[0].case_name}. The document gives no case name, so only the "
                        f"citation was checked."
                    ),
                    resolved_case=slot_owners[0],
                    evidence=evidence,
                ),
                citation,
                advisories,
                slot_owners[0],
            )

        if name_outcome.failed and cite_outcome.failed:
            return self._unverifiable(
                citation, advisories, evidence,
                f"Neither the case name nor the reporter citation could be looked up: "
                f"{name_outcome.error or cite_outcome.error}",
            )

        if confirming_record is not None:
            return self._with_advisories(
                Finding(
                    citation=citation,
                    verdict=Verdict.VERIFIED,
                    error_class=ErrorClass.NONE,
                    confidence=0.95 if name_match is not None else 0.8,
                    explanation=(
                        f"The case exists in the corpus and the reporter citation "
                        f"{citation.matched_text} is one of its recorded citations."
                    ),
                    resolved_case=confirming_record,
                    evidence=evidence,
                ),
                citation,
                advisories,
                confirming_record,
            )

        if name_match is not None:
            # The case exists. The citation number is checked against everything
            # the corpus records for this case, and a finding of miscitation is
            # only made when something positively disagrees with it.
            recorded_citations = sorted(
                {c for record in litigation_records + slot_owners for c in record.citations}
            )
            unrelated_owners = [
                owner
                for owner in slot_owners
                if case_name_similarity(citation.case_name, owner.case_name)
                < NAME_ACCEPT_WITH_CITE_THRESHOLD
            ]
            if slot_owners and unrelated_owners and len(unrelated_owners) == len(slot_owners):
                other = unrelated_owners[0]
                return self._with_advisories(
                    Finding(
                        citation=citation,
                        verdict=Verdict.MISCITED,
                        error_class=ErrorClass.WRONG_SLOT,
                        confidence=0.85,
                        explanation=(
                            f"The case exists, but the reporter citation {citation.matched_text} "
                            f"is recorded for a different case ({other.case_name}). The corpus "
                            f"records this case as {', '.join(recorded_citations) or 'unknown'}."
                        ),
                        resolved_case=name_match,
                        slot_owner=other,
                        evidence=evidence,
                        suggestion=(
                            f"{name_match.case_name}, {name_match.citations[0]}"
                            if name_match.citations
                            else None
                        ),
                    ),
                    citation,
                    advisories,
                    name_match,
                )

            recorded_courts = [record.court for record in litigation_records if record.court]
            if (
                citation.court_source == "document"
                and citation.court
                and recorded_courts
                and not any(
                    normalize_court(citation.court) == normalize_court(court)
                    for court in recorded_courts
                )
            ):
                return self._with_advisories(
                    Finding(
                        citation=citation,
                        verdict=Verdict.MISCITED,
                        error_class=ErrorClass.WRONG_COURT,
                        confidence=0.8,
                        explanation=(
                            f"The case exists, but every record of it in the corpus is from a "
                            f"different court ({', '.join(recorded_courts)}), while the document "
                            f"gives {citation.court}. The corpus records this case as "
                            f"{', '.join(recorded_citations) or 'unknown'}."
                        ),
                        resolved_case=name_match,
                        evidence=evidence,
                        suggestion=(
                            f"{name_match.case_name}, {name_match.citations[0]}"
                            if name_match.citations
                            else None
                        ),
                    ),
                    citation,
                    advisories,
                    name_match,
                )

            record_count = len(litigation_records) + len(slot_owners)
            adjudicated = (
                f"The corpus records {record_count} record(s) for this case, with the citations "
                f"{', '.join(recorded_citations) or 'none'}, and none of them is "
                f"{citation.matched_text}."
                if citation.matched_text
                else "The document gives no reporter citation to compare."
            )
            limitation = (
                "The search endpoint returns the opinions that mention a citation rather than the "
                "case that holds it, so it cannot confirm or contradict this citation number. "
                "CourtListener's citation-lookup endpoint exists for that purpose and requires an "
                "API token. The citation is therefore left unverified rather than reported as wrong."
            )
            return self._unverifiable(
                citation,
                advisories,
                evidence,
                f"The case exists in the corpus. {adjudicated} {limitation}",
                resolved=name_match,
            )

        if name_match is None and slot_owners:
            owner = slot_owners[0]
            return self._with_advisories(
                Finding(
                    citation=citation,
                    verdict=Verdict.FABRICATED,
                    error_class=ErrorClass.FABRICATED_CASE_NAME,
                    confidence=0.9,
                    explanation=(
                        f"No case matching {citation.case_name!r} was found in the corpus, and the "
                        f"reporter citation {citation.matched_text} belongs to a different case "
                        f"({owner.case_name})."
                    ),
                    slot_owner=owner,
                    evidence=evidence,
                ),
                citation,
                advisories,
                None,
            )

        if name_match is None and not slot_owners:
            confidence = 0.9 if slot_reliable else 0.7
            if not citation.case_name and not slot_reliable:
                return self._unverifiable(
                    citation,
                    advisories,
                    evidence,
                    "The document gives neither a checkable case name nor a checkable reporter citation.",
                )
            subject = (
                f"No case matching {citation.case_name!r} was found in the corpus"
                if citation.case_name
                else "The reporter citation was not found in the corpus"
            )
            detail = (
                f", and no case in the corpus holds the reporter citation {citation.matched_text}."
                if citation.matched_text
                else "."
            )
            return self._with_advisories(
                Finding(
                    citation=citation,
                    verdict=Verdict.FABRICATED,
                    error_class=ErrorClass.FABRICATED_CITE,
                    confidence=confidence,
                    explanation=f"{subject}{detail}",
                    evidence=evidence,
                ),
                citation,
                advisories,
                None,
            )

        return self._unverifiable(
            citation, advisories, evidence, "The citation could not be classified from the available evidence."
        )

    def _with_advisories(
        self,
        finding: Finding,
        citation: ExtractedCitation,
        advisories: list[str],
        resolved: ResolvedCase | None,
    ) -> Finding:
        """Attach year and court comparisons, which inform but do not decide the verdict."""

        if resolved is not None:
            resolved_year = _year_from_date(resolved.date_filed)
            if citation.year and resolved_year and citation.year != resolved_year:
                advisories.append(
                    f"The document gives the year as {citation.year}; the corpus records this case "
                    f"as decided in {resolved_year}."
                )
            # Only compare the court when the document wrote one. When no court is
            # written the value comes from the reporter abbreviation, so a
            # difference against the corpus record carries no information.
            if citation.court and resolved.court and citation.court_source == "document":
                if normalize_court(citation.court) != normalize_court(resolved.court):
                    advisories.append(
                        f"The document gives the court as {citation.court}; the corpus records "
                        f"{resolved.court.rstrip('.')}."
                    )
        finding.advisories = advisories
        return finding

    def _unverifiable(
        self,
        citation: ExtractedCitation,
        advisories: list[str],
        evidence: list[Evidence],
        explanation: str,
        resolved: ResolvedCase | None = None,
    ) -> Finding:
        return Finding(
            citation=citation,
            verdict=Verdict.UNVERIFIABLE,
            error_class=ErrorClass.NOT_CHECKED,
            confidence=0.0,
            explanation=explanation,
            resolved_case=resolved,
            evidence=evidence,
            advisories=advisories,
        )

    # -- audit -------------------------------------------------------------

    def audit(self, text: str, title: str | None = None) -> AuditReport:
        """Extract and verify every citation in a document."""

        started = time.monotonic()
        audit_id = uuid.uuid4().hex[:12]

        def report(message: str, fraction: float) -> None:
            if self.options.progress:
                self.options.progress(message, fraction)

        report("Reading the document for citations", 0.02)
        citations, notes = extract_citations(text)
        case_citations, other_citations = split_by_kind(citations)
        if other_citations:
            kinds = sorted({c.kind.value for c in other_citations})
            notes.append(
                f"{len(other_citations)} citation(s) of type {', '.join(kinds)} were listed but not "
                "checked: this audit verifies case-law authorities against the case-law corpus."
            )
        notes.append(
            "Every verdict records the queries that produced it. A citation that could not be found "
            "is not by itself proof that the authority was invented: the corpus does not hold every "
            "opinion ever issued."
        )

        findings: list[Finding] = []
        total = max(1, len(case_citations))
        for position, citation in enumerate(case_citations):
            report(
                f"Checking {citation.case_name or citation.matched_text}",
                0.05 + 0.7 * (position / total),
            )
            finding = self.verify_citation(citation)
            if self.options.check_quotes:
                finding.quote_check = self.check_quote(citation, finding.resolved_case)
            if self.options.check_support:
                report(
                    f"Reviewing whether the authority supports the proposition "
                    f"({position + 1} of {len(case_citations)})",
                    0.75 + 0.2 * (position / total),
                )
                finding.fidelity = self.check_support(citation, finding.resolved_case)
            findings.append(finding)

        counts = AuditCounts()
        for finding in findings:
            if finding.verdict == Verdict.VERIFIED:
                counts.verified += 1
            elif finding.verdict == Verdict.FABRICATED:
                counts.fabricated += 1
            elif finding.verdict == Verdict.MISCITED:
                counts.miscited += 1
            else:
                counts.unverifiable += 1

        integrity = (
            round(100.0 * counts.verified / counts.checkable, 1) if counts.checkable else None
        )
        coverage = (
            round(100.0 * counts.checkable / counts.total, 1) if counts.total else None
        )

        report("Assembling the report", 1.0)
        return AuditReport(
            audit_id=audit_id,
            created_at=datetime.now(timezone.utc),
            document_title=title,
            access_mode="token" if self.client.has_token else "anonymous",
            counts=counts,
            statute_count=len(other_citations),
            integrity_score=integrity,
            check_coverage=coverage,
            findings=findings,
            duration_ms=int((time.monotonic() - started) * 1000),
            api_requests=self.client.stats.requests,
            cache_hits=self.client.stats.cache_hits,
            notes=notes,
        )
