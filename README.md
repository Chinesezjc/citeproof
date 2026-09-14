# CiteProof

CiteProof audits the citations in a legal document. It extracts every case citation,
checks each one against the CourtListener case-law corpus, and reports per citation
whether the authority is real, does not exist, or is real but cited with a reporter
citation that belongs to a different case. It also checks whether quoted language
attributed to an authority appears in that authority.

Built for LexHack 2026, in the tracks **AI Safety, Ethics & Governance** and **Access to
Justice & Civic Tech**.

## The problem

On 1 March 2023, lawyers filed an affirmation in opposition in *Mata v. Avianca, Inc.*,
No. 22-cv-1461 (S.D.N.Y.). On 22 June 2023 the court found that six of the decisions cited
in it did not exist, and that the filing's author had obtained them from a language model.
The findings are quoted, with the docket citations, in
[`data/benchmark/README.md`](data/benchmark/README.md).

A citation that does not exist is not a typographical error. A reader who follows it finds
nothing, and the argument it was offered to support has no authority behind it. The
failure is also cheap to detect from public data, which is what this tool does.

## What is checked

For each case citation the audit reports one of four verdicts.

| Verdict | Meaning |
| --- | --- |
| `verified` | The case exists in the corpus and the cited reporter citation is one of its recorded citations. |
| `fabricated` | No case matching the cited name exists in the corpus. |
| `miscited` | The case exists, but the cited reporter citation belongs to a different case, or contradicts the record on court or year. |
| `unverifiable` | The corpus could not adjudicate the citation. The finding states which evidence was missing. |

Alongside the verdict, each finding carries a confidence, the explanation, every query that
was run and the number of results it returned, the case record the citation resolved to with
a link to CourtListener, the case that actually holds the cited citation when that differs,
the citations the corpus records for the resolved case, and any advisories such as a year or
court that disagrees with the record.

## Measured accuracy

Measured by `scripts/run_benchmark.py` on 29 citations across two fixtures with hand-verified
ground truth, using the corpus in anonymous access mode. Run `python scripts/run_benchmark.py`
to reproduce it; the produced figures are also displayed in the application.

| Class | Precision | Recall | F1 | tp / fp / fn |
| --- | --- | --- | --- | --- |
| `real` | **1.000** | **1.000** | 1.000 | 19 / 0 / 0 |
| `fabricated` | **1.000** | 0.875 | 0.933 | 7 / 0 / 1 |
| `miscited` | 0.667 | **1.000** | 0.800 | 2 / 1 / 0 |

Verdict accuracy 28/29 (96.6%). The extractor found all 29 citations; none was missed.

The precision of `real` and `fabricated` is the number that matters most here. A tool that
tells a lawyer a correct citation is fabricated is worse than no tool, so the engine is built
to abstain rather than guess, and both of those classes recorded no false accusations. The
single error is one boundary case between `fabricated` and `miscited`, described in
[`data/benchmark/README.md`](data/benchmark/README.md) under "Judgment calls"; it is left in
the measurement rather than resolved by relabelling.

The fixtures are described in [`data/benchmark/README.md`](data/benchmark/README.md), which
records the primary source for every entry, the retrieval date, and every item that could not
be verified. The fixtures are public third-party court documents and are not this project's
own work.

## How a citation is decided

The full description is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). The parts that
determine what the tool claims are:

1. **The case name decides whether the authority exists.** The corpus indexes a case name for
   every opinion it holds, so a name search is the reliable test. Both parties must match, so
   that a case sharing one party name is not accepted. Party names the document abbreviates
   are matched against longer recorded names.
2. **The reporter citation decides which decision is meant.** One dispute produces several
   records with different citations: a district decision, a circuit decision, a certiorari
   grant and the decision on the merits are separate records. A citation is only confirmed
   when a record that both matches the name and lists the citation is found.
3. **A record that holds the citation but names a different case confirms nothing.** That
   pattern is how a fabricated name is paired with a real citation number, and treating it as
   confirmation would mark an invented authority as verified.
4. **Absence of a citation is not proof that a citation is wrong.** The corpus does not record
   a reporter citation for every opinion it holds, and public-domain citations such as
   `2013 IL App (1st) 111279-U` are frequently absent from the citation field even when the
   case is present. When a citation cannot be confirmed and nothing positively disagrees with
   it, the verdict is `unverifiable` and the finding names the missing evidence instead of
   guessing.

Every finding can be audited against the queries it was derived from, and the Markdown export
prints them.

## Quick start

Requires Python 3.11 or newer. No configuration is needed; the application starts in anonymous
access mode.

