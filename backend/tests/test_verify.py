"""Tests for the verification engine.

Each test states the evidence the stub corpus returns and the verdict that
evidence must produce. The two most important tests are
``test_negative_control_produces_no_accusations`` and
``test_unrelated_record_does_not_confirm_a_citation``: a tool that accuses a
correctly cited authority is worse than useless, so those behaviours are pinned.
"""

from __future__ import annotations

from citeproof.extract import extract_citations
from citeproof.schemas import ErrorClass, Verdict
from citeproof.verify import CitationVerifier, VerifierOptions

from conftest import FakeCorpus, case_result


def _verify(text: str, corpus: FakeCorpus):
    citations, _ = extract_citations(text)
    assert len(citations) == 1, "these tests use single-citation documents"
    verifier = CitationVerifier(corpus, options=VerifierOptions(check_quotes=False))
    return verifier.verify_citation(citations[0])


# -- fabricated ------------------------------------------------------------


def test_absent_case_name_and_absent_citation_is_fabricated():
    corpus = FakeCorpus({})
    finding = _verify(
        "See Varghese v. China Southern Airlines Co., 925 F.3d 1339 (11th Cir. 2019).", corpus
    )
    assert finding.verdict == Verdict.FABRICATED
    assert finding.error_class == ErrorClass.FABRICATED_CITE
    assert finding.confidence >= 0.9


def test_absent_name_whose_citation_belongs_to_another_case_is_fabricated():
    """The pattern of a fabricated case name paired with a real citation slot."""

    corpus = FakeCorpus(
        {
            '"905 F. Supp. 2d 121"': [
                case_result(1, "United States v. ISS Marine Services, Inc.", ["905 F. Supp. 2d 121"])
            ]
        }
    )
    finding = _verify("Petersen v. Iran Air, 905 F. Supp. 2d 121 (D.D.C. 2012).", corpus)
    assert finding.verdict == Verdict.FABRICATED
    assert finding.error_class == ErrorClass.FABRICATED_CASE_NAME
    assert finding.slot_owner is not None
    assert "ISS Marine" in finding.slot_owner.case_name


# -- verified --------------------------------------------------------------


def test_case_and_citation_that_agree_are_verified():
    corpus = FakeCorpus(
        {
            '"Zicherman v. Korean Air Lines Co."': [
                case_result(
                    7,
                    "Zicherman v. Korean Air Lines Co.",
                    ["516 U.S. 217", "116 S. Ct. 629"],
                    court="2d Cir.",
                    date_filed="1996-02-27",
                )
            ]
        }
    )
    finding = _verify("Zicherman v. Korean Air Lines Co., 516 U.S. 217 (1996).", corpus)
    assert finding.verdict == Verdict.VERIFIED
    assert finding.error_class == ErrorClass.NONE
    assert finding.resolved_case is not None


def test_a_later_decision_in_the_same_litigation_does_not_break_verification():
    """One dispute yields several records with different citations.

    The name search returns the record whose citations do not include the cited
    one; the record that does include it is found through the citation search.
    Both must be combined before deciding.
    """

    corpus = FakeCorpus(
        {
            '"Zicherman v. Korean Air Lines Co."': [
                case_result(7, "Zicherman v. Korean Air Lines Co.", ["92 F.3d 126"], court="2d Cir.")
            ],
            '"516 U.S. 217"': [
                case_result(
                    8,
                    "Zicherman v. Korean Air Lines Co.",
                    ["516 U.S. 217", "116 S. Ct. 629"],
                    court="Supreme Court",
                    date_filed="1996-06-17",
                )
            ],
        }
    )
    finding = _verify("Zicherman v. Korean Air Lines Co., 516 U.S. 217 (1996).", corpus)
    assert finding.verdict == Verdict.VERIFIED
    assert finding.resolved_case is not None
    assert "516 U.S. 217" in finding.resolved_case.citations


