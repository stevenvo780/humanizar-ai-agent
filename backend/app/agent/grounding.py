"""Citations: number retrieved sources for the model and keep only valid [S#] references."""

import json
import re
from typing import Any

from app.api.schemas import Source
from app.core.security import redact


def annotate_sources(
    output: str, retrieved: list[Source], sources: list[Source], source_ids: dict[str, int]
) -> str:
    """Register new sources in request order and add their ``[S#]`` label to the tool output."""
    annotated: list[dict[str, Any]] = []
    for source in retrieved:
        if source.chunk_id not in source_ids:
            sources.append(source)
            source_ids[source.chunk_id] = len(sources)
        annotated.append({"citation": f"[S{source_ids[source.chunk_id]}]", **source.model_dump()})
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload["sources"] = annotated
    return json.dumps(payload, ensure_ascii=False)


def grounded_sources(answer: str, sources: list[Source]) -> tuple[str, list[Source]]:
    """Only IDs actually present in this request's retrieval become visible citations."""
    cited: list[Source] = []
    identifiers: dict[str, int] = {}

    def citation(number: str) -> str:
        index = int(number) - 1
        if index < 0 or index >= len(sources):
            return "[fuente no disponible]"
        source = sources[index]
        if source.chunk_id not in identifiers:
            cited.append(source)
            identifiers[source.chunk_id] = len(cited)
        return f"[S{identifiers[source.chunk_id]}]"

    def replace(match: re.Match[str]) -> str:
        # Models sometimes group citations as [S1, S2]; normalize them to [S1][S2].
        return "".join(citation(number) for number in re.findall(r"\d+", match.group(1)))

    pattern = r"\[(S\d+(?:\s*[,;]\s*S?\d+)*)\]"
    return re.sub(pattern, replace, redact(answer)), cited
