"""Demo mode: deterministic calculation or extractive excerpts, never an LLM answer."""

import asyncio
import re
import uuid

from app.agent.events import Emit
from app.api.schemas import ChatRequest, ChatResponse, Source, ToolTrace, Usage
from app.core.settings import Settings
from app.knowledge.embeddings import QUESTION_WORDS, terms
from app.tools.registry import ToolRegistry


def _arithmetic(message: str) -> str | None:
    """An explicit expression, or "calcula N% de X" rewritten as ``X * N / 100``."""
    expression = re.fullmatch(
        r"\s*(?:(?:calcula|calcular|calculate)\s+)?([\d.\s()+*/%\-]+)\s*",
        message,
        re.IGNORECASE,
    )
    arithmetic = expression.group(1) if expression else None
    percent = re.match(r"\s*calcula\s+(?:el\s*)?([\d.,]+)\s*%", message, re.IGNORECASE)
    if percent and arithmetic is None:
        amounts = re.findall(r"\d+(?:[.,]\d+)*", message[percent.end() :])
        if len(amounts) == 1:

            def number(value: str) -> str:
                if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", value):
                    return value.replace(".", "")
                return value.replace(",", ".")

            arithmetic = f"{number(amounts[0])} * {number(percent.group(1))} / 100"
    return arithmetic


async def demo_answer(
    settings: Settings, registry: ToolRegistry, request: ChatRequest, emit: Emit
) -> ChatResponse:
    trace: list[ToolTrace] = []
    arithmetic = _arithmetic(request.message)
    if arithmetic:
        result = await registry.run("calculate", {"expression": arithmetic})
        sources: list[Source] = []
        answer = f"Modo demostración · cálculo determinista: {result.trace.output}"
    else:
        result = await registry.run("search_knowledge", {"query": request.message[:1000]})
        substantive = (
            set(terms(request.message)) - QUESTION_WORDS - set(terms(settings.company_name))
        )
        sources = [
            source
            for source in result.sources
            if not substantive or substantive.issubset(set(terms(source.text)))
        ][:3]
        if sources:
            excerpts = [f"{source.text} [S{index}]" for index, source in enumerate(sources, 1)]
            answer = (
                "Modo demostración · respuesta extractiva de tus documentos:\n\n"
                + "\n\n".join(excerpts)
            )
        else:
            answer = (
                "Modo demostración · no encontré información relacionada en los documentos. "
                "Carga un archivo de la empresa o reformula la pregunta."
            )
    trace.append(result.trace)
    await emit("tool", result.trace.model_dump())
    for start in range(0, len(answer), 70):
        await emit("token", {"text": answer[start : start + 70]})
        await asyncio.sleep(0)
    return ChatResponse(
        answer=answer,
        sources=sources,
        trace=trace,
        mode="demo",
        model=settings.anthropic_model,
        usage=Usage(),
        session_id=request.session_id or str(uuid.uuid4()),
    )
