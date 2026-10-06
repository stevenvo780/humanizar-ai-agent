# Lumen — company knowledge agent

This is a prepared technical-assessment baseline, not the unknown exam solution.
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

- backend/app: FastAPI, settings, document ingestion, persistent Qdrant retrieval,
  bounded Anthropic Haiku tool loop, demo mode, SSE and MCP server.
- backend/app/auth.py and database.py: JWT, Argon2, rotating refresh/session families,
  roles, SQLite conversations and encrypted provider credentials.
- backend/knowledge/humanizar: public sourced initial corpus. Clear KNOWLEDGE_DIR
  and use a new DATA_DIR when adapting another company.
- frontend/src: strict React/TypeScript UI, real login, chats, requests and admin views.
- sandbox: nonroot Docker-only terminal presets; no arbitrary shell execution.
- scripts: setup, local run, scoped verification, sanitized ZIP import/package.
- .claude/skills/speckit-*: actual Spec Kit skills installed by specify-cli.
- specs/001-company-agent: baseline intent and architecture; adapt to real brief.

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
API docs: http://127.0.0.1:8000/api/docs. Local UI: http://127.0.0.1:5173.
Docker UI: http://127.0.0.1:8080. MCP requires a running API; inspect `/mcp`.
Read docs/SPECKIT.md for feature selection: 001 is the implemented baseline;
002 is pending adaptation to the actual brief. Never overwrite 001 to invent exam completion.

## Rules

No frontend secrets. No real API credentials in source, logs, prompts or generated
artifacts. Do not read .env: refer to .env.example and ask the user to set values
locally. Demo mode is extractive, not an LLM. Hash vectors are lexical, not semantic.
Optional semantic embeddings download a model; disclose that initialization step.
Never silently fall back from a failed live Anthropic request into a demo answer.
Reject ZIP traversal/symlinks/bombs; never run imported scripts automatically.
Keep tool calls and time bounded, show sources and report failures accurately.
