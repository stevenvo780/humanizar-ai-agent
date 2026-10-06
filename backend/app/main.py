import asyncio
import json
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from typing import Annotated, Any
from weakref import WeakValueDictionary

import anthropic
from fastapi import Depends, FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import SecretStr
from starlette.requests import Request

from app.agent import AgentFailure, CompanyAgent, MessageProvider
from app.auth import CURRENT_USER_ID, User, require_admin, require_user
from app.auth import router as auth_router
from app.business import BusinessStore
from app.database import ApplicationDatabase
from app.ingestion import IngestionError, parse_upload
from app.knowledge_bootstrap import load_initial_knowledge
from app.models import (
    ActionConfirmation,
    ChatRequest,
    ChatResponse,
    DocumentList,
    HistoryMessage,
    ProviderConfiguration,
    ToolRequest,
    ToolTrace,
    UploadResponse,
)
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
    active_agents: dict[CompanyAgent, int] = {}
    retired_agents: set[CompanyAgent] = set()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        async with AsyncExitStack() as resources:
            database = await asyncio.to_thread(ApplicationDatabase, config.data_dir)
            resources.push_async_callback(asyncio.to_thread, database.close)
            store = await asyncio.to_thread(KnowledgeStore, config)
            resources.push_async_callback(asyncio.to_thread, store.close)
            if config.seed_demo and config.company_name.casefold() == "forma":
                await asyncio.to_thread(store.seed, DEMO_DOCUMENTS)
            await asyncio.to_thread(load_initial_knowledge, store, config)
            runtime_config = config
            saved_key = await asyncio.to_thread(database.get_provider_key)
            if saved_key:
                runtime_config = config.model_copy(
                    update={"anthropic_api_key": SecretStr(saved_key), "llm_mode": "auto"}
                )
            business = await asyncio.to_thread(BusinessStore, config.data_dir)
            resources.push_async_callback(asyncio.to_thread, business.close)
            registry = ToolRegistry(runtime_config, store, business)
            resources.push_async_callback(registry.close)
            agent = CompanyAgent(runtime_config, registry, provider)
            application.state.store, application.state.registry, application.state.agent = (
                store,
                registry,
                agent,
            )
            application.state.database = database
            application.state.business = business
            application.state.settings = runtime_config
            application.state.provider_verified = False
            application.state.provider_generation = 0
            application.state.provider_lock = asyncio.Lock()
            application.state.retired_agents = retired_agents

            async def close_agents() -> None:
                async with AsyncExitStack() as closers:
                    for current in {application.state.agent, *retired_agents}:
                        closers.push_async_callback(current.close)
                retired_agents.clear()
                active_agents.clear()

            resources.push_async_callback(close_agents)
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
        user = require_user(request) if config.auth_enabled else None
        token = CURRENT_USER_ID.set(user.id if user is not None else None)
        try:
            yield user
        finally:
            CURRENT_USER_ID.reset(token)

    async def admin_scope(
        request: Request,
        _credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> AsyncIterator[User | None]:
        user = require_admin(request) if config.auth_enabled else None
        token = CURRENT_USER_ID.set(user.id if user is not None else None)
        try:
            yield user
        finally:
            CURRENT_USER_ID.reset(token)

    @asynccontextmanager
    async def agent_scope() -> AsyncIterator[CompanyAgent]:
        async with api.state.provider_lock:
            current: CompanyAgent = api.state.agent
            active_agents[current] = active_agents.get(current, 0) + 1
        try:
            yield current
        finally:
            async with api.state.provider_lock:
                remaining = active_agents[current] - 1
                if remaining:
                    active_agents[current] = remaining
                else:
                    active_agents.pop(current)
                    if current in retired_agents:
                        retired_agents.remove(current)
                        await current.close()

    async def open_conversation(request: ChatRequest, user: User | None) -> ChatRequest:
        if user is None:
            return request
        database: ApplicationDatabase = api.state.database
        try:
            identifier = await asyncio.to_thread(
                database.create_conversation, user.id, request.session_id, request.message[:90]
            )
        except PermissionError as exc:
            raise HTTPException(404, "Conversación no encontrada.") from exc
        return request.model_copy(update={"session_id": identifier})

    async def with_server_history(request: ChatRequest, user: User | None) -> ChatRequest:
        if user is None or request.session_id is None:
            return request
        database: ApplicationDatabase = api.state.database
        records = await asyncio.to_thread(
            database.conversation_history, user.id, request.session_id
        )
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
            database: ApplicationDatabase = api.state.database
            await asyncio.to_thread(
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

    @api.get("/api/health")
    async def health() -> dict[str, Any]:
        active: Settings = api.state.settings
        registry: ToolRegistry = api.state.registry
        return {
            "status": "ok",
            "mode": active.mode,
            "model": active.anthropic_model,
            "embedding": config.embedding_label,
            "tools": {"sandbox": await registry.sandbox_available(), "mcp": config.mcp_enabled},
        }

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

    @api.get("/api/company")
    def company() -> dict[str, str]:
        return {
            "company_name": redact(config.company_name),
            "company_description": redact(config.company_description),
            "assistant_name": redact(config.assistant_name),
        }

    @api.get("/api/search")
    def search(
        query: Annotated[str, Query(min_length=1, max_length=1000)],
        _user: Annotated[User | None, Depends(user_scope)],
    ) -> dict[str, Any]:
        store: KnowledgeStore = api.state.store
        return {"sources": [source.model_dump() for source in store.search(query)]}

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
            parsed, skipped = await asyncio.to_thread(
                parse_upload,
                file.filename or "",
                bytes(data),
                config,
            )
            store: KnowledgeStore = api.state.store
            created = await asyncio.to_thread(store.add_documents, parsed)
            current = await asyncio.to_thread(store.list_documents)
            return UploadResponse(
                documents=created, total_chunks=current.total_chunks, skipped=skipped
            )
        except IngestionError as exc:
            raise HTTPException(422, str(exc)) from exc
        finally:
            ingestion_slots.release()
            await file.close()

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
        business: BusinessStore = api.state.business
        return {"requests": await asyncio.to_thread(business.list_requests, user.id)}

    @api.get("/api/admin/requests", dependencies=[Depends(bearer)])
    async def admin_requests(_user: Annotated[User, Depends(require_admin)]) -> dict[str, Any]:
        business: BusinessStore = api.state.business
        return {"requests": await asyncio.to_thread(business.list_all_requests)}

    @api.get("/api/conversations", dependencies=[Depends(bearer)])
    async def conversations(user: Annotated[User, Depends(require_user)]) -> dict[str, Any]:
        database: ApplicationDatabase = api.state.database
        return {"conversations": await asyncio.to_thread(database.list_conversations, user.id)}

    @api.delete("/api/conversations/{identifier}", status_code=204, dependencies=[Depends(bearer)])
    async def remove_conversation(
        identifier: str, user: Annotated[User, Depends(require_user)]
    ) -> Response:
        database: ApplicationDatabase = api.state.database
        try:
            removed = await asyncio.to_thread(database.delete_conversation, user.id, identifier)
        except PermissionError as exc:
            raise HTTPException(404, "Conversación no encontrada.") from exc
        if not removed:
            raise HTTPException(404, "Conversación no encontrada.")
        return Response(status_code=204)

    @api.get("/api/settings/provider", dependencies=[Depends(bearer)])
    def provider_status(_user: Annotated[User, Depends(require_admin)]) -> dict[str, Any]:
        active: Settings = api.state.settings
        return {
            "configured": bool(active.anthropic_api_key.get_secret_value()),
            "model": active.anthropic_model,
            "mode": active.mode,
            "verified": api.state.provider_verified,
        }

    @api.put("/api/settings/provider", dependencies=[Depends(bearer)])
    async def configure_provider(
        request: ProviderConfiguration, _user: Annotated[User, Depends(require_admin)]
    ) -> dict[str, Any]:
        database: ApplicationDatabase = api.state.database
        secret = request.api_key.get_secret_value().strip()
        if len(secret) < 20:
            raise HTTPException(422, "Introduce una clave válida de Anthropic.")
        async with api.state.provider_lock:
            active: Settings = api.state.settings.model_copy(
                update={"anthropic_api_key": SecretStr(secret), "llm_mode": "auto"}
            )
            replacement = CompanyAgent(active, api.state.registry)
            try:
                await asyncio.to_thread(database.set_provider_key, secret)
            except BaseException:
                await replacement.close()
                raise
            old: CompanyAgent = api.state.agent
            api.state.settings = active
            api.state.registry.settings = active
            api.state.agent = replacement
            api.state.provider_verified = False
            api.state.provider_generation += 1
            if active_agents.get(old, 0):
                retired_agents.add(old)
            else:
                await old.close()
        return {
            "configured": True,
            "model": active.anthropic_model,
            "mode": active.mode,
            "verified": False,
        }

    @api.post("/api/settings/provider/test", dependencies=[Depends(bearer)])
    async def test_provider(_user: Annotated[User, Depends(require_admin)]) -> dict[str, Any]:
        active: Settings = api.state.settings
        generation: int = api.state.provider_generation
        if not active.anthropic_api_key.get_secret_value():
            raise HTTPException(409, "Configura una clave de Anthropic primero.")
        try:
            async with anthropic.AsyncAnthropic(
                api_key=active.anthropic_api_key.get_secret_value(), timeout=20, max_retries=0
            ) as client:
                response = await client.messages.create(
                    model=active.anthropic_model,
                    max_tokens=8,
                    messages=[{"role": "user", "content": "Responde solo OK."}],
                )
            if generation != api.state.provider_generation:
                raise HTTPException(409, "La configuración cambió; verifica la clave actual.")
            if not response.content:
                raise HTTPException(503, "Anthropic devolvió una respuesta vacía.")
            api.state.provider_verified = True
        except anthropic.AuthenticationError as exc:
            raise HTTPException(400, "Anthropic rechazó la clave.") from exc
        except anthropic.APIError as exc:
            raise HTTPException(503, "No se pudo verificar la conexión con Anthropic.") from exc
        return {"ok": api.state.provider_verified, "message": "Claude Haiku conectado."}

    @api.post("/api/chat", response_model=ChatResponse)
    async def chat(
        request: ChatRequest, user: Annotated[User | None, Depends(user_scope)]
    ) -> ChatResponse:
        request = await open_conversation(request, user)
        async with conversation_lock(request, user):
            request = await with_server_history(request, user)
            async with agent_scope() as agent:
                result = await agent.answer(request)
            await save_exchange(user, request, result)
            return result

    @api.post("/api/chat/stream")
    async def stream_chat(
        request: ChatRequest, user: Annotated[User | None, Depends(user_scope)]
    ) -> StreamingResponse:
        request = await open_conversation(request, user)

        async def events() -> AsyncGenerator[str, None]:
            async with conversation_lock(request, user):
                prepared = await with_server_history(request, user)

                async def persist(result: ChatResponse) -> None:
                    await save_exchange(user, prepared, result)

                async with agent_scope() as agent:
                    async for event in chat_events(agent, prepared, persist):
                        yield event

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return api


app = create_app()