def test_court_filtered_search_recovers_a_case_whose_merits_record_is_ranked_low():
    """The plain citation search returns opinions that mention the citation.

    When no name-search record lists the citation, one further search restricted
    to the court recorded for the reporter is issued, and a record of the case
    found there confirms the citation.
    """

    corpus = FakeCorpus(
        {
            '"Monell v. Department of Social Services"': [
                case_result(
                    1,
                    "Monell v. Department of Social Services of the City of New York",
                    ["429 U.S. 1071", "97 S. Ct. 807"],
                    court="Supreme Court",
                    date_filed="1977-01-10",
                )
            ],
            '"436 U.S. 658"': [
                case_result(2, "Castro v. County of Los Angeles", ["785 F.3d 336"])
            ],
            ('"436 U.S. 658"', "scotus"): [
                case_result(
                    3,
                    "Monell v. Department of Social Services",
                    ["436 U.S. 658", "98 S. Ct. 2018"],
                    court="Supreme Court",
                    date_filed="1978-06-06",
                )
            ],
        }
    )
    finding = _verify("Monell v. Department of Social Services, 436 U.S. 658, 694 (1978).", corpus)
    assert finding.verdict == Verdict.VERIFIED
    assert finding.resolved_case is not None
    assert finding.resolved_case.cluster_id == 3


def test_a_citation_without_a_case_name_is_verified_from_the_citation_alone():
    corpus = FakeCorpus(
        {
            '"516 U.S. 217"': [
                case_result(9, "Zicherman v. Korean Air Lines Co.", ["516 U.S. 217"])
            ]
        }
    )
    citations, _ = extract_citations("See 516 U.S. 217 (1996).")
    verifier = CitationVerifier(corpus, options=VerifierOptions(check_quotes=False))
    finding = verifier.verify_citation(citations[0])
    assert finding.verdict == Verdict.VERIFIED
    assert finding.confidence < 0.9  # only the citation could be checked


# -- miscited --------------------------------------------------------------


def test_citation_recorded_for_an_unrelated_case_is_miscited():
    """A real case cited with a reporter citation that belongs to another case."""

    corpus = FakeCorpus(
        {
            '"Ehrlich v. American Airlines, Inc."': [
                case_result(
                    11,
                    "Ehrlich v. American Airlines, Inc.",
                    ["360 F.3d 366", "2004 WL 419438"],
                    court="2d Cir.",
                    date_filed="2004-03-08",
                )
            ],
            '"360 F. Supp. 2d 1327"': [
                case_result(12, "WITEX, U.S.A., Inc. v. United States", ["360 F. Supp. 2d 1327"])
            ],
        }
    )
    finding = _verify(
        "Ehrlich v. American Airlines, Inc., 360 F. Supp. 2d 1327 (S.D. Ga. 2005).", corpus
    )
    assert finding.verdict == Verdict.MISCITED
    assert finding.error_class == ErrorClass.WRONG_SLOT
    assert finding.slot_owner is not None
    assert finding.suggestion is not None and "360 F.3d 366" in finding.suggestion


def test_citation_unconfirmed_and_wrong_court_is_miscited():
    """With no citation slot available, a court that contradicts every record decides."""

    corpus = FakeCorpus(
        {
            '"Ehrlich v. American Airlines, Inc."': [
                case_result(
                    21,
                    "Ehrlich v. American Airlines, Inc.",
                    ["360 F.3d 366"],
                    court="2d Cir.",
                    date_filed="2004-03-08",
                )
            ]
        }
    )
    finding = _verify(
        "Ehrlich v. American Airlines, Inc., 360 F. Supp. 2d 1327 (S.D. Ga. 2005).", corpus
    )
    assert finding.verdict == Verdict.MISCITED
    assert finding.error_class == ErrorClass.WRONG_COURT


# -- the honesty rules -----------------------------------------------------


