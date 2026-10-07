"""Single-turn RAG shared by ``POST /api/ask`` and ``POST /preguntar``.

Retrieve the most relevant fragments, inject only those into the prompt and let the model
answer under the caller's restrictive system prompt. Without relevant fragments the model is
never called; demo mode returns the labelled fragments instead of an LLM answer.
"""

from dataclasses import dataclass

import anthropic
from anthropic.types import MessageParam

from app.agent.provider import log_provider_failure, provider_failure
from app.api.schemas import Source
from app.core.concurrency import run_sync
from app.core.security import redact
from app.core.settings import Settings
from app.knowledge.store import KnowledgeStore

DEMO_LABEL = "Modo demostración (extractivo, sin modelo de lenguaje):"


@dataclass(frozen=True)
class RagPolicy:
    """What the model is allowed to do and what to answer when evidence is missing."""

    system: str
    no_context: str
    temperature: float | None = None


@dataclass(frozen=True)
class RagAnswer:
    text: str
    sources: list[Source]
    model: str  # "none" without evidence, "demo" in demo mode, else the provider's model


def numbered_context(sources: list[Source]) -> str:
    return "\n\n".join(f"[S{index}] {source.text}" for index, source in enumerate(sources, 1))


def user_prompt(question: str, sources: list[Source]) -> str:
    return f"Contexto:\n{numbered_context(sources)}\n\nPregunta: {question}"


async def answer(
    settings: Settings, store: KnowledgeStore, question: str, top_k: int, policy: RagPolicy
) -> RagAnswer:
    sources = await run_sync(store.search, question, top_k)
    if not sources:
        return RagAnswer(policy.no_context, [], "none")
    if settings.mode == "demo":
        return RagAnswer(f"{DEMO_LABEL}\n\n{numbered_context(sources)}", sources, "demo")
    client = anthropic.AsyncAnthropic(
        api_key=settings.anthropic_api_key.get_secret_value(),
        timeout=settings.anthropic_timeout_seconds,
        max_retries=1,
    )
    messages: list[MessageParam] = [{"role": "user", "content": user_prompt(question, sources)}]
    try:
        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.max_output_tokens,
            system=policy.system,
            messages=messages,
            temperature=anthropic.omit if policy.temperature is None else policy.temperature,
        )
    except Exception as exc:
        log_provider_failure(exc)
        raise provider_failure(exc) from exc  # mapped to 503 {detail, code} by api/errors.py
    finally:
        await client.close()
    text = "".join(block.text for block in message.content if block.type == "text").strip()
    return RagAnswer(redact(text) or policy.no_context, sources, message.model)
