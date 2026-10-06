# Baseline: company knowledge agent

## User stories

1. A user asks about company facts and receives a grounded answer with inspectable
   source excerpts, or an explicit statement that the documents do not contain it.
2. An administrator imports company documents or a bounded ZIP; authenticated
   customers can search their contents without gaining document management permissions.
3. A user sees actual tool activity and can demonstrate search, calculation, MCP and
   container terminal presets when the corresponding service is enabled.
4. A candidate opens Claude Code with Spec Kit and adapts the baseline to a real brief.
5. Customers authenticate with individual accounts and recover only their own chats.
6. Customers confirm demo/support requests; administrators review the stored inbox.

## Acceptance criteria

- Runnable FastAPI API and responsive React UI with strict types and checks.
- Persistent vector storage, supported ingestion and bounded error handling.
- Anthropic Haiku integration with actual tool use and bounded steps.
- Explicit demo mode usable without a key; no claim of real model activity in demo.
- Terminal sandbox without arbitrary host execution, keys or Docker socket.
- Read-only MCP connected to the API and configured for Claude Code.
- Reproducible local setup and locked container build; sanitized packaging.
- JWT access with rotating refresh, Argon2, roles and persistent private histories.
- Admin-only provider configuration encrypted at rest and real connection verification.
- Public Humanizar corpus preloaded; grounded product recommendations and confirmed requests.

## Scope limits

This baseline is configured for Humanizar using public official information.
Actual assessment acceptance criteria, company identity and tool policies still
come from the brief. PDF OCR, external message delivery, automatic calendar booking
and arbitrary autonomous code execution are outside this implementation.

## Requirement traceability

| ID | Baseline requirement | Acceptance evidence |
| --- | --- | --- |
| FR-001 | Answers expose retrieved evidence; absent facts produce uncertainty | Grounding/unknown-answer tests and source inspection |
| FR-002 | Admin ingestion is bounded and documents/vectors persist | ZIP boundaries, ownership permissions and restart tests |
| FR-003 | Anthropic tool use has bounded turns, tokens and errors | Mocked provider loop and budgets; live credential check remains environment-dependent |
| FR-004 | Demo mode is labelled and never claims a model call | Demo tests and visible mode |
| FR-005 | Terminal uses fixed presets in the separate nonroot container | Injection/resource tests; actual Docker execution remains pending |
| FR-006 | MCP reads through the API without another Qdrant writer | Handshake/company identity; protected search requires authentication |
| FR-007 | Locked setup, source packaging and ten Spec Kit skills are portable | Setup/check commands, allowlist tests and scaffold hash/reference audit |
| FR-008 | JWT/Argon2, roles, revocable sessions and histories isolate accounts | Auth, refresh, role and conversation ownership tests |
| FR-009 | Admin provider credentials are encrypted and verification is guarded | Settings/provider race and permission tests; live call requires a user's key |
| FR-010 | Public Humanizar evidence supports recommendations and confirmed local requests | Recommendation, idempotency, owner listing and admin inbox tests |

Build, types, lint and responsive browser checks apply across these requirements.
Detailed execution evidence and external-service limits are recorded in docs/VALIDATION.md.
