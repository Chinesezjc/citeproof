"""Extract structured citations from document text.

Citation detection and reporter normalisation are delegated to eyecite (Free Law
Project), which resolves reporter abbreviations through the same reporter
database that indexes the case-law corpus.

Three fields are deliberately not taken from eyecite:

``year`` and ``parenthetical``
    When a citation's own parenthetical contains no court, eyecite continues
    scanning forward for a court-and-year parenthetical and can cross into the
    next citation in the same sentence, attributing that citation's year to this
    one. ``full_span`` behaves the same way and can extend across a following
    citation. Both fields are resolved here from a window bounded by the
    neighbouring citation spans, so metadata cannot bleed between citations.

``case_name``
    The name as written in the document is used. eyecite's reconstructed name
    drops short words inside long party names: it reports
    "Zicherman Ex Rel. Estate  Kole" for the text "Zicherman Ex Rel. Estate of
    Kole". The document's own wording is also the name that has to be verified
    against the corpus. The name is located by anchoring on the plaintiff token
    eyecite recognised and reading forward to the citation, so the slice cannot
    include prose that precedes the party name.

``court``
    The court written on the citation is preferred, because that is what the
    document asserts. It is cleaned of month and day tokens so that
    "(Tex. App. Apr. 11, 2019)" yields "Tex. App." rather than "Tex. App. Apr. 11,".
"""

from __future__ import annotations

import re

from eyecite import get_citations
from eyecite.models import (
    CitationBase,
    FullCaseCitation,
    FullJournalCitation,
    FullLawCitation,
    IdCitation,
    ReferenceCitation,
    ShortCaseCitation,
    SupraCitation,
)
from eyecite.tokenizers import AhocorasickTokenizer

from .normalize import normalize_case_name, normalize_cite_key, normalize_quote, split_case_name
from .schemas import CitationKind, ExtractedCitation

_TOKENIZER = AhocorasickTokenizer()

# Tokens whose trailing period does not end a sentence. Needed because case
# names and reporter citations contain them ("Delta Air Lines, Inc.",
# "Zicherman Ex Rel. Estate", "516 U.S. 217", "F. Supp. 2d 121").
_ABBREVIATIONS = {
    "inc", "co", "corp", "ltd", "llc", "lp", "plc", "rel", "ex", "no", "nos",
    "st", "ct", "dept", "bros", "assn", "ry", "transp", "fed", "natl", "intl",
    "univ", "bd", "commr", "sec", "jr", "sr", "mr", "mrs", "ms", "dr", "hon",
    "gen", "gov", "sen", "rep", "app", "supp", "ed", "cir", "dist", "div",
    "cfr", "usc", "stat", "mem", "ord", "op", "v", "vs", "et", "al",
    # Words that appear inside party names and are followed by a period.
    "atl", "bros", "assn", "ins", "grp", "holdings", "enters", "prods", "sys",
    "techs", "steamship", "nav", "ry", "transp", "fed", "natl", "intl", "univ",
    # Reporters and jurisdiction abbreviations.
    "us", "sct", "led", "wl", "fsupp", "fappx", "appx", "misc", "ny", "cal",
    "tex", "ill", "mich", "ohio", "pa", "ga", "fla", "md", "va", "nc", "sc",
    "ala", "miss", "la", "okla", "kan", "neb", "iowa", "minn", "mo", "ark",
    "tenn", "ky", "ind", "wis", "wash", "or", "ariz", "colo", "utah", "ida",
    "mont", "wyo", "nm", "sd", "nd", "me", "nh", "vt", "ri", "conn", "nj",
    "del", "wva", "dc", "pr",
}

# Lowercase words that legitimately appear inside a party name. "v" and "vs"
# are the separator itself.
_NAME_CONNECTORS = {
    "v", "vs", "of", "the", "and", "&", "de", "del", "la", "le", "van", "von",
    "der", "den", "ex", "rel", "in", "re", "on", "for", "by", "as", "a", "an",
}

_MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"

