"""Shared FastAPI dependencies: authentication scopes, chat admission and typed app state."""

import asyncio
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request

from app.accounts.dependencies import CURRENT_USER_ID, require_admin, require_user
from app.agent.company_agent import CompanyAgent
from app.core.concurrency import run_sync
from app.core.settings import Settings
from app.knowledge.store import KnowledgeStore
from app.persistence.contracts import BusinessRepository, IdentityStore
from app.persistence.models import User
from app.tools.registry import ToolRegistry

bearer = HTTPBearer(auto_error=False, scheme_name="JWT")


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_store(request: Request) -> KnowledgeStore:
    store: KnowledgeStore = request.app.state.store
    return store


def get_registry(request: Request) -> ToolRegistry:
    registry: ToolRegistry = request.app.state.registry
    return registry


def get_agent(request: Request) -> CompanyAgent:
    agent: CompanyAgent = request.app.state.agent
    return agent


def get_database(request: Request) -> IdentityStore:
    database: IdentityStore = request.app.state.database
    return database


def get_business(request: Request) -> BusinessRepository:
    business: BusinessRepository = request.app.state.business
    return business


async def user_scope(
    request: Request,
    _credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AsyncIterator[User | None]:
    """Authenticated user (or None when AUTH_ENABLED=false) bound to CURRENT_USER_ID."""
    enabled = get_settings(request).auth_enabled
    user = await run_sync(require_user, request) if enabled else None
    token = CURRENT_USER_ID.set(user.id if user is not None else None)
    try:
        yield user
    finally:
        CURRENT_USER_ID.reset(token)


async def admin_scope(
    request: Request,
    _credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AsyncIterator[User | None]:
    enabled = get_settings(request).auth_enabled
    user = await run_sync(require_admin, request) if enabled else None
    token = CURRENT_USER_ID.set(user.id if user is not None else None)
    try:
        yield user
    finally:
        CURRENT_USER_ID.reset(token)


async def chat_admission(request: Request) -> AsyncIterator[None]:
    """Global bound shared by JSON and SSE chat; excess requests receive 429."""
    slots: asyncio.Queue[None] = request.app.state.chat_slots
    try:
        slots.get_nowait()
    except asyncio.QueueEmpty:
        raise HTTPException(
            429,
            "El asistente está ocupado. Intenta nuevamente en unos segundos.",
            headers={"Retry-After": "2"},
        ) from None
    try:
        yield
    finally:
        slots.put_nowait(None)


SettingsDep = Annotated[Settings, Depends(get_settings)]
StoreDep = Annotated[KnowledgeStore, Depends(get_store)]
RegistryDep = Annotated[ToolRegistry, Depends(get_registry)]
AgentDep = Annotated[CompanyAgent, Depends(get_agent)]
DatabaseDep = Annotated[IdentityStore, Depends(get_database)]
BusinessDep = Annotated[BusinessRepository, Depends(get_business)]
# Scopes honour AUTH_ENABLED; the plain dependencies always require a valid JWT.
ScopedUser = Annotated[User | None, Depends(user_scope)]
ScopedAdmin = Annotated[User | None, Depends(admin_scope)]
RequiredUser = Annotated[User, Depends(require_user)]
RequiredAdmin = Annotated[User, Depends(require_admin)]
ChatAdmission = Annotated[None, Depends(chat_admission, scope="request")]
