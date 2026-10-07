import asyncio
import json
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from typing import Annotated, Any
from weakref import WeakValueDictionary

from fastapi import Depends, FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request

from app.agent import AgentFailure, CompanyAgent, MessageProvider
from app.auth import (
    CURRENT_USER_ID,
    CustomerCreatedResponse,
    CustomerListResponse,
    PublicCustomer,
    SignupRequest,
    User,
    hash_password,
    require_admin,
    require_user,
)
from app.auth import router as auth_router
from app.concurrency import run_sync
from app.ingestion import IngestionError, parse_upload
from app.knowledge_bootstrap import load_initial_knowledge
from app.models import (
    ActionConfirmation,
    ChatRequest,
    ChatResponse,
    CompanyInfo,
    DocumentDetail,
    DocumentList,
    HealthResponse,
    HealthTools,
    HistoryMessage,
    ToolRequest,
    ToolTrace,
    UploadResponse,
)
from app.persistence import BusinessRepository, IdentityStore, PersistenceUnavailable
from app.persistence_factory import create_business_store, create_identity_store
from app.request_guard import RequestGuard
from app.sample_data import DEMO_DOCUMENTS
from app.security import redact
from app.settings import Settings
from app.storage import KnowledgeStore
from app.tools import ToolRegistry


async def chat_events(
    agent: CompanyAgent,
    request: ChatRequest,
    on_complete: Callable[[ChatResponse], Awaitable[None]] | None = None,
) -> AsyncGenerator[str, None]:
    queue: asyncio.Queue[tuple[str, dict[str, Any]] | None] = asyncio.Queue(maxsize=128)

    async def emit(event: str, payload: dict[str, Any]) -> None:
        await queue.put((event, payload))

    async def produce() -> None:
        try:
            result = await agent.answer(request, emit)
            if on_complete is not None:
                await on_complete(result)
            await emit("done", result.model_dump())
        except AgentFailure as exc:
            await emit("error", {"message": exc.message, "code": exc.code})
        except Exception:
            await emit(
                "error", {"message": "No se pudo completar la consulta.", "code": "internal_error"}
            )
        finally:
            current = asyncio.current_task()
            if current is not None and not current.cancelling():
                await queue.put(None)

    task = asyncio.create_task(produce())
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            event, payload = item
            yield f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