def test_unrelated_record_does_not_confirm_a_citation():
    """A record that holds the citation but names a different case confirms nothing.

    Treating any record that holds the citation as proof would mark a fabricated
    case name as verified whenever its citation number happened to be in use.
    """

    corpus = FakeCorpus(
        {
            '"Petersen v. Iran Air"': [],
            '"905 F. Supp. 2d 121"': [
                case_result(
                    31,
                    "United States v. ISS Marine Services, Inc.",
                    ["905 F. Supp. 2d 121"],
                    court="D.D.C.",
                )
            ],
        }
    )
    finding = _verify("Petersen v. Iran Air, 905 F. Supp. 2d 121 (D.D.C. 2012).", corpus)
    assert finding.verdict == Verdict.FABRICATED


def test_negative_control_produces_no_accusations():
    """A document whose citations are all real must produce no findings against it.

    The stub returns, for each authority, records of the same litigation whose
    citation lists do not include the cited citation. The engine must not read
    that as a miscitation, because the search endpoint cannot resolve a citation
    to the case that holds it.
    """

    cases = [
        ("Bell Atlantic Corp. v. Twombly, 550 U.S. 544, 570 (2007).", "Bell Atlantic Corp. v. Twombly", "550 U.S. 544", "scotus"),
        ("Ashcroft v. Iqbal, 556 U.S. 662 (2009).", "Ashcroft v. Iqbal", "556 U.S. 662", "scotus"),
        ("West v. Atkins, 487 U.S. 42 (1988).", "West v. Atkins", "487 U.S. 42", "scotus"),
    ]
    responses: dict[object, list[dict]] = {}
    for text, name, cite, court_id in cases:
        responses[f'"{name}"'] = [
            case_result(hash(name) % 10000, name, ["1 U.S. 1"], court="Supreme Court", date_filed="1900-01-01")
        ]
    corpus = FakeCorpus(responses)

    for text, name, cite, _ in cases:
        finding = _verify(text, corpus)
        assert finding.verdict not in (Verdict.FABRICATED, Verdict.MISCITED), (
            f"{name} is a real, correctly cited authority and was reported as {finding.verdict}: "
            f"{finding.explanation}"
        )


def test_citation_that_cannot_be_confirmed_is_left_unverified():
    """The engine states its limitation instead of guessing whether the citation is wrong."""

    corpus = FakeCorpus(
        {
            '"Monell v. Department of Social Services"': [
                case_result(
                    41,
                    "Monell v. Department of Social Services",
                    ["429 U.S. 1071"],
                    court="Supreme Court",
                    date_filed="1977-01-10",
                )
            ]
        }
    )
    finding = _verify("Monell v. Department of Social Services, 436 U.S. 658, 694 (1978).", corpus)
    assert finding.verdict == Verdict.UNVERIFIABLE
    assert finding.error_class == ErrorClass.NOT_CHECKED
    assert "citation-lookup" in finding.explanation
    assert "436 U.S. 658" in finding.explanation


def test_both_lookups_failing_is_unverifiable_not_fabricated():
    corpus = FakeCorpus(
        {'"Zicherman v. Korean Air Lines Co."': [], '"516 U.S. 217"': []},
        failing={'"Zicherman v. Korean Air Lines Co."', '"516 U.S. 217"'},
    )
    finding = _verify("Zicherman v. Korean Air Lines Co., 516 U.S. 217 (1996).", corpus)
    assert finding.verdict == Verdict.UNVERIFIABLE
    assert finding.verdict != Verdict.FABRICATED


def test_a_public_domain_citation_is_reported_with_its_weaker_evidence():
    corpus = FakeCorpus({})
    finding = _verify("Shaboon v. EgyptAir, 2013 IL App (1st) 111279-U (Ill. App. Ct. 2013).", corpus)
    assert finding.verdict == Verdict.FABRICATED
    assert any("public-domain" in note for note in finding.advisories)
    assert finding.confidence < 0.9
