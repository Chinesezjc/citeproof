# Demonstration video script

Target length 2 minutes 55 seconds. The video must show the working software, so every claim
in it is made against the running application rather than described.

## Before recording

1. Start the application with a **cold cache** so the audit runs in real time and the progress
   display is visible:
   ```bash
   rm -f data/cache/cache.sqlite
   ./.venv/bin/python -m uvicorn citeproof.api:app --port 8000
   ```
2. Open <http://localhost:8000> and check that the notice about running without an API token is
   visible. That notice is part of what the video shows.
3. Have the two examples ready. Load the first one, then the second.

If a CourtListener API token has been configured by then, say so when the notice is absent and
say what it changes: exact citation resolution and comparison of a quotation against the text
of the cited authority.

## Shots

### 0:00 – 0:25 The problem

Screen: the CourtListener record for *Mata v. Avianca, Inc.*, and then the benchmark README
showing the primary source.

Narration:

> In March 2023 a law firm filed an affirmation citing six decisions. According to the court's
> opinion three months later, none of the six existed. They had been produced by a language
> model. A citation that does not exist is not a typo: a reader who follows it finds nothing,
> and the argument it was offered to support has no authority behind it.
>
> CiteProof audits a document for exactly that failure, using public case-law data.

### 0:25 – 0:40 What it does

Screen: the application with an empty input.

Narration:

> Paste a brief. CiteProof extracts every case citation, checks each one against the
> CourtListener corpus, and reports four verdicts: verified, fabricated, miscited, or
> unverifiable when the corpus cannot adjudicate it.

### 0:40 – 1:30 The audit, in real time

Screen: paste the first example (`fabricated_and_miscited_citations`), press **Audit citations**,
let the progress bar and the live status message run, then the summary.

Narration while it runs:

> The document is a reconstruction of the citations from that affirmation, with five real
> air-carriage authorities mixed in. The progress line reports each authority as it is checked.
> Each citation costs two requests to the corpus, and without an API token those requests are
> paced, which is why this takes about a minute.

Screen: the summary header, then expand the first finding.

Narration:

> The headline number is citation integrity: the share of citations the corpus could adjudicate
> that resolved correctly. Expand a finding and the audit shows its work. Here is the search for
> the case name, and here is the search for the reporter citation, with the number of results
> each returned. Varghese v. China Southern Airlines at 925 F.3d 1339 does not exist as a case
> name and no case holds that citation.

Screen: expand the finding for *Petersen v. Iran Air*.

Narration:

> This one is worth pausing on. The name does not exist, but the citation number does: it is
> held by United States v. ISS Marine Services. That is how an invented authority is made to
> look plausible, so a tool that resolved citations by number alone would call this verified.
> CiteProof requires the record to carry the case name as well.

### 1:30 – 1:50 The negative control

Screen: load the second example (`all_citations_verified`) and run the audit.

Narration:

> A tool that flags real citations is worse than no tool, so the second example contains only
> real, correctly cited authorities. Fourteen citations, and the audit accuses none of them.

Screen: the summary showing integrity 100 per cent and no fabricated or miscited findings.

### 1:50 – 2:10 A real case with a wrong citation

Screen: back to the first example, expand the *Miller v. United Lumber* and *Ehrlich* findings.

Narration:

> Not every problem is an invented case. Here the case exists but the citation does not point
> at it. The finding names the case that actually holds that citation number, and gives the
> citation the corpus records for the case the document meant.

### 2:10 – 2:30 Measured accuracy

Screen: the benchmark panel in the application.

Narration:

> The accuracy is measured, not asserted. Twenty-nine citations across two fixtures, each with
> ground truth established from the docket, produce these figures. Precision for real citations
> is one: the tool does not accuse a correct authority. Precision for fabricated citations is
> also one. The single error is a documented boundary case between two categories.

### 2:30 – 2:50 How it decides

Screen: the decision table from `docs/ARCHITECTURE.md`, or a simple diagram of the same.

Narration:

> The design follows from one measurement. The corpus records a case name for every opinion it
> holds, but it does not record a reporter citation for every opinion, and a search for a
> citation returns the opinions that mention it rather than the case that holds it. So the name
> decides whether the authority exists, the citation decides which decision in a dispute is
> meant, and when neither can be established the report says so instead of guessing. That
> limitation is printed in every report.

### 2:50 – 2:55 Close

Screen: the repository URL and the application.

Narration:

> CiteProof. The audit, the benchmark and every query behind every verdict are in the
> repository.

## Claims to avoid

- Do not say the corpus contains every decided case. It does not, and the README states the
  limitation.
- Do not say a citation is fabricated when the finding says `unverifiable`.
- Do not present the demonstration document as a verbatim copy of a filed brief. It is a
  reconstruction, and `data/benchmark/avianca.json` says so in its `provenance` field.
- Do not describe the confidence values as calibrated probabilities. They express the strength
  of the corpus evidence.
