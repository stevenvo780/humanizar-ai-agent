"""Model provider boundary: the MessageProvider protocol, Anthropic streaming and failures."""

import logging
from collections.abc import Awaitable, Callable
from typing import Protocol

import anthropic
from anthropic import AsyncAnthropic
from anthropic.types import Message, MessageParam, ToolParam

from app.core.settings import Settings

TextCallback = Callable[[str], Awaitable[None]]
logger = logging.getLogger(__name__)


class AgentFailure(Exception):
    """A public, non-leaking failure with a stable ``code`` returned as HTTP 503."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def provider_failure(exc: Exception) -> AgentFailure:
    if isinstance(exc, anthropic.AuthenticationError):
        return AgentFailure("La clave de Anthropic no está autorizada.", "authentication")
    if isinstance(exc, anthropic.RateLimitError):
        return AgentFailure("Anthropic alcanzó su límite de uso. Prueba más tarde.", "rate_limit")
    if isinstance(
        exc, anthropic.NotFoundError | anthropic.BadRequestError | anthropic.PermissionDeniedError
    ):
        # Usually a wrong ANTHROPIC_MODEL or account permissions: not a transient outage.
        return AgentFailure(
            "Anthropic rechazó la configuración de la consulta (modelo o permisos).",
            "provider_configuration",
        )
    if isinstance(exc, anthropic.APIError | TimeoutError):
        return AgentFailure("Anthropic no está disponible en este momento.", "provider_unavailable")
    return AgentFailure("No se pudo completar la respuesta de Claude.", "provider_error")


def log_provider_failure(exc: Exception) -> None:
    """Record type, status and request id only: never bodies, prompts or credentials."""
    logger.warning(
        "Anthropic request failed: %s status=%s request_id=%s",
        type(exc).__name__,
        getattr(exc, "status_code", None),
        getattr(exc, "request_id", None),
    )


class MessageProvider(Protocol):
    async def complete(
        self,
        messages: list[MessageParam],
        tools: list[ToolParam],
        system: str,
        on_text: TextCallback | None,
    ) -> Message: ...


class AnthropicProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value(),
            timeout=settings.anthropic_timeout_seconds,
            max_retries=1,
        )

    async def complete(
        self,
        messages: list[MessageParam],
        tools: list[ToolParam],
        system: str,
        on_text: TextCallback | None,
    ) -> Message:
        async with self.client.messages.stream(
            model=self.settings.anthropic_model,
            max_tokens=self.settings.max_output_tokens,
            system=system,
            messages=messages,
            tools=tools,
        ) as stream:
            async for event in stream:
                if (
                    on_text is not None
                    and event.type == "content_block_delta"
                    and event.delta.type == "text_delta"
                ):
                    await on_text(event.delta.text)
            return await stream.get_final_message()

    async def close(self) -> None:
        await self.client.close()
