from base64 import b64encode
from collections.abc import Iterator
from typing import Any, Literal

import anthropic
import httpx
import pytest
from anthropic.types import Message, MessageParam, ToolParam
from pydantic import SecretStr

from app.agent import AgentFailure, CompanyAgent, TextCallback, grounded_sources
from app.auth import CURRENT_USER_ID
from app.business import BusinessStore
from app.ingestion import ParsedDocument
from app.models import ChatRequest, Source, ToolTrace
from app.settings import Settings
from app.storage import KnowledgeStore
from app.tools import ToolRegistry


def message(
    content: list[dict[str, Any]], stop: Literal["end_turn", "tool_use"] = "end_turn"
) -> Message:
    return Message.model_validate(
        {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": "claude-haiku-4-5",
            "content": content,
            "stop_reason": stop,
            "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
    )


class ScriptedProvider:
    def __init__(self, responses: list[Message | Exception]) -> None:
        self.responses: Iterator[Message | Exception] = iter(responses)
        self.messages: list[list[MessageParam]] = []

    async def complete(
        self,
        messages: list[MessageParam],
        tools: list[ToolParam],
        system: str,
        on_text: TextCallback | None,
    ) -> Message:
        self.messages.append(list(messages))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        if on_text:
            for block in response.content:
                if block.type == "text":
                    await on_text(block.text)
        return response


def anthropic_settings(settings: Settings, **kwargs: Any) -> Settings:
    return settings.model_copy(
        update={
            "llm_mode": "anthropic",
            "anthropic_api_key": SecretStr("test-placeholder"),
            **kwargs,
        }
    )


async def test_tool_loop_batches_results_and_grounded_sources(
    settings: Settings,
    store: KnowledgeStore,
) -> None:
    store.add_documents([ParsedDocument("rates.md", "Starter 29 euros mensuales")])
    provider = ScriptedProvider(
        [
            message(
                [
                    {
                        "type": "tool_use",
                        "id": "call_search",
                        "name": "search_knowledge",
                        "input": {"query": "Starter"},
                    },
                    {
                        "type": "tool_use",
                        "id": "call_math",
                        "name": "calculate",
                        "input": {"expression": "29*12"},
                    },
                ],
                "tool_use",
            ),
            message([{"type": "text", "text": "Starter cuesta 29 euros [S1]. Anual: 348 euros."}]),
        ]
    )
    registry = ToolRegistry(settings, store)
    config = anthropic_settings(settings)
    agent = CompanyAgent(config, registry, provider)
    events: list[str] = []

    async def emit(event: str, _payload: dict[str, Any]) -> None:
        events.append(event)

    try:
        response = await agent.answer(ChatRequest(message="Precio anual Starter"), emit)
        assert [trace.tool for trace in response.trace] == ["search_knowledge", "calculate"]
        assert len(response.sources) == 1 and response.sources[0].document_name == "rates.md"
        assert response.usage.input_tokens == 20 and response.usage.output_tokens == 10
        assert events.count("tool") == 2 and "token" in events
        final_messages = provider.messages[1]
        assert final_messages[-2]["role"] == "assistant"
        outputs = final_messages[-1]["content"]
        assert isinstance(outputs, list) and len(outputs) == 2
        assert outputs[0]["tool_use_id"] == "call_search"
        assert "[S1]" in str(outputs[0])
    finally:
        await registry.close()


async def test_budgets_enforced(settings: Settings, store: KnowledgeStore) -> None:
    call = message(
        [{"type": "tool_use", "id": "tool", "name": "calculate", "input": {"expression": "1+1"}}],
        "tool_use",
    )
    registry = ToolRegistry(settings, store)
    try:
        config = anthropic_settings(settings, max_agent_iterations=2, max_tool_calls=8)
        provider = ScriptedProvider([call, call, call])
        with pytest.raises(AgentFailure, match="pasos"):
            await CompanyAgent(config, registry, provider).answer(ChatRequest(message="loop"))
        assert len(provider.messages) == 2
        config = anthropic_settings(settings, max_agent_iterations=5, max_tool_calls=1)
        provider = ScriptedProvider([call, call])
        with pytest.raises(AgentFailure, match="herramientas"):
            await CompanyAgent(config, registry, provider).answer(ChatRequest(message="loop"))
        assert len(provider.messages) == 2
    finally:
        await registry.close()


async def test_sdk_error_sanitized(settings: Settings, store: KnowledgeStore) -> None:
    registry = ToolRegistry(settings, store)
    error = anthropic.APIConnectionError(
        message="sensitive-debug-sk-ant-abcdefghijklmnop",
        request=httpx.Request("POST", "https://api.anthropic.com"),
    )
    provider = ScriptedProvider([error])
    try:
        with pytest.raises(AgentFailure) as failure:
            await CompanyAgent(anthropic_settings(settings), registry, provider).answer(
                ChatRequest(message="hello")
            )
        assert failure.value.code == "provider_unavailable"
        assert "sensitive" not in failure.value.message
        assert "sk-ant" not in failure.value.message
    finally:
        await registry.close()


def test_only_actual_citations_returned() -> None:
    source = Source(document_id="doc", document_name="rate", chunk_id="chunk", text="29", score=0.7)
    answer, citations = grounded_sources("Price [S1], unknown [S9], again [S1]", [source])
    assert citations == [source]
    assert "[S9]" not in answer
    assert "fuente no disponible" in answer


def test_sparse_reversed_and_duplicate_citations_renumbered() -> None:
    sources = [
        Source(
            document_id=str(index),
            document_name=f"doc{index}",
            chunk_id=str(index),
            text=f"fact{index}",
            score=0.8,
        )
        for index in range(3)
    ]
    answer, cited = grounded_sources("Third [S3] then second [S2], third again [S3]", sources)
    assert answer == "Third [S1] then second [S2], third again [S1]"
    assert cited == [sources[2], sources[1]]
    answer, cited = grounded_sources("Only second [S2]", sources)
    assert answer == "Only second [S1]" and cited == [sources[1]]


async def test_demo_explicit_no_provider(settings: Settings, store: KnowledgeStore) -> None:
    store.add_documents([ParsedDocument("rates.txt", "Starter cuesta 29 euros")])
    registry = ToolRegistry(settings, store)
    provider = ScriptedProvider([])
    try:
        response = await CompanyAgent(settings, registry, provider).answer(
            ChatRequest(message="Starter")
        )
        assert response.mode == "demo" and "extractiva" in response.answer
        assert response.usage.input_tokens == 0 and provider.messages == []
        assert response.trace[0].tool == "search_knowledge"
    finally:
        await registry.close()


@pytest.mark.parametrize(
    "query", ["¿Quién es el CEO de Forma?", "Facturación anual de Forma", "Ingresos de Forma"]
)
async def test_demo_missing_facts_refuse(
    settings: Settings,
    store: KnowledgeStore,
    query: str,
) -> None:
    from app.sample_data import DEMO_DOCUMENTS

    store.seed(DEMO_DOCUMENTS)
    registry = ToolRegistry(settings, store)
    try:
        response = await CompanyAgent(settings, registry).answer(ChatRequest(message=query))
        assert response.sources == [] and "no encontré" in response.answer
    finally:
        await registry.close()


async def test_demo_percentage_uses_calculator(settings: Settings, store: KnowledgeStore) -> None:
    registry = ToolRegistry(settings, store)
    try:
        response = await CompanyAgent(settings, registry).answer(
            ChatRequest(message="Calcula el 21% de IVA sobre 4.500 euros")
        )
        assert "945" in response.answer and response.trace[0].tool == "calculate"
    finally:
        await registry.close()


async def test_ungrounded_provider_claim_not_emitted(
    settings: Settings, store: KnowledgeStore
) -> None:
    provider = ScriptedProvider(
        [
            message(
                [
                    {
                        "type": "text",
                        "text": "El CEO es Inventado. sk-ant-abcdefghijklmnopqrstuvwxyz [S99]",
                    }
                ]
            )
        ]
    )
    registry = ToolRegistry(settings, store)
    events: list[dict[str, Any]] = []

    async def emit(_event: str, payload: dict[str, Any]) -> None:
        events.append(payload)

    try:
        response = await CompanyAgent(anthropic_settings(settings), registry, provider).answer(
            ChatRequest(message="CEO de Forma"), emit
        )
        assert "evidencia suficiente" in response.answer
        assert "Inventado" not in str(events) and "sk-ant" not in str(events)
    finally:
        await registry.close()


@pytest.mark.parametrize(
    "query,expected",
    [
        ("¿Quién es el CEO de Forma?", "evidencia suficiente"),
        ("Calcula 1+1", "1+1 = 2"),
    ],
)
async def test_calculation_never_authorizes_extra_company_claims(
    settings: Settings, store: KnowledgeStore, query: str, expected: str
) -> None:
    provider = ScriptedProvider(
        [
            message(
                [
                    {
                        "type": "tool_use",
                        "id": "math",
                        "name": "calculate",
                        "input": {"expression": "1+1"},
                    }
                ],
                "tool_use",
            ),
            message([{"type": "text", "text": "2. No hay problemas: el CEO es Inventado."}]),
        ]
    )
    registry = ToolRegistry(settings, store)
    emitted: list[dict[str, Any]] = []

    async def emit(_event: str, payload: dict[str, Any]) -> None:
        emitted.append(payload)

    try:
        response = await CompanyAgent(anthropic_settings(settings), registry, provider).answer(
            ChatRequest(message=query), emit
        )
        assert expected in response.answer and response.sources == []
        assert "Inventado" not in response.answer and "Inventado" not in str(emitted)
        assert response.trace[0].status == "completed" and response.trace[0].output == "2"
    finally:
        await registry.close()


@pytest.mark.parametrize("query", ["Hola", "CEO de Forma"])
async def test_greeting_and_refusal_prefix_do_not_authorize_unsupported_prose(
    settings: Settings, store: KnowledgeStore, query: str
) -> None:
    provider = ScriptedProvider(
        [message([{"type": "text", "text": "No hay problemas, CEO Inventado."}])]
    )
    registry = ToolRegistry(settings, store)
    try:
        response = await CompanyAgent(anthropic_settings(settings), registry, provider).answer(
            ChatRequest(message=query)
        )
        assert "Inventado" not in response.answer
        assert (
            "Hola" in response.answer
            if query == "Hola"
            else "evidencia suficiente" in response.answer
        )
    finally:
        await registry.close()


async def test_no_source_action_proposal_uses_actual_pending_state(
    settings: Settings, store: KnowledgeStore
) -> None:
    business = BusinessStore(settings.data_dir)
    registry = ToolRegistry(settings, store, business)
    provider = ScriptedProvider(
        [
            message(
                [
                    {
                        "type": "tool_use",
                        "id": "support",
                        "name": "create_support_ticket",
                        "input": {"subject": "Acceso", "description": "Ayuda con acceso"},
                    }
                ],
                "tool_use",
            ),
            message([{"type": "text", "text": "Ticket ya guardado y correo enviado."}]),
        ]
    )
    context = CURRENT_USER_ID.set("synthetic-owner")
    try:
        response = await CompanyAgent(anthropic_settings(settings), registry, provider).answer(
            ChatRequest(message="Necesito soporte")
        )
        assert "pendiente de tu confirmación" in response.answer
        assert "correo enviado" not in response.answer
        assert business.list_requests("synthetic-owner") == []
    finally:
        CURRENT_USER_ID.reset(context)
        await registry.close()
        business.close()


async def test_mcp_identity_no_source_answer_uses_actual_configured_result(
    settings: Settings, store: KnowledgeStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = ToolRegistry(settings.model_copy(update={"mcp_enabled": True}), store)

    async def identity() -> str:
        return '{"company_name":"Empresa Sintética","company_description":"Descripción aprobada"}'

    monkeypatch.setattr(registry, "_mcp_company_info", identity)
    provider = ScriptedProvider(
        [
            message(
                [{"type": "tool_use", "id": "mcp", "name": "mcp_company_info", "input": {}}],
                "tool_use",
            ),
            message([{"type": "text", "text": "CEO Inventado, soy Otra Empresa"}]),
        ]
    )
    try:
        response = await CompanyAgent(anthropic_settings(settings), registry, provider).answer(
            ChatRequest(message="¿Quién eres?")
        )
        assert "Empresa Sintética" in response.answer and "Descripción aprobada" in response.answer
        assert "Inventado" not in response.answer and "Otra Empresa" not in response.answer
    finally:
        await registry.close()


async def test_retrieved_authorization_is_redacted_before_model_and_public_sources(
    settings: Settings, store: KnowledgeStore
) -> None:
    secret = b64encode(b"synthetic:only").decode("ascii")
    document = store.add_documents(
        [ParsedDocument("legacy.md", "Servicio documentado.\nProxy-Authorization: Basic " + secret)]
    )[0]
    provider = ScriptedProvider(
        [
            message(
                [
                    {
                        "type": "tool_use",
                        "id": "search",
                        "name": "search_knowledge",
                        "input": {"query": "Servicio"},
                    }
                ],
                "tool_use",
            ),
            message([{"type": "text", "text": "Servicio documentado [S1]."}]),
        ]
    )
    registry = ToolRegistry(settings, store)
    try:
        response = await CompanyAgent(anthropic_settings(settings), registry, provider).answer(
            ChatRequest(message="Servicio")
        )
        assert response.sources and secret not in response.model_dump_json()
        assert secret not in str(provider.messages)
        private = store.get_document(document.id)
        assert private is not None and secret in private.content
    finally:
        await registry.close()


# Regressions for adaptation: clarifications, grouped citations and new tools.
def source(chunk: str) -> Source:
    return Source(document_id="d", document_name="doc.md", chunk_id=chunk, text="texto", score=1.0)


def test_grouped_citations_are_normalized() -> None:
    answer, cited = grounded_sources("Dato [S1, S2] y [S2;S1].", [source("a"), source("b")])
    assert answer == "Dato [S1][S2] y [S2][S1]."
    assert [item.chunk_id for item in cited] == ["a", "b"]


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Quiero solicitar una demo", "nombre, correo, empresa, interés y necesidades"),
        ("Necesito soporte, no puedo entrar", "asunto y descripción del problema"),
    ],
)
async def test_request_clarification_is_not_replaced_by_missing_evidence(
    settings: Settings, store: KnowledgeStore, question: str, expected: str
) -> None:
    registry = ToolRegistry(settings, store, BusinessStore(settings.data_dir))
    provider = ScriptedProvider([message([{"type": "text", "text": "¿Me das tus datos?"}])])
    try:
        response = await CompanyAgent(anthropic_settings(settings), registry, provider).answer(
            ChatRequest(message=question)
        )
        assert expected in response.answer
        assert "evidencia suficiente" not in response.answer
    finally:
        await registry.close()


async def test_new_tool_output_is_rendered_without_agent_changes(
    settings: Settings, store: KnowledgeStore
) -> None:
    registry = ToolRegistry(settings, store)
    agent = CompanyAgent(anthropic_settings(settings), registry, ScriptedProvider([]))
    trace = ToolTrace(
        id="t",
        tool="order_status",
        input={"order": "A-1"},
        output='{"status": "enviado"}',
        status="completed",
        duration_ms=1,
    )
    try:
        rendered = agent._without_sources(ChatRequest(message="estado A-1"), [trace])
        assert "Resultado de order_status" in rendered and '"status": "enviado"' in rendered
    finally:
        await registry.close()


async def test_model_configuration_errors_are_reported_as_configuration(
    settings: Settings, store: KnowledgeStore
) -> None:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    error = anthropic.NotFoundError(
        "model not found", response=httpx.Response(404, request=request), body=None
    )
    registry = ToolRegistry(settings, store)
    try:
        with pytest.raises(AgentFailure) as failure:
            await CompanyAgent(
                anthropic_settings(settings), registry, ScriptedProvider([error])
            ).answer(ChatRequest(message="hola"))
        assert failure.value.code == "provider_configuration"
    finally:
        await registry.close()
