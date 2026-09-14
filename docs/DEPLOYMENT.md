# Deployment

The application is a single process: FastAPI serves both the JSON API and the built frontend
from `frontend/dist`. One container, one port, no external services beyond the CourtListener
API. The response cache and the persisted audit reports live in `CITEPROOF_CACHE_PATH`
(default `data/cache/cache.sqlite`), so mount that path if you want the cache to survive a
restart.

> **Status of this document.** The container image has not been built or run, because no
> container runtime is installed on the machine this was developed on. The command line, the
> test suite, the API and the frontend have all been run and verified; the image definition
> has not. Treat the build as unverified until it has been run once.

## Configuration

Two environment variables change behaviour. Both are optional.

| Variable | Effect |
| --- | --- |
| `COURTLISTENER_TOKEN` | A free CourtListener API token. Switches the corpus client from anonymous access to authenticated access, which raises the request allowance and enables exact citation resolution and opinion text. |
| `CITEPROOF_LLM_API_KEY` | Enables the proposition-support check. Any OpenAI-compatible `/chat/completions` endpoint works; set `CITEPROOF_LLM_BASE_URL` and `CITEPROOF_LLM_MODEL` to match. |

Set `PORT` if the platform requires a specific port. The default is 8000.

## Docker, locally

```bash
docker build -t citeproof .
docker run --rm -p 8000:8000 -v citeproof-data:/data \
  -e COURTLISTENER_TOKEN=... \
  citeproof
```

Then open <http://localhost:8000>.

## Hugging Face Spaces

1. Create a Space with **Docker** as the SDK and a blank template.
2. Push this repository to the Space's git remote.
3. Add the Space's `README.md` front matter so the platform knows which port to publish:

   ```yaml
   ---
   title: CiteProof
   sdk: docker
   app_port: 8000
   ---
   ```

4. Add `COURTLISTENER_TOKEN` and, if a language model is wanted,
   `CITEPROOF_LLM_API_KEY` under the Space's settings, as secrets rather than as variables, so
   they are not printed in logs.

The free tier has limited memory and disk. The SQLite cache is small, but a Space restarts
without warning, so expect the cache to be cold after a restart. A cold audit in anonymous mode
takes roughly 7 seconds per citation.

## Render

Create a Web Service from the repository, choose the Docker environment, and set the health
check path to `/api/health`. Render injects `PORT`, which the image already honours. Add the
same two environment variables in the dashboard. The free tier has an ephemeral filesystem, so
the cache does not persist; attach a disk if that matters.

## Fly.io

```bash
fly launch --no-deploy          # accept the existing Dockerfile
fly secrets set COURTLISTENER_TOKEN=...
fly secrets set CITEPROOF_LLM_API_KEY=...
fly deploy
```

Add a volume for `/data` if the cache should persist, and set
`internal_port = 8000` in `fly.toml` under `[http_service]`.

## Verifying a deployment

```bash
curl -s https://<host>/api/health
```

`case_law_access` reports `token` or `anonymous`, which is how you confirm the token reached
the process. Then load <https://<host>/> , press "Load example", and press "Audit citations".
The all-real fixture must report integrity 100 per cent with no fabricated or miscited
findings; if it reports anything else, the deployment is not behaving as the measured results
in the README describe, and the discrepancy needs investigating before submitting.