```bash
python3 -m venv .venv
./.venv/bin/pip install -e .
./.venv/bin/python -m uvicorn citeproof.api:app --port 8000
```

Open <http://localhost:8000>, press "Load example", then "Audit citations". The built
interface is committed under `frontend/dist` and served by the API, so no Node toolchain is
needed to run it. The first example
is the Avianca material with fabricated and miscited citations; the second contains only real,
correctly cited authorities and is the negative control.

To build the frontend rather than use a prebuilt one:

```bash
cd frontend && pnpm install && pnpm build
```

The built files in `frontend/dist` are served by the API at `/`.

### Tests

The test suite runs without network access. It is an extra, so it is not installed by
`pip install -e .`:

```bash
./.venv/bin/pip install -e ".[dev]"
./.venv/bin/python -m pytest backend/tests -q
```

47 tests, about 0.1 seconds.

### Demo interaction script

Use a local script that starts the backend, checks health, creates a sample audit, polls it,
and prints the markdown report:

```bash
./scripts/demo_local.sh
```

To avoid cache interference or port conflicts:

```bash
API_PORT=8001 ./scripts/demo_local.sh
```

To start the frontend too and keep the browser session open for manual interaction:

```bash
START_FRONTEND=1 WAIT_FOR_INTERACTION=1 ./scripts/demo_local.sh
```

`START_FRONTEND=1` starts `pnpm dev` on port 5173 and opens the page automatically when `open` is available.
`WAIT_FOR_INTERACTION=1` keeps both backend and frontend processes alive after the sample audit completes.

The script exits non-zero if the backend is not reachable, frontend fails to start, or the sample audit fails.

### Demo recording

A recording script is provided for generating the benchmark walkthrough assets:

```bash
./.venv/bin/python scripts/record_demo.py --url http://127.0.0.1:8000 --out docs/demo --screenshots docs/screenshots
```

The script requires Playwright in the project environment:

```bash
./.venv/bin/pip install playwright
./.venv/bin/playwright install chromium
```

The generated outputs are consumed as evidence and optional upload source for the final video.

### Command line

```bash
./.venv/bin/python scripts/run_audit.py data/examples/fabricated_and_miscited_citations.txt
./.venv/bin/python scripts/run_audit.py brief.txt --deep --markdown-out report.md
./.venv/bin/python scripts/run_benchmark.py
```

`run_audit.py` exits non-zero when the document contains a fabricated or miscited citation,
so it can be used as a check.

## Configuration

Copy `.env.example` to `.env`. Every setting is optional.

| Variable | Effect |
| --- | --- |
| `COURTLISTENER_TOKEN` | A free CourtListener API token. See "Access modes" below. |
| `CITEPROOF_LLM_API_KEY` | Enables the proposition-support check. Any OpenAI-compatible `/chat/completions` endpoint works. |
| `CITEPROOF_LLM_BASE_URL`, `CITEPROOF_LLM_MODEL` | Which endpoint and model the support check uses. |
| `CITEPROOF_CACHE_PATH` | Where upstream responses are cached. |
| `CITEPROOF_MIN_INTERVAL_TOKEN`, `CITEPROOF_MIN_INTERVAL_ANON` | Seconds between upstream requests in each mode. |

Every upstream response is cached in SQLite, so re-auditing a document, or auditing a second
document that cites the same authorities, performs no upstream requests.

An audit costs two upstream requests per case citation, plus one more when a citation is not
confirmed and the reporter implies a court. In anonymous access mode requests are paced to stay
inside the corpus allowance, and that pacing dominates the runtime: a cold-cache audit of the
14-citation fixture measured **2 minutes 35 seconds**, about 11 seconds per citation. With a
token, the same audit completes in seconds. A cached audit performs no upstream requests and
finishes in milliseconds.

### Access modes

CourtListener's API works with and without a token, and the difference is a capability
boundary rather than a performance setting. Measured on 11 September 2026:

| | Anonymous | With a token |
| --- | --- | --- |
| Rate limit | About 10 requests per 36-second window, then HTTP 429 with `Retry-After: 36` | Not throttled at that level |
| Case name search | Available | Available |
| `citation-lookup` endpoint | HTTP 401 | Available; resolves many citations per request and returns the case that holds each citation |
| Opinion text | HTTP 401 | Available; required to compare a quotation against the text of the cited authority |

Without a token the tool relies on the case name to establish existence and on the citation
lists in search results to confirm a citation. The `/c/` citation resolver on the CourtListener
website is unavailable to automated clients, and the public opinion pages answer HTTP 202 with
an empty body, so a quotation can only be searched corpus-wide: that establishes whether a
phrase occurs anywhere in the corpus, not whether it comes from the cited authority. The
finding states which of those two checks was performed.

