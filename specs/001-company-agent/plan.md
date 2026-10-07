# Baseline implementation plan

## Stack

Python 3.12+, FastAPI, Pydantic settings, Anthropic async SDK, Qdrant client, document
parsers and semantic multilingual FastEmbed selected by the prepared configuration;
deterministic hash vectors remain the explicitly labelled offline alternative.
React, Vite, TypeScript strict, ESLint typed rules, safe Markdown and handcrafted CSS.
Docker Compose separates web, API and preset terminal sandbox. MCP uses stdio.
PyJWT and pwdlib/Argon2 protect accounts. SQLite WAL or optional PostgreSQL through
SQLAlchemy Core/psycopg stores identities, revocable session families, private
conversations, messages and business requests. PostgreSQL uses a dedicated schema,
verified TLS and transaction locks for bootstrap, refresh and idempotent requests.
A private persistent local secret or stable production JWT secret signs sessions.
Initial production administration uses the private CLI. Anthropic uses only backend
environment configuration; legacy provider records are preserved but never activated.
Admin-only customer endpoints create fixed customer accounts without issuing sessions
or cookies. Paginated lists use coherent read snapshots and expose only public fields.

The Vercel UI proxies requests to the HTTPS Docker API on the VPS through a protected
origin. Production uses external PostgreSQL, a persistent local Qdrant volume and one
API worker; the terminal sandbox remains separate. Deployment and laptop preparation
are documented in docs/DEPLOYMENT.md and docs/FEDORA.md. Installing on the actual
Fedora laptop still requires its SSH address and local authentication.

## Contracts and data

Canonical baseline contract: docs/API_CONTRACT.md. Documents own chunk metadata;
retrieval returns document/chunk identifiers, excerpts and scores. Responses contain
answer, sources, trace, provider mode, model and actual usage. SSE exposes status,
tool, token, done and error events.
New uploads also retain their complete extracted text for an administrator-only
document reader. An additive SQLite migration preserves previous records; legacy
documents reconstruct readable text from ordered chunks and explicitly disclose
formatting limits. The browser renders Markdown safely and can display its text.

## Verification

Test malformed ZIPs, persistent retrieval, document removal, unsupported inputs,
unknown facts, mocked provider tool loops and tool budgets. Verify frontend SSE
chunk boundaries, typecheck, lint and build. Inspect UI in a browser with real API.
Verify MCP handshake/read-only calls. Validate Compose and exercise the real VPS
sandbox; distinguish production runtime evidence from an unavailable local daemon.
Verify setup concurrency, role and ownership checks, expired/tampered JWTs,
refresh rotation and stale logout, confirmation idempotency, backend-only provider
configuration, canceled ingestion limits and authentication event-loop responsiveness.
Run PostgreSQL integration tests against an isolated test schema, then verify
production TLS, API restart persistence, secure cookies and real SSE tool activity.
Record results in docs/VALIDATION.md; local passing gates do not imply that remote
GitHub Actions ran when the account blocks execution.
Verify customer creation keeps the administrator cookie and permissions, customer
login stays private, malformed role inputs fail and concurrent registrations do not
invalidate pagination. Inspect readable text, contrast and responsive layouts. The
UI enables customer management only when the backend declares that capability in
its health response, allowing frontend and API releases to proceed independently.
Keep one section navigation with typed role/capability metadata. Desktop and mobile
share the same sidebar; the mobile drawer and help dialog share focus handling.
Closed drawers are inert, and section content is labelled by the visible header.
Verify authenticated reading, exact text after restart for new uploads, legacy
migration and reconstruction, deleted/missing documents, request cancellation and
readable Markdown headings, tables and code on desktop and mobile.

## Assessment adaptation

Map real requirements to existing layers. Keep checked components; alter only
necessary corpus, branding, tool/schema and provider implementation. Reverify those
paths and record any deviation from the baseline constitution.
Use `specs/002-exam-adaptation` for those requirements; its tasks remain pending
until the real brief and acceptance evidence exist.
