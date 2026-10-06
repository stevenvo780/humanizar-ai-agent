# Baseline work

- [x] T001 FR-001/FR-002: typed API, ingest, persistent Qdrant and bounded tools (`backend/app`, `backend/tests`).
- [x] T002 FR-003/FR-004/FR-006: Haiku cycle, labelled demo, SSE and MCP (`backend/app/agent.py`, `backend/app/mcp_server.py`).
- [x] T003 FR-001/FR-002/FR-010: typed responsive customer UI, sources and tool views (`frontend/src`).
- [x] T004 FR-005/FR-007: preset sandbox, safe ZIP importer and setup (`sandbox`, `scripts`).
- [x] T005 FR-007: Claude Code, Spec Kit, documentation and source packaging (`.claude`, `.specify`, `docs`).
- [x] T006 FR-001–FR-010: proportional gates and browser integration (`scripts/check.sh`, `docs/VALIDATION.md`).
- [x] T007 FR-010: sourced public Humanizar corpus and branding (`backend/knowledge/humanizar`).
- [x] T008 FR-008: JWT, sessions, roles and private histories (`backend/app/auth.py`, `backend/app/database.py`).
- [x] T009 FR-009: encrypted provider settings and guarded verification (`backend/app/main.py`, `backend/tests`).
- [x] T010 FR-010: sourced recommendations and confirmed requests/admin inbox (`backend/app/business.py`, `backend/app/tools.py`).

Pending environment checks: real Anthropic authentication, remote Qdrant and Docker
image/runtime execution. See docs/VALIDATION.md for evidence and limitations.

The actual exam will introduce new tasks based on its brief; do not mark those done
without implementation and acceptance evidence.
