# Lumen — company knowledge agent

This is a prepared technical-assessment baseline, not the unknown exam solution.
The assessment project is Softop; Humanizar remains its example company until the
owner explicitly asks to change company identity and knowledge.
The website is a customer-facing company assistant. Claude Code is the development
tool used during the exam with Opus 5.5. The website's configurable API model defaults
to Haiku; these are separate roles. Keep visitor/customer language in the product.
Start with README.md, docs/EXAM_20_MIN.md, docs/API_CONTRACT.md, and
.specify/memory/constitution.md. The real requirements will arrive as a ZIP.
The readable public configuration template is config/env.example. Project
permissions intentionally deny `.env.*` reads, including the root example;
do not loosen that deny to inspect credentials. Neither these permissions nor
allowed build commands constitute an OS sandbox for Claude Code.

## Quick orientation

- backend/app (one package per domain; `app.main:app` wires them):
  - core/: settings, secret redaction, request limits, thread offloading.
  - api/: schemas (HTTP contracts), dependencies (auth scopes, typed state), errors and
    routes/ with one router per resource (system, knowledge, tools, requests, customers,
    conversations, chat + SSE).
  - agent/: bounded Anthropic Haiku tool loop, demo mode and citation grounding.
  - tools/: tool contract (definitions), execution (registry) and safe calculator.
  - knowledge/: ingestion, PDF parser, embeddings, Qdrant store, initial corpus bootstrap.
  - accounts/: JWT, Argon2, rotating refresh/session families and roles.
  - persistence/: store contracts and SQLite/PostgreSQL implementations.
  - business/: company profile and customer demo/support requests.
  - mcp/: read-only MCP server and its authenticated API client.
  - manage.py: operator CLI (`python -m app.manage create-admin`, `mcp-login`).
  Anthropic credentials come exclusively from the backend environment.
- backend/tests mirrors those domains; regressions/ holds adaptation regressions.
- backend/knowledge/humanizar: public sourced initial corpus. Clear KNOWLEDGE_DIR
  and use a new DATA_DIR when adapting another company.
- frontend/src: strict React/TypeScript UI, real login, chats, requests and admin views.
- sandbox: nonroot Docker-only terminal presets; no arbitrary shell execution.
- scripts: setup, local run, scoped verification, sanitized ZIP import/package.
- .claude/skills/speckit-*: actual Spec Kit skills installed by specify-cli.
- specs/001-company-agent: baseline intent and architecture; adapt to real brief.
- prueba-tecnica/: drop zone for the exam material (git-ignored except README);
  /prueba-tecnica runs the read → goal → implement → verify → ship procedure.

## Adaptation sequence

1. Inspect the imported README and requirements. Build a short requirement-to-file
   matrix. Explicitly identify provider, database, interface and deliverables.
2. Preserve this working UI and API; adapt company_name, corpus, prompt, schemas
   and tool definitions. Replace architecture only if the brief requires it.
3. Use /speckit-specify, /speckit-plan, /speckit-tasks and /speckit-implement when
   appropriate; do not spend the whole 20-minute window regenerating scaffolding.
4. Verify grounded answer, unknown-answer refusal, upload, a real tool call,
   frontend build/typecheck/lint and relevant backend tests.
   Preserve ownership checks, confirmation and authentication unless the brief
   explicitly changes them. Never ship AUTH_ENABLED=false to avoid login work.
5. Write a concise result with checks actually executed and remaining gaps.

## Commands

`make setup`, `make dev`, `make check`, `make docker`, `make package`.
Claude Code starts with Opus 5.5 via project settings or `make claude` (CLI >=2.1.280).
`CLAUDE_CODE_MODEL` overrides the Make target; `opus` is a supported family alias.
The website keeps its separate Anthropic Haiku configuration.
Production: docs/DEPLOYMENT.md; Vercel serves the frontend and proxies `/api` to
the persistent Docker backend. DATABASE_URL selects PostgreSQL with a dedicated
DATABASE_SCHEMA and verified TLS. Local SQLite remains available offline.
Prepare a Fedora presentation copy with docs/FEDORA.md. Deployment secrets are
provided privately to the relevant runtime, never copied as whole environment files
or placed in source, browser bundles, commands or documentation.
API docs: http://127.0.0.1:8000/api/docs. Local UI: http://127.0.0.1:5173.
Docker UI: http://127.0.0.1:8080. MCP requires a running API; inspect `/mcp`.
Read docs/SPECKIT.md for feature selection: 001 is the implemented baseline;
002 is pending adaptation to the actual brief. Never overwrite 001 to invent exam completion.

## Rules

No frontend secrets. No real API credentials in source, logs, prompts or generated
artifacts. Do not read .env: refer to config/env.example and ask the user to set values
locally. Demo mode is extractive, not an LLM. Hash vectors are lexical, not semantic.
Optional semantic embeddings download a model; disclose that initialization step.
Never silently fall back from a failed live Anthropic request into a demo answer.
Reject ZIP traversal/symlinks/bombs; never run imported scripts automatically.
Keep tool calls and time bounded, show sources and report failures accurately.
