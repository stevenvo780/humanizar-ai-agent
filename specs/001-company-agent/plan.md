# Baseline implementation plan

## Stack

Python 3.12+, FastAPI, Pydantic settings, Anthropic async SDK, Qdrant client, document
parsers and semantic multilingual FastEmbed selected by the prepared configuration;
deterministic hash vectors remain the explicitly labelled offline alternative.
React, Vite, TypeScript strict, ESLint typed rules, safe Markdown and handcrafted CSS.
Docker Compose separates web, API and preset terminal sandbox. MCP uses stdio.
PyJWT and pwdlib/Argon2 protect accounts. SQLite WAL stores identities, revocable
session families, private conversations, messages and business requests. A private
persistent server secret signs sessions. Anthropic uses only backend environment
configuration; legacy provider records are preserved but never read or activated.

## Contracts and data

Canonical baseline contract: docs/API_CONTRACT.md. Documents own chunk metadata;
retrieval returns document/chunk identifiers, excerpts and scores. Responses contain
answer, sources, trace, provider mode, model and actual usage. SSE exposes status,
tool, token, done and error events.

## Verification

Test malformed ZIPs, persistent retrieval, document removal, unsupported inputs,
unknown facts, mocked provider tool loops and tool budgets. Verify frontend SSE
chunk boundaries, typecheck, lint and build. Inspect UI in a browser with real API.
Verify MCP handshake/read-only calls. Validate Compose and report daemon limits.
Verify setup concurrency, role and ownership checks, expired/tampered JWTs,
refresh rotation and stale logout, confirmation idempotency, backend-only provider
configuration, canceled ingestion limits and authentication event-loop responsiveness.

## Assessment adaptation

Map real requirements to existing layers. Keep checked components; alter only
necessary corpus, branding, tool/schema and provider implementation. Reverify those
paths and record any deviation from the baseline constitution.
Use `specs/002-exam-adaptation` for those requirements; its tasks remain pending
until the real brief and acceptance evidence exist.
