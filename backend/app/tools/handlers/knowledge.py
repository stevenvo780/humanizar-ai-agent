"""Knowledge tools: cited retrieval and catalog recommendations grounded in documents."""

import json
import re
from typing import Any

from app.api.schemas import Source
from app.core.concurrency import run_sync
from app.core.security import redact
from app.core.text import normalized
from app.tools.handlers.base import ToolContext, ToolOutput, string_argument


async def search_knowledge(context: ToolContext) -> ToolOutput:
    query = string_argument(context.arguments, "query", 1000)
    sources = [
        source.model_copy(
            update={
                "text": redact(source.text),
                "document_name": redact(source.document_name),
            }
        )
        for source in await run_sync(context.store.search, query)
    ]
    output = json.dumps(
        {"sources": [source.model_dump() for source in sources]}, ensure_ascii=False
    )
    return ToolOutput(output, sources)


async def recommend_product(context: ToolContext) -> ToolOutput:
    process = string_argument(context.arguments, "process", 1000)
    evidence = await run_sync(context.store.search, process, 5)
    sources = [
        source.model_copy(
            update={
                "text": redact(source.text[:1000]),
                "document_name": redact(source.document_name[:200]),
            }
        )
        for source in evidence[:3]
    ]
    words = {word.rstrip("s") for word in re.findall(r"\w+", normalized(process))}
    choices: list[tuple[int, dict[str, Any]]] = []
    for definition in context.settings.products:
        product, topics = definition.name, definition.keywords
        matching = [source for source in sources if normalized(product) in normalized(source.text)]
        score = sum(normalized(topic).rstrip("s") in words for topic in topics)
        if normalized(product) in normalized(process):
            score += 3
        if not score or not matching:
            continue
        source = matching[0]
        lines = [
            line.strip()
            for line in source.text.splitlines()
            if normalized(product) in normalized(line) and not line.startswith(("#", "Fuente"))
        ]
        excerpt = max(lines, key=len)[:300] if lines else source.text[:300]
        choices.append(
            (
                score,
                {
                    "product": product,
                    "documented_basis": excerpt,
                    "source_ids": [source.chunk_id],
                },
            )
        )
    choices.sort(key=lambda item: -item[0])
    message = (
        "Orientación basada en documentos; confirma el alcance en una demo o diagnóstico. "
        "Esta herramienta no cotiza ni garantiza integraciones o resultados."
        if choices
        else "No hay evidencia suficiente para recomendar un producto concreto. "
        "Describe tu proceso o solicita un diagnóstico."
    )
    payload: dict[str, Any] = {
        "recommendations": [choice for _, choice in choices[:3]],
        "message": message,
        "sources": [source.model_dump() for source in sources],
    }
    _fit_payload(payload, sources)
    return ToolOutput(json.dumps(payload, ensure_ascii=False), sources)


def _fit_payload(payload: dict[str, Any], sources: list[Source]) -> None:
    """Drop trailing sources (and recommendations citing only them) to stay under 7500 chars."""
    while sources and len(json.dumps(payload, ensure_ascii=False)) > 7500:
        sources.pop()
        identifiers = {source.chunk_id for source in sources}
        payload["sources"] = [source.model_dump() for source in sources]
        payload["recommendations"] = [
            item
            for item in payload["recommendations"]
            if any(identifier in identifiers for identifier in item["source_ids"])
        ]