# "(11th Cir. 2019)", "(1996)", "(Tex. App. Apr. 11, 2019)".
# The optional leading group consumes a pin cite; because pin cites are
# digit-only it cannot absorb words that begin a different clause.
_PAREN_AFTER = re.compile(r"^\s*(?:,\s*[\d,\s\-–]+)?\s*\(\s*([^()]{0,80}?)\s*(\d{4})\s*\)")

# Quoted language following the court-and-year parenthetical.
_QUOTE_AFTER_PAREN = re.compile(r'^\s*\(\s*(["\u201c][^"\u201d]{0,600}["\u201d])\s*\)')

# Last-resort 'Plaintiff v. Defendant' match, used only when eyecite recognised
# no party name at all. Commas are excluded so that the match cannot run across
# a clause boundary; names containing an internal comma are reachable through
# the eyecite-anchored path instead.
_CASE_NAME_BEFORE = re.compile(
    r"([A-Z][^,;:()\[\]{}]{0,80}?)\s+[Vv]\.?\s+([A-Z][^,;:()\[\]{}]{0,80}?)\s*,\s*$"
)

_LOOKAHEAD = 90
_LOOKBEHIND = 220
_MAX_NAME_LENGTH = 160


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _token_before(text: str, period_position: int) -> str:
    """The word immediately preceding a period, lowercased, periods removed."""

    index = period_position - 1
    while index >= 0 and (text[index].isalnum() or text[index] == "."):
        index -= 1
    return text[index + 1 : period_position].replace(".", "").lower().strip()


def _ends_sentence(text: str, position: int) -> bool:
    """Whether the terminator at ``position`` closes a sentence.

    A period does not close a sentence when it terminates an abbreviation or a
    single-letter initial, which is what keeps "Inc." and "Ex Rel." inside a
    case name and "U.S." inside a citation.
    """

    if text[position] in "?!":
        return True
    before = _token_before(text, position)
    if not before:
        return True
    if len(before) == 1:
        return False
    return before not in _ABBREVIATIONS


def _next_sentence_end(text: str, start: int) -> int:
    """Offset just past the next sentence-closing terminator at or after ``start``.

    A period followed by a digit does not close a sentence. Reporter citations
    place a number directly after the reporter ("516 U.S. 217", "F. Supp. 2d
    121"), so treating a following digit as the start of a new sentence truncates
    sentences in the middle of every citation.
    """

    for match in re.finditer(r"[.!?]", text[start:]):
        position = start + match.start()
        if not _ends_sentence(text, position):
            continue
        after = text[position + 1 :]
        if after.strip() == "":
            return len(text)
        if re.match(r"^\s+[\"“(\[]*[A-Z]", after):
            return position + 1
    return len(text)


def _sentence_bounds(text: str, position: int) -> tuple[int, int]:
    """Return the (start, end) offsets of the sentence containing ``position``."""

    if position < 0:
        return 0, 0
    start = 0
    cursor = 0
    while cursor < len(text):
        end = _next_sentence_end(text, cursor)
        if end >= position:
            break
        start = end
        if end <= cursor:
            break
        cursor = end
    return start, _next_sentence_end(text, start)


def _clean_court(value: str | None) -> str | None:
    """Drop month and day tokens that a court parenthetical may also carry."""

    if not value:
        return None
    cleaned = value.strip().rstrip(",").strip()
    cleaned = re.sub(rf"[,]?\s*{_MONTHS}\s+\d{{1,2}}\s*,?\s*$", "", cleaned, flags=re.I)
    cleaned = re.sub(rf"[,]?\s*{_MONTHS}\s*,?\s*$", "", cleaned, flags=re.I)
    cleaned = cleaned.strip().rstrip(",").strip()
    return cleaned or None


def _bounded_metadata(
    text: str, matched_end: int, limit: int
) -> tuple[str | None, str | None, str | None]:
    """Read court, year and quoted parenthetical from the window after a citation.

    ``limit`` is the offset at which the next citation begins, so the window
    cannot reach into a neighbouring citation. Anything absent from the window is
    reported as absent rather than guessed from elsewhere in the document.
    """

    window = text[matched_end : min(limit, matched_end + _LOOKAHEAD)]
    match = _PAREN_AFTER.match(window)
    if not match:
        return None, None, None

    court = _clean_court(match.group(1))
    year = match.group(2)

    quote: str | None = None
    quote_match = _QUOTE_AFTER_PAREN.match(window[match.end() :])
    if quote_match:
        quote = quote_match.group(1).strip()

    return court, year, quote


