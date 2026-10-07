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

Terminology: a *visitor* is an unauthenticated browser; a *user* is any signed-in
account (chat requires one while authentication is enabled); a *customer* is a user
with the customer role; an *administrator* has the admin role; an *operator* holds
private server access; a *candidate* adapts the baseline with Claude Code.

## Clarifications

### Session 2026-10-07

Non-interactive session on the implemented baseline: every answer is the behavior
verified in code at this date, not a new product decision.

- Q: Which operations are reserved for administrators, and what does a customer receive when requesting another account's conversation? → A: Document listing, upload, reading and deletion, direct tool runs (`POST /api/tools/run`), customer creation/listing and the request inbox require the administrator role (403 otherwise). Any authenticated account may chat, search, read the tool catalog, confirm its own proposed actions and list or delete its own conversations and requests; another account's conversation returns 404. The single first administrator is created through `POST /api/auth/setup` (gated by a private bootstrap token when configured) or the private `create-admin` CLI; public registration creates customers only after that setup.
- Q: How long do sessions last and how are sign-in attempts throttled? → A: HS256 access tokens last 30 minutes; the HttpOnly, SameSite=Strict refresh cookie (path `/api/auth`) lasts 7 days and is rotated on every refresh within its session family; refresh and logout require the `X-Requested-With` header; logout revokes the whole family. Setup, registration and login each allow 10 attempts per client address in a sliding 5-minute window held in the API process memory (login counts only failures), then return 429 with `Retry-After: 300`. Passwords have 6–128 characters.
- Q: What numeric bounds apply to a single chat turn? → A: Defaults, configurable only within hard caps: 5 model iterations (≤10), 8 tool calls (≤20), 1,500 output tokens (≤4,096) and a 45 s provider timeout (≤120 s) with one SDK retry. Messages have at most 10,000 characters; for authenticated users the client history is replaced by the owner's server history (last 40 messages, ≤32,000 characters). At most 4 chats run concurrently per API process; excess JSON or SSE requests receive 429 with `Retry-After: 2`.
- Q: Which files and sizes does document ingestion accept? → A: `.txt`, `.md`, `.pdf`, `.docx`, `.json` and `.csv`, individually or inside a `.zip`. Defaults: 15 MB per upload, at most 100 ZIP entries, 40 MB decompressed (also the extracted-text bound) and a 100:1 compression ratio; absolute/traversal paths, symlinks and encrypted entries reject the whole archive. Inside a ZIP, unsupported, unreadable, empty or credential-bearing entries are skipped and reported; the same condition on a single file is rejected with 422. There is no OCR and only one ingestion runs at a time.
- Q: What does the user receive when the model's answer cites no retrieved source or a live Anthropic request fails? → A: Model prose without a valid `[S#]` citation to a source retrieved in that turn is replaced by deterministic text built only from completed tool results, or by the explicit "No encontré evidencia suficiente en los documentos…" statement; citation numbers that were not retrieved render as "[fuente no disponible]". Provider errors, refusals, output-limit, empty responses and tool or iteration budgets return HTTP 503 (an SSE `error` event) with a stable code, are not saved to the conversation and never fall back to demo mode. Demo mode runs only with `LLM_MODE=demo` or `LLM_MODE=auto` without a key; `LLM_MODE=anthropic` without a key fails at startup.

## Acceptance criteria

- Runnable FastAPI API and responsive React UI with strict types and checks.
- Persistent vector storage and ingestion of TXT, MD, PDF, DOCX, JSON and CSV files,
  alone or in a ZIP, within the upload, entry, decompressed-size and ratio limits
  recorded in Clarifications; rejected inputs return a fixed, non-leaking error.
- Anthropic Haiku integration with actual tool use, bounded iterations, tool calls,
  output tokens and timeout, and a global concurrent-chat bound answered with 429.
- Answers whose prose cites no source retrieved in that turn are replaced by
  tool-derived text or the explicit no-evidence statement.
- The system prompt treats documents, tool results and history as untrusted data whose
  instructions are not followed; uncited prose that obeys such an instruction is replaced.
