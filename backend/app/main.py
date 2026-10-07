"""ASGI entry point (`app.main:app`): wires settings, resources, middleware and routers."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from weakref import WeakValueDictionary

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.accounts.auth import router as auth_router
from app.agent.company_agent import CompanyAgent, MessageProvider
from app.api.errors import register_exception_handlers
from app.api.routes import ROUTERS
from app.core.request_guard import RequestGuard
from app.core.settings import Settings
from app.knowledge.bootstrap import load_initial_knowledge
from app.knowledge.sample_data import DEMO_DOCUMENTS
from app.knowledge.store import KnowledgeStore
from app.persistence.factory import create_business_store, create_identity_store
from app.tools.registry import ToolRegistry


def create_app(
    settings: Settings | None = None, provider: MessageProvider | None = None
) -> FastAPI:
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        # Resources open in dependency order and close in reverse, also on startup failure.
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
            application.state.database = database
            application.state.store = store
            application.state.business = business
            application.state.registry = registry
            application.state.agent = agent
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
    api.state.settings = config
    api.state.ingestion_slots = asyncio.Semaphore(1)
    api.state.conversation_locks = WeakValueDictionary()
    chat_slots: asyncio.Queue[None] = asyncio.Queue(maxsize=config.max_concurrent_chats)
    for _ in range(config.max_concurrent_chats):
        chat_slots.put_nowait(None)
    api.state.chat_slots = chat_slots

    api.add_middleware(RequestGuard, upload_limit=config.max_upload_mb * 1024 * 1024)
    api.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        allow_credentials=True,
    )
    register_exception_handlers(api)
    api.include_router(auth_router)
    for router in ROUTERS:
        api.include_router(router)
    return api


app = create_app()
