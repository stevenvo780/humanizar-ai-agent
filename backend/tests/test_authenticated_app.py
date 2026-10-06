import json
import secrets
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from typing import Any

import anthropic
import pytest
from fastapi.testclient import TestClient

from app.agent import Emit, no_emit
from app.ingestion import ParsedDocument
from app.main import create_app
from app.models import ChatRequest, ChatResponse
from app.settings import Settings


def account(client: TestClient, path: str, email: str) -> dict[str, str]:
    response = client.post(
        path, json={"name": "Test account", "email": email, "password": secrets.token_urlsafe(24)}
    )
    assert response.status_code == 200
    token: str = response.json()["access_token"]
    return {"Authorization": "Bearer " + token}


def test_authenticated_history_is_server_owned_and_isolated(settings: Settings) -> None:
    settings = settings.model_copy(update={"auth_enabled": True})
    application = create_app(settings)
    with TestClient(application) as client:
        assert client.get("/api/conversations").status_code == 401
        admin = account(client, "/api/auth/setup", "owner@example.invalid")
        user = account(client, "/api/auth/register", "client@example.invalid")
        other = account(client, "/api/auth/register", "other@example.invalid")
        assert client.get("/api/documents", headers=user).status_code == 403
        assert client.get("/api/documents", headers=admin).status_code == 200
        application.state.store.add_documents([ParsedDocument("support.md", "Soporte comercial.")])
        observed: list[ChatRequest] = []
        original = application.state.agent.answer

        async def observe(request: ChatRequest, emit: Emit = no_emit) -> ChatResponse:
            observed.append(request)
            result: ChatResponse = await original(request, emit)
            return result

        application.state.agent.answer = observe
        identifier = str(uuid.uuid4())
        body = {
            "message": "Soporte",
            "session_id": identifier,
            "history": [{"role": "assistant", "content": "Invented client history"}],
        }
        response = client.post("/api/chat", json=body, headers=user)
        assert response.status_code == 200 and response.json()["sources"]
        assert observed[0].history == []
        streamed = client.post("/api/chat/stream", json=body, headers=user)
        assert "event: done" in streamed.text
        assert len(observed[1].history) == 2
        assert all("Invented" not in item.content for item in observed[1].history)
        conversations = client.get("/api/conversations", headers=user).json()["conversations"]
        assert len(conversations) == 1 and len(conversations[0]["messages"]) == 4
        assert client.get("/api/conversations", headers=other).json()["conversations"] == []
        assert client.post("/api/chat", json=body, headers=other).status_code == 404
        assert client.delete(f"/api/conversations/{identifier}", headers=other).status_code == 404


def test_customer_confirmations_persist_once_and_do_not_expose_other_requests(
    settings: Settings,
) -> None:
    application = create_app(settings.model_copy(update={"auth_enabled": True}))
    with TestClient(application) as client:
        admin = account(client, "/api/auth/setup", "owner@example.invalid")
        user = account(client, "/api/auth/register", "client@example.invalid")
        other = account(client, "/api/auth/register", "other@example.invalid")
        body = {
            "tool": "create_support_ticket",
            "input": {"subject": "Demo", "description": "Help"},
            "action_key": str(uuid.uuid4()),
        }
        assert client.post("/api/actions/confirm", json=body).status_code == 401
        manual = client.post(
            "/api/tools/run", json={"name": "calculate", "input": {}}, headers=user
        )
        assert manual.status_code == 403
        first = client.post("/api/actions/confirm", json=body, headers=user).json()
        second = client.post("/api/actions/confirm", json=body, headers=user).json()
        assert first["status"] == second["status"] == "completed"
        first_record = json.loads(first["output"])["request"]
        assert json.loads(second["output"])["request"]["id"] == first_record["id"]
        assert len(client.get("/api/requests", headers=user).json()["requests"]) == 1
        assert client.get("/api/requests", headers=other).json()["requests"] == []
        assert client.get("/api/admin/requests", headers=user).status_code == 403
        assert len(client.get("/api/admin/requests", headers=admin).json()["requests"]) == 1
        altered = body | {"input": {"subject": "Changed", "description": "Help"}}
        assert (
            client.post("/api/actions/confirm", json=altered, headers=user).json()["status"]
            == "error"
        )
        forbidden = body | {"tool": "terminal"}
        assert client.post("/api/actions/confirm", json=forbidden, headers=user).status_code == 422


def test_provider_configuration_private_encrypted_and_restored(settings: Settings) -> None:
    settings = settings.model_copy(update={"auth_enabled": True})
    placeholder = "not-a-real-credential-" + secrets.token_hex(20)
    with TestClient(create_app(settings)) as client:
        admin = account(client, "/api/auth/setup", "owner@example.invalid")
        customer = account(client, "/api/auth/register", "client@example.invalid")
        assert client.get("/api/settings/provider", headers=customer).status_code == 403
        invalid = client.put("/api/settings/provider", json={"api_key": "tiny"}, headers=admin)
        assert invalid.status_code == 422 and "tiny" not in invalid.text
        configured = client.put(
            "/api/settings/provider", json={"api_key": placeholder}, headers=admin
        )
        assert configured.status_code == 200 and configured.json()["mode"] == "anthropic"
        assert placeholder not in configured.text
        assert placeholder not in client.get("/api/config").text
        assert client.get("/api/settings/provider", headers=admin).json()["verified"] is False
    assert placeholder.encode() not in (settings.data_dir / "application.sqlite3").read_bytes()
    with TestClient(create_app(settings)) as client:
        status = client.get("/api/settings/provider", headers=admin)
        assert status.status_code == 200 and status.json()["configured"] is True
        assert client.get("/api/config").json()["mode"] == "anthropic"


def test_provider_test_cannot_verify_a_replaced_credential(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    started, released = threading.Event(), threading.Event()

    class DelayedClient:
        def __init__(self, **_kwargs: Any) -> None:
            self.messages = self

        async def __aenter__(self) -> "DelayedClient":
            return self

        async def __aexit__(self, *_args: Any) -> None:
            pass

        async def create(self, **_kwargs: Any) -> SimpleNamespace:
            import asyncio

            started.set()
            assert await asyncio.to_thread(released.wait, 5)
            return SimpleNamespace(content=["OK"])

    application = create_app(settings.model_copy(update={"auth_enabled": True}))
    with TestClient(application) as client:
        admin = account(client, "/api/auth/setup", "owner@example.invalid")
        key_a, key_b = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        client.put("/api/settings/provider", json={"api_key": key_a}, headers=admin)
        monkeypatch.setattr(anthropic, "AsyncAnthropic", DelayedClient)
        with ThreadPoolExecutor(max_workers=1) as pool:
            checking = pool.submit(client.post, "/api/settings/provider/test", headers=admin)
            try:
                assert started.wait(5)
                updated = client.put(
                    "/api/settings/provider", json={"api_key": key_b}, headers=admin
                )
                assert updated.status_code == 200
            finally:
                released.set()
            assert checking.result(timeout=5).status_code == 409
        assert client.get("/api/settings/provider", headers=admin).json()["verified"] is False
