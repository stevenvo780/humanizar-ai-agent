# Lumen API contract

All routes use `/api`. Local development proxies these routes to port 8000.

Interactive Swagger uses `GET /api/docs`; OpenAPI uses `GET /api/openapi.json`.
Both are available through the same-origin frontend proxy, including LAN access.

Authentication is enabled by default. `/health`, `/config`, `/company` and auth
setup/login/register/status are public. Other routes require an access JWT in
`Authorization: Bearer TOKEN`. Document management, manual tools
and `/admin/requests` require the admin role. `/admin/customers` requires an admin
JWT even when other component routes disable authentication for isolated tests.
Tests explicitly disable auth only
for legacy isolated component checks.

`GET /auth/status` -> `{setup_required: boolean}`.
`POST /auth/setup` creates the sole first administrator; `/auth/register` creates
customers. Both accept `{name,email,password}` (password 6–128 characters).
`POST /auth/login` accepts `{email,password}`. These return
`{access_token,token_type:"bearer",user:{id,name,email,role}}` and set an HttpOnly
refresh cookie. Access JWT lasts 30 minutes; refresh lasts seven days.
`POST /auth/refresh` rotates the session, `/auth/logout` revokes its family; both
require `X-Requested-With: Humanizar`. `GET /auth/me` returns the authenticated user.
The browser keeps access tokens only in memory.

`GET /api/admin/customers?limit=25&offset=0` requires an administrator and returns
`{customers: Customer[], total: number, limit: number, offset: number}`. `limit` is
1–100 (default 25); `offset` is nonnegative (default 0). Only customer accounts are
included, ordered by creation time descending, then id. An offset past the last
account returns an empty page with the same total. Each page and its total use
the same database snapshot, including during concurrent registrations.

`Customer`: `{id: string, name: string, email: string, role: "customer", created_at: string}`.
`created_at` is an ISO 8601 UTC timestamp. Passwords, hashes and session data are
never included.

`POST /api/admin/customers` requires an administrator and accepts exactly
`{name,email,password}` using the same signup validation: trimmed name (1–120),
normalized email (3–254), password (6–128). It returns **201**
`{customer: Customer}`. Additional fields, including `role`, are rejected; the
created account always has the customer role. Creation does not issue tokens,
create a session, set cookies or change the administrator's session. Duplicate
accounts return a generic 409; invalid fields/pagination return 422. Missing or
invalid JWT returns 401; a customer JWT returns 403. Successful customer-management
responses set `Cache-Control: no-store`. SQLite and PostgreSQL share this contract.

Production configures `AUTH_BOOTSTRAP_TOKEN`: `/auth/setup` then requires a matching
`X-Bootstrap-Token` header. The token is never exposed by `/auth/status` or other
responses. Provision the administrator privately before publishing the frontend:
`python -m app.manage create-admin` inside the API container, or `--stdin-json`
with `{name,email,password}` over private stdin. The CLI emits no session or JWT.
Password limits remain 6–128 characters. Once an administrator exists, bootstrap
returns 409 and all public registrations create customers.

`GET /api/health`: `{status: "ok", mode: "demo" | "anthropic", model: string, embedding: string, tools: {sandbox: boolean, mcp: boolean}, features: {customer_management: true, document_reading: true}}`.
`features.customer_management` is always true in this backend version, independently
of `AUTH_ENABLED`; it signals that the customer-management routes exist. Older
versions may omit `features`, so clients should only expose this feature when the
flag is explicitly true. Health is public and returns no customer or account data.
`features.document_reading` signals that the document-content route exists; the
reader only enables when this flag is explicitly true. Earlier API releases may
omit it, allowing frontend and backend updates to occur independently.

`GET /api/config`: `{company_name: string, company_description: string, assistant_name: string, model: string, mode: "demo" | "anthropic", embedding: string, max_upload_mb: number}`.

`GET /api/company`: `{company_name: string, company_description: string, assistant_name: string, website?: string, suggested_questions?: string[]}`. An absent list lets the UI show generic prompts; `[]` hides them.
The optional website uses HTTP(S); suggestions have at most eight items. The
frontend remains compatible with older responses containing only the three
identity strings. Humanizar defaults only apply to the Humanizar profile.

