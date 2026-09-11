# Legal-citation benchmark corpus

This directory holds two hand-verified fixture documents used to measure whether the
citation-verification tool classifies citations correctly. Each file records, for every
citation in its `text`, the verdict the tool is expected to reach (`real`, `fabricated` or
`miscited`), the specific error class, and the evidence the verdict rests on.

Retrieval date for every source cited in this directory: **2026-09-11**.

All documents behind these fixtures are public third-party court filings and public
third-party case-law records. They are used here as test fixtures only. They are not the
project's own original code, they are not authored by the project, and nothing in this
directory is a statement about the parties or counsel in the underlying litigation beyond
what the cited public records state.

## Contents

| File | Entries | Verdicts | Purpose |
| --- | --- | --- | --- |
| `avianca.json` | 15 | 7 `fabricated`, 3 `miscited`, 5 `real` | Positive cases: citations that the tool must flag, taken from the Mata v. Avianca litigation, with real authorities mixed in as negative controls. |
| `real_brief.json` | 14 | 14 `real` | Pure negative control: a tool that reports any `fabricated` or `miscited` finding on this document has produced a false positive. |

Both files use the required structure: `id`, `title`, `source_url`, `provenance`, `text`,
`expected`. Each `expected` entry carries `citation_verbatim`, `case_name`, `volume`,
`reporter`, `page`, `court`, `year`, `verdict`, `error_class`, `slot_occupied_by`,
`source_url` and `notes`. Every `citation_verbatim` string was asserted to occur as an exact
substring of the corresponding `text` before the files were written, so the regex-based
extractor can find each one.

## Primary sources

Retrieved on 2026-09-11 unless a different date is stated.

Court filings in Mata v. Avianca, Inc., No. 22-cv-1461 (PKC) (S.D.N.Y.), from the RECAP
archive on `storage.courtlistener.com`:

| Document | URL |
| --- | --- |
| ECF 21, Affirmation in Opposition, filed 2023-03-01 (the filing that first cited the fabricated cases) | `https://storage.courtlistener.com/recap/gov.uscourts.nysd.575368/gov.uscourts.nysd.575368.21.0.pdf` |
| ECF 24, Defendant's reply memorandum, filed 2023-03-15 | `https://storage.courtlistener.com/recap/gov.uscourts.nysd.575368/gov.uscourts.nysd.575368.24.0.pdf` |
| ECF 30, Defendant's letter, filed 2023-04-26 | `https://storage.courtlistener.com/recap/gov.uscourts.nysd.575368/gov.uscourts.nysd.575368.30.0.pdf` |
| ECF 31, Order to Show Cause, filed 2023-05-04 | `https://storage.courtlistener.com/recap/gov.uscourts.nysd.575368/gov.uscourts.nysd.575368.31.0.pdf` |
| ECF 45, Respondents' response to the Order to Show Cause, filed 2023-06-06 | `https://storage.courtlistener.com/recap/gov.uscourts.nysd.575368/gov.uscourts.nysd.575368.45.0.pdf` |
| ECF 54, Opinion and Order on Sanctions, filed 2023-06-22 | `https://storage.courtlistener.com/recap/gov.uscourts.nysd.575368/gov.uscourts.nysd.575368.54.0.pdf` |

Case-law lookups used the CourtListener v4 search API, which answers without authentication:

- Search endpoint: `https://www.courtlistener.com/api/rest/v4/search/?q=<query>&type=o`
- Each `expected` entry's `source_url` is the exact query URL that was retrieved and that
  supports that entry. Anonymous requests are limited to roughly ten per 36-second window
  and were paced at one request per five seconds; HTTP 429 responses were handled by waiting
  the number of seconds given in `Retry-After` and retrying.
- The API detail endpoints (`clusters/<id>/`, `opinions/<id>/`) return HTTP 401 without a
  token, and the public HTML pages return HTTP 202 with an empty body, so no opinion text was
  read from CourtListener.

Full text of one opinion was retrieved for quotation checking:

- Campbell v. Air Jamaica, Ltd., 760 F.3d 1165 (11th Cir. 2014), opinion as filed:
  `https://www.govinfo.gov/content/pkg/USCOURTS-ca11-12-14860/pdf/USCOURTS-ca11-12-14860-0.pdf`

One state-court order was retrieved from the issuing court's own website:

- 2018 IL App (2d) 170970-U, Order filed June 21, 2018, No. 2-17-0970, captioned
  *Pete Occhipinti v. City of De Kalb*:
  `https://www.illinoiscourts.gov/Resources/79bbe289-a03b-4df0-acc5-e9a0f8982584/2170970_R23.pdf`

## `avianca.json`

### What it is

A reconstruction of the argument in the March 1, 2023 Affirmation in Opposition (ECF 21),
the filing in which counsel for the plaintiff cited decisions that ChatGPT had produced.
The `text` is not a verbatim copy of ECF 21 and does not claim to be. The argument order, the
propositions and the citations are the brief's; the sentence wording is written for this
fixture. ECF 21 is an image-only PDF, so its ten pages were rendered at 300 dpi and read with
OCR, and every citation labelled in the notes as "filed" was read from that OCR output.
Verbatim text quoted in the file's `provenance` field states this too.

### What it tests

1. `fabricated_cite`: a citation whose case does not exist in the corpus at all.
2. `wrong_slot`: a citation whose reporter volume and page are held by a different, real case.
3. `wrong_court`: a citation naming a real case but attributing it to the wrong court.
4. Negative control: real authorities that a plaintiff in this position would cite, which
   must not be flagged.
5. Quotation verification: the `text` carries one quotation that is deliberately taken from
   the fabricated opinion and will not be found in the corpus, alongside quotations that are
   genuine.

### How ground truth was established

The controlling documents are the Court's Order to Show Cause of May 4, 2023 (ECF 31), which
states that "Six of the submitted cases appear to be bogus judicial decisions with bogus
quotes and bogus internal citations" and then names them, and the Opinion and Order on
Sanctions of June 22, 2023 (ECF 54), whose Findings of Fact 26 through 36 examine each
fabricated decision, and Finding of Fact 36 of which records that Respondents acknowledged
that the "Varghese", "Miller", "Petersen", "Shaboon", "Martinez" and "Durden" decisions were
generated by ChatGPT and do not exist. Every verdict in this file was additionally checked
against the CourtListener v4 search API by volume, reporter and page, and against a name
search. Where a reporter slot is occupied by a different real case, the occupant was verified
independently and recorded in `slot_occupied_by`.

### The record's list of fabricated citations

The six decisions that the May 4, 2023 Order to Show Cause (ECF 31) and the June 22, 2023
Opinion and Order (ECF 54, Finding of Fact 36) identify as fabricated are:

1. `Varghese v. China South Airlines Ltd, 925 F.3d 1339 (11th Cir. 2019)` (spelled
   "Varghese v. China Southern Airlines Co. Ltd." in ECF 21)
2. `Shaboon v. Egyptair, 2013 IL App (1st) 111279-U (Ill. App. Ct. 2013)`
3. `Petersen v. Iran Air, 905 F. Supp. 2d 121 (D.D.C. 2012)`
4. `Martinez v. Delta Airlines, Inc., 2019 WL 4639462 (Tex. App. Sept. 25, 2019)`
5. `Estate of Durden v. KLM Royal Dutch Airlines, 2017 WL 2418825 (Ga. Ct. App. June 5, 2017)`
6. `Miller v. United Airlines, Inc., 174 F.3d 366 (2d Cir. 1999)`

