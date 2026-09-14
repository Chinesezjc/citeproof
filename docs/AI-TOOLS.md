# Tool disclosure

This file records every third-party component, API and AI tool used to build or run
CiteProof, as required by the LexHack 2026 submission requirements.

## AI tools used to build this project

The code in this repository was written with **DeepSeek Harness**, an agentic coding tool, in
a session driven by the sole team member. The team member directed the work, chose the project
and its scope, and holds responsibility for every claim in it. Recording this plainly, because
the submission rules require participants to be able to explain how their code operates, and
because a project about unfounded citations should be exact about its own provenance.

What this means concretely:

- Every architectural decision described in `docs/ARCHITECTURE.md` is documented in the
  repository with the measurement that produced it. The reasons for the verdict logic, the
  three fields that are deliberately not taken from the citation parser, and the decision to
  abstain rather than guess are all written down where they can be checked.
- The correctness evidence is mechanical rather than a claim of diligence: 47 tests under
  `backend/tests`, a benchmark with hand-verified ground truth under `data/benchmark`, and a
  two-way control that includes a document of only real, correctly cited authorities which the
  engine must not accuse. The accuracy figures in the README are produced by
  `scripts/run_benchmark.py`, which anyone can run.
- No source file was written by an AI tool that was not also read, run and tested in this
  repository. The behaviour each test asserts was observed on the real corpus before the test
  was written: several tests exist because the engine was wrong in a way that a run on real
  data exposed.

The engine's own use of a language model is separate and optional. See "Language model used at
runtime" below.

## Language model used at runtime

The proposition-support check (`backend/citeproof/llm.py`) sends one request per citation to an
OpenAI-compatible `/chat/completions` endpoint. It is disabled unless `CITEPROOF_LLM_API_KEY`
is set and the audit requests `deep`. The model used during development was DeepSeek
(`deepseek-chat`, model identifier `deepseek-flash`); any compatible endpoint can be substituted
through `CITEPROOF_LLM_BASE_URL` and `CITEPROOF_LLM_MODEL`.

That check is the only runtime dependence on a language model. The existence checks, citation
checks and quotation checks are deterministic and work with no model configured.

## Libraries and frameworks

| Component | Role |
| --- | --- |
| [eyecite](https://github.com/freelawproject/eyecite) (Free Law Project) | Citation extraction and reporter-abbreviation resolution. |
| [CourtListener REST API v4](https://www.courtlistener.com/help/api/rest/) (Free Law Project) | The case-law corpus: case search and citation lookup. |
| Python 3.11+ | Backend language. |
| [FastAPI](https://fastapi.tiangolo.com/) | HTTP API. |
| [Uvicorn](https://www.uvicorn.org/) | ASGI server. |
| [httpx](https://www.python-httpx.org/) | Upstream HTTP client. |
| [Pydantic](https://docs.pydantic.dev/) | Data models and validation. |
| [python-docx](https://python-docx.readthedocs.io/) | Reading `.docx` uploads. |
| SQLite (Python standard library) | Cache of upstream responses, and audit persistence. |
| [pytest](https://pytest.org/) | Test runner. |
| [React](https://react.dev/) and [TypeScript](https://www.typescriptlang.org/) | Frontend. |
| [Vite](https://vite.dev/) | Frontend build. |
| [Tailwind CSS](https://tailwindcss.com/) | Frontend styling. |

## Public data used as test fixtures

The benchmark documents under `data/benchmark/` are public third-party court documents and court
records. They are test data, not the project's own work, and they are not covered by this
project's licence. Every entry records its primary source URL, the retrieval date and what was
verified. Sources used:

- The RECAP docket for *Mata v. Avianca, Inc.*, No. 22-cv-1461 (PKC) (S.D.N.Y.), including the
  1 March 2023 Affirmation in Opposition (ECF 21), the 15 March 2023 reply (ECF 24), the 4 May
  2023 Order to Show Cause (ECF 31) and the 22 June 2023 Opinion and Order (ECF 54).
- The CourtListener REST API, for case records and citation lists.
- The Illinois courts' published PDF of *Occhipinti v. City of De Kalb*, 2018 IL App (2d)
  170970-U.
- govinfo, for the full text of one opinion used to verify a quotation.

`data/benchmark/README.md` lists, separately and explicitly, every claim that could not be
verified. Those entries record which verdicts rest on the court's own findings rather than on an
independent corpus check, because Westlaw and Lexis citation numbers cannot be verified without
a subscription.

## Items deliberately not used

- No Westlaw, Lexis or other subscription citator. That is the limitation the `miscited` class
  is bounded by, and the benchmark documents it.
- No web scraping of CourtListener's HTML pages: they answer automated requests with HTTP 202
  and an empty body, and the API is the supported interface.
- No training data, model or corpus of this project's own. Every authority the tool verifies
  comes from the CourtListener API at audit time.
