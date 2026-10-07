"""Chat over JSON and SSE: admission, per-conversation locking and server-side history."""

import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import suppress
from typing import Any
from weakref import WeakValueDictionary

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from starlette.requests import Request

from app.agent.company_agent import CompanyAgent
from app.agent.provider import AgentFailure
from app.api.dependencies import AgentDep, ChatAdmission, DatabaseDep, ScopedUser
from app.api.schemas import ChatRequest, ChatResponse, HistoryMessage
from app.core.concurrency import run_sync
from app.persistence.contracts import IdentityStore
from app.persistence.models import User

router = APIRouter(prefix="/api", tags=["chat"])
HISTORY_MESSAGES = 40
HISTORY_CHARACTERS = 32000


async def chat_events(
    agent: CompanyAgent,
    request: ChatRequest,
    on_complete: Callable[[ChatResponse], Awaitable[None]] | None = None,
) -> AsyncGenerator[str, None]:
    """Serialize agent status/tool/token/done/error events as Server-Sent Events."""
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


async def open_conversation(
    request: ChatRequest, user: User | None, database: IdentityStore
) -> ChatRequest:
    if user is None:
        return request
    try:
        identifier = await run_sync(
            database.create_conversation, user.id, request.session_id, request.message[:90]
        )
    except PermissionError as exc:
        raise HTTPException(404, "Conversación no encontrada.") from exc
    return request.model_copy(update={"session_id": identifier})


async def with_server_history(
    request: ChatRequest, user: User | None, database: IdentityStore
) -> ChatRequest:
    """Replace client-supplied history with the owner's bounded server history."""
    if user is None or request.session_id is None:
        return request
    records = await run_sync(database.conversation_history, user.id, request.session_id)
    bounded: list[HistoryMessage] = []
    characters = 0
    for record in reversed(records[-HISTORY_MESSAGES:]):
        message = HistoryMessage.model_validate(record)
        if characters + len(message.content) > HISTORY_CHARACTERS:
            break
        characters += len(message.content)
        bounded.append(message)
    history = list(reversed(bounded))
    # Trimming can leave an assistant turn first; providers expect a user turn first.
    while history and history[0].role != "user":
        history.pop(0)
    return request.model_copy(update={"history": history})


def conversation_lock(http: Request, request: ChatRequest, user: User | None) -> asyncio.Lock:
    locks: WeakValueDictionary[str, asyncio.Lock] = http.app.state.conversation_locks
    key = f"{user.id if user else 'anonymous'}:{request.session_id or id(request)}"
    lock = locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        locks[key] = lock
    return lock


async def save_exchange(
    user: User | None, request: ChatRequest, result: ChatResponse, database: IdentityStore
) -> None:
    if user is not None and request.session_id is not None:
        await run_sync(
            database.save_exchange,
            user.id,
            request.session_id,
            request.message,
            result.model_dump(),
        )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    http: Request,
    request: ChatRequest,
    user: ScopedUser,
    _admission: ChatAdmission,
    agent: AgentDep,
    database: DatabaseDep,
) -> ChatResponse:
    request = await open_conversation(request, user, database)
    async with conversation_lock(http, request, user):
        request = await with_server_history(request, user, database)
        result = await agent.answer(request)
        await save_exchange(user, request, result, database)
        return result


@router.post("/chat/stream")
async def stream_chat(
    http: Request,
    request: ChatRequest,
    user: ScopedUser,
    _admission: ChatAdmission,
    agent: AgentDep,
    database: DatabaseDep,
) -> StreamingResponse:
    request = await open_conversation(request, user, database)

    async def events() -> AsyncGenerator[str, None]:
        async with conversation_lock(http, request, user):
            prepared = await with_server_history(request, user, database)

            async def persist(result: ChatResponse) -> None:
                await save_exchange(user, prepared, result, database)

            async for event in chat_events(agent, prepared, persist):
                yield event

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
