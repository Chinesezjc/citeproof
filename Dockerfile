# CiteProof runs as a single container: the API also serves the built frontend.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    CITEPROOF_CACHE_PATH=/data/cache.sqlite

WORKDIR /app

# Install the Python dependencies first so that editing the source does not
# invalidate the dependency layer.
COPY pyproject.toml README.md ./
COPY backend ./backend
RUN pip install --no-cache-dir .

# The frontend build is committed under frontend/dist, so the image does not need
# a Node toolchain. Rebuild it with `cd frontend && pnpm install && pnpm build`
# and commit the result when the interface changes.
COPY frontend/dist ./frontend/dist
COPY data ./data
COPY docs ./docs
COPY scripts ./scripts

# Writable location for the response cache and the persisted audit reports.
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

# Configuration is read from the environment. See .env.example:
#   COURTLISTENER_TOKEN     a free CourtListener API token
#   CITEPROOF_LLM_API_KEY   enables the proposition-support check
CMD ["sh", "-c", "exec python -m uvicorn citeproof.api:app --host 0.0.0.0 --port ${PORT}"]
