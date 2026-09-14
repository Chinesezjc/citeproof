# Architecture

This document describes what the audit engine does and why each step is built the way it is.
It is written so that the reasoning behind every verdict can be explained and defended.

## Pipeline

```
document text
    │
    ├─ 1. normalise            collapse all whitespace to single spaces
    │
    ├─ 2. extract              eyecite finds citations; metadata is read from bounded windows
    │
    ├─ 3. verify               for each case citation: name search + citation search
    │                          → verdict, error class, confidence, evidence
    │
    ├─ 4. quote check          compare quoted language against the cited authority, or
    │                          search it across the corpus when opinion text is unavailable
    │
    ├─ 5. support check        (optional) does the authority support the proposition
    │
    └─ 6. report               counts, integrity score, Markdown and JSON rendering
```

## 1. Normalisation

All whitespace runs are collapsed to single spaces before extraction, and all offsets in the
result refer to the normalised text. Documents copied out of a PDF or a word processor break
lines at the page margin, and a break can fall inside a citation:

```
Ehrlich v. American Airlines, Inc., 360 F. Supp. 2d
1327 (S.D. Ga. 2005)
```

Citation patterns do not match across a line break, so without normalisation this citation is
missed entirely. The test `test_citation_split_across_a_line_break_is_still_found` pins this.

## 2. Extraction

