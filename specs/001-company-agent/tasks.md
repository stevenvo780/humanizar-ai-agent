# Baseline work

- [x] T001 FR-001/FR-002: typed API, ingest, persistent Qdrant and bounded tools (`backend/app`, `backend/tests`).
- [x] T002 FR-003/FR-004/FR-006: Haiku cycle, labelled demo, SSE and MCP (`backend/app/agent/`, `backend/app/mcp/server.py`).
- [x] T003 FR-001/FR-002/FR-010: typed responsive customer UI, sources and tool views (`frontend/src`).
- [x] T004 FR-005/FR-007: preset sandbox, safe ZIP importer and setup (`sandbox`, `scripts`).
- [x] T005 FR-007: Claude Code, Spec Kit, documentation and source packaging (`.claude`, `.specify`, `docs`).
- [x] T006 FR-001–FR-010: proportional gates and browser integration (`scripts/check.sh`, `docs/VALIDATION.md`).
- [x] T007 FR-010: sourced public Humanizar corpus and branding (`backend/knowledge/humanizar`).
- [x] T008 FR-008: JWT, sessions, roles and private histories (`backend/app/accounts/`, `backend/app/persistence/sqlite/`).
- [x] T009 FR-009: backend-only environment configuration; remove browser key routes and ignore legacy provider records (`backend/app/main.py`, `backend/tests`).
- [x] T010 FR-010: sourced recommendations and confirmed requests/admin inbox (`backend/app/business/requests.py`, `backend/app/tools/handlers/`).
- [x] T011 FR-011: optional PostgreSQL repositories, dedicated schema, verified TLS and concurrency coverage (`backend/app/persistence/postgres/`, `backend/tests/persistence/test_postgres.py`, `docs/DEPLOYMENT.md`).
- [x] T012 FR-012: Vercel/Docker deployment, protected proxy, private environment and runtime validation (`frontend`, `compose.production.yaml`, `scripts`, `docs/DEPLOYMENT.md`, `docs/VALIDATION.md`).
- [x] T013 FR-013: admin customer creation/listing, fixed role, session preservation and coherent pagination (`backend/app`, `backend/tests`, `frontend/src/features/customers/CustomersPanel.tsx`, `frontend/src/features/customers/customers.test.ts`).
- [x] T014 FR-014: readable typography/contrast, single section navigation, shared dialog focus and visible Markdown upload (`frontend/src/styles/global.css`, `frontend/src/features/docs/docs.css`, `frontend/src/app/App.tsx`, `frontend/src/app/workspaceNavigation.ts`, `frontend/src/shared/hooks/useDialogFocus.ts`).
- [ ] T015 FR-013: publish the updated API to the VPS and verify customer management through the public Vercel UI; requires an authenticated SSH connection.
- [x] T016 FR-002/FR-008/FR-014: persist complete document text, migrate legacy metadata, add authenticated content API and safe Markdown/text reader, and verify storage, roles and browser behavior.
- [ ] T017 FR-014: publish the document reader API/UI and verify reading from Vercel; requires an authenticated SSH connection to update the VPS API.
- [x] T018 FR-007: Fedora 44 laptop holds the checkout in ~/Documentos/repos/SoftopPrueba (symlinked data disk); uv 0.11.21, make setup and make check passed on 2026-10-07. Private steps (Anthropic key, admin, mcp-login) remain with the operator.
- [x] T019 FR-001/FR-003: prevent unrelated successful tools from admitting unsupported company claims; preserve legitimate arithmetic and explicit action results with regression tests.
- [x] T020 FR-002/FR-007: exclude session/runtime material before ZIP reads, redact authentication headers and make authenticated uploads explicit (`scripts/import-material.py`, `scripts/tests`).
- [x] T021 FR-006/FR-008: add a private, authenticated MCP session flow with bounded refresh and distinct authentication/availability errors (`backend/app/mcp/server.py`, `backend/app/manage.py`).
- [x] T022 FR-001/FR-002: isolate remote vector collections by a persistent corpus namespace without deleting existing knowledge (`backend/app/knowledge/store.py`, `backend/tests`).
- [x] T023 FR-007/FR-010/FR-014: configure company identity/catalog and share tool input schemas with the typed frontend, preserving the Humanizar example (`backend/app`, `frontend/src`).
- [x] T024 FR-008/FR-014: preserve the session on transient refresh errors and announce completed chat responses accessibly (`frontend/src`, `frontend/src/shared/api/auth.test.ts`).
- [x] T025 FR-007/FR-014: keep prerequisite checks read-only, document the local scaffold patch and use measurable UI acceptance criteria (`.specify`, `scripts/tests/test_speckit.py`, `docs`).
- [ ] T026 FR-012: publish the audited backend and verify the public application with the final source revision; requires authenticated VPS access.

Production Docker sandbox execution, real Haiku responses and PostgreSQL persistence
were verified and are recorded in docs/VALIDATION.md. Remote Qdrant remains untested;
production uses its persistent local volume. The Fedora preparation helper exists,
but installation on the actual laptop remains pending its SSH address. Credentials
are excluded from the public clone. GitHub Actions execution is blocked by account
billing; the passing gates reported in the validation document were run locally.

The actual exam will introduce new tasks based on its brief; do not mark those done
without implementation and acceptance evidence.