## API

| Endpoint | Description |
| --- | --- |
| `GET /api/health` | Access mode, whether a language model is configured, cache path. |
| `GET /api/examples` | The bundled demonstration documents. |
| `POST /api/extract` | Extract citations without contacting the corpus. |
| `POST /api/audits` | Start an audit. Returns a job; poll it. |
| `POST /api/audits/file` | Same, from an uploaded `.txt`, `.md` or `.docx` file. |
| `GET /api/audits/{id}` | Job status, progress and, when finished, the report. |
| `GET /api/audits/{id}/markdown` | The report as Markdown. |
| `GET /api/audits/{id}/json` | The report as JSON. |
| `GET /api/benchmark` | The measured accuracy figures. |
| `GET /api/stats` | Number of cached upstream responses. |

Audits run one at a time on a single worker so that concurrent submissions cannot exceed the
anonymous request allowance.

## The proposition-support check

With a language model configured and `deep` enabled, each citation is additionally reviewed
for whether the cited authority supports the proposition the sentence asserts. The model is
given the citing sentence and passages retrieved from the cited authority, and is instructed
to judge only from those passages and to answer `unknown` when they are insufficient. A
quotation the model returns as its evidence is discarded unless that text occurs in the
passages it was given, so a fabricated phrase cannot be presented as the reason for a verdict.
Passages are selected from the authority by lexical overlap with the citing sentence, and the
finding records that the passage was selected this way.

**This check needs a CourtListener token to produce a verdict.** Judging whether an authority
supports a proposition requires the text of that authority. In anonymous access mode the corpus
cannot return it: a search for an authority returns the opinions that *mention* it, and using
one of those as the authority's text would make the verdict describe the wrong document. The
check therefore only accepts a passage that comes from the cited authority itself, and without
a token it reports `unknown` together with that reason. Verified against the live model: a
passage that supports the proposition is reported as `supported`, a passage stating the
opposite as `contradicted`, and no passage at all leaves the model uncalled.

This check is off by default because it costs one model call per citation.

## Limitations

- **The corpus does not hold every opinion ever issued.** A citation that cannot be found is
  not proof that the authority was invented. The tool's fabrications are based on the case
  name being absent, which is a strong signal but not a proof of intent, and non-existence in
  this corpus is not the same as non-existence.
- **Anonymous mode cannot confirm a citation number.** See "Access modes".
- **Only case-law authorities are verified.** Statutes, regulations and journal articles are
  listed and counted, and reported as not checked. No statute or regulation corpus is queried.
- **A citation whose case name the document abbreviates beyond recognition may not resolve.**
  Abbreviated party names are matched against longer recorded names, but an abbreviation that
  shares no token with the recorded name will not be matched.
- **Confidence values are heuristic.** They express how strong the corpus evidence was, not a
  calibrated probability.
- **The pinned page of a citation is not verified.** The corpus indexes the first page of each
  case, so a pin cite such as `1349` cannot be checked, and the audit does not claim to.
- **The tool reports on citations, not on the law.** A `verified` verdict means the authority
  exists and the citation points at it. It does not mean the authority is on point, still good
  law, or correctly applied.

## Repository layout

```
backend/citeproof/       the audit engine
  extract.py             citation extraction and bounded metadata
  normalize.py           citation keys, case-name and quotation comparison
  courtlistener.py       paced, cached, retrying corpus client
  verify.py              the verdict logic
  llm.py                 the proposition-support client
  report.py              Markdown and JSON rendering
  api.py                 HTTP API and job runner
backend/tests/           47 tests, no network access
frontend/                React + TypeScript + Tailwind user interface
data/benchmark/          fixtures with hand-verified ground truth
data/examples/           the demonstration documents, generated from the fixtures
scripts/                 command line entry points
docs/                    architecture, and the AI tool disclosure
```

## Tech stack and credits

See [`docs/AI-TOOLS.md`](docs/AI-TOOLS.md) for the full disclosure, including which parts of
this repository were written with an AI assistant.

- [eyecite](https://github.com/freelawproject/eyecite) (Free Law Project) extracts citations
  and resolves reporter abbreviations.
- [CourtListener](https://www.courtlistener.com/help/api/rest/) (Free Law Project) provides
  the case-law corpus.
- Python, FastAPI, Uvicorn, httpx, Pydantic, SQLite.
- React, TypeScript, Vite, Tailwind CSS.

## Licence

MIT. See [`LICENSE`](LICENSE). The benchmark fixtures are public court documents used as test
data and are not covered by this project's licence; their sources are recorded in
[`data/benchmark/README.md`](data/benchmark/README.md).
