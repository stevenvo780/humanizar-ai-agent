import asyncio
import json
import secrets
import threading
import time
from typing import Any

import httpx
import pytest
from starlette.requests import Request
from starlette.types import Message, Scope

import app.api.dependencies as dependencies_module
import app.api.routes.knowledge as knowledge_routes
from app.agent.events import Emit, no_emit
from app.api.schemas import ChatRequest, ChatResponse, Usage
from app.core.settings import Settings
from app.knowledge.ingestion import ParsedDocument
from app.main import create_app
from app.persistence.models import User


def response_for(request: ChatRequest) -> ChatResponse:
    return ChatResponse(
        answer="Synthetic response",
        sources=[],
        trace=[],
        mode="demo",
        model="test",
        usage=Usage(),
        session_id=request.session_id or "test-session",
    )


@pytest.mark.parametrize("first_path", ["/api/chat", "/api/chat/stream"])
async def test_chat_and_sse_share_nonqueued_capacity(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, first_path: str
) -> None:
    application = create_app(settings.model_copy(update={"max_concurrent_chats": 1}))
    entered, released = asyncio.Event(), asyncio.Event()
    calls = 0

    async def delayed(request: ChatRequest, emit: Emit = no_emit) -> ChatResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            entered.set()
            await released.wait()
        return response_for(request)

    async with application.router.lifespan_context(application):
        monkeypatch.setattr(application.state.agent, "answer", delayed)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://testserver"
        ) as client:
            pending = asyncio.create_task(client.post(first_path, json={"message": "first"}))
            try:
                await asyncio.wait_for(entered.wait(), 1)
                for path in ("/api/chat", "/api/chat/stream"):
                    rejected = await client.post(path, json={"message": "overflow"})
                    assert rejected.status_code == 429
                    assert rejected.headers["retry-after"]
                assert calls == 1
            finally:
                released.set()
                assert (await pending).status_code == 200
            assert (await client.post(first_path, json={"message": "next"})).status_code == 200


async def test_cancelled_upload_keeps_parser_slot_until_thread_finishes(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = create_app(settings)
    entered, second_entered, released = threading.Event(), threading.Event(), threading.Event()
    count = 0
    counter_lock = threading.Lock()

    def blocked_parser(
        name: str, _data: bytes, _settings: Settings
    ) -> tuple[list[ParsedDocument], list[str]]:
        nonlocal count
        with counter_lock:
            count += 1
            if count == 1:
                entered.set()
            else:
                second_entered.set()
        assert released.wait(5)
        return [ParsedDocument(name, "Synthetic company document")], []

    monkeypatch.setattr(knowledge_routes, "parse_upload", blocked_parser)
    async with (
        application.router.lifespan_context(application),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://testserver"
        ) as client,
    ):
        first = asyncio.create_task(
            client.post("/api/documents", files={"file": ("first.txt", b"First")})
        )
        second: asyncio.Task[httpx.Response] | None = None
        try:
            assert await asyncio.to_thread(entered.wait, 1)
            first.cancel()
            second = asyncio.create_task(
                client.post("/api/documents", files={"file": ("second.txt", b"Second")})
            )
            assert not await asyncio.to_thread(second_entered.wait, 0.1)
            assert not first.done()
            # Repeated cancellation must not release a still-running parser either.
            first.cancel()
            await asyncio.sleep(0)
            assert not first.done()
        finally:
            released.set()
            with pytest.raises(asyncio.CancelledError):
                await first
            if second is not None:
                assert (await second).status_code == 200
        listed = application.state.store.list_documents()
        assert [document.name for document in listed.documents] == ["second.txt"]


@pytest.mark.parametrize("path", ["/api/chat", "/api/chat/stream"])
async def test_cancelled_chat_keeps_capacity_until_retrieval_thread_finishes(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    application = create_app(settings.model_copy(update={"max_concurrent_chats": 1}))
    entered, released = threading.Event(), threading.Event()
    calls = 0

    def blocked_search(_query: str, _limit: int = 5) -> list[Any]:
        nonlocal calls
        calls += 1
        entered.set()
        assert released.wait(5)
        return []

    async with application.router.lifespan_context(application):
        monkeypatch.setattr(application.state.store, "search", blocked_search)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://testserver"
        ) as client:
            first = asyncio.create_task(client.post(path, json={"message": "first"}))
            try:
                assert await asyncio.to_thread(entered.wait, 1)
                first.cancel()
                await asyncio.sleep(0.05)
                for other_path in ("/api/chat", "/api/chat/stream"):
                    assert (
                        await client.post(other_path, json={"message": "overflow"})
                    ).status_code == 429
                assert calls == 1 and not first.done()
            finally:
                released.set()
                with pytest.raises(asyncio.CancelledError):
                    await first
            assert (await client.post(path, json={"message": "next"})).status_code == 200


