from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from base import app as app_module
from base.llm import NO_INFO, SYSTEM_PROMPT, LLMUnavailable, build_prompt
from base.rag import FaqIndex, TfidfEmbedder, load_faqs

FAQS = load_faqs(Path(__file__).parents[1] / "base" / "faq.json")


@pytest.fixture
def index() -> FaqIndex:
    return FaqIndex(FAQS, TfidfEmbedder([faq.texto for faq in FAQS]), min_score=0.1)


class FakeLLM:
    def __init__(self, reply: str = "Ve a Ventas > Devoluciones.", error: Exception | None = None):
        self.reply, self.error, self.calls = reply, error, []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if self.error:
            raise self.error
        return self.reply


@pytest.fixture
def client(index: FaqIndex, monkeypatch: pytest.MonkeyPatch):
    llm = FakeLLM()
    monkeypatch.setattr(app_module, "get_llm", lambda: llm)
    app_module.app.dependency_overrides[app_module.get_index] = lambda: index
    with TestClient(app_module.app) as test_client:
        test_client.llm = llm  # type: ignore[attr-defined]
        yield test_client
    app_module.app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("question", "faq_id"),
    [
        ("¿Cómo hago una devolución?", 8),
        ("cómo cierro la caja al final del día", 10),
        ("quiero agendar una cita con el optómetra", 5),
        ("el inventario no me cuadra", 2),
        ("cómo saco el reporte del mes", 3),
    ],
)
def test_retrieves_the_relevant_faq_first(index: FaqIndex, question: str, faq_id: int) -> None:
    assert index.search(question)[0][0].id == faq_id


def test_unrelated_question_retrieves_nothing(index: FaqIndex) -> None:
    assert index.search("¿Cuál es la capital de Francia?") == []


def test_preguntar_injects_only_retrieved_context(client: TestClient) -> None:
    response = client.post("/preguntar", json={"pregunta": "¿Cómo hago una devolución?"})
    assert response.status_code == 200
    assert response.json() == {"respuesta": "Ve a Ventas > Devoluciones."}
    system, user = client.llm.calls[0]  # type: ignore[attr-defined]
    assert system == SYSTEM_PROMPT and "ÚNICAMENTE" in system
    assert "[FAQ 8]" in user and "Ventas > Devoluciones" in user
    assert "Cierre de caja" not in user  # irrelevant FAQs are not injected


def test_no_context_answers_without_calling_the_model(client: TestClient) -> None:
    response = client.post("/preguntar", json={"pregunta": "¿Cuál es la capital de Francia?"})
    assert response.json() == {"respuesta": NO_INFO}
    assert client.llm.calls == []  # type: ignore[attr-defined]


def test_invalid_payload_is_rejected(client: TestClient) -> None:
    assert client.post("/preguntar", json={"question": "x"}).status_code == 422
    assert client.post("/preguntar", json={"pregunta": ""}).status_code == 422


@pytest.mark.parametrize("error", [LLMUnavailable("Configura una clave."), RuntimeError("boom")])
def test_provider_failure_returns_503(client: TestClient, error: Exception) -> None:
    client.llm.error = error  # type: ignore[attr-defined]
    response = client.post("/preguntar", json={"pregunta": "¿Cómo hago una devolución?"})
    assert response.status_code == 503 and "boom" not in response.text


def test_prompt_lists_each_fragment_with_its_id() -> None:
    prompt = build_prompt("¿Pregunta?", [(FAQS[0], 0.9), (FAQS[2], 0.5)])
    assert prompt.index("[FAQ 1]") < prompt.index("[FAQ 3]") < prompt.index("PREGUNTA DEL USUARIO")
