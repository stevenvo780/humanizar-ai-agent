# Baseline work

- [x] T001 FR-001/FR-002: typed API, ingest, persistent Qdrant and bounded tools (`backend/app`, `backend/tests`).
- [x] T002 FR-003/FR-004/FR-006: Haiku cycle, labelled demo, SSE and MCP (`backend/app/agent/`, `backend/app/api/routes/chat.py`, `backend/app/mcp/server.py`).
- [x] T003 FR-001/FR-002/FR-010: typed responsive customer UI, sources and tool views (`frontend/src`).
- [x] T004 FR-005/FR-007: preset sandbox, safe ZIP importer and setup (`sandbox`, `scripts`).
- [x] T005 FR-007: Claude Code, Spec Kit, documentation and source packaging (`.claude`, `.specify`, `docs`).
- [x] T006 FR-001–FR-010: proportional gates and browser integration (`scripts/check.sh`, `docs/VALIDATION.md`).
- [x] T007 FR-010: sourced public Humanizar corpus and branding (`backend/knowledge/humanizar`).
- [x] T008 FR-008: JWT, sessions, roles and private histories (`backend/app/accounts/`, `backend/app/persistence/sqlite/`).
- [x] T009 FR-009: backend-only environment configuration; remove browser key routes and ignore legacy provider records (`backend/app/api/routes/`, `backend/app/persistence/sqlite/base.py`, `backend/tests/api/test_authenticated_app.py`).
- [x] T010 FR-010: sourced recommendations and confirmed requests/admin inbox (`backend/app/business/requests.py`, `backend/app/tools/handlers/`).
- [x] T011 FR-011: optional PostgreSQL repositories, dedicated schema, verified TLS and concurrency coverage (`backend/app/persistence/postgres/`, `backend/tests/persistence/test_postgres.py`, `docs/DEPLOYMENT.md`).
- [x] T012 FR-012: Vercel/Docker deployment, protected proxy, private environment and runtime validation (`frontend`, `compose.production.yaml`, `scripts`, `docs/DEPLOYMENT.md`, `docs/VALIDATION.md`).
- [x] T013 FR-013: admin customer creation/listing, fixed role, session preservation and coherent pagination (`backend/app`, `backend/tests`, `frontend/src/features/customers/CustomersPanel.tsx`, `frontend/src/features/customers/customers.test.ts`).
- [x] T014 FR-014: readable typography/contrast, single section navigation, shared dialog focus and visible Markdown upload (`frontend/src/styles/global.css`, `frontend/src/features/docs/docs.css`, `frontend/src/app/App.tsx`, `frontend/src/app/workspaceNavigation.ts`, `frontend/src/shared/hooks/useDialogFocus.ts`).
- [x] T015 FR-013: API published to the VPS on 2026-10-07 (9ac20b0, then bf8f1c8) after a coordinated backup; the public /api/health declares `customer_management`; creating, listing and paginating customers plus 403/401 for non-admins were verified end to end in the browser on the same code. Signing in with the real production admin remains an operator smoke check (docs/OPERATIONS.md).
- [x] T016 FR-002/FR-008/FR-014: persist complete document text, migrate legacy metadata, add authenticated content API and safe Markdown/text reader, and verify storage, roles and browser behavior (`backend/app/knowledge/store.py`, `backend/app/api/routes/knowledge.py`, `frontend/src/features/documents/`).
- [x] T017 FR-014: reader API and UI published (Vercel and VPS at bf8f1c8); the public /api/health declares `document_reading`; upload, safe rendering (no scripts, remote images or `javascript:` links), raw view and 403/401 for customers were verified end to end in the browser on the same code. The production admin smoke is the same operator check as T015.
- [x] T018 FR-007: Fedora 44 laptop holds the checkout in ~/Documentos/repos/SoftopPrueba (symlinked data disk); uv 0.11.21, make setup and make check passed on 2026-10-07. Private steps (Anthropic key, admin, mcp-login) remain with the operator.
- [x] T019 FR-001/FR-003: prevent unrelated successful tools from admitting unsupported company claims; preserve legitimate arithmetic and explicit action results with regression tests.
- [x] T020 FR-002/FR-007: exclude session/runtime material before ZIP reads, redact authentication headers and make authenticated uploads explicit (`scripts/import-material.py`, `scripts/material_import/`, `scripts/tests`).
- [x] T021 FR-006/FR-008: add a private, authenticated MCP session flow with bounded refresh and distinct authentication/availability errors (`backend/app/mcp/server.py`, `backend/app/mcp/client.py`, `backend/app/mcp/sessions.py`, `backend/app/manage.py`).
- [x] T022 FR-001/FR-002: isolate remote vector collections by a persistent corpus namespace without deleting existing knowledge (`backend/app/knowledge/store.py`, `backend/tests`).
- [x] T023 FR-007/FR-010/FR-014: configure company identity/catalog and share tool input schemas with the typed frontend, preserving the Humanizar example (`backend/app`, `frontend/src`).
- [x] T024 FR-008/FR-014: preserve the session on transient refresh errors and announce completed chat responses accessibly (`frontend/src`, `frontend/src/shared/api/auth.test.ts`).
- [x] T025 FR-007/FR-014: keep prerequisite checks read-only, document the local scaffold patch and use measurable UI acceptance criteria (`.specify`, `scripts/tests/test_speckit.py`, `docs`).
- [x] T026 FR-012: audited backend bf8f1c8 published with backup and a rehearsed restore; the public application was verified over HTTPS (health and features, 26 OpenAPI operations, 401 for anonymous chat, CSP on every SPA route, no API errors in logs); the VPS checkout tracks the final revision.