`GET /api/documents`: `{documents: Document[], total_chunks: number}`.

`Document`: `{id: string, name: string, chunks: number, characters: number, created_at: string}`.

`GET /api/documents/{id}`: administrator-only document reader. Returns the
`Document` fields plus `{content: string, reconstructed: boolean}`; missing or
deleted ids return 404. With authentication enabled, missing/invalid JWTs return
401 and customer JWTs return 403. Responses use `Cache-Control: no-store`.
New uploads retain their complete extracted text, with `reconstructed: false`.
Legacy documents are read from stored chunks in insertion order with overlaps
removed when possible, with `reconstructed: true`; the original whitespace or
Markdown formatting is not guaranteed. Reading does not query the vector service.

`POST /api/documents`: multipart field `file`, supports TXT, MD, PDF, CSV, JSON, DOCX and ZIP. Returns `{documents: Document[], total_chunks: number, skipped: string[]}`. ZIP paths are never extracted to the host. Maximum upload and decompressed sizes must be enforced.

`DELETE /api/documents/{id}`: 204. Missing id: 404.

`POST /api/chat` or `POST /api/chat/stream`: JSON `{message: string, history?: {role: "user" | "assistant", content: string}[], session_id?: string}`.
With authentication the server loads the user's database history and ignores the
client-supplied history. Completed exchanges persist before the SSE `done` event.
`GET /conversations` -> `{conversations: Conversation[]}` (frontend representation);
`DELETE /conversations/{id}` -> 204 or 404, strictly scoped to the authenticated owner.

`Source`: `{document_id: string, document_name: string, chunk_id: string, text: string, score: number}`.

`ToolTrace`: `{id: string, tool: string, input: object, output: string, status: "completed" | "error", duration_ms: number}`. Execution traces report actual tool calls; never show internal chain of thought.

`ChatResponse`: `{answer: string, sources: Source[], trace: ToolTrace[], mode: "demo" | "anthropic", model: string, usage: {input_tokens: number, output_tokens: number}, session_id: string}`.

Streaming uses SSE (`text/event-stream`) with standard `event: NAME\ndata: JSON\n\n` framing:

- `status`: `{message: string}`.
- `tool`: `ToolTrace`.
- `token`: `{text: string}`.
- `done`: complete `ChatResponse`.
- `error`: `{message: string, code: string}`. Provider codes: `authentication`,
  `rate_limit`, `provider_configuration` (model or permissions rejected),
  `provider_unavailable`, `provider_error`, `refusal`, `output_limit`, `tool_limit`,
  `iteration_limit`. Provider failures are logged with type, status and request id only.

`GET /api/tools`: `{tools: {name: string, description: string, enabled: boolean, input_schema: object}[]}`.
The bounded JSON Schema has `type: "object"`, `properties`, `required` and
`additionalProperties: false`. Properties are string (`minLength`/`maxLength`/`enum`),
number or integer (`minimum`/`maximum`) or boolean; `required` omits optional ones. The same central definition is sent to Anthropic.
The browser derives simple string/enum/number/boolean fields from that schema;
older APIs without schemas retain compatible forms for their existing tools.
Registering a schema does not register an executable handler or grant permissions.

`POST /api/tools/run`: admin only, `{name: string, input: object, confirmed?: boolean}`,
returns `ToolTrace`. Existing tools: `search_knowledge` (`query`), `calculate`
(`expression`), `terminal` (named preset) and `mcp_company_info` (empty input).
Terminal only runs on the dedicated sandbox service.

New tools: `recommend_product` (`process`), `create_demo_request`
(`name,email,company,interest,needs`), `create_support_ticket`
(`subject,description`) and `list_my_requests` (empty input).
Agent write calls return `{requires_confirmation:true,action:{tool,input},message}`
inside `ToolTrace.output`; no record is created yet. A user click calls
`POST /actions/confirm` with `{tool,input,action_key: trace.id}`. Only the two business
write tools are accepted. Confirmation is idempotent per user and action key.
Successful output is `{request:{id,kind,status:"received",created_at,details},message}`.
`GET /requests` lists the user's records. `GET /admin/requests` lists the admin inbox.
No external notifications or calendar bookings are made.

