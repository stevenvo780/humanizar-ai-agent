# Lumen API contract

All routes use `/api`. Local development proxies these routes to port 8000.

Interactive Swagger uses `GET /api/docs`; OpenAPI uses `GET /api/openapi.json`.
Both are available through the same-origin frontend proxy, including LAN access.

Authentication is enabled by default. `/health`, `/config`, `/company` and auth
setup/login/register/status are public. Other routes require an access JWT in
`Authorization: Bearer TOKEN`. Document management, manual tools, provider settings
and `/admin/requests` require the admin role. Tests explicitly disable auth only
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

`GET /api/health`: `{status: "ok", mode: "demo" | "anthropic", model: string, embedding: string, tools: {sandbox: boolean, mcp: boolean}}`.

`GET /api/config`: `{company_name: string, company_description: string, assistant_name: string, model: string, mode: "demo" | "anthropic", embedding: string, max_upload_mb: number}`.

`GET /api/documents`: `{documents: Document[], total_chunks: number}`.

`Document`: `{id: string, name: string, chunks: number, characters: number, created_at: string}`.

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
- `error`: `{message: string, code: string}`.

`GET /api/tools`: `{tools: {name: string, description: string, enabled: boolean}[]}`.

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

`GET /settings/provider` -> `{configured,model,mode,verified}`; admin-only
`PUT /settings/provider` accepts `{api_key}` and encrypts it at rest. The key is never
returned. `POST /settings/provider/test` makes a real eight-token Haiku call and
only verifies the current configuration. Saving activates the Anthropic provider
without restarting. SDK authentication errors are explicit; no silent demo fallback.

The sandbox interface (port 8001) is `GET /health` and `POST /run` with `{command: string}` -> `{stdout: string, stderr: string, exit_code: number}`. No credentials, arbitrary shell, Docker socket or writable host mounts. Commands cannot make network requests; Compose attaches only an internal network. The API accesses it using `SANDBOX_URL`.

The read-only MCP server lives at `backend/app/mcp_server.py`, invoked with `uv run --project backend --extra semantic python -m app.mcp_server`. It exposes company_info and search_knowledge via persistent API HTTP calls to avoid a second writer opening Qdrant local storage. Default URL `http://127.0.0.1:8000`, configurable with `LUMEN_API_URL`. `GET /api/company` exposes configured identity; `GET /api/search?query=...` returns `{sources: Source[]}` for MCP retrieval.

Backend settings: `ANTHROPIC_API_KEY`, `LLM_MODE=demo|anthropic|auto`,
`ANTHROPIC_MODEL=claude-haiku-4-5`, `COMPANY_NAME=Humanizar`, `COMPANY_DESCRIPTION`,
`ASSISTANT_NAME=Humanizar IA`, `DATA_DIR`, `AUTH_ENABLED=true`, `SEED_DEMO=false`,
`KNOWLEDGE_DIR=knowledge/humanizar`, `EMBEDDING_PROVIDER=hash|fastembed`, `QDRANT_URL`,
`SANDBOX_URL`, `MCP_ENABLED=true`. Relative `KNOWLEDGE_DIR` resolves from backend/;
Markdown/TXT source documents are loaded once per filename without replacing uploads.
Root `.env` is never sent to the frontend or sandbox. API uses a single worker with
local Qdrant storage.
