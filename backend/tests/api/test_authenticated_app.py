import json
import secrets
import uuid
from typing import Any

import anthropic
import httpx
import pytest
from anthropic.types import Message
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.agent.events import Emit, no_emit
from app.api.schemas import ChatRequest, ChatResponse
from app.core.settings import Settings
from app.knowledge.ingestion import ParsedDocument
from app.main import create_app
from app.persistence.sqlite import ApplicationDatabase


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


def test_document_detail_is_admin_only_and_reads_extracted_text(settings: Settings) -> None:
    application = create_app(settings.model_copy(update={"auth_enabled": True}))
    with TestClient(application) as client:
        admin = account(client, "/api/auth/setup", "owner@example.invalid")
        customer = account(client, "/api/auth/register", "customer@example.invalid")
        text = "\n## Synthetic knowledge\n\n" + "Fila con texto público.\n" * 150 + "\n"
        uploaded = client.post(
            "/api/documents", files={"file": ("public.md", text.encode())}, headers=admin
        )
        assert uploaded.status_code == 200
        document = uploaded.json()["documents"][0]
        assert document["chunks"] > 1
        identifier = document["id"]
        path = f"/api/documents/{identifier}"
        assert client.get(path).status_code == 401
        assert client.get(path, headers=customer).status_code == 403
        assert client.get("/api/documents/missing", headers=customer).status_code == 403
        response = client.get(path, headers=admin)
        assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
        assert response.json() == {**document, "content": text.strip(), "reconstructed": False}
        listed = client.get("/api/documents", headers=admin).json()["documents"][0]
        assert "content" not in listed and "reconstructed" not in listed
        assert client.get("/api/documents/missing", headers=admin).status_code == 404
        assert client.delete(path, headers=admin).status_code == 204
        assert client.get(path, headers=admin).status_code == 404


@pytest.mark.parametrize(
    ("mode", "configured", "expected"),
    [("auto", False, "demo"), ("auto", True, "anthropic"), ("demo", True, "demo")],
)
def test_provider_config_is_backend_only_and_legacy_database_does_not_override(
    settings: Settings, mode: str, configured: bool, expected: str
) -> None:
    # A deliberately invalid legacy ciphertext proves startup neither decodes nor uses it.
    legacy = "legacy-ciphertext-placeholder"
    database = ApplicationDatabase(settings.data_dir)
    database._db.execute("INSERT INTO config VALUES ('anthropic_api_key', ?)", (legacy,))
    database.close()
    placeholder = "synthetic-environment-provider-value"
    config = settings.model_copy(
        update={
            "llm_mode": mode,
            "anthropic_api_key": SecretStr(placeholder if configured else ""),
        }
    )

    class NoNetworkProvider:
        async def complete(self, *_args: Any, **_kwargs: Any) -> Message:
            raise AssertionError("This configuration test must not call any provider")

    application = create_app(config, NoNetworkProvider())
    with TestClient(application) as client:
        for path in ("/api/health", "/api/config"):
            result = client.get(path)
            assert result.status_code == 200 and result.json()["mode"] == expected
            assert placeholder not in result.text and legacy not in result.text
        for method, path in (
            ("GET", "/api/settings/provider"),
            ("PUT", "/api/settings/provider"),
            ("POST", "/api/settings/provider/test"),
        ):
            assert client.request(method, path).status_code == 404
        schema = client.get("/api/openapi.json").json()
        assert not any(path.startswith("/api/settings/provider") for path in schema["paths"])
        assert "ProviderConfiguration" not in schema["components"]["schemas"]
        assert (
            application.state.database._db.execute(
                "SELECT value FROM config WHERE key='anthropic_api_key'"
            ).fetchone()[0]
            == legacy
        )


@pytest.mark.parametrize("path", ["/api/chat", "/api/chat/stream"])
def test_provider_failure_is_coded_unsaved_and_never_a_demo_answer(
    settings: Settings, path: str
) -> None:
    class UnavailableProvider:
        async def complete(self, *_args: Any, **_kwargs: Any) -> Message:
            raise anthropic.APIConnectionError(
                message="synthetic-outage-detail",
                request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
            )

    config = settings.model_copy(
        update={
            "auth_enabled": True,
            "llm_mode": "anthropic",
            "anthropic_api_key": SecretStr("synthetic-environment-provider-value"),
        }
    )
    application = create_app(config, UnavailableProvider())
    with TestClient(application) as client:
        account(client, "/api/auth/setup", "owner@example.invalid")
        user = account(client, "/api/auth/register", "client@example.invalid")
        body = {"message": "Hola", "session_id": str(uuid.uuid4())}
        response = client.post(path, json=body, headers=user)
        if path.endswith("stream"):
            assert response.status_code == 200
            assert "event: error" in response.text and "event: done" not in response.text
            line = response.text.split("event: error\ndata: ", 1)[1].split("\n", 1)[0]
            payload = json.loads(line)
        else:
            assert response.status_code == 503
            payload = response.json()
            assert set(payload) == {"detail", "code"}
        assert payload["code"] == "provider_unavailable"
        assert "synthetic-outage-detail" not in response.text
        assert "Modo demostración" not in response.text and '"mode"' not in response.text
        conversations = client.get("/api/conversations", headers=user).json()["conversations"]
        assert all(conversation["messages"] == [] for conversation in conversations)
