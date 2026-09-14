# Devpost submission text

Every field the LexHack 2026 submission form asks for, written to be pasted in. The form's
required fields are the project title and short description, the problem and solution summary,
the repository or live link, the demonstration video, and the tech stack. The remaining
sections are here because the form asks for them under "additional info" and because the
judging criteria weight documentation.

---

## Project title

CiteProof

## Short description (one line)

Audits the citations in a legal document against public case-law data, and reports which
authorities do not exist, which are cited with a citation that belongs to a different case, and
which the corpus cannot adjudicate.

## Inspiration

In March 2023 a filing in *Mata v. Avianca, Inc.* cited six decisions that did not exist. They
had been produced by a language model and passed on without being checked. The court's opinion
three months later documented each one.

That failure is not exotic. It is the predictable result of a system that produces fluent text
with no mechanism for distinguishing a real authority from a plausible one, in a domain where
the reader cannot tell the difference without doing the research. And it is detectable: the
cases either exist in public case-law data or they do not.

## What it does

Paste a brief. CiteProof extracts every case citation, checks each one against the CourtListener
case-law corpus, and reports one of four verdicts per citation:

- **Verified** — the case exists and the cited reporter citation is one of its recorded citations.
- **Fabricated** — no case matching the cited name exists.
- **Miscited** — the case exists, but the citation belongs to a different case, or contradicts
  the record on court or year.
- **Unverifiable** — the corpus could not adjudicate it. The finding states which evidence was
  missing.

Every finding shows its work: each query that was run with the number of results it returned,
the case record the citation resolved to with a link to CourtListener, the case that actually
holds the cited citation when that differs, the citations the corpus records for the resolved
case, and any advisory such as a year that disagrees with the record. The Markdown export prints
all of it, so a reader can reproduce the check rather than take the verdict on trust.

## How it works

The design follows from three measurements, each made against the live corpus before the
corresponding code was written.

**The case name decides whether the authority exists.** The corpus indexes a case name for every
opinion it holds, so absence of a name is a meaningful signal. It does not record a reporter
citation for every opinion: public-domain citations such as `2013 IL App (1st) 111279-U` are
often absent from the citation field even when the case is present. A tool that decided by
citation number alone would accuse real cases of being fabricated. Both parties in the name must
match, so a case sharing one party name is not accepted.

**The reporter citation decides which decision is meant.** One dispute produces several records
with different citations. For *Monell v. Department of Social Services* the corpus holds a
district decision at 357 F. Supp. 1051, a circuit decision at 532 F.2d 259, a certiorari grant
at 429 U.S. 1071, and the decision on the merits at 436 U.S. 658. A citation is confirmed only
by a record that both matches the name and lists the citation.

**A record that holds the citation but names a different case confirms nothing.** That is the
pattern of an invented authority. *Petersen v. Iran Air, 905 F. Supp. 2d 121* has a name that
does not exist while the citation number is held by *United States v. ISS Marine Services, Inc.*
Treating slot occupancy as confirmation would report the invented case as verified.

The third measurement is what the tool cannot do. Anonymous access to the corpus cannot resolve
a reporter citation to the case that holds it: a phrase search for `436 U.S. 658` returns 14,346
results, which are the opinions that mention the citation ranked by relevance, and the case
itself need not appear on the first page. CourtListener provides a citation-lookup endpoint for
that purpose and it requires an API token. So when a citation cannot be confirmed and nothing
contradicts it, the verdict is `unverifiable` and the finding names the missing evidence. The
tool abstains rather than guessing, because the cost of abstaining is a less informative report
and the cost of guessing is a false accusation against a real authority.

## Measured accuracy

Measured on 29 citations across two fixtures with hand-verified ground truth, using public
case-law data in anonymous access mode. `scripts/run_benchmark.py` reproduces it, and the
figures are displayed in the application.

| Class | Precision | Recall | F1 |
| --- | --- | --- | --- |
| Real | **1.000** | **1.000** | 1.000 |
| Fabricated | **1.000** | 0.875 | 0.933 |
| Miscited | 0.667 | **1.000** | 0.800 |

Verdict accuracy 28 of 29. The extractor found all 29 citations.

Precision for real citations is the figure that matters most: a tool that tells a lawyer a
correct citation is fabricated is worse than no tool. Neither real nor fabricated citations
recorded a single false accusation. The one error is a boundary case between the fabricated and
miscited categories, where the corpus contains a decision with the same name as the cited one
but from a different court and a different decade. It is documented in
`data/benchmark/README.md` and left in the measurement rather than resolved by relabelling,
because relabelling would remove the only measurement of that boundary.

## Ground truth

