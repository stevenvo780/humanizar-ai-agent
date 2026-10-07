# Baseline work

- [x] T001 FR-001/FR-002: typed API, ingest, persistent Qdrant and bounded tools (`backend/app`, `backend/tests`).
- [x] T002 FR-003/FR-004/FR-006: Haiku cycle, labelled demo, SSE and MCP (`backend/app/agent.py`, `backend/app/mcp_server.py`).
- [x] T003 FR-001/FR-002/FR-010: typed responsive customer UI, sources and tool views (`frontend/src`).
- [x] T004 FR-005/FR-007: preset sandbox, safe ZIP importer and setup (`sandbox`, `scripts`).
- [x] T005 FR-007: Claude Code, Spec Kit, documentation and source packaging (`.claude`, `.specify`, `docs`).
- [x] T006 FR-001–FR-010: proportional gates and browser integration (`scripts/check.sh`, `docs/VALIDATION.md`).
- [x] T007 FR-010: sourced public Humanizar corpus and branding (`backend/knowledge/humanizar`).
- [x] T008 FR-008: JWT, sessions, roles and private histories (`backend/app/auth.py`, `backend/app/database.py`).
- [x] T009 FR-009: backend-only environment configuration; remove browser key routes and ignore legacy provider records (`backend/app/main.py`, `backend/tests`).
- [x] T010 FR-010: sourced recommendations and confirmed requests/admin inbox (`backend/app/business.py`, `backend/app/tools.py`).
- [x] T011 FR-011: optional PostgreSQL repositories, dedicated schema, verified TLS and concurrency coverage (`backend/app/postgres.py`, `backend/tests/test_postgres.py`, `docs/DEPLOYMENT.md`).
- [x] T012 FR-012: Vercel/Docker deployment, protected proxy, private environment and runtime validation (`frontend`, `compose.production.yaml`, `scripts`, `docs/DEPLOYMENT.md`, `docs/VALIDATION.md`).

Production Docker sandbox execution, real Haiku responses and PostgreSQL persistence
were verified and are recorded in docs/VALIDATION.md. Remote Qdrant remains untested;
production uses its persistent local volume. The Fedora preparation helper exists,
but installation on the actual laptop remains pending its SSH address. Credentials
are excluded from the public clone. GitHub Actions execution is blocked by account
billing; the passing gates reported in the validation document were run locally.

The actual exam will introduce new tasks based on its brief; do not mark those done
without implementation and acceptance evidence.
