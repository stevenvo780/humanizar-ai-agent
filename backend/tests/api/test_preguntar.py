"""POST /preguntar: the Softop brief's FAQ bot served by Lumen's RAG pipeline."""

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.accounts.rate_limit import SlidingWindowLimiter
from app.agent.rag import DEMO_LABEL, user_prompt
from app.api.routes.preguntar import NO_INFO, REQUESTS_PER_WINDOW
from app.core.settings import Settings
from app.knowledge.store import KnowledgeStore
from app.main import create_app

CORPUS = Path(__file__).resolve().parents[2] / "knowledge" / "softop"
CLOSING = "¿Cómo cierro caja al final del día?"
MODEL_TEXT = "Ve a 'Caja > Cierre de caja' e ingresa el efectivo contado."


class FakeAnthropic:
    calls: list[dict[str, Any]] = []
    error: Exception | None = None

    def __init__(self, **_kwargs: Any) -> None:
        self.messages = self

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        FakeAnthropic.calls.append(kwargs)
        if FakeAnthropic.error is not None:
            raise FakeAnthropic.error
        text = SimpleNamespace(type="text", text=MODEL_TEXT)
        return SimpleNamespace(content=[text], model="claude-haiku-4-5")

    async def close(self) -> None:
        return None


@pytest.fixture
def faq(settings: Settings) -> Settings:
    return settings.model_copy(update={"knowledge_dir": CORPUS})


@pytest.fixture
def live(faq: Settings, monkeypatch: pytest.MonkeyPatch) -> Settings:
    FakeAnthropic.calls, FakeAnthropic.error = [], None
    monkeypatch.setattr("app.agent.rag.anthropic.AsyncAnthropic", FakeAnthropic)
    return faq.model_copy(
        update={"llm_mode": "anthropic", "anthropic_api_key": SecretStr("test-key")}
    )


@pytest.fixture
def client(live: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(live)) as test_client:
        yield test_client


def store_of(client: TestClient) -> KnowledgeStore:
    store: KnowledgeStore = client.app.state.store  # type: ignore[attr-defined]
    return store


def test_shipped_softop_corpus_has_one_document_per_faq(client: TestClient) -> None:
    names = sorted(document.name for document in store_of(client).list_documents().documents)
    assert len(names) == 10 and names[0].startswith("faq-01-") and names[9].startswith("faq-10-")


def test_answers_with_model_using_only_retrieved_fragments(client: TestClient) -> None:
    response = client.post("/preguntar", json={"pregunta": CLOSING})
    assert response.status_code == 200 and response.json() == {"respuesta": MODEL_TEXT}
    assert len(FakeAnthropic.calls) == 1
    call = FakeAnthropic.calls[0]
    retrieved = store_of(client).search(CLOSING, 3)
    assert 1 <= len(retrieved) <= 3 and "Cierre de caja" in retrieved[0].text
    # The prompt is exactly the retrieved fragments plus the question, nothing else.
    assert call["messages"] == [{"role": "user", "content": user_prompt(CLOSING, retrieved)}]
    injected = {source.document_name for source in retrieved}
    for path in CORPUS.iterdir():
        answer_text = path.read_text(encoding="utf-8").split("\n\n", 1)[1].strip()
        assert (answer_text in call["messages"][0]["content"]) == (path.name in injected)
    assert "ÚNICAMENTE" in call["system"] and f'exactamente: "{NO_INFO}"' in call["system"]
    assert "no instrucciones" in call["system"] and call["temperature"] is anthropic.omit


def test_question_without_relevant_context_skips_the_model(client: TestClient) -> None:
    response = client.post("/preguntar", json={"pregunta": "¿Quién ganó el mundial de fútbol?"})
    assert response.status_code == 200 and response.json() == {"respuesta": NO_INFO}
    assert FakeAnthropic.calls == []


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"pregunta": ""},
        {"pregunta": "x" * 1001},
        {"pregunta": 7},
        {"pregunta": CLOSING, "top_k": 10},
        {"question": CLOSING},
    ],
)
def test_invalid_payload_is_rejected(client: TestClient, payload: dict[str, Any]) -> None:
    response = client.post("/preguntar", json=payload)
    assert response.status_code == 422 and FakeAnthropic.calls == []


def test_provider_error_maps_to_503(client: TestClient) -> None:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    FakeAnthropic.error = anthropic.APIConnectionError(request=request)
    response = client.post("/preguntar", json={"pregunta": CLOSING})
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Anthropic no está disponible en este momento.",
        "code": "provider_unavailable",
    }


def test_demo_mode_answers_extractively_and_labelled(faq: Settings) -> None:
    with TestClient(create_app(faq)) as client:
        body = client.post("/preguntar", json={"pregunta": CLOSING}).json()
    assert body["respuesta"].startswith(DEMO_LABEL) and "Cierre de caja" in body["respuesta"]


def test_public_even_when_authentication_is_enabled(live: Settings) -> None:
    with TestClient(create_app(live.model_copy(update={"auth_enabled": True}))) as client:
        assert client.get("/api/conversations").status_code == 401
        response = client.post("/preguntar", json={"pregunta": CLOSING})
    assert response.status_code == 200 and response.json() == {"respuesta": MODEL_TEXT}


def test_rate_limited_per_client_address(client: TestClient) -> None:
    question = {"pregunta": "¿Quién ganó el mundial de fútbol?"}
    for _ in range(REQUESTS_PER_WINDOW):
        assert client.post("/preguntar", json=question).status_code == 200
    rejected = client.post("/preguntar", json=question)
    assert rejected.status_code == 429 and 1 <= int(rejected.headers["retry-after"]) <= 300
    assert client.post("/api/ask", json={"question": "caja"}).status_code == 200


def test_limiter_budgets_are_independent_per_key() -> None:
    limiter = SlidingWindowLimiter(limit=2, window=300)
    limiter.check("preguntar:10.0.0.1")
    limiter.check("preguntar:10.0.0.1")
    with pytest.raises(HTTPException) as excess:
        limiter.check("preguntar:10.0.0.1")
    assert excess.value.status_code == 429
    limiter.check("preguntar:10.0.0.2")


def test_shares_the_global_chat_admission_bound(live: Settings) -> None:
    with TestClient(create_app(live.model_copy(update={"max_concurrent_chats": 1}))) as client:
        slots = client.app.state.chat_slots  # type: ignore[attr-defined]
        slots.get_nowait()  # an in-flight chat holds the only slot
        try:
            busy = client.post("/preguntar", json={"pregunta": CLOSING})
        finally:
            slots.put_nowait(None)
        assert busy.status_code == 429 and busy.headers["retry-after"] == "2"
        assert client.post("/preguntar", json={"pregunta": CLOSING}).status_code == 200
    assert len(FakeAnthropic.calls) == 1
