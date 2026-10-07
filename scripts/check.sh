#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
bash -n scripts/bootstrap.sh scripts/dev.sh scripts/check.sh scripts/package.sh scripts/install-gitleaks.sh scripts/prepare-fedora.sh scripts/codex-worker.sh scripts/exam-tmux.sh
uv run --project backend --locked --extra dev --extra semantic ruff check --config backend/pyproject.toml backend/app backend/tests
uv run --project backend --locked --extra dev --extra semantic ruff format --check --config backend/pyproject.toml backend/app backend/tests
uv run --project backend --locked --extra dev --extra semantic mypy --config-file backend/pyproject.toml backend/app backend/tests
uv run --project backend --locked --extra dev --extra semantic pytest backend/tests -q
uv run --project sandbox --locked ruff check --config sandbox/pyproject.toml sandbox scripts
uv run --project sandbox --locked ruff format --check --config sandbox/pyproject.toml sandbox scripts
uv run --project sandbox --locked mypy --config-file sandbox/pyproject.toml sandbox/app scripts/import-material.py scripts/package.py scripts/audit-public.py scripts/smoke-docker.py scripts/deploy-vps.py scripts/deploy-vercel.py scripts/deploy-tests.py
uv run --project sandbox --locked pytest -c sandbox/pyproject.toml sandbox/tests scripts/tests -q
uv run --project sandbox --locked python scripts/deploy-tests.py -q
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test -- --run
npm --prefix frontend run build