- Explicit demo mode usable without a key; no claim of real model activity in demo.
  A failed live request returns a coded 503/SSE error and never a demo answer.
  The active embedding mode is labelled, including the non-semantic lexical hash option.
- Terminal sandbox without arbitrary host execution, keys or Docker socket: five fixed
  presets (`pwd`, `ls`, `date`, `python --version`, `wc`), 2 s wall time, 1 s CPU,
  128 MiB memory, 16 KiB output, no file writes and four concurrent runs. Calculator
  expressions have at most 200 characters and nesting depth 12.
- Disabled optional tools (sandbox, MCP) are not offered to the model and appear as
  disabled in the catalog; an unreachable sandbox is reported as a failed tool call.
- Read-only MCP connected to the API and configured for Claude Code.
- Reproducible local setup and locked container build; sanitized packaging.
- JWT access with rotating refresh, Argon2, roles and persistent private histories;
  session lifetimes and per-client sign-in throttling as recorded in Clarifications.
  The browser ends the session only when refresh returns 401/403; network errors and
  other refresh failures keep it for a later retry.
- Document management, the tool playground, customer management and the request
  inbox are administrator-only; another account's conversation is reported as not found.
- Users can delete their own conversations; administrators can delete documents,
  which removes their chunks and vectors. Accounts are not deleted through the API.
- Backend-only provider environment configuration, without browser key forms or HTTP key routes.
- Public Humanizar corpus preloaded; grounded product recommendations and confirmed requests.
- A demo or support request is stored only after the user confirms it, once per user
  and action key, with the single status `received`; it sends no external message.
  Customers list their latest 20 requests; the administrator inbox is a read-only
  list of the latest 50.
- Optional PostgreSQL persistence with a dedicated schema, verified TLS and transactional session handling.
- Vercel same-origin API proxy to the HTTPS Docker backend, with authenticated sessions and streamed tool activity.
- Admin-only customer creation and paginated public account fields, with fixed customer roles and unchanged administrator cookies.
- Single section navigation, visible upload and document-reading controls; text at
  least 12 CSS px, text contrast at least 4.5:1, keyboard-operable controls and no
  horizontal page overflow at viewport widths of 320, 390 and 1440 CSS px. Chat
  completion is announced once to assistive technology without announcing every token.

## Scope limits

This baseline prepares the Softop technical assessment and remains configured for
Humanizar using public official information until the owner requests a company change.
Actual assessment acceptance criteria, company identity and tool policies still
come from the brief. PDF OCR, external message delivery, automatic calendar booking
and arbitrary autonomous code execution are outside this implementation. So are
account self-service beyond sign-up (password reset, e-mail verification, account
deletion), request status workflows and latency/throughput targets.

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
| FR-009 | Provider credentials come only from the backend environment | Removed HTTP routes, ignored legacy DB configuration and public-response isolation tests; live calls require the operator's backend key |
| FR-010 | Public Humanizar evidence supports recommendations and confirmed local requests | Recommendation, idempotency, owner listing and admin inbox tests |
| FR-011 | Optional PostgreSQL preserves auth and business contracts in a dedicated schema | Fifteen isolated PostgreSQL tests, concurrent bootstrap, production TLS 1.3 and persistence after API restart |
| FR-012 | Vercel proxies authenticated requests and SSE to the persistent Docker backend | Ready production deployment, secure session cookies, real tools, Swagger, protected origin and absence of backend keys from browser assets |
| FR-013 | Administrators create and list customer accounts without changing their session | Auth/role/public-field tests, coherent pagination snapshots in SQLite and PostgreSQL; production API rollout tracked separately |
| FR-014 | UI text, single navigation and Markdown upload/reading are readable and discoverable | Browser checks across 320–1440 px, measured contrast, admin ingestion/reading, persistent original text, legacy migration, role-aware navigation and keyboard-accessible mobile drawer |

Build, types, lint and responsive browser checks apply across these requirements.
Detailed execution evidence and external-service limits are recorded in docs/VALIDATION.md.
