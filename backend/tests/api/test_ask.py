from types import SimpleNamespace
from typing import Any

import anthropic
import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.settings import Settings
from app.knowledge.ingestion import ParsedDocument
from app.main import create_app

FACT = "Softop ofrece el plan Pro por 49 USD al mes con soporte 24/7."


def seeded(settings: Settings) -> TestClient:
    client = TestClient(create_app(settings))
    client.__enter__()
    client.app.state.store.add_documents([ParsedDocument("precios.md", FACT)])  # type: ignore[attr-defined]
    return client


def test_ask_demo_returns_context_with_sources(settings: Settings) -> None:
    client = seeded(settings)
    try:
        body = client.post("/api/ask", json={"question": "precio plan Pro"}).json()
        assert body["model"] == "demo" and "49 USD" in body["answer"]
        assert body["sources"][0]["document_name"] == "precios.md"
    finally:
        client.__exit__(None, None, None)


def test_ask_without_context_admits_missing_information(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        body = client.post("/api/ask", json={"question": "precio"}).json()
    assert body == {"answer": "No encontré esa información.", "sources": [], "model": "none"}


class FakeAnthropic:
    calls: list[dict[str, Any]] = []
    error: Exception | None = None

    def __init__(self, **_kwargs: Any) -> None:
        self.messages = self

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        FakeAnthropic.calls.append(kwargs)
        if FakeAnthropic.error is not None:
            raise FakeAnthropic.error
        text = SimpleNamespace(type="text", text="El plan Pro cuesta 49 USD al mes [S1].")
        return SimpleNamespace(content=[text], model="claude-haiku-4-5")

    async def close(self) -> None:
        return None


@pytest.fixture
def live(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Settings:
    FakeAnthropic.calls, FakeAnthropic.error = [], None
    monkeypatch.setattr("app.agent.rag.anthropic.AsyncAnthropic", FakeAnthropic)
    return settings.model_copy(
        update={"llm_mode": "anthropic", "anthropic_api_key": SecretStr("test-key")}
    )


def test_ask_sends_numbered_context_to_the_model(live: Settings) -> None:
    client = seeded(live)
    try:
        body = client.post("/api/ask", json={"question": "¿Cuánto cuesta el plan Pro?"}).json()
    finally:
        client.__exit__(None, None, None)
    assert body["answer"].endswith("[S1].") and body["model"] == "claude-haiku-4-5"
    prompt = FakeAnthropic.calls[0]["messages"][0]["content"]
    assert "[S1] " + FACT in prompt and "¿Cuánto cuesta el plan Pro?" in prompt


def test_ask_maps_provider_errors_to_503(live: Settings) -> None:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    FakeAnthropic.error = anthropic.APIConnectionError(request=request)
    client = seeded(live)
    try:
        response = client.post("/api/ask", json={"question": "plan Pro"})
    finally:
        client.__exit__(None, None, None)
    assert response.status_code == 503 and response.json()["code"] == "provider_unavailable"