Production Docker sandbox execution, real Haiku responses and PostgreSQL persistence
were verified and are recorded in docs/VALIDATION.md. Remote Qdrant remains untested;
production uses its persistent local volume. The actual Fedora 44 laptop holds the
checkout and passed setup/check (T018); its private operator steps remain. Credentials
are excluded from the public clone. GitHub Actions execution is blocked by account
billing; the passing gates reported in the validation document were run locally.

The actual exam will introduce new tasks based on its brief; do not mark those done
without implementation and acceptance evidence.

## Phase 2: Convergence

- [x] T027 Add regression tests proving that the system prompt sent to the provider marks documents, tool results and history as untrusted data, and that uncited prose obeying an instruction injected in a retrieved document is replaced (`backend/tests/agent/test_agent.py`) per Constitution I and spec §Acceptance criteria (partial) Evidence 2026-10-07: `test_injected_document_instruction_stays_untrusted_tool_data`; fails if the untrusted-data rule or the uncited-prose replacement is removed.
- [x] T028 Add tests that an agent failure returns HTTP 503 `{detail, code}` on JSON and an SSE `error` event with the same code, is not saved to the conversation and yields no demo answer, and that `LLM_MODE=anthropic` without a key fails settings validation (`backend/tests/api/test_authenticated_app.py`, `backend/tests/agent/test_agent.py`) per FR-003, FR-004 and Clarifications Q5 (partial) Evidence 2026-10-07: `test_provider_failure_is_coded_unsaved_and_never_a_demo_answer` (JSON and SSE) and `test_anthropic_mode_without_backend_key_fails_validation`; fail on a 200 status, a silent demo fallback or a missing key check.
- [x] T029 Add an ingestion test rejecting a ZIP that contains an encrypted entry (`backend/tests/knowledge/test_ingestion.py`) per FR-002, Clarifications Q4 and Constitution III (partial) Evidence 2026-10-07: `test_zip_with_encrypted_entry_is_rejected`; fails if the encrypted-entry check is removed.
- [x] T030 Trace the exam-only development tooling (`scripts/codex-worker.sh`, `scripts/exam-tmux.sh`, `.agents/skills/`, `.claude/skills/prueba-tecnica/`) in plan.md as outside the product scope per FR-007 and plan: assessment adaptation (unrequested) Evidence 2026-10-07: plan.md §Assessment adaptation names the exam tooling and its limits.
