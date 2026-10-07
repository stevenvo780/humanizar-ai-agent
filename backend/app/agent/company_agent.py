"""CompanyAgent: demo dispatch and the bounded Anthropic tool loop with grounded answers."""

import asyncio
import uuid
from typing import Any, cast

from anthropic.types import MessageParam, TextBlock, ToolResultBlockParam, ToolUseBlock

from app.accounts.dependencies import CURRENT_USER_ID
from app.agent.demo import demo_answer
from app.agent.events import Emit, no_emit
from app.agent.fallback import without_sources
from app.agent.grounding import annotate_sources, grounded_sources
from app.agent.prompt import system_prompt
from app.agent.provider import (
    AgentFailure,
    AnthropicProvider,
    MessageProvider,
    log_provider_failure,
    provider_failure,
)
from app.api.schemas import ChatRequest, ChatResponse, Source, ToolTrace, Usage
from app.core.security import redact
from app.core.settings import Settings
from app.tools.registry import ToolRegistry


class CompanyAgent:
    def __init__(
        self, settings: Settings, registry: ToolRegistry, provider: MessageProvider | None = None
    ) -> None:
        self.settings, self.registry = settings, registry
        self.provider = provider
        if self.provider is None and settings.mode == "anthropic":
            self.provider = AnthropicProvider(settings)

    async def answer(self, request: ChatRequest, emit: Emit = no_emit) -> ChatResponse:
        await emit("status", {"message": "Consultando el conocimiento de la empresa…"})
        if self.settings.mode == "demo":
            return await demo_answer(self.settings, self.registry, request, emit)
        return await self._anthropic(request, emit)

    async def _anthropic(self, request: ChatRequest, emit: Emit) -> ChatResponse:
        assert self.provider is not None
        messages: list[MessageParam] = [
            {"role": item.role, "content": redact(item.content)} for item in request.history
        ]
        messages.append({"role": "user", "content": redact(request.message)})
        trace: list[ToolTrace] = []
        sources: list[Source] = []
        source_ids: dict[str, int] = {}
        usage = Usage()

        for iteration in range(self.settings.max_agent_iterations):
            await emit("status", {"message": f"Claude · paso {iteration + 1}"})
            try:
                async with asyncio.timeout(self.settings.anthropic_timeout_seconds + 5):
                    response = await self.provider.complete(
                        messages,
                        self.registry.schemas(),
                        system_prompt(self.settings),
                        None,
                    )
            except Exception as exc:
                log_provider_failure(exc)
                raise provider_failure(exc) from exc
            usage.input_tokens += response.usage.input_tokens
            usage.output_tokens += response.usage.output_tokens
            if response.stop_reason == "refusal":
                raise AgentFailure("Claude rechazó responder a esta consulta.", "refusal")
            if response.stop_reason == "max_tokens":
                # A truncated turn may also contain an incomplete tool_use block.
                raise AgentFailure("La respuesta excedió el límite de salida.", "output_limit")
            calls = [block for block in response.content if isinstance(block, ToolUseBlock)]
            if not calls:
                answer = "\n".join(
                    block.text for block in response.content if isinstance(block, TextBlock)
                ).strip()
                if not answer:
                    raise AgentFailure("Claude devolvió una respuesta vacía.", "empty_response")
                answer, cited = grounded_sources(answer, sources)
                if not cited:
                    answer = without_sources(request, trace, self.settings, self.registry)
                # Emit only validated final text. Raw provider deltas may split secrets or
                # contain unsupported citations; tool and status events remain live.
                await emit("token", {"text": answer})
                return ChatResponse(
                    answer=answer,
                    sources=cited,
                    trace=trace,
                    mode="anthropic",
                    model=self.settings.anthropic_model,
                    usage=usage,
                    session_id=request.session_id or str(uuid.uuid4()),
                )
            if len(trace) + len(calls) > self.settings.max_tool_calls:
                raise AgentFailure(
                    "Se alcanzó el límite de herramientas de la consulta.", "tool_limit"
                )
            messages.append(
                {
                    "role": "assistant",
                    "content": cast(
                        Any, [block.model_dump(exclude_none=True) for block in response.content]
                    ),
                }
            )
            outputs: list[ToolResultBlockParam] = []
            for call in calls:
                arguments = call.input if isinstance(call.input, dict) else {}
                result = await self.registry.run(
                    call.name, arguments, user_id=CURRENT_USER_ID.get()
                )
                trace.append(result.trace)
                await emit("tool", result.trace.model_dump())
                tool_output = result.trace.output
                if result.sources:
                    tool_output = annotate_sources(tool_output, result.sources, sources, source_ids)
                outputs.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call.id,
                        "content": tool_output,
                        "is_error": result.trace.status == "error",
                    }
                )
            messages.append({"role": "user", "content": outputs})
        raise AgentFailure("Se alcanzó el límite de pasos de la consulta.", "iteration_limit")

    async def close(self) -> None:
        if isinstance(self.provider, AnthropicProvider):
            await self.provider.close()
