import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.agent import CompanyAgent, Emit
from app.main import chat_events, create_app
from app.models import ChatRequest, ChatResponse
from app.settings import Settings
from app.storage import KnowledgeStore
from app.tools import ToolRegistry


def test_api_upload_chat_delete_and_stream(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/health").json()["mode"] == "demo"
        config = client.get("/api/config").json()
        assert config["company_name"] == "Forma" and "api_key" not in str(config)
        uploaded = client.post(
            "/api/documents", files={"file": ("support.md", b"Soporte lunes viernes 9 a 18")}
        )
        assert uploaded.status_code == 200
        identifier = uploaded.json()["documents"][0]["id"]
        assert client.get("/api/documents").json()["total_chunks"] == 1
        assert client.get("/api/search", params={"query": "Soporte"}).json()["sources"]
        response = client.post("/api/chat", json={"message": "Soporte"}).json()
        assert response["sources"][0]["document_id"] == identifier
        assert "demostración" in response["answer"]
        streamed = client.post("/api/chat/stream", json={"message": "Soporte"})
        assert streamed.headers["content-type"].startswith("text/event-stream")
        frames = [frame.splitlines() for frame in streamed.text.strip().split("\n\n")]
        events = [(lines[0][7:], json.loads(lines[1][6:])) for lines in frames]
        assert events[0][0] == "status" and events[-1][0] == "done"
        assert any(event == "tool" for event, _ in events)
        tokens = "".join(data["text"] for event, data in events if event == "token")
        assert tokens == events[-1][1]["answer"]
        assert client.delete(f"/api/documents/{identifier}").status_code == 204
        assert client.delete(f"/api/documents/{identifier}").status_code == 404


def test_validation_upload_size_and_cors(settings: Settings) -> None:
    settings = settings.model_copy(update={"max_upload_mb": 1})
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/chat", json={"message": ""}).status_code == 422
        response = client.post(
            "/api/documents", files={"file": ("big.txt", b"a" * (1024 * 1024 + 1))}
        )
        assert response.status_code == 413
        response = client.options(
            "/api/chat",
            headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
        )
        assert "access-control-allow-origin" not in response.headers
        trace = client.post(
            "/api/tools/run", json={"name": "calculate", "input": {"expression": "29*12"}}
        ).json()
        assert trace["output"] == "348" and trace["status"] == "completed"
        history = [{"role": "user", "content": "x" * 20000}] * 2
        invalid = client.post("/api/chat", json={"message": "hello", "history": history})
        assert invalid.status_code == 422


@pytest.mark.parametrize("auth_enabled", [True, False])
def test_health_declares_customer_capability_without_account_data(
    settings: Settings, auth_enabled: bool
) -> None:
    with TestClient(
        create_app(settings.model_copy(update={"auth_enabled": auth_enabled}))
    ) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["features"] == {"customer_management": True}
        assert set(body) == {"status", "mode", "model", "embedding", "tools", "features"}


def test_swagger_works_under_api_proxy_and_declares_jwt(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        docs = client.get("/api/docs")
        assert docs.status_code == 200 and "/api/openapi.json" in docs.text
        assert "/api/docs/oauth2-redirect" in docs.text
        assert client.get("/api/redoc").status_code == 200
        schema = client.get("/api/openapi.json").json()
        assert schema["components"]["securitySchemes"]["JWT"]["scheme"] == "bearer"
        assert {"JWT": []} in schema["paths"]["/api/chat"]["post"]["security"]
        assert "/docs" not in schema["paths"]
        for legacy, destination in (("/docs", "/api/docs"), ("/redoc", "/api/redoc")):
            redirect = client.get(legacy, follow_redirects=False)
            assert redirect.status_code == 307 and redirect.headers["location"] == destination


def test_cors_allows_only_configured_authenticated_frontend(settings: Settings) -> None:
    origin = "http://localhost:5173"
    with TestClient(create_app(settings.model_copy(update={"cors_origins": [origin]}))) as client:
        for method, headers in (
            ("PUT", "authorization,content-type"),
            ("POST", "x-requested-with,content-type"),
        ):
            response = client.options(
                "/api/chat",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": method,
                    "Access-Control-Request-Headers": headers,
                },
            )
            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == origin
            assert response.headers["access-control-allow-credentials"] == "true"
        rejected = client.options(
            "/api/chat",
            headers={
                "Origin": "https://other.example.invalid",
                "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        assert rejected.status_code == 400
        assert "access-control-allow-origin" not in rejected.headers


def test_json_body_bounded_before_parsing_with_or_without_declared_length(
    settings: Settings,
) -> None:
    with TestClient(create_app(settings)) as client:
        oversized = b'{"message":"' + b"x" * (512 * 1024) + b'"}'
        for body in (oversized, iter([oversized[:200000], oversized[200000:]])):
            response = client.post(
                "/api/chat", content=body, headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 413
            assert len(response.content) < 200
        # Reject unreasonable declared sizes without attempting a huge integer conversion.
        response = client.post(
            "/api/chat",
            content=b"{}",
            headers={"Content-Type": "application/json", "Content-Length": "9" * 5000},
        )
        assert response.status_code == 413


def test_maximum_unicode_chat_history_still_fits_body_limit(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        payload = {
            "message": "\U0001f600" * 10000,
            "history": [
                {"role": "user", "content": "\U0001f600" * 16000},
                {"role": "assistant", "content": "\U0001f600" * 16000},
            ],
        }
        for ascii_escaped in (True, False):
            response = client.post(
                "/api/chat",
                content=json.dumps(payload, ensure_ascii=ascii_escaped).encode(),
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 200


async def test_stream_disconnect_full_queue_no_hang(
    settings: Settings,
    store: KnowledgeStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = ToolRegistry(settings, store)
    agent = CompanyAgent(settings, registry)
    blocked, stopped = asyncio.Event(), asyncio.Event()

    async def flood(_request: ChatRequest, emit: Emit) -> ChatResponse:
        try:
            for index in range(500):
                if index == 129:
                    blocked.set()
                await emit("token", {"text": "flood"})
        finally:
            stopped.set()
        raise AssertionError("Flood should be cancelled")

    monkeypatch.setattr(agent, "answer", flood)
    events = chat_events(agent, ChatRequest(message="hello"))
    try:
        assert "token" in await anext(events)
        await asyncio.wait_for(blocked.wait(), timeout=1)
        await asyncio.wait_for(events.aclose(), timeout=1)
        assert stopped.is_set()
    finally:
        await registry.close()