The fixtures are `data/benchmark/avianca.json` and `data/benchmark/real_brief.json`. Ground
truth was established from the RECAP docket for *Mata v. Avianca, Inc.*, including the 1 March
2023 Affirmation in Opposition (ECF 21, an image-only PDF that was OCR'd), the 15 March 2023
reply, the 4 May 2023 Order to Show Cause, and the 22 June 2023 Opinion and Order (ECF 54),
whose findings of fact name each non-existent decision.

`data/benchmark/README.md` records the primary source for every entry, the retrieval date, and
separately every claim that could not be verified. Westlaw citation numbers cannot be verified
without a subscription, so entries resting on the court's own findings say so.

The second fixture is the negative control: fourteen citations that are all real and correctly
cited. The engine must not accuse any of them, and does not. Discovery of one fixture was a
finding in itself: three of the six citation forms supplied to the research step from memory do
not appear in the docket at all, which is precisely the failure this tool exists to catch.

## Challenges

**The citation parser takes metadata from the wrong citation.** eyecite scans forward for a
court-and-year parenthetical when a citation has no court of its own, and can cross into the
next citation in the same sentence. In one documented sentence it reports the year 2019 for a
1996 decision. The year and the quoted parenthetical are read from a window bounded by the
neighbouring citations instead, which is a correction that has to be made deliberately because
the parser's own output looks plausible.

**Rate limiting shapes the architecture.** Anonymous access allows about ten requests in a
36-second window. An audit costs two requests per citation. The engine paces itself, caches
every response in SQLite so repeat audits make no upstream requests, and runs audits on a single
worker so concurrent submissions cannot exceed the allowance together.

**Being honest about abstention is the hard part of the interface.** Four verdicts rather than
two means the report has to make `unverifiable` feel like a result rather than a failure. It
carries the explanation of what was missing and why, and the decision table that produced it is
in the repository.

## What is next

- A free CourtListener API token switches the corpus client to exact citation resolution through
  the `citation-lookup` endpoint and makes the text of a cited authority readable, which turns
  the quotation check from a corpus-wide phrase search into a comparison against the source.
  The code path is implemented and exercised; the token is a configuration change.
- Advisory treatment analysis: whether an authority has been overruled or distinguished, from
  the citation graph the corpus exposes.
- Coverage for statutes and regulations, which are currently listed and reported as not checked.

## Built with

Python, FastAPI, Uvicorn, httpx, Pydantic, SQLite, eyecite, the CourtListener REST API v4,
React, TypeScript, Vite, Tailwind CSS, and an optional OpenAI-compatible language model for the
proposition-support check. Full disclosure, including which parts of the repository were written
with an AI assistant, is in `docs/AI-TOOLS.md`.

## Try it

- Repository: <https://github.com/Chinesezjc/citeproof>
- Run locally: `pip install -e . && python -m uvicorn citeproof.api:app --port 8000`, then open
  <http://localhost:8000>, press "Load example", and press "Audit citations".

## Submission checklist

| Requirement | Status |
| --- | --- |
| Project title and short description | Done, above. |
| Problem and solution | Done, above. |
| Working link or code repository | Done: <https://github.com/Chinesezjc/citeproof> |
| Demonstration video, 3 minutes or less | **Recorded, not yet hosted.** The recording is `docs/demo/citeproof-walkthrough.webm`, 1 minute 22 seconds. The rules require the video to be hosted on YouTube, Vimeo or Loom, so it has to be uploaded before submitting. `docs/VIDEO-SCRIPT.md` has narration to record over it if a narrated version is preferred. |
| Tech stack and credits | Done: `docs/AI-TOOLS.md`. |
| Screenshots | Done: `docs/screenshots/`, listed below. |

### What still has to be done outside this repository

1. **Upload the demonstration video** to YouTube, Vimeo or Loom and put the link in the
   submission. The rules do not accept a repository path for the video.
2. **Optionally deploy a live instance** so a reviewer can run an audit without cloning.
   `docs/DEPLOYMENT.md` covers this; it needs an account on a hosting platform, which is why
   it is not already done. The repository satisfies the rules on its own: they accept a public
   code repository in place of a live link.
3. **Supply a CourtListener API token** to the deployed instance to switch it from anonymous
   access to authenticated access. Without one the deployed instance still detects fabricated
   citations, which is the headline capability, but it cannot confirm a citation number and
   the proposition-support check reports `unknown`.
4. **Submit the entry on Devpost** before 27 September 2026, 5:00pm EDT.

### Screenshot order for the submission gallery

| File | Shows |
| --- | --- |
| `01-input.png` | The document input, the example loaders and the token notice. |
| `02-example-loaded.png` | The Avianca fixture loaded, before the audit. |
| `03-progress.png` | The audit running, with the live status line. |
| `04-report-summary.png` | The summary: citation integrity, the four counts, coverage. |
| `05-findings-evidence.png` | Findings with every query and its result count. |
| `06-slot-occupancy.png` | A fabricated case name whose citation number is held by another case. |
| `07-negative-control.png` | The all-real fixture at integrity 100 per cent, with no accusations. |
| `08-benchmark.png` | The measured precision and recall, and the confusion matrix. |

The walkthrough recording is at `docs/demo/citeproof-walkthrough.webm`. It runs 1 minute
22 seconds, and both the recording and the screenshots are produced by
`scripts/record_demo.py` against the running application.
| Declared pre-existing libraries and tools | `docs/AI-TOOLS.md` |
