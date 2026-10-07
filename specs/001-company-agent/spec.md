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
7. An operator uses PostgreSQL for shared production persistence while SQLite remains
   available for local setup under the same authentication and business contracts.
8. Public visitors use the Vercel UI with the persistent Docker API and terminal sandbox.
9. Administrators create and browse customer accounts without replacing their own session.
10. Visitors can read text and operate the UI on mobile and desktop; administrators
    can find the Markdown upload control directly in Documentation.

## Acceptance criteria

- Runnable FastAPI API and responsive React UI with strict types and checks.
- Persistent vector storage, supported ingestion and bounded error handling.
- Anthropic Haiku integration with actual tool use and bounded steps.
- Explicit demo mode usable without a key; no claim of real model activity in demo.
- Terminal sandbox without arbitrary host execution, keys or Docker socket.
- Read-only MCP connected to the API and configured for Claude Code.
- Reproducible local setup and locked container build; sanitized packaging.
- JWT access with rotating refresh, Argon2, roles and persistent private histories.
- Backend-only provider environment configuration, without browser key forms or HTTP key routes.
- Public Humanizar corpus preloaded; grounded product recommendations and confirmed requests.
- Optional PostgreSQL persistence with a dedicated schema, verified TLS and transactional session handling.
- Vercel same-origin API proxy to the HTTPS Docker backend, with authenticated sessions and streamed tool activity.
- Admin-only customer creation and paginated public account fields, with fixed customer roles and unchanged administrator cookies.
- Readable text, single section navigation, visible upload and document-reading controls, sufficient contrast and responsive layouts without horizontal page overflow.

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
| FR-003 | Anthropic tool use has bounded turns, tokens and errors | Provider-loop and budget tests; deployed Haiku SSE response with retrieval and nonzero usage; each new installation requires its own backend key |
| FR-004 | Demo mode is labelled and never claims a model call | Demo tests and visible mode |
| FR-005 | Terminal uses fixed presets in the separate nonroot container | Injection/resource tests; real Python preset in the deployed nonroot, read-only sandbox with internal networking and resource limits |
| FR-006 | MCP reads through the API without another Qdrant writer | Handshake/company identity; protected search requires authentication |
| FR-007 | Locked setup, source packaging and ten Spec Kit skills are portable | Setup/check commands, allowlist tests and scaffold hash/reference audit |
| FR-008 | JWT/Argon2, roles, revocable sessions and histories isolate accounts | Auth, refresh, role and conversation ownership tests |
| FR-009 | Provider credentials come only from the backend environment | Removed HTTP routes, ignored legacy DB configuration and public-response isolation tests; live calls require a user's key |
| FR-010 | Public Humanizar evidence supports recommendations and confirmed local requests | Recommendation, idempotency, owner listing and admin inbox tests |
| FR-011 | Optional PostgreSQL preserves auth and business contracts in a dedicated schema | Fifteen isolated PostgreSQL tests, concurrent bootstrap, production TLS 1.3 and persistence after API restart |
| FR-012 | Vercel proxies authenticated requests and SSE to the persistent Docker backend | Ready production deployment, secure session cookies, real tools, Swagger, protected origin and absence of backend keys from browser assets |
| FR-013 | Administrators create and list customer accounts without changing their session | Auth/role/public-field tests, coherent pagination snapshots in SQLite and PostgreSQL; production API rollout tracked separately |
| FR-014 | UI text, single navigation and Markdown upload/reading are readable and discoverable | Browser checks across 320–1440 px, measured contrast, admin ingestion/reading, persistent original text, legacy migration, role-aware navigation and keyboard-accessible mobile drawer |

Build, types, lint and responsive browser checks apply across these requirements.
Detailed execution evidence and external-service limits are recorded in docs/VALIDATION.md.
