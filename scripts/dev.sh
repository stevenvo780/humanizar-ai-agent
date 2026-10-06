#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
LUMEN_BIND_HOST="${LUMEN_WEB_HOST:-127.0.0.1}"
children=()
cleanup() {
  trap - EXIT INT TERM
  for child in "${children[@]}"; do
    kill -TERM -- "-$child" 2>/dev/null || true
  done
  for child in "${children[@]}"; do wait "$child" 2>/dev/null || true; done
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
command -v setsid >/dev/null || { echo 'setsid is required for clean process cleanup.' >&2; exit 1; }
if command -v docker >/dev/null && docker info >/dev/null 2>&1; then
  if docker compose -f compose.yaml -f compose.local.yaml up -d --build sandbox; then
    export SANDBOX_URL='http://127.0.0.1:8081'
  else
    export SANDBOX_URL=''
    echo 'Sandbox container could not start: terminal execution is disabled.' >&2
  fi
else
  export SANDBOX_URL=''
  echo 'Docker is unavailable: terminal execution is disabled. Chat and knowledge tools remain available.' >&2
fi
setsid uv run --project backend --locked --extra dev --extra semantic uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log --reload --reload-dir backend/app &
children+=("$!")
setsid npm --prefix frontend run dev -- --host "$LUMEN_BIND_HOST" --port 5173 --strictPort &
children+=("$!")
echo "Lumen: web $LUMEN_BIND_HOST:5173 (API: http://127.0.0.1:8000)"
wait -n "${children[@]}"