def _plaintiff_offset(text: str, start_of_citation: int, floor: int, plaintiff: str | None) -> int | None:
    """Where the plaintiff name begins, located from the plaintiff token itself.

    Anchoring on a token eyecite recognised keeps the returned offset from
    landing in prose that precedes the party name.
    """

    if not plaintiff:
        return None
    token = next((t for t in re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", plaintiff)), None)
    if not token:
        return None
    window_start = max(floor, start_of_citation - _LOOKBEHIND)
    window = text[window_start:start_of_citation]
    found = None
    for match in re.finditer(rf"(?<![A-Za-z]){re.escape(token)}", window, re.IGNORECASE):
        found = match
    if found is None:
        return None
    return window_start + found.start()


def _plausible_party_name(value: str) -> bool:
    """Whether a candidate string looks like a party name rather than prose.

    Every token must be capitalised or be a connector word, which rejects prose
    such as "See also" or "Court held".
    """

    tokens = value.split()
    if not tokens or len(tokens) > 20:
        return False
    for token in tokens:
        stripped = token.strip(",.;:()[]&'’")
        if not stripped:
            continue
        if stripped[0].isupper() or stripped[0].isdigit():
            continue
        if stripped.lower() in _NAME_CONNECTORS:
            continue
        return False
    return True


def _name_between(text: str, name_offset: int | None, match_start: int) -> str | None:
    """The party name occupying the text between ``name_offset`` and the citation.

    No sentence-boundary test is applied here. The offset is anchored on the
    plaintiff token eyecite recognised, so the slice begins at the party name and
    ends at the citation and cannot include surrounding prose.
    """

    if name_offset is None or name_offset >= match_start:
        return None
    raw = re.sub(r"[\s,]+$", "", text[name_offset:match_start])
    raw = _collapse(raw).strip()
    if not raw or len(raw) > _MAX_NAME_LENGTH:
        return None
    if not split_case_name(raw):
        return None
    if not _plausible_party_name(raw):
        return None
    return raw


def _name_by_pattern(text: str, start_of_citation: int, floor: int) -> str | None:
    """Last-resort name lookup for citations whose parties eyecite did not read."""

    window_start = max(floor, start_of_citation - _LOOKBEHIND)
    sentence_start, _ = _sentence_bounds(text, start_of_citation - 1)
    window = text[max(window_start, sentence_start) : start_of_citation]
    for match in reversed(list(_CASE_NAME_BEFORE.finditer(window))):
        plaintiff, defendant = match.group(1).strip(), match.group(2).strip()
        candidate = f"{plaintiff} v. {defendant}"
        if _plausible_party_name(plaintiff) and _plausible_party_name(defendant):
            return _collapse(candidate)
    return None


def _verbatim_for(
    text: str, matched_start: int, matched_end: int, name_start: int | None
) -> str:
    """The citation as written, including the case name when one was located."""

    start = name_start if name_start is not None and name_start < matched_start else matched_start
    end = matched_end
    tail = text[matched_end : matched_end + 80]
    tail_match = re.match(r"(?:,\s*[\d,\s\-–]+)?\s*(?:\([^()]{0,80}?\d{4}\))?", tail)
    if tail_match:
        end = matched_end + tail_match.end()
    return _collapse(text[start:end]).strip()


def _kind_of(citation: CitationBase) -> CitationKind:
    if isinstance(citation, FullCaseCitation):
        return CitationKind.CASE
    if isinstance(citation, FullLawCitation):
        return CitationKind.STATUTE
    if isinstance(citation, FullJournalCitation):
        return CitationKind.JOURNAL
    return CitationKind.OTHER


def normalize_document(text: str) -> str:
    """Collapse all whitespace runs in a document to single spaces.

    Documents copied out of a PDF or a word processor break lines at the page
    margin, which can fall in the middle of a citation ("360 F. Supp. 2d\\n1327").
    Citation patterns do not match across a line break, so the document is
    normalised before extraction. All spans in the returned citations index this
    normalised text.
    """

    return re.sub(r"\s+", " ", text or "").strip()


def extract_citations(text: str) -> tuple[list[ExtractedCitation], list[str]]:
    """Extract the distinct authorities a document cites.

    Returns the entities plus human-readable notes about anything that could not
    be attributed (a supra citation with no identifiable antecedent, for example).
    """

    notes: list[str] = []
    if not text or not text.strip():
        return [], notes

    text = normalize_document(text)

    raw = get_citations(text, tokenizer=_TOKENIZER)
    if not raw:
        return [], notes

    ordered = sorted(raw, key=lambda c: c.span()[0])
    spans = [c.span() for c in ordered]

    def next_citation_start(index: int) -> int:
        for later in range(index + 1, len(ordered)):
            if spans[later][0] > spans[index][1]:
                return spans[later][0]
        return len(text)

    def previous_citation_end(index: int) -> int:
        for earlier in range(index - 1, -1, -1):
            if spans[earlier][1] <= spans[index][0]:
                return spans[earlier][1]
        return 0

    entities: list[ExtractedCitation] = []
    last_case_entity: int | None = None
    unattributed_short = 0
    supra_count = 0

    for position, citation in enumerate(ordered):
        # Short forms carry no new authority; they count as further occurrences
        # of an authority already extracted.
        if isinstance(citation, (IdCitation, SupraCitation, ShortCaseCitation)):
            target: int | None = None
            if isinstance(citation, ShortCaseCitation):
                groups = citation.groups or {}
                short_key = normalize_cite_key(
                    groups.get("volume"), groups.get("reporter"), groups.get("page")
                )
                for candidate in range(len(entities) - 1, -1, -1):
                    if short_key and entities[candidate].cite_key == short_key:
                        target = candidate
                        break
                if target is None:
                    for candidate in range(len(entities) - 1, -1, -1):
                        if entities[candidate].reporter == groups.get("reporter"):
                            target = candidate
                            break
            elif isinstance(citation, IdCitation):
                target = last_case_entity
            else:
                supra_count += 1

            if target is not None:
                entities[target].occurrence_count += 1
                entities[target].spans.append(citation.span())
            elif isinstance(citation, ShortCaseCitation):
                unattributed_short += 1
            continue

        if isinstance(citation, ReferenceCitation):
            continue

        match_start, match_end = citation.span()
        floor = previous_citation_end(position)
        limit = next_citation_start(position)

        groups = citation.groups or {}
        metadata = getattr(citation, "metadata", None)
        pin_cite = getattr(metadata, "pin_cite", None) if metadata else None
        meta_court = getattr(metadata, "court", None) if metadata else None
        meta_plaintiff = getattr(metadata, "plaintiff", None) if metadata else None
        meta_defendant = getattr(metadata, "defendant", None) if metadata else None

        extraction_notes: list[str] = []
        case_name: str | None = None
        name_offset: int | None = None
        if isinstance(citation, FullCaseCitation):
            name_offset = _plaintiff_offset(text, match_start, floor, meta_plaintiff)
            case_name = _name_between(text, name_offset, match_start)
            if case_name is None:
                fallback = _name_by_pattern(text, match_start, floor)
                if fallback:
                    case_name = fallback
                    token = next(
                        (t for t in re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", fallback)), None
                    )
                    if token:
                        located = _plaintiff_offset(text, match_start, floor, token)
                        name_offset = located if located is not None else name_offset

        if case_name:
            parts = split_case_name(case_name)
            plaintiff, defendant = parts if parts else (meta_plaintiff, meta_defendant)
        else:
            plaintiff, defendant = meta_plaintiff, meta_defendant
            if meta_plaintiff and meta_defendant:
                case_name = f"{meta_plaintiff} v. {meta_defendant}"
                token = next(
                    (t for t in re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", meta_plaintiff)), None
                )
                name_offset = _plaintiff_offset(text, match_start, floor, token)

        if case_name and meta_plaintiff and meta_defendant:
            reconstructed = f"{meta_plaintiff} v. {meta_defendant}"
            if _collapse(reconstructed) != _collapse(case_name):
                extraction_notes.append(
                    f"The citation parser read the party names as {reconstructed!r}; "
                    f"the document text reads {case_name!r}. The document text was used."
                )

        bounded_court, bounded_year, parenthetical = _bounded_metadata(text, match_end, limit)

        sentence_start, sentence_end = _sentence_bounds(text, match_start)
        context = _collapse(text[sentence_start:sentence_end]).strip()
        if sentence_start > 0:
            previous_start, previous_end = _sentence_bounds(text, sentence_start - 1)
            if previous_end <= sentence_start + 1 and previous_start < sentence_start:
                previous = _collapse(text[previous_start:previous_end]).strip()
                if previous and not context.startswith(previous):
                    context = f"{previous} {context}"

        entities.append(
            ExtractedCitation(
                index=len(entities),
                verbatim=_verbatim_for(text, match_start, match_end, name_offset),
                matched_text=citation.matched_text(),
                kind=_kind_of(citation),
                volume=groups.get("volume"),
                reporter=groups.get("reporter"),
                page=groups.get("page"),
                pin_cite=pin_cite,
                court=bounded_court or meta_court,
                # eyecite resolves the reporter abbreviation to a CourtListener
                # court identifier ("scotus", "ca11"), which can be used directly
                # as a search filter. Court names written in the document cannot.
                court_id=(
                    meta_court
                    if meta_court and re.fullmatch(r"[a-z0-9]+", meta_court)
                    else None
                ),
                court_source=(
                    "document" if bounded_court else ("reporter" if meta_court else None)
                ),
                year=bounded_year,
                case_name=case_name,
                plaintiff=plaintiff,
                defendant=defendant,
                parenthetical=parenthetical,
                cite_key=normalize_cite_key(
                    groups.get("volume"), groups.get("reporter"), groups.get("page")
                ),
                spans=[citation.span()],
                occurrence_count=1,
                context=context,
                extraction_notes=extraction_notes,
            )
        )
        if entities[-1].kind == CitationKind.CASE:
            last_case_entity = len(entities) - 1

    if unattributed_short:
        notes.append(
            f"{unattributed_short} short-form citation(s) had no matching full citation in this document."
        )
    if supra_count:
        notes.append(
            f"{supra_count} supra citation(s) were counted with the authority preceding them."
        )

    # A document that cites the same authority several times produces one
    # citation object per occurrence. They are merged so that each authority is
    # verified once, with the number of references recorded.
    merged: list[ExtractedCitation] = []
    seen: dict[str, int] = {}
    for entity in entities:
        key = entity.cite_key or (
            normalize_case_name(entity.case_name) if entity.case_name else None
        )
        if key and key in seen:
            existing = merged[seen[key]]
            existing.occurrence_count += entity.occurrence_count
            existing.spans.extend(entity.spans)
            continue
        if key:
            seen[key] = len(merged)
        merged.append(entity)

    for position, entity in enumerate(merged):
        entity.index = position
    if len(merged) != len(entities):
        notes.append(
            f"{len(entities) - len(merged)} repeat reference(s) to an already listed authority were merged."
        )
    return merged, notes


def split_by_kind(
    citations: list[ExtractedCitation],
) -> tuple[list[ExtractedCitation], list[ExtractedCitation]]:
    """Split into case-law citations (checkable) and everything else."""

    cases = [c for c in citations if c.kind == CitationKind.CASE]
    others = [c for c in citations if c.kind != CitationKind.CASE]
    return cases, others


def quote_from(citation: ExtractedCitation) -> str | None:
    """The quoted language attributed to a citation, in comparable form."""

    if not citation.parenthetical:
        return None
    return normalize_quote(citation.parenthetical) or None