def create_app(
    settings: Settings | None = None, provider: MessageProvider | None = None
) -> FastAPI:
    config = settings or Settings()
    ingestion_slots = asyncio.Semaphore(1)
    conversation_locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()
    chat_slots: asyncio.Queue[None] = asyncio.Queue(maxsize=config.max_concurrent_chats)
    for _ in range(config.max_concurrent_chats):
        chat_slots.put_nowait(None)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        async with AsyncExitStack() as resources:
            database = await asyncio.to_thread(create_identity_store, config)
            resources.push_async_callback(asyncio.to_thread, database.close)
            store = await asyncio.to_thread(KnowledgeStore, config)
            resources.push_async_callback(asyncio.to_thread, store.close)
            if config.seed_demo and config.company_name.casefold() == "forma":
                await asyncio.to_thread(store.seed, DEMO_DOCUMENTS)
            await asyncio.to_thread(load_initial_knowledge, store, config)
            business = await asyncio.to_thread(create_business_store, config, database)
            resources.push_async_callback(asyncio.to_thread, business.close)
            registry = ToolRegistry(config, store, business)
            resources.push_async_callback(registry.close)
            agent = CompanyAgent(config, registry, provider)
            resources.push_async_callback(agent.close)
            application.state.store, application.state.registry, application.state.agent = (
                store,
                registry,
                agent,
            )
            application.state.database = database
            application.state.business = business
            application.state.settings = config
            yield

    api = FastAPI(
        title="Lumen company assistant",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url="/api/redoc",
        swagger_ui_oauth2_redirect_url="/api/docs/oauth2-redirect",
    )

    @api.get("/docs", include_in_schema=False)
    def legacy_docs() -> RedirectResponse:
        return RedirectResponse("/api/docs", status_code=307)

    @api.get("/redoc", include_in_schema=False)
    def legacy_redoc() -> RedirectResponse:
        return RedirectResponse("/api/redoc", status_code=307)

    api.include_router(auth_router)
    bearer = HTTPBearer(auto_error=False, scheme_name="JWT")

    async def user_scope(
        request: Request,
        _credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> AsyncIterator[User | None]:
        user = await run_sync(require_user, request) if config.auth_enabled else None
        token = CURRENT_USER_ID.set(user.id if user is not None else None)
        try:
            yield user
        finally:
            CURRENT_USER_ID.reset(token)

    async def admin_scope(
        request: Request,
        _credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> AsyncIterator[User | None]:
        user = await run_sync(require_admin, request) if config.auth_enabled else None
        token = CURRENT_USER_ID.set(user.id if user is not None else None)
        try:
            yield user
        finally:
            CURRENT_USER_ID.reset(token)

    async def chat_admission() -> AsyncIterator[None]:
        try:
            chat_slots.get_nowait()
        except asyncio.QueueEmpty:
            raise HTTPException(
                429,
                "El asistente está ocupado. Intenta nuevamente en unos segundos.",
                headers={"Retry-After": "2"},
            ) from None
        try:
            yield
        finally:
            chat_slots.put_nowait(None)

    async def open_conversation(request: ChatRequest, user: User | None) -> ChatRequest:
        if user is None:
            return request
        database: IdentityStore = api.state.database
        try:
            identifier = await run_sync(
                database.create_conversation, user.id, request.session_id, request.message[:90]
            )
        except PermissionError as exc:
            raise HTTPException(404, "Conversación no encontrada.") from exc
        return request.model_copy(update={"session_id": identifier})

    async def with_server_history(request: ChatRequest, user: User | None) -> ChatRequest:
        if user is None or request.session_id is None:
            return request
        database: IdentityStore = api.state.database
        records = await run_sync(database.conversation_history, user.id, request.session_id)
        bounded: list[HistoryMessage] = []
        characters = 0
        for record in reversed(records[-40:]):
            message = HistoryMessage.model_validate(record)
            if characters + len(message.content) > 32000:
                break
            characters += len(message.content)
            bounded.append(message)
        return request.model_copy(update={"history": list(reversed(bounded))})

    def conversation_lock(request: ChatRequest, user: User | None) -> asyncio.Lock:
        key = f"{user.id if user else 'anonymous'}:{request.session_id or id(request)}"
        lock = conversation_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            conversation_locks[key] = lock
        return lock

    async def save_exchange(user: User | None, request: ChatRequest, result: ChatResponse) -> None:
        if user is not None and request.session_id is not None:
            database: IdentityStore = api.state.database
            await run_sync(
                database.save_exchange,
                user.id,
                request.session_id,
                request.message,
                result.model_dump(),
            )

    api.add_middleware(
        RequestGuard,
        upload_limit=config.max_upload_mb * 1024 * 1024,
    )
    api.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        allow_credentials=True,
    )

    @api.exception_handler(AgentFailure)
    async def agent_error(_request: Request, exc: AgentFailure) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": exc.message, "code": exc.code})

    @api.exception_handler(PersistenceUnavailable)
    async def persistence_error(_request: Request, _exc: PersistenceUnavailable) -> JSONResponse:
        return JSONResponse(
            status_code=503, content={"detail": "El almacenamiento no está disponible."}
        )

    @api.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        # Validation payloads may contain passwords or a rejected provider credential.
        return JSONResponse(
            status_code=422, content={"detail": "Los datos enviados no son válidos."}
        )

    @api.exception_handler(Exception)
    async def safe_error(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500, content={"detail": "No se pudo completar la operación."}
        )

    @api.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        active: Settings = api.state.settings
        registry: ToolRegistry = api.state.registry
        return HealthResponse(
            mode=active.mode,
            model=active.anthropic_model,
            embedding=config.embedding_label,
            tools=HealthTools(sandbox=await registry.sandbox_available(), mcp=config.mcp_enabled),
        )

    @api.get("/api/config")
    def public_config() -> dict[str, Any]:
        active: Settings = api.state.settings
        return {
            "company_name": redact(config.company_name),
            "company_description": redact(config.company_description),
            "assistant_name": redact(config.assistant_name),
            "model": active.anthropic_model,
            "mode": active.mode,
            "embedding": config.embedding_label,
            "max_upload_mb": config.max_upload_mb,
        }

    @api.get("/api/company", response_model=CompanyInfo, response_model_exclude_none=True)
    def company() -> CompanyInfo:
        return CompanyInfo(
            company_name=redact(config.company_name),
            company_description=redact(config.company_description),
            assistant_name=redact(config.assistant_name),
            website=redact(config.website) if config.website else None,
            suggested_questions=[redact(item) for item in config.suggested_questions],
        )

    @api.get("/api/search")
    async def search(
        query: Annotated[str, Query(min_length=1, max_length=1000)],
        _user: Annotated[User | None, Depends(user_scope)],
    ) -> dict[str, Any]:
        store: KnowledgeStore = api.state.store
        sources = await run_sync(store.search, query)
        return {"sources": [source.model_dump() for source in sources]}

    @api.get("/api/documents", response_model=DocumentList)
    def documents(_user: Annotated[User | None, Depends(admin_scope)]) -> DocumentList:
        store: KnowledgeStore = api.state.store
        return store.list_documents()

    @api.post("/api/documents", response_model=UploadResponse)
    async def upload(
        file: Annotated[UploadFile, File()],
        _user: Annotated[User | None, Depends(admin_scope)],
    ) -> UploadResponse:
        await ingestion_slots.acquire()
        data = bytearray()
        limit = config.max_upload_mb * 1024 * 1024
        try:
            while block := await file.read(65536):
                data.extend(block)
                if len(data) > limit:
                    raise HTTPException(413, "El archivo excede el tamaño permitido.")
            parsed, skipped = await run_sync(
                parse_upload,
                file.filename or "",
                bytes(data),
                config,
            )
            store: KnowledgeStore = api.state.store
            created = await run_sync(store.add_documents, parsed)
            current = await run_sync(store.list_documents)
            return UploadResponse(
                documents=created, total_chunks=current.total_chunks, skipped=skipped
            )
        except IngestionError as exc:
            raise HTTPException(422, str(exc)) from exc
        finally:
            ingestion_slots.release()
            await file.close()

    @api.get("/api/documents/{document_id}", response_model=DocumentDetail)
    async def document_detail(
        document_id: str,
        response: Response,
        _user: Annotated[User | None, Depends(admin_scope)],
    ) -> DocumentDetail:
        store: KnowledgeStore = api.state.store
        detail = await run_sync(store.get_document, document_id)
        if detail is None:
            raise HTTPException(404, "Documento no encontrado.")
        response.headers["Cache-Control"] = "no-store"
        return detail

    @api.delete("/api/documents/{document_id}", status_code=204)
    def delete(document_id: str, _user: Annotated[User | None, Depends(admin_scope)]) -> Response:
        store: KnowledgeStore = api.state.store
        if not store.delete(document_id):
            raise HTTPException(404, "Documento no encontrado.")
        return Response(status_code=204)

    @api.get("/api/tools")
    def tools(_user: Annotated[User | None, Depends(user_scope)]) -> dict[str, Any]:
        registry: ToolRegistry = api.state.registry
        return {"tools": registry.catalog()}

    @api.post("/api/tools/run", response_model=ToolTrace)
    async def tool_run(
        request: ToolRequest, user: Annotated[User | None, Depends(admin_scope)]
    ) -> ToolTrace:
        registry: ToolRegistry = api.state.registry
        return (
            await registry.run(
                request.name,
                request.input,
                user_id=user.id if user else None,
                confirmed=request.confirmed,
            )
        ).trace

    @api.post("/api/actions/confirm", response_model=ToolTrace, dependencies=[Depends(bearer)])
    async def confirm_action(
        request: ActionConfirmation, user: Annotated[User, Depends(require_user)]
    ) -> ToolTrace:
        registry: ToolRegistry = api.state.registry
        return (
            await registry.run(
                request.tool,
                request.input,
                user_id=user.id,
                confirmed=True,
                action_key=request.action_key,
            )
        ).trace

    @api.get("/api/requests", dependencies=[Depends(bearer)])
    async def my_requests(user: Annotated[User, Depends(require_user)]) -> dict[str, Any]:
        business: BusinessRepository = api.state.business
        return {"requests": await run_sync(business.list_requests, user.id)}

    @api.get("/api/admin/requests", dependencies=[Depends(bearer)])
    async def admin_requests(_user: Annotated[User, Depends(require_admin)]) -> dict[str, Any]:
        business: BusinessRepository = api.state.business
        return {"requests": await run_sync(business.list_all_requests)}

    @api.get(
        "/api/admin/customers",
        response_model=CustomerListResponse,
        dependencies=[Depends(bearer)],
    )
    async def admin_customers(
        response: Response,
        _user: Annotated[User, Depends(require_admin)],
        limit: Annotated[int, Query(ge=1, le=100)] = 25,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> CustomerListResponse:
        database: IdentityStore = api.state.database
        customers, total = await run_sync(database.list_customers, limit, offset)
        response.headers["Cache-Control"] = "no-store"
        return CustomerListResponse(
            customers=[PublicCustomer.model_validate(customer) for customer in customers],
            total=total,
            limit=limit,
            offset=offset,
        )

    @api.post(
        "/api/admin/customers",
        response_model=CustomerCreatedResponse,
        status_code=201,
        dependencies=[Depends(bearer)],
    )
    async def create_customer(
        payload: SignupRequest,
        response: Response,
        _user: Annotated[User, Depends(require_admin)],
    ) -> CustomerCreatedResponse:
        database: IdentityStore = api.state.database
        password_hash = await run_sync(hash_password, payload.password.get_secret_value())
        try:
            user = await run_sync(
                database.register_customer, payload.name, payload.email, password_hash
            )
        except ValueError:
            raise HTTPException(409, "No se pudo crear la cuenta.") from None
        customer = await run_sync(database.get_customer, user.id)
        if customer is None:
            raise PersistenceUnavailable()
        response.headers["Cache-Control"] = "no-store"
        return CustomerCreatedResponse(customer=PublicCustomer.model_validate(customer))

    @api.get("/api/conversations", dependencies=[Depends(bearer)])
    async def conversations(user: Annotated[User, Depends(require_user)]) -> dict[str, Any]:
        database: IdentityStore = api.state.database
        return {"conversations": await run_sync(database.list_conversations, user.id)}

    @api.delete("/api/conversations/{identifier}", status_code=204, dependencies=[Depends(bearer)])
    async def remove_conversation(
        identifier: str, user: Annotated[User, Depends(require_user)]
    ) -> Response:
        database: IdentityStore = api.state.database
        try:
            removed = await run_sync(database.delete_conversation, user.id, identifier)
        except PermissionError as exc:
            raise HTTPException(404, "Conversación no encontrada.") from exc
        if not removed:
            raise HTTPException(404, "Conversación no encontrada.")
        return Response(status_code=204)

    @api.post("/api/chat", response_model=ChatResponse)
    async def chat(
        request: ChatRequest,
        user: Annotated[User | None, Depends(user_scope)],
        _admission: Annotated[None, Depends(chat_admission, scope="request")],
    ) -> ChatResponse:
        request = await open_conversation(request, user)
        async with conversation_lock(request, user):
            request = await with_server_history(request, user)
            agent: CompanyAgent = api.state.agent
            result = await agent.answer(request)
            await save_exchange(user, request, result)
            return result

    @api.post("/api/chat/stream")
    async def stream_chat(
        request: ChatRequest,
        user: Annotated[User | None, Depends(user_scope)],
        _admission: Annotated[None, Depends(chat_admission, scope="request")],
    ) -> StreamingResponse:
        request = await open_conversation(request, user)

        async def events() -> AsyncGenerator[str, None]:
            async with conversation_lock(request, user):
                prepared = await with_server_history(request, user)

                async def persist(result: ChatResponse) -> None:
                    await save_exchange(user, prepared, result)

                agent: CompanyAgent = api.state.agent
                async for event in chat_events(agent, prepared, persist):
                    yield event

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return api


app = create_app()
