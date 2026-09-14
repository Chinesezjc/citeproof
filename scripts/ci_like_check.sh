#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

: "${SKIP_VIDEO:=0}"
: "${API_PORT:=8000}"
API_URL="http://127.0.0.1:${API_PORT}"

log(){ echo "[$(date '+%H:%M:%S')] $*"; }

log "Checking environment"
./.venv/bin/python -m pip show -q -q citeproof >/dev/null 2>&1 || {
  ./.venv/bin/pip install -e .
}

log "Running unit tests"
./.venv/bin/pytest -q

log "Running CLI smoke checks"
set +e
./.venv/bin/python scripts/run_audit.py data/examples/fabricated_and_miscited_citations.txt > /tmp/lexhack_cli_smoke.txt 2>&1
cli_rc=$?
set -e

if [[ ! -s /tmp/lexhack_cli_smoke.txt ]]; then
  echo "CLI smoke did not produce output"
  exit 1
fi

cat /tmp/lexhack_cli_smoke.txt
if [[ $cli_rc -ne 0 ]]; then
  log "CLI smoke returned exit code $cli_rc; continuing because results are domain feedback"
fi

log "Running API smoke flow"
./scripts/demo_local.sh > /tmp/lexhack_api_smoke.txt 2>&1 || {
  echo "API smoke execution failed"
  cat /tmp/lexhack_api_smoke.txt || true
  exit 1
}

log "Verifying API smoke flow output"
if ! grep -q "Demo flow complete" /tmp/lexhack_api_smoke.txt; then
  cat /tmp/lexhack_api_smoke.txt
  exit 1
fi

start_api_for_recording() {
  log "Starting temporary API server for recording"
  ./.venv/bin/python -m uvicorn citeproof.api:app --port "$API_PORT" > /tmp/lexhack_record_api.log 2>&1 &
  REC_API_PID=$!
  for i in $(seq 1 30); do
    if curl -sSf "$API_URL/api/health" >/tmp/lexhack_health_for_recording.json 2>/tmp/lexhack_health_for_recording.err; then
      log "Temporary API server ready"
      return 0
    fi
    sleep 1
  done
  echo "Temporary API server failed to start"
  cat /tmp/lexhack_record_api.log
  return 1
}

stop_api_for_recording() {
  if [[ -n "${REC_API_PID:-}" ]] && kill -0 "$REC_API_PID" 2>/dev/null; then
    kill "$REC_API_PID"
    wait "$REC_API_PID" 2>/dev/null || true
  fi
}

if [[ "$SKIP_VIDEO" == "0" ]]; then
  log "Checking Playwright availability"
  if ! ./.venv/bin/python -c 'import playwright' >/dev/null 2>&1; then
    log "Installing the playwright package (no browser download: the recorder drives the system Chrome)"
    ./.venv/bin/pip install playwright >/tmp/lexhack_pw_install.log 2>&1 || true
  fi

  if ./.venv/bin/python - <<'PY'
import importlib.util,sys
sys.exit(0 if importlib.util.find_spec('playwright') else 1)
PY
  then
    API_HAD_TO_START=0
    if ! curl -sSf "$API_URL/api/health" >/tmp/lexhack_health_for_recording.json 2>/tmp/lexhack_health_for_recording.err; then
      start_api_for_recording || {
        log "Recording skipped: temporary API server could not be started"
        exit 0
      }
      API_HAD_TO_START=1
      trap stop_api_for_recording EXIT
    fi

    log "Running local recording"
    set +e
    ./.venv/bin/python scripts/record_demo.py --url "$API_URL" --out docs/demo --screenshots docs/screenshots
    rec_rc=$?
    set -e
    if [[ $rec_rc -ne 0 ]]; then
      log "Recording returned exit code $rec_rc; continuing because smoke checks succeeded"
    fi
    if [[ "$API_HAD_TO_START" == "1" ]]; then
      stop_api_for_recording
      trap - EXIT
    fi
  else
    log "Skipping recording: playwright module not available"
  fi
else
  log "SKIP_VIDEO=1, skipping recording"
fi

log "All checks done"