JSON and SSE chat share a global concurrency bound (`MAX_CONCURRENT_CHATS=4`).
When all slots are occupied, requests receive 429 with `Retry-After: 2` rather
than starting additional model calls. Cancellation releases a chat slot after
the agent stops. Ingestion holds its exclusive slot until parsing/storage workers
actually finish, including when the requesting client disconnects.

Anthropic configuration comes exclusively from the backend environment. There are
no HTTP routes for reading, saving or testing API keys. Restart the API after
changing its private configuration. `/health` and `/config` expose only the active
mode and model. SDK authentication errors are explicit; no silent demo fallback.

The sandbox interface (port 8001) is `GET /health` and `POST /run` with `{command: string}` -> `{stdout: string, stderr: string, exit_code: number}`. No credentials, arbitrary shell, Docker socket or writable host mounts. Commands cannot make network requests; Compose attaches only an internal network. The API accesses it using `SANDBOX_URL`.

The read-only MCP server lives at `backend/app/mcp/server.py`, invoked with `uv run --project backend --extra semantic python -m app.mcp.server`. It exposes company_info and search_knowledge via persistent API HTTP calls to avoid a second writer opening Qdrant local storage. Default URL `http://127.0.0.1:8000`, configurable with `LUMEN_API_URL`. `GET /api/company` exposes configured identity; `GET /api/search?query=...` returns `{sources: Source[]}` for MCP retrieval.
Protected MCP searches use an explicit `LUMEN_API_TOKEN` or a private origin-bound
session from `LUMEN_API_TOKEN_FILE`, created by the interactive `mcp-login` CLI.
The API remains authenticated; public identity does not require a session.
Refresh failures distinguish rejected credentials from transient unavailability
and preserve the saved file on temporary errors. See `docs/MCP.md` for setup.

Backend settings: `ANTHROPIC_API_KEY`, `LLM_MODE=demo|anthropic|auto`,
`ANTHROPIC_MODEL=claude-haiku-4-5`, `MAX_CONCURRENT_CHATS=4`,
`COMPANY_NAME=Humanizar`, `COMPANY_DESCRIPTION`,
`COMPANY_WEBSITE`, `COMPANY_SUGGESTED_QUESTIONS` (JSON string array),
`COMPANY_PRODUCTS` (JSON array of `{name, keywords}`),
`ASSISTANT_NAME=Humanizar IA`, `DATA_DIR`, `AUTH_ENABLED=true`, `SEED_DEMO=false`,
`KNOWLEDGE_DIR=knowledge/humanizar`, `EMBEDDING_PROVIDER=hash|fastembed`, `QDRANT_URL`,
`SANDBOX_URL`, `MCP_ENABLED=true`, `DATABASE_URL`, `DATABASE_SCHEMA=lumen`,
`JWT_SECRET`, `AUTH_BOOTSTRAP_TOKEN`. Relative `KNOWLEDGE_DIR` resolves from backend/;
Markdown/TXT source documents are loaded once per filename without replacing uploads.
Root `.env` is never sent to the frontend or sandbox. API uses a single worker with
local Qdrant storage.

An empty `DATABASE_URL` selects persistent SQLite. PostgreSQL uses a dedicated
schema and requires verified TLS for remote connections. The production URL has
the form `postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE?sslmode=verify-full&sslrootcert=system`,
with URL-encoded credentials supplied privately. Only `sslmode` and `sslrootcert`
query options are accepted. Accounts, refresh families, histories and business
requests keep the same HTTP contract on either database. PostgreSQL bootstrap,
refresh/revocation and confirmed actions use transactions and interprocess locks.
Health/config never return database URLs, secrets or credentials.

The deployed browser uses Vercel's same-origin rewrite for `/api`, including SSE,
Swagger and OpenAPI. A server-side `ORIGIN_SECRET` protects access to the VPS proxy;
it is separate from API authentication and is never included in browser headers.
HTTPS sets the refresh cookie's Secure flag. API responses must not be cached.
See [DEPLOYMENT.md](DEPLOYMENT.md) for environment placement and verification.
