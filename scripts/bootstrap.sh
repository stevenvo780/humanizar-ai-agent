#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SKIP_MODEL_DOWNLOAD=false
for option in "$@"; do
  case "$option" in
    --skip-model-download) SKIP_MODEL_DOWNLOAD=true ;;
    --help|-h)
      echo 'Usage: bash scripts/bootstrap.sh [--skip-model-download]'
      echo 'Requires uv >=0.11.21 and Node.js >=22; installs locked project dependencies.'
      echo 'LUMEN_PYTHON selects the Python interpreter (default: 3.12).'
      exit 0 ;;
    *) echo 'Unknown setup option. Use --help.' >&2; exit 2 ;;
  esac
done
command -v uv >/dev/null || { echo 'Install uv before bootstrapping.' >&2; exit 1; }
command -v npm >/dev/null || { echo 'Install Node.js and npm before bootstrapping.' >&2; exit 1; }
command -v node >/dev/null || { echo 'Install Node.js 22 or newer.' >&2; exit 1; }
UV_VERSION="$(uv --version)"
if [[ ! "$UV_VERSION" =~ ^uv[[:space:]]+([0-9]+)\.([0-9]+)\.([0-9]+) ]]; then
  echo 'Cannot identify uv version; use uv 0.11.21 or newer.' >&2; exit 1
fi
if (( BASH_REMATCH[1] == 0 && (BASH_REMATCH[2] < 11 || (BASH_REMATCH[2] == 11 && BASH_REMATCH[3] < 21)) )); then
  echo 'Upgrade uv to 0.11.21 or newer.' >&2; exit 1
fi
NODE_MAJOR="$(node -p 'Number(process.versions.node.split(".")[0])')"
if (( NODE_MAJOR < 22 )); then echo 'Node.js 22 or newer is required.' >&2; exit 1; fi
PYTHON_SPEC="${LUMEN_PYTHON:-3.12}"
if [[ ! -e .env && ! -L .env ]]; then
  (umask 077; set -o noclobber; cat config/env.example > .env)
fi
if [[ ! -e .specify/feature.json && ! -L .specify/feature.json ]]; then
  (set -o noclobber; echo '{"feature_directory":"specs/001-company-agent"}' > .specify/feature.json)
fi
uv sync --project backend --python "$PYTHON_SPEC" --locked --extra dev --extra semantic
uv sync --project sandbox --python "$PYTHON_SPEC" --locked --group dev
npm --prefix frontend ci
if [[ "$SKIP_MODEL_DOWNLOAD" == false ]]; then
  uv run --project backend --locked --extra dev --extra semantic python -c 'from app.embeddings import SemanticEmbedder; from app.settings import Settings; s=Settings(); e=SemanticEmbedder(s.fastembed_model,s.fastembed_threads); print("Embedding model ready:",e.dimension)'
else
  echo 'Embedding weights were not prepared. Use hash mode locally or prepare the model before starting.'
fi
echo 'Dependencies ready. Configure .env locally when using Anthropic.'