Citation detection is delegated to [eyecite](https://github.com/freelawproject/eyecite), which
resolves reporter abbreviations through the same reporter database that indexes the corpus.
Three fields are not taken from eyecite:

**`year` and the quoted parenthetical.** When a citation's own parenthetical contains no court,
eyecite continues scanning forward for a court-and-year parenthetical, and can cross into the
next citation in the same sentence. In

```
In Zicherman v. Korean Air Lines Co., 516 U.S. 217, 228 (1996), the Court held X.
See also Varghese v. China Southern Airlines Co., 925 F.3d 1339, 1349 (11th Cir. 2019).
```

eyecite reports the year `2019` for the Zicherman citation. Its `full_span` behaves the same
way. Both fields are therefore read from a window bounded by the offsets of the neighbouring
citations, so metadata cannot move between them. A citation with no year in its own window is
recorded with no year, rather than with a year belonging to something else.

**`case_name`.** eyecite's party extraction drops short words inside long party names,
reporting `Zicherman Ex Rel. Estate  Kole` for the text `Zicherman Ex Rel. Estate of Kole`. The
name is instead read from the document: the offset of the plaintiff token eyecite recognised is
located, and the text from there to the start of the citation is the name. Anchoring on the
plaintiff token means the slice cannot begin in the prose before the party name, and reading to
the citation means it cannot run past it. Where the two readings disagree, the disagreement is
recorded on the citation and shown in the audit.

`court` is taken from the citation's own parenthetical in preference to eyecite's value,
because that is what the document asserts, and it is cleaned of month and day tokens so that
`(Tex. App. Apr. 11, 2019)` yields `Tex. App.`. eyecite's value is kept separately as
`court_id`, a CourtListener court identifier such as `scotus` or `ca11`, which is usable as a
search filter.

Short forms (`Id.`, `supra`, `925 F.3d at 1349`) carry no new authority. They are attributed to
the authority they refer to and counted as further references. Two citations of the same
authority anywhere in the document are merged into one entity, so each authority is verified
once and the number of references is reported.

## 3. Verification

### Why the case name is the primary test

The corpus indexes a case name for every opinion it holds, so absence of a name is a meaningful
signal. It does **not** record a reporter citation for every opinion: public-domain citations
such as `2013 IL App (1st) 111279-U` are frequently absent from the citation field even when the
case is present. A design that decided by citation number alone would therefore accuse real
cases of being fabricated whenever the citation field was empty.

Case-name matching requires **both parties** to match. `case_name_similarity` splits the name at
the `v.` separator and computes, for each side, the fraction of the cited side's identifying
tokens present in the candidate. The minimum of the two is the score. Requiring both sides is
what rejects `Martinez v. Delta Air Lines` against the real `Lorme v. Delta Air Lines, Inc.`,
which shares a defendant and would otherwise score well. Tokens the document itself writes as
abbreviations may match a longer token in the corpus record, so `Bell Atl. Corp.` matches
`Bell Atlantic Corp.`; the restriction to tokens the document actually abbreviated keeps two
different names from being brought together by a shared prefix.

### Why the reporter citation is the secondary test

The citation number identifies **which** decision in a dispute is meant. One dispute produces
several records with different citations: for *Monell v. Department of Social Services*, the
corpus holds a district decision at 357 F. Supp. 1051, a circuit decision at 532 F.2d 259, a
certiorari grant at 429 U.S. 1071, and the decision on the merits at 436 U.S. 658. The name
search returns the first three and not the fourth. A citation is confirmed only when a record
is found that both matches the cited name and lists the cited reporter citation.

The citation search is repeated with the court recorded for the reporter as a filter when the
citation is not yet confirmed. Since `436 U.S. 658` uses the `U.S.` reporter, the filter is
`court=scotus`, which brings the decision on the merits into the result set. This is what
recovered *Monell* from `unverifiable` to `verified`.

### Why a record that holds the citation is not by itself confirmation

The pattern of a fabricated authority is a name that does not exist paired with a citation
number that is in use by an unrelated case. *Petersen v. Iran Air, 905 F. Supp. 2d 121* is that
pattern: the slot is held by *United States v. ISS Marine Services, Inc.* Treating any record
that holds a citation as confirmation would report the invented authority as verified, so
confirmation requires the record to carry the cited case's name as well. The test
`test_unrelated_record_does_not_confirm_a_citation` pins this.

### Why absence is not reported as miscitation

The search endpoint cannot resolve a reporter citation to the case that holds it. A phrase
search for `436 U.S. 658` returns 14,346 results, which are the opinions that **mention** the
citation ranked by relevance; the case itself need not appear on the first page. CourtListener
provides a `citation-lookup` endpoint for that purpose and it requires an API token.

So when a name-matched case exists, the citation is not in any of its recorded citations, and
nothing positively disagrees with the citation, the verdict is `unverifiable` and the finding
names the missing evidence. The engine abstains rather than guessing. The cost of abstaining is
a less informative report; the cost of guessing is a false accusation against a real authority,
which is why the trade is made this way. `test_citation_that_cannot_be_confirmed_is_left_unverified`
pins this.

### The decision table

Let `name_match` be the record of the cited case that best agrees with the court and year the
document asserts, and `confirming_record` a record that both matches the name and lists the
cited reporter citation.

| Condition | Verdict | Error class |
| --- | --- | --- |
| A confirming record exists | `verified` | `none` |
| Case name exists, the citation is held by a record whose name does not match, and none of the name-matching records holds it | `miscited` | `wrong_slot` |
| Case name exists, the citation is unconfirmed, and the document's court disagrees with every record | `miscited` | `wrong_court` |
| Case name exists, the citation is unconfirmed, and nothing disagrees | `unverifiable` | `not_checked` |
| No case name, but a record holds the citation | `fabricated` | `fabricated_case_name` |
| No case name and no record holds the citation | `fabricated` | `fabricated_cite` |
| Both queries failed | `unverifiable` | `not_checked` |
| The document gives no case name and the citation resolves | `verified` | `none` |

Advisories are recorded independently of the verdict: a year or court that disagrees with the
corpus record, an extraction disagreement between eyecite and the document, and a note when the
citation format is one the corpus indexes unreliably. The court advisory is only produced when
the document wrote a court, because a court inferred from a reporter abbreviation carries no
information.

## 4. Quotation check

Quoted language attributed to an authority is checked in one of two ways, and the finding says
which was used.

With a token, the text of the cited authority is retrieved and the quotation is compared
against it after normalising quotation marks, internal ellipses, bracketed editorial insertions
and punctuation. The result is `verbatim`, `variant` (the source contains similar wording,
which is reported so it can be inspected) or `not_found`.

Without a token, only a corpus-wide phrase search is possible, and the result is reported as
`corpus_miss` or `corpus_hit`. A `corpus_miss` establishes that no opinion in the indexed
corpus contains the phrase. It does **not** establish that the phrase is absent from the cited
authority, and the finding says so. Short quotations are not searched at all, because a short
phrase occurs in unrelated opinions.

## 5. Proposition-support check

Optional, and off unless a language model is configured and `deep` is requested. The model
receives the citing sentence and passages retrieved from the cited authority, and is instructed
to judge only from those passages and to answer `unknown` when they are insufficient. The
prompt is in `llm.py`; the constraint exists because a tool for detecting unfounded legal
claims should not itself make unfounded legal claims.

A quotation the model returns as its evidence is discarded unless that text occurs in the
passages it was given. Passages are selected from the authority by lexical overlap with the
citing sentence, which is recorded in the finding so the retrieval step is not hidden.

## 6. Report

The report carries the counts, an integrity score (the percentage of adjudicable citations that
resolved correctly), a coverage figure (the percentage of extracted citations that the corpus
could adjudicate), the request and cache statistics, and the notes on method and limitations.
The Markdown rendering prints every query with its result count for every finding, so a reader
can reproduce the check rather than take the verdict on trust.

## Cost of an audit

Each case citation costs two upstream requests: one name search and one citation search. A
court-filtered citation search is added when the citation is not confirmed and the reporter
implies a court. In anonymous mode requests are paced at 3.6 seconds apart, and that pacing
dominates the runtime: a cold-cache audit of the 14-citation fixture was measured at 2 minutes
35 seconds, about 11 seconds per citation. With a token configured, the same audit completes in
seconds. Every response is cached in SQLite, so a repeated audit performs no upstream requests
at all and the measured figures in the README can be reproduced from the cache.