@pytest.mark.parametrize("path", ["/api/chat", "/api/chat/stream"])
async def test_agent_error_releases_chat_capacity(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    application = create_app(settings.model_copy(update={"max_concurrent_chats": 1}))
    calls = 0

    async def flaky(request: ChatRequest, emit: Emit = no_emit) -> ChatResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("Synthetic failure")
        return response_for(request)

    async with application.router.lifespan_context(application):
        monkeypatch.setattr(application.state.agent, "answer", flaky)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://testserver"
        ) as client:
            first = await client.post(path, json={"message": "first"})
            assert first.status_code == (200 if path.endswith("stream") else 500)
            if path.endswith("stream"):
                assert "event: error" in first.text
            assert "Synthetic failure" not in first.text
            assert (await client.post(path, json={"message": "next"})).status_code == 200


@pytest.mark.parametrize(
    ("dependency", "path"), [("require_user", "/api/tools"), ("require_admin", "/api/documents")]
)
async def test_sqlite_auth_validation_runs_outside_event_loop(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, dependency: str, path: str
) -> None:
    application = create_app(settings.model_copy(update={"auth_enabled": True}))
    observed: list[int] = []
    event_loop_thread = threading.get_ident()

    def observe(_request: Request) -> User:
        observed.append(threading.get_ident())
        return User("test-owner", "Test", "test@example.invalid", "admin", "test-hash")

    monkeypatch.setattr(dependencies_module, dependency, observe)
    async with (
        application.router.lifespan_context(application),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://testserver"
        ) as client,
    ):
        assert (await client.get(path)).status_code == 200
    assert observed and all(thread != event_loop_thread for thread in observed)


async def test_retrieval_does_not_block_health_event_loop(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = create_app(settings)
    entered, released = threading.Event(), threading.Event()

    def blocked_search(_query: str, _limit: int = 5) -> list[Any]:
        entered.set()
        assert released.wait(5)
        return []

    async def no_sandbox() -> bool:
        return False

    async with application.router.lifespan_context(application):
        monkeypatch.setattr(application.state.store, "search", blocked_search)
        monkeypatch.setattr(application.state.registry, "sandbox_available", no_sandbox)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://testserver"
        ) as client:
            pending = asyncio.create_task(client.get("/api/search", params={"query": "search"}))
            try:
                assert await asyncio.to_thread(entered.wait, 1)
                health = await asyncio.wait_for(client.get("/api/health"), 0.5)
                assert health.status_code == 200
            finally:
                released.set()
                assert (await pending).status_code == 200


async def test_sqlite_lock_does_not_delay_async_heartbeat(
    settings: Settings,
) -> None:
    application = create_app(settings.model_copy(update={"auth_enabled": True}))
    entered, released = threading.Event(), threading.Event()

    async with (
        application.router.lifespan_context(application),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://testserver"
        ) as client,
    ):
        signup = await client.post(
            "/api/auth/setup",
            json={
                "name": "Test owner",
                "email": "owner@example.invalid",
                "password": secrets.token_urlsafe(24),
            },
        )
        assert signup.status_code == 200
        headers = {"Authorization": "Bearer " + signup.json()["access_token"]}

        def hold_lock() -> None:
            with application.state.database._lock:
                entered.set()
                assert released.wait(3)

        locked = asyncio.create_task(asyncio.to_thread(hold_lock))
        pending: asyncio.Task[httpx.Response] | None = None
        try:
            assert await asyncio.to_thread(entered.wait, 1)
            pending = asyncio.create_task(client.get("/api/tools", headers=headers))
            start = time.monotonic()
            await asyncio.sleep(0.01)
            assert time.monotonic() - start < 0.2
            assert not pending.done()
        finally:
            released.set()
            await locked
            if pending is not None:
                assert (await pending).status_code == 200


async def test_sse_disconnect_drains_retrieval_before_releasing_capacity(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = create_app(settings.model_copy(update={"max_concurrent_chats": 1}))
    entered, released = threading.Event(), threading.Event()
    disconnected, sent = asyncio.Event(), asyncio.Event()
    payload = json.dumps({"message": "first"}).encode()
    consumed = False

    def blocked_search(_query: str, _limit: int = 5) -> list[Any]:
        entered.set()
        assert released.wait(5)
        return []

    async def receive() -> Message:
        nonlocal consumed
        if not consumed:
            consumed = True
            return {"type": "http.request", "body": payload, "more_body": False}
        await disconnected.wait()
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        if message["type"] == "http.response.body" and message.get("body"):
            sent.set()

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/chat/stream",
        "raw_path": b"/api/chat/stream",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "server": ("testserver", 80),
        "client": ("testclient", 123),
    }
    async with application.router.lifespan_context(application):
        monkeypatch.setattr(application.state.store, "search", blocked_search)
        first = asyncio.create_task(application(scope, receive, send))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://testserver"
        ) as client:
            try:
                await asyncio.wait_for(sent.wait(), 1)
                assert await asyncio.to_thread(entered.wait, 1)
                disconnected.set()
                await asyncio.sleep(0.05)
                overflow = await client.post("/api/chat", json={"message": "overflow"})
                assert overflow.status_code == 429 and not first.done()
            finally:
                released.set()
                disconnected.set()
                await asyncio.wait_for(first, 2)
            assert (await client.post("/api/chat", json={"message": "next"})).status_code == 200
