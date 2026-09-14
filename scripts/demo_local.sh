#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8000}"
API_URL="http://127.0.0.1:${API_PORT}"
FE_PORT="${FE_PORT:-5173}"
START_FRONTEND="${START_FRONTEND:-0}"
WAIT_FOR_INTERACTION="${WAIT_FOR_INTERACTION:-0}"

cleanup() {
  if [[ -n "${API_PID:-}" ]] && kill -0 "$API_PID" 2>/dev/null; then
    kill "$API_PID"
    wait "$API_PID" 2>/dev/null || true
  fi
  if [[ -n "${FE_PID:-}" ]] && kill -0 "$FE_PID" 2>/dev/null; then
    kill "$FE_PID"
    wait "$FE_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

./.venv/bin/python -m uvicorn citeproof.api:app --port "$API_PORT" > /tmp/lexhack_local_api.log 2>&1 &
API_PID=$!

echo "Backend pid: $API_PID ($API_URL)"

if [[ "$START_FRONTEND" == "1" ]]; then
  FE_PWD="$PWD"
  cd frontend
  pnpm dev --host 127.0.0.1 --port "$FE_PORT" > /tmp/lexhack_local_vite.log 2>&1 &
  FE_PID=$!
  cd "$FE_PWD"
  for i in $(seq 1 30); do
    if curl -sSf "http://127.0.0.1:$FE_PORT" > /tmp/lexhack_frontend.txt 2>/dev/null; then
      echo "Frontend pid: $FE_PID, serving http://127.0.0.1:$FE_PORT"
      break
    fi
    sleep 1
    if [[ "$i" -eq 30 ]]; then
      echo "Frontend did not become ready."
      cat /tmp/lexhack_local_vite.log
      exit 1
    fi
  done
  if command -v open >/dev/null 2>&1; then
    open "http://127.0.0.1:$FE_PORT"
  fi
fi

for i in $(seq 1 30); do
  if curl -sSf "$API_URL/api/health" > /tmp/lexhack_health.json 2>/tmp/lexhack_health.err; then
    echo "Backend health OK"
    break
  fi
  sleep 1
  if [[ "$i" -eq 30 ]]; then
    echo "Backend did not become ready."
    cat /tmp/lexhack_local_api.log
    exit 1
  fi
done

audit_payload='{"text":"This court held in Smith v. Jones, 123 F.3d 456 (9th Cir. 2010), that clear findings are required.","deep":false}'
audit_response=$(curl -sS -X POST "$API_URL/api/audits" \
  -H 'Content-Type: application/json' \
  -d "$audit_payload")

audit_id=$(printf '%s' "$audit_response" | ./.venv/bin/python -c 'import sys, json; print(json.loads(sys.stdin.read()).get("audit_id", ""))')

if [[ -z "$audit_id" ]]; then
  echo "Failed to create audit"
  echo "$audit_response"
  exit 1
fi

echo "Created audit: $audit_id"

for i in $(seq 1 40); do
  status_response=$(curl -sS "$API_URL/api/audits/$audit_id")
  status=$(printf '%s' "$status_response" | ./.venv/bin/python -c 'import sys, json; print(json.loads(sys.stdin.read()).get("status", ""))')
  echo "poll $i: $status"
  if [[ "$status" == "done" || "$status" == "failed" ]]; then
    break
  fi
  sleep 1
done

if [[ "$status" == "done" ]]; then
echo "--- markdown report head ---"
  curl -sS "$API_URL/api/audits/$audit_id/markdown" | sed -n '1,40p'
else
  echo "Final status: $status_response"
  exit 1
fi

if [[ "$WAIT_FOR_INTERACTION" == "1" && "$START_FRONTEND" == "1" ]]; then
  echo "Demo flow complete. Keeping frontend and API alive for manual interaction."
  echo "Press Ctrl-C to stop both processes."
  wait
else
  echo "Demo flow complete."
fi
