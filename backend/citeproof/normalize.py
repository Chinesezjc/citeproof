"""Normalisation helpers shared by the extraction and verification engines.

Reporter abbreviations and case names are written inconsistently across
documents and across the upstream corpus ("F. Supp. 2d" / "F.Supp.2d",
"Zicherman v. Korean Air Lines Co." / "Zicherman Ex Rel. Estate of Kole v.
Korean Air Lines Co."). Matching therefore happens on normalised forms rather
than on raw strings.
"""

from __future__ import annotations

import re

_WS = re.compile(r"\s+")

# Corporate and procedural noise that carries no identity information.
_NOISE_TOKENS = {
    "co",
    "inc",
    "llc",
    "ltd",
    "corp",
    "corporation",
    "company",
    "the",
    "of",
    "and",
    "ex",
    "rel",
    "estate",
    "in",
    "re",
    "matter",
    "no",
    "nos",
    "et",
    "al",
    "on",
    "behalf",
    "as",
    "trustee",
    "jr",
    "sr",
    "ii",
    "iii",
}

_PARTY_SPLIT = re.compile(r"\s+v\.?\s+", re.IGNORECASE)

# A token the document writes as an abbreviation, such as "Atl." in
# "Bell Atl. Corp.". Only tokens that the document itself abbreviates are
# allowed to match a longer token in the corpus record, so that two genuinely
# different names are not brought together by a shared prefix.
_ABBREVIATED_TOKEN = re.compile(r"\b([A-Za-z][A-Za-z'\-]*)\.(?=\s|,|$)")


def _abbreviated_bases(value: str | None) -> set[str]:
    if not value:
        return set()
    return {match.group(1).lower() for match in _ABBREVIATED_TOKEN.finditer(value)}


def normalize_cite_key(volume: str | None, reporter: str | None, page: str | None) -> str | None:
    """Build a comparison key for a reporter citation.

    Both the citation being checked and the citations returned by the corpus are
    reduced with this function, so differences in spacing, capitalisation and
    periods ("F. Supp. 2d" / "F.Supp.2d") do not affect equality.
    """

    if not volume or not reporter or not page:
        return None
    raw = f"{volume}{reporter}{page}"
    return citation_string_key(raw)


def citation_string_key(value: str) -> str:
    """Reduce a full citation string such as '905 F. Supp. 2d 121' to a key."""

    if not value:
        return ""
    lowered = value.lower()
    # Collapse the whitespace that separates volume, reporter and page.
    lowered = _WS.sub("", lowered)
    return lowered.replace(".", "").replace(",", "")


def normalize_case_name(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.lower()
    lowered = lowered.replace("&", " and ")
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return _WS.sub(" ", lowered).strip()


def _identity_tokens(value: str | None) -> set[str]:
    """Tokens that identify a party, with corporate and procedural noise removed."""

    tokens = {t for t in normalize_case_name(value).split() if t and t not in _NOISE_TOKENS}
    # Fall back to the raw tokens when a name consists only of noise words.
    if not tokens:
        tokens = {t for t in normalize_case_name(value).split() if t}
    return tokens


def split_case_name(value: str | None) -> tuple[str, str] | None:
    """Split 'Plaintiff v. Defendant' into its two sides.

    Returns None when the string does not contain a 'v.' separator.
    """

    if not value:
        return None
    parts = _PARTY_SPLIT.split(value.strip(), maxsplit=1)
    if len(parts) != 2:
        return None
    return parts[0].strip(), parts[1].strip()


def _containment(
    cited: set[str], candidate: set[str], abbreviations: set[str] | None = None
) -> float:
    """Fraction of the cited side's identifying tokens present in the candidate.

    A token counts as present when it appears in the candidate, or when the
    document wrote it as an abbreviation and some candidate token begins with it
    ("Atl." against "Atlantic"). Prefix matching is restricted to tokens the
    document actually abbreviated, so that two different names are not brought
    together by a shared prefix alone.
    """

    if not cited:
        return 0.0
    abbreviations = abbreviations or set()
    hits = 0
    for token in cited:
        if token in candidate:
            hits += 1
        elif token in abbreviations and any(
            other.startswith(token) and len(other) > len(token) for other in candidate
        ):
            hits += 1
    return hits / len(cited)


def case_name_similarity(cited: str | None, candidate: str | None) -> float:
    """Score how well ``candidate`` matches the cited case name, in [0, 1].

    Both parties must match, so a case sharing only one party name ("Martinez v.
    Delta Air Lines" against the real "Lorme v. Delta Air Lines") scores low
    rather than being accepted on the strength of the shared defendant.
    """

    abbreviations = _abbreviated_bases(cited)
    cited_split = split_case_name(cited)
    candidate_split = split_case_name(candidate)
    if cited_split and candidate_split:
        scores = [
            _containment(_identity_tokens(a), _identity_tokens(b), abbreviations)
            for a, b in zip(cited_split, candidate_split)
        ]
        # A party that matches on no token at all means a different case; the
        # minimum is used so that one strong side cannot carry the match.
        return min(scores)
    return _containment(_identity_tokens(cited), _identity_tokens(candidate), abbreviations)


def case_name_similarity_any(cited: str | None, candidates: list[str | None]) -> float:
    if not candidates:
        return 0.0
    return max((case_name_similarity(cited, c) for c in candidates), default=0.0)


def normalize_quote(value: str | None) -> str:
    """Reduce quoted language to a comparable form.

    Straight and curly quotation marks, internal ellipses and whitespace are all
    removed, because a quotation that differs only in those respects still
    appears in the source.
    """

    if not value:
        return ""
    text = value.strip()
    for ch in "\u201c\u201d\u2018\u2019\"'":
        text = text.replace(ch, " ")
    text = text.replace("\u2026", " ").replace("...", " ")
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(r"[^A-Za-z0-9\s]", " ", text)
    return _WS.sub(" ", text).strip().lower()


def quote_is_distinctive(value: str, min_chars: int = 40, min_words: int = 6) -> bool:
    """Whether a quotation is long enough for a corpus-wide search to be meaningful.

    Short quotations produce hits in unrelated opinions, so they are reported as
    not checked rather than as verified.
    """

    normalized = normalize_quote(value)
    return len(normalized) >= min_chars and len(normalized.split()) >= min_words


def normalize_court(value: str | None) -> str:
    """Map a court citation string or id onto a comparable token."""

    if not value:
        return ""
    lowered = value.lower().replace(".", "").replace(" ", "")
    aliases = {
        "scotus": "scotus",
        "supremecourt": "scotus",
        "us": "scotus",
        "ca1": "ca1",
        "ca2": "ca2",
        "ca3": "ca3",
        "ca4": "ca4",
        "ca5": "ca5",
        "ca6": "ca6",
        "ca7": "ca7",
        "ca8": "ca8",
        "ca9": "ca9",
        "ca10": "ca10",
        "ca11": "ca11",
        "cadc": "cadc",
        "cafc": "cafc",
    }
    if lowered in aliases:
        return aliases[lowered]
    # Circuit courts are written as "11th Cir." in documents and reported as
    # "ca11" or "Court of Appeals for the Eleventh Circuit" by the corpus.
    circuit = re.match(r"^(\d{1,2})(?:st|nd|rd|th)cir", lowered)
    if circuit:
        return f"ca{circuit.group(1)}"
    return lowered
