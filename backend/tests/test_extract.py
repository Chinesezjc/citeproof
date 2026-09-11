"""Tests for citation extraction.

The cases here are regression tests for defects found while building the
extractor. Each one records what the citation parser gets wrong on its own, so
that the correction in ``extract`` cannot be removed without a test failing.
"""

from __future__ import annotations

from citeproof.extract import extract_citations, normalize_document


def test_year_is_not_taken_from_a_following_citation():
    """eyecite reports the year of the next citation when a citation has no court.

    In this sentence the first citation's own parenthetical carries 1996 and the
    following citation's carries 2019. Reading the year from the citation parser
    yields 2019 for both.
    """

    text = (
        "In Zicherman v. Korean Air Lines Co., 516 U.S. 217, 228 (1996), the Court held X. "
        "See also Varghese v. China Southern Airlines Co., 925 F.3d 1339, 1349 (11th Cir. 2019) "
        '("the Warsaw Convention does not preempt").'
    )
    citations, _ = extract_citations(text)
    assert [c.year for c in citations] == ["1996", "2019"]
    assert [c.case_name for c in citations] == [
        "Zicherman v. Korean Air Lines Co.",
        "Varghese v. China Southern Airlines Co.",
    ]


def test_quoted_language_attaches_to_the_citation_that_carries_it():
    text = (
        'Zicherman v. Korean Air Lines Co., 516 U.S. 217 (1996). '
        'Smith v. Jones Corp., 123 F.3d 456, 460 (9th Cir. 1997) ("we hold that the statute applies").'
    )
    citations, _ = extract_citations(text)
    assert citations[0].parenthetical is None
    assert citations[1].parenthetical == '"we hold that the statute applies"'


def test_case_name_containing_a_comma_is_kept_whole():
    """A case name with an internal comma must not lose its corporate suffix."""

    text = "Martinez v. Delta Air Lines, Inc., 2019 WL 1584623 (Tex. App. Apr. 11, 2019)."
    citations, _ = extract_citations(text)
    assert citations[0].case_name == "Martinez v. Delta Air Lines, Inc."
    assert citations[0].court == "Tex. App."
    assert citations[0].year == "2019"


def test_party_name_is_read_from_the_document_not_from_the_parser():
    """eyecite drops 'of' inside a long party name.

    It reports "Zicherman Ex Rel. Estate  Kole" for the text
    "Zicherman Ex Rel. Estate of Kole". The document's own wording is used, and
    the disagreement is recorded rather than silently resolved.
    """

    text = (
        "Zicherman Ex Rel. Estate of Kole v. Korean Air Lines Co., 516 U.S. 217, 228 (1996) "
        "(holding that the Convention provides the exclusive remedy)."
    )
    citations, _ = extract_citations(text)
    assert citations[0].case_name == "Zicherman Ex Rel. Estate of Kole v. Korean Air Lines Co."
    assert citations[0].extraction_notes
    assert "Estate  Kole" in citations[0].extraction_notes[0]


def test_prose_before_the_name_is_not_absorbed():
    text = "See also Varghese v. China Southern Airlines Co., 925 F.3d 1339 (11th Cir. 2019)."
    citations, _ = extract_citations(text)
    assert citations[0].case_name == "Varghese v. China Southern Airlines Co."
    assert citations[0].verbatim == "Varghese v. China Southern Airlines Co., 925 F.3d 1339 (11th Cir. 2019)"


def test_citation_split_across_a_line_break_is_still_found():
    """Documents copied from a PDF break lines inside citations."""

    text = "The court relied on Ehrlich v. American Airlines, Inc., 360 F. Supp. 2d\n1327 (S.D. Ga. 2005)."
    citations, _ = extract_citations(text)
    assert len(citations) == 1
    assert citations[0].matched_text == "360 F. Supp. 2d 1327"


def test_whitespace_normalisation_is_what_the_spans_index():
    text = "First line.\n\n\nSecond   line cites 516 U.S. 217."
    normalized = normalize_document(text)
    assert normalized == "First line. Second line cites 516 U.S. 217."
    citations, _ = extract_citations(text)
    start, end = citations[0].spans[0]
    assert normalized[start:end] == "516 U.S. 217"


def test_short_forms_and_id_count_as_further_references():
    text = (
        "Zicherman v. Korean Air Lines Co., 516 U.S. 217, 228 (1996). "
        "The Court there held otherwise. Id. at 230. See 516 U.S. at 231."
    )
    citations, _ = extract_citations(text)
    assert len(citations) == 1
    assert citations[0].occurrence_count == 3


def test_repeat_references_to_one_authority_are_merged():
    text = (
        "Zicherman v. Korean Air Lines Co., 516 U.S. 217 (1996), controls. "
        "The rule of Zicherman v. Korean Air Lines Co., 516 U.S. 217 (1996), is settled."
    )
    citations, notes = extract_citations(text)
    assert len(citations) == 1
    assert citations[0].occurrence_count == 2
    assert any("merged" in note for note in notes)


def test_non_case_citations_are_separated():
    text = "Under 42 U.S.C. \u00a7 1983 and Zicherman v. Korean Air Lines Co., 516 U.S. 217 (1996), the claim fails."
    citations, _ = extract_citations(text)
    kinds = {c.kind.value for c in citations}
    assert "statute" in kinds and "case" in kinds


def test_public_domain_citation_is_parsed():
    text = "Shaboon v. EgyptAir, 2013 IL App (1st) 111279-U (Ill. App. Ct. 2013)."
    citations, _ = extract_citations(text)
    assert citations[0].volume == "2013"
    assert citations[0].reporter == "IL App (1st)"
    assert citations[0].page == "111279-U"


def test_court_from_reporter_is_distinguished_from_court_in_the_document():
    reporter_court, _ = extract_citations("Zicherman v. Korean Air Lines Co., 516 U.S. 217 (1996).")
    assert reporter_court[0].court_source == "reporter"
    assert reporter_court[0].court_id == "scotus"

    written_court, _ = extract_citations(
        "Varghese v. China Southern Airlines Co., 925 F.3d 1339 (11th Cir. 2019)."
    )
    assert written_court[0].court_source == "document"
    assert written_court[0].court == "11th Cir."


def test_empty_document_yields_nothing():
    citations, notes = extract_citations("   \n  ")
    assert citations == []
    assert notes == []
