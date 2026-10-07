# Specification Analysis Report: 001-company-agent

**Command**: `/speckit-analyze` (Spec Kit 1.0.7), non-interactive · **Date**: 2026-10-07
**Feature selection**: `SPECIFY_FEATURE=001-company-agent SPECIFY_FEATURE_DIRECTORY=specs/001-company-agent` (`.specify/feature.json` unchanged)
**Inputs**: spec.md (after the 2026-10-07 Clarifications), plan.md, tasks.md, constitution 1.0.0,
checklists/requirements-quality.md and the canonical contract docs/API_CONTRACT.md named by plan.md.
Code was read only to decide whether a statement is current. The analysis pass was read-only;
the remediation applied afterwards is listed separately.

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| C1 | Constitution Alignment | HIGH | constitution §I; spec.md; backend/tests | "Document instructions cannot override system rules" had no requirement and no test. The prompt marks documents, tool results and history as untrusted; uncited prose is replaced. | Acceptance criterion + regression test |
| C2 | Constitution Alignment | MEDIUM | constitution §V; spec acceptance | The lexical-embedding label was not required (health/config/sidebar already show it). | Extend the demo-mode bullet |
| C3 | Constitution Alignment | MEDIUM | constitution §IV; FR-005 | Calculator and terminal bounds were not quantified (code: 200 chars and depth 12; 5 presets, 2 s, 16 KiB, 1 s CPU, 128 MiB, no writes, 4 concurrent runs). | Quantify in the spec |
| I1 | Inconsistency | HIGH | spec FR-009 vs FR-003, plan §Stack | "live calls require a user's key" contradicts backend-only configuration. | "the operator's backend key" |
| I2 | Inconsistency | MEDIUM | plan.md; tasks.md footer; docs/SPECKIT.md; docs/VALIDATION.md | They said the Fedora install was pending its SSH address, although T018 is done (setup/check passed on 2026-10-07). | Align with T018 |
| I3 | Inconsistency | MEDIUM | tasks.md T002, T009, T016, T020, T021 | Paths incomplete or stale after 9ac20b0/bf8f1c8 (api/routes/chat.py, persistence/sqlite/, scripts/material_import/, mcp/sessions.py and client.py). | Update the paths |
| I4 | Inconsistency | MEDIUM | docs/ARCHITECTURE.md | Public deployment was listed as not implemented (contradicts FR-012/T012); the diagram showed only SQLite. | Fix the text |
| I5 | Inconsistency | LOW | docs/API_CONTRACT.md error codes | `empty_response` and `internal_error` were missing. | Add them |
| T1 | Terminology | LOW | spec stories 1/3/8/10 | user/visitor/customer/candidate were undefined. | Glossary |
| U1 | Underspecification | MEDIUM | story 6, FR-010 | Business-request lifecycle undefined (single `received` status, idempotency per user and action key, read-only inbox of 50, 20 per customer). | Record in acceptance |
| U2 | Underspecification | MEDIUM | story 5, Scope limits | Conversation/document deletion not specified; account self-service neither specified nor excluded. | Acceptance + Scope limits |
| U3 | Underspecification | LOW | FR-008, T024 | Browser recovery on transient refresh errors had no requirement. | Add to acceptance |
| U4 | Underspecification | LOW | story 3 | Behaviour of disabled or unreachable optional services undefined. | Add to acceptance |
| U5 | Underspecification | MEDIUM | FR-008, Clarifications Q2 | Reuse of a rotated refresh token returns 401 without revoking the session family; not specified. | Owner decision (not changed) |
| U6 | Underspecification | LOW | spec | No performance targets or logging requirement. | Optional |
| U7 | Underspecification | LOW | FR-011/FR-012 | Storage outage (503) and remote Qdrant have no requirement. | Optional |
| D1 | Duplication | LOW | Acceptance vs Traceability | Intentional restatement without conflict. | No action |

No placeholders (TODO, TKTK, ???, `<placeholder>`) in spec/plan/tasks.

## Coverage Summary

| Requirement | Has Task? | Task IDs | Notes |
|---|---|---|---|
| FR-001 | Yes | T001, T019, T027 | C1 |
| FR-002 | Yes | T001, T016, T020, T022, T029 | |
| FR-003 | Yes | T002, T019, T028 | |
| FR-004 | Yes | T002, T028 | C2 |
| FR-005 | Yes | T004 | C3 |
| FR-006 | Yes | T002, T021 | |
| FR-007 | Yes | T004, T005, T018, T020, T023, T025, T030 | |
| FR-008 | Yes | T008, T016, T021, T024 | U3, U5 |
| FR-009 | Yes | T009 | I1 |
| FR-010 | Yes | T003, T007, T010, T023 | U1 |
| FR-011 | Yes | T011 | |
| FR-012 | Yes | T012, T026 | |
| FR-013 | Yes | T013, T015 | |
| FR-014 | Yes | T014, T016, T017, T023, T024, T025 | |

**Constitution alignment:** C1 (HIGH), C2, C3 (MEDIUM): the code satisfied the principles but the
spec did not state them or no test proved them. No CRITICAL issue.
**Unmapped tasks:** none.
**Metrics at analysis time:** 14 requirements · 26 tasks (23 done, 3 open: T015/T017/T026) ·
coverage 100% · ambiguities 2 · duplications 1 · critical 0 · underspecification 7.

## Remediation applied

| Finding | Edit |
|---|---|
| I1 | spec FR-009: "the operator's backend key" |
| I2 | plan.md, tasks.md footer, docs/SPECKIT.md, docs/VALIDATION.md and the /docs status section aligned with T018 |
| I3 | paths of T002/T009/T016/T020/T021 updated (IDs and status unchanged) |
| I4 | docs/ARCHITECTURE.md fixed |
| I5 | docs/API_CONTRACT.md: `empty_response`, `internal_error`, JSON 503/500 |
| C2, C3, T1, U1–U4 | spec.md: glossary, embedding label, quantified bounds, request lifecycle, deletion, refresh recovery, optional services, scope exclusions |
| C1 | tasks.md Phase 2 T027, implemented with a regression test |
| T015/T017/T026 | closed afterwards with production and end-to-end evidence (see tasks.md) |
| U5–U7 | not changed: U5 awaits the owner's decision; U6/U7 optional |