The March 1, 2023 Affirmation (ECF 21) also cited `Ehrlich v. American Airlines Inc. 360 N.J.
Super. 360 (App. Div. 2003)`. Avianca's letter of April 26, 2023 (ECF 30) states that the
*Ehrlich* and *In re Air Crash Disaster Near New Orleans* cases are the only ones it "has
always agreed ... do exist", and adds that "Plaintiff has attributed Ehrlich to the New Jersey
Appellate Division, when it is actually a Second Circuit case." ECF 21 further cited the real
`In re Air Crash Disaster Near New Orleans, La. 821 F.2d 1147, 1165 (5th Cir. 1987)`, and it
quoted a fabricated Eleventh Circuit decision purporting to be `Zicherman v. Korean Air Lines
Co., Ltd., 516 F.3d 1237, 1254 (11th Cir. 2008)`, a citation that Finding of Fact 29(e)
addresses.

### Verdicts in this file

| Citation as written in `text` | Verdict | Error class | Slot occupant |
| --- | --- | --- | --- |
| Varghese v. China Southern Airlines Co., 925 F.3d 1339, 1349 (11th Cir. 2019) | `fabricated` | `fabricated_cite` | J.D. v. Azar, 925 F.3d 1291 (D.C. Cir. 2019), recorded by the record for that page |
| Shaboon v. EgyptAir, 2013 IL App (1st) 111279-U (Ill. App. Ct. 2013) | `fabricated` | `fabricated_cite` | none found |
| Petersen v. Iran Air, 905 F. Supp. 2d 121 (D.D.C. 2012) | `fabricated` | `fabricated_case_name` | United States v. ISS Marine Services, Inc., 905 F. Supp. 2d 121 (D.D.C. 2012); the verdict was corrected from `miscited`, see the note below |
| Martinez v. Delta Air Lines, Inc., 2019 WL 1584623 (Tex. App. Apr. 11, 2019) | `fabricated` | `fabricated_cite` | none found |
| Ehrlich v. American Airlines, Inc., 360 F. Supp. 2d 1327 (S.D. Ga. 2005) | `miscited` | `wrong_slot` | Witex, U.S.A., Inc. v. United States, 360 F. Supp. 2d 1327 (Ct. Int'l Trade 2005) |
| Miller v. United Lumber & Supply Co., 2018 IL App (2d) 170970-U (Ill. App. Ct. 2018) | `fabricated` | `fabricated_cite` | Occhipinti v. City of De Kalb, 2018 IL App (2d) 170970-U (Ill. App. Ct. 2d Dist. June 21, 2018) |
| Martinez v. Delta Airlines, Inc., 2019 WL 4639462 (Tex. App. Sept. 25, 2019) | `fabricated` | `fabricated_cite` | none found |
| Estate of Durden v. KLM Royal Dutch Airlines, 2017 WL 2418825 (Ga. Ct. App. June 5, 2017) | `fabricated` | `fabricated_cite` | none found |
| Miller v. United Airlines, Inc., 174 F.3d 366, 371-72 (2d Cir. 1999) | `fabricated` | `fabricated_cite` | none found; see the note on Greenleaf v. Garlock, Inc., 174 F.3d 352 (3d Cir. 1999) |
| Ehrlich v. American Airlines, Inc., 360 N.J. Super. 360 (App. Div. 2003) | `miscited` | `wrong_court` | none found |
| Zicherman v. Korean Air Lines Co., 516 U.S. 217 (1996) | `real` | `none` | not applicable |
| El Al Israel Airlines, Ltd. v. Tsui Yuan Tseng, 525 U.S. 155, 156 (1999) | `real` | `none` | not applicable |
| Ehrlich v. American Airlines, Inc., 360 F.3d 366 (2d Cir. 2004) | `real` | `none` | not applicable |
| In re Air Crash Disaster Near New Orleans, 821 F.2d 1147, 1165 (5th Cir. 1987) | `real` | `none` | not applicable |
| Kaiser Steel Corp. v. W.S. Ranch Co., 391 U.S. 593 (1968) | `real` | `none` | not applicable |

### Where this file departs from the specification that requested it

The specification listed six citations as "the six fabricated decisions reported in the
sanctions opinion". Three of the six are supported by the record with different citation
data, and one decision the record identifies as fabricated is absent from the specification's
list. The departures are stated in the affected entries' `notes` fields and summarised here.

| Specification form | What the record shows | Source |
| --- | --- | --- |
| `Martinez v. Delta Air Lines, Inc., 2019 WL 1584623 (Tex. App. Apr. 11, 2019)` | The filed citation is `Martinez v. Delta Airlines, Inc., 2019 WL 4639462 (Tex. App. Sept. 25, 2019)`. No filing retrieved from the docket contains the Westlaw number 1584623 or the date April 11, 2019. | ECF 21 (OCR), ECF 24 n.1, ECF 31 |
| `Ehrlich v. American Airlines, Inc., 360 F. Supp. 2d 1327 (S.D. Ga. 2005)` | The filed citation is `Ehrlich v. American Airlines Inc. 360 N.J. Super. 360 (App. Div. 2003)`. No filing retrieved from the docket contains 360 F. Supp. 2d 1327 or the Southern District of Georgia. The record's *Ehrlich* citation is also not one of the six decisions the court found fabricated; Avianca conceded that the Ehrlich case exists. | ECF 21 (OCR), ECF 24 n.1, ECF 30 |
| `Miller v. United Lumber & Supply Co., 2018 IL App (2d) 170970-U (Ill. App. Ct. 2018)` | The filed citation is `Miller v. United Airlines, Inc., 174 F.3d 366 (2d Cir. 1999)`. No filing retrieved from the docket contains the name `Miller v. United Lumber & Supply Co.` or the citation 2018 IL App (2d) 170970-U. | ECF 21 (OCR), ECF 24, ECF 31 |
| absent from the specification's list | `Estate of Durden v. KLM Royal Dutch Airlines, 2017 WL 2418825 (Ga. Ct. App. June 5, 2017)` is one of the six decisions identified as fabricated, and is included in this file. | ECF 24 n.1, ECF 31, ECF 54 Finding of Fact 36 |

Because the specification's forms are not in the record, they appear in `text` only inside the
final section headed "CITATION VARIANTS SUPPLIED WITH THIS FIXTURE", which pairs each with
the form the brief actually filed. The verdict for each was still set on its own evidence and
is recorded in the table above.

### Judgment calls recorded in this file

- **Petersen.** The verdict for this entry was changed to `fabricated` after the fixture was
  first built; the change is recorded in the entry's `label_correction` field. The original
  label was `miscited`, and it followed an instruction in the task specification to classify
  this citation by its occupied reporter slot. That label contradicts two things. First, the
  definition this fixture states for the categories, which reserves `miscited` for a citation
  whose case exists; the source material states that this case does not exist. Second, the
  primary source the fixture itself cites: Finding of Fact 34 of the June 22, 2023 Opinion and
  Order (ECF 54) states "The 'Petersen' decision does not exist", and Finding of Fact 36 records
  the Respondents' admission that it was ChatGPT-generated. The verified slot fact is unaffected
  and is still recorded: 905 F. Supp. 2d 121 is held by *United States v. ISS Marine Services,
  Inc.* (D.D.C. 2012), so a tool that resolves citations by slot alone reaches a different
  answer. The engine under test reports `fabricated` for this entry from the case name alone and
  does not read the corrected label, so the correction does not flatter the implementation.
- **Miller v. United Airlines, Inc., 174 F.3d 366.** The verdict is `fabricated` on the court's
  finding (Finding of Fact 32: "The 'Miller' decision does not exist"; the Federal Reporter
  citation for "Miller" is to *Greenleaf v. Garlock, Inc.*, 174 F.3d 352 (3d Cir. 1999)). The
  engine under test reports `miscited` instead, because the corpus does contain a decision named
  *Miller v. United Airlines, Inc.* at 174 Cal. App. 3d 878 (Cal. Ct. App. 1985), which is a
  different decision from the Second Circuit case the document asserts. This is a difference in
  where the two categories are bounded, not an error in either reading: both conclusions state
  that the citation cannot be relied on. It is left in place rather than resolved by relabelling,
  because relabelling would remove the only measurement of that boundary from the results. It is
  counted as an error in the reported metrics.
- **Miller v. United Lumber & Supply Co.** The slot 2018 IL App (2d) 170970-U is real and is
  held by a different case, which is verified against the Illinois courts' own PDF, but no
  source I searched shows a case named *Miller v. United Lumber & Supply Co.* The verdict is
  therefore `fabricated`, and the verified slot occupant is recorded in `slot_occupied_by`
  because a tool that resolves this citation by slot rather than by name would reach
  `miscited`.
- **Ehrlich, both forms.** Both are `miscited` because the case named *Ehrlich v. American
  Airlines, Inc.* is real and is reported at 360 F.3d 366 (2d Cir. 2004). That makes these two
  entries the ones where the specification's list is most clearly wrong: the cited case
  exists, so the defect is in the reporter citation, the court and the year, not in the
  existence of the case.

## `real_brief.json`

### What it is

A composed passage in the register of a plaintiff's memorandum on the Montreal Convention's
limitations period and preemptive scope. It is not an excerpt from a filed document and the
file's `provenance` field says so. The specification for this file permits a passage composed
from real, individually verified citations. The subject matter and the citation set follow the
Convention arguments in the Mata v. Avianca record; `source_url` points to ECF 24, the reply
memorandum whose authorities and propositions most of the passage follows.

### What it tests

False positives. Every entry carries `verdict: "real"` and `error_class: "none"`. A tool that
reports any `fabricated` or `miscited` verdict on this document has produced a finding that
this corpus shows to be wrong. The document deliberately spans the court hierarchy that the
tool handles differently: 4 Supreme Court citations, 5 federal court of appeals citations
(Second Circuit twice, Eleventh Circuit twice, Ninth Circuit once), 2 federal district court
citations, and 3 state citations (New York Court of Appeals once, New York Appellate Division
twice). It also exercises quotation verification with two quotations that I verified against
retrieved opinion text.

### How ground truth was established

Each citation was checked by volume, reporter and page against the CourtListener v4 search
API, and the entry's `source_url` is the exact query URL that returns the named case with that
quoted citation; each entry's `notes` records how many results the query returned and which
result is the case. Propositions attributed to cases come either from the Mata filings that
used the same authorities (which supplies the pin cites for *Fishman*, *Mateo*, *Kahn*,
*Podraza* and *O'Hara*) or from the full text of *Campbell v. Air Jamaica, Ltd.*, retrieved
from the Government Publishing Office and read, which is where the pin cites and the
propositions for *Marotte* and *Pennington* also come from.

### Entries

| Citation | Court | Basis |
| --- | --- | --- |
| Air France v. Saks, 470 U.S. 392 (1985) | Supreme Court | citation query returned 354 results; Saks is among them with that citation |
| Eastern Airlines, Inc. v. Floyd, 499 U.S. 530 (1991) | Supreme Court | citation query returned 219 results; Floyd is among them with that citation |
| El Al Israel Airlines, Ltd. v. Tsui Yuan Tseng, 525 U.S. 155 (1999) | Supreme Court | citation query returned 258 results; Tseng is among them with that citation |
| Zicherman v. Korean Air Lines Co., 516 U.S. 217 (1996) | Supreme Court | citation query returned 158 results; the cluster with that citation is first |
| Ehrlich v. American Airlines, Inc., 360 F.3d 366 (2d Cir. 2004) | Second Circuit | citation query returned 68 results; Ehrlich is first with that citation |
| Fishman v. Delta Air Lines, Inc., 132 F.3d 138, 144 (2d Cir. 1998) | Second Circuit | citation query returned 49 results; Fishman is first with that citation |
| Campbell v. Air Jamaica, Ltd., 760 F.3d 1165 (11th Cir. 2014) | Eleventh Circuit | citation query returned 18 results; Campbell is first with that citation; full text read |
| Marotte v. American Airlines, Inc., 296 F.3d 1255, 1260 (11th Cir. 2002) | Eleventh Circuit | citation query returned 21 results; Marotte is first with that citation |
| Doe v. United States, 419 F.3d 1058 (9th Cir. 2005) | Ninth Circuit | citation query returned 57 results; Doe is first with that citation |
| Mateo v. JetBlue Airways Corp., 847 F. Supp. 2d 383, 387-88 (E.D.N.Y. 2012) | E.D.N.Y. | citation query returned 4 results; Mateo is first with that citation |
| Pennington v. British Airways, 275 F. Supp. 2d 601, 606-07 (E.D. Pa. 2003) | E.D. Pa. | citation query returned 4 results; Pennington is first with that citation |
| Kahn v. Trans World Airlines, Inc., 82 A.D.2d 696 (N.Y. App. Div. 1981) | N.Y. App. Div. | citation query returned 13 results; Kahn is first with that citation |
| Podraza v. Carriero, 212 A.D.2d 331 (N.Y. App. Div. 1995) | N.Y. App. Div. | citation query returned exactly 1 result, Podraza v. Carriero |
| O'Hara v. Bayliner, 89 N.Y.2d 636 (N.Y. 1997) | N.Y. | citation query returned 6 results; O'Hara v. Bayliner is first with that citation |

### Quotations in this file

Two quotations appear in `text`, and both were checked against the corpus rather than assumed.

1. Attached to *Campbell v. Air Jamaica, Ltd.*: "we agree with the consensus of courts that
   the Montreal Convention permits the application of Rule 15(c) relation back". Verified
   verbatim against the retrieved full text of the opinion, and a CourtListener phrase search
   for the sentence returns exactly 1 result, that case.
2. Attached to *Fishman v. Delta Air Lines, Inc.* at 144: "Almost every court that has
   reviewed the drafting minutes of the Convention". Verified in two ways: the words appear in
   the retrieved full text of *Campbell*, which quotes *Fishman* at that page, and a
   CourtListener phrase search for the words returns 2 results, one of which is *Fishman*
   itself at 132 F.3d 138, so the words are in *Fishman*'s own opinion text. The quotation is
   limited to that clause because *Campbell* inserts a bracketed article number into the rest
   of the sentence, and I could not confirm the underlying article number against *Fishman*'s
   text directly.

## What could not be fully verified

Recorded here so that no reader assumes more verification than was performed.

1. **The Westlaw citations.** CourtListener does not carry Westlaw-only citations. I could
   not test whether any Texas appellate decision bears the number 2019 WL 4639462 or 2019 WL
   1584623, or whether any Georgia appellate decision bears the number 2017 WL 2418825, and I
   had no access to Westlaw or Lexis. The verdicts for those three entries rest on the court's
   findings and on the Respondents' admission recorded in ECF 54 Finding of Fact 36, not on a
   corpus lookup.
2. **Illinois unpublished orders.** CourtListener does not index unpublished Illinois Rule 23
   orders. The zero results returned for "111279-U" and for "170970-U" are therefore weak
   evidence, and for `2018 IL App (2d) 170970-U` I replaced that weak evidence with the
   Illinois Administrative Office of the Courts PDF, which shows the slot is held by
   *Occhipinti v. City of De Kalb*. For `2013 IL App (1st) 111279-U` I could not reach an
   equivalent authoritative document: the order is from 2013, the Illinois courts website
   stores Rule 23 orders under opaque resource identifiers with no browsable index, and a
   search of that site and of the open web did not surface it. The `Shaboon` verdict rests on
   ECF 31, ECF 54 Finding of Fact 36 and the Respondents' admission.
3. **Existence of a New Jersey decision at 360 N.J. Super. 360.** A CourtListener citation
   query for that string returned 0 results, and CourtListener's coverage of the New Jersey
   Superior Court Appellate Division is incomplete. I could not verify that any New Jersey
   appellate decision is reported at 360 N.J. Super. 360, and I could not verify that none is
   either. The `miscited` verdict for that entry rests on the reporter, court and year mismatch
   that *is* verified: the real *Ehrlich* decision is 360 F.3d 366 (2d Cir. 2004).
4. **The origin of the specification's three altered citation forms.** I could not find where
   `Martinez v. Delta Air Lines, Inc., 2019 WL 1584623 (Tex. App. Apr. 11, 2019)`,
   `Ehrlich v. American Airlines, Inc., 360 F. Supp. 2d 1327 (S.D. Ga. 2005)` and
   `Miller v. United Lumber & Supply Co., 2018 IL App (2d) 170970-U (Ill. App. Ct. 2018)` come
   from. They appear in no filing in the docket that I retrieved. Separately, a secondary
   source consulted during the search, the Open Bankruptcy Project page on this case, states a
   different list of six fabricated decisions again, naming "Estate of Durden v. KLM Royal
   Dutch Airlines" and "Miller v. United Airlines"; it is not a primary source and I did not
   rely on it.
5. **Page 1339 inside J.D. v. Azar, and page 366 inside Greenleaf v. Garlock.** CourtListener
   indexes only the starting page of each case report, and its opinion-text endpoints return
   HTTP 401 without a token. I verified that 925 F.3d 1291 resolves to *J.D. v. Azar* and that
   no case begins at 925 F.3d 1339, and that 174 F.3d 352 resolves to *Greenleaf v. Garlock*
   and that no case begins at 174 F.3d 366, but I could not confirm from the corpus itself
   whether pages 1339 and 366 fall inside those two reports. For both, the record's statement
   is reproduced and attributed to the record in the entry's `notes`.
6. **Pin cites not read in the source report.** The pin cite 144 for *Fishman*, 156 for
   *El Al v. Tseng*, 1165 for *In re Air Crash Disaster*, 387-88 for *Mateo* and 606-07 for
   *Pennington* were taken from filings or opinions that use them (ECF 21, ECF 24, and the
   retrieved full text of *Campbell*), not read at that page of the reporter. No entry's
   verdict depends on a pin cite; the volume, reporter and page fields record the citation
   start page only.
7. **Full text of most real cases.** Full opinion text was retrieved and read only for
   *Campbell v. Air Jamaica, Ltd.* Full text could not be retrieved for the other thirteen
   cases in `real_brief.json`: `law.justia.com`, `openjurist.org` and the Library of Congress
   US Reports PDF path all rejected the requests, and the Government Publishing Office holds
   the *Campbell* package but returned a not-found page for the Second Circuit and Ninth
   Circuit docket numbers tried. Propositions attributed to those cases therefore rest either
   on the Mata filings that used them or on the verified text of *Campbell*, and each entry's
   `notes` says which.
8. **Propositions in `real_brief.json`.** The file is a composed passage, so its propositions
   are statements about what the cited cases hold. They are grounded in the sources listed
   above, but they were not each checked against the full text of the cited opinion, because
   of item 7. No entry's `verdict` depends on a proposition; the verdicts depend on whether
   the citation resolves to the named case.
9. **CourtListener caption renderings.** CourtListener sometimes renders a caption differently
   from the form used in these files. It writes the *Zicherman* cluster as "Zicherman Ex Rel.
   Estate of Kole v. Korean Air Lines Co.", the *Mateo* defendant as "Jetblue", the *Fishman*
   plaintiff with a repeated given name, and the *ISS Marine Services* case as "United States
   of America v. Iss Marine Services, Inc." These differences are noted in the relevant
   entries and do not affect the citations.

## Reproducing the verification

1. Fetch each entry's `source_url`. The CourtListener URLs are search API calls and answer
   without authentication; space them at least five seconds apart to stay inside the anonymous
   allowance, and wait the number of seconds in `Retry-After` on HTTP 429.
2. Compare the citation list of the returned clusters with the entry's `volume`, `reporter`
   and `page`. In several entries the named case is not the first result, because the search
   index also matches opinions that cite it; the entry's `notes` record where in the result
   list the case appears.
3. For the two entries whose `source_url` is not a CourtListener query, fetch the PDF and
   compare the caption and the reported citation.
