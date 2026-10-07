"""Tool catalog and the single execution path: validate, dispatch, redact, time, map errors."""

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from anthropic.types import ToolParam

from app.api.schemas import Source, ToolTrace
from app.business.requests import BusinessValidationError
from app.core.security import redact, safe_input
from app.core.settings import Settings
from app.knowledge.store import KnowledgeStore
from app.persistence.contracts import BusinessRepository
from app.tools.definitions import BY_NAME, DEFINITIONS
from app.tools.handlers import HANDLERS, ToolContext, ToolOutput
from app.tools.handlers.sandbox import sandbox_health


def bounded_safe_input(arguments: dict[str, Any]) -> dict[str, Any]:
    def bound(value: Any, depth: int = 0) -> Any:
        if depth >= 4:
            return "[contenido omitido]"
        if isinstance(value, str):
            return value[:2000]
        if isinstance(value, dict):
            return {str(key)[:80]: bound(item, depth + 1) for key, item in list(value.items())[:12]}
        if isinstance(value, list):
            return [bound(item, depth + 1) for item in value[:8]]
        return value

    result = safe_input(bound(arguments))
    while result and len(json.dumps(result, ensure_ascii=False)) > 6000:
        result.pop(next(reversed(result)))
    return result


@dataclass
class ToolResult:
    trace: ToolTrace
    sources: list[Source]


class ToolRegistry:
    def __init__(
        self, settings: Settings, store: KnowledgeStore, business: BusinessRepository | None = None
    ) -> None:
        self.settings = settings
        self.store = store
        self.business = business
        self.http = httpx.AsyncClient(timeout=8.0, follow_redirects=False)

    def _enabled(self, availability: str) -> bool:
        return {
            "always": True,
            "business": self.business is not None,
            "sandbox": bool(self.settings.sandbox_url),
            "mcp": self.settings.mcp_enabled,
        }[availability]

    def catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "name": definition.name,
                "description": definition.description,
                "enabled": self._enabled(definition.availability),
                "input_schema": definition.input_schema,
            }
            for definition in DEFINITIONS
        ]

    def schemas(self) -> list[ToolParam]:
        return [
            definition.provider_schema()
            for definition in DEFINITIONS
            if self._enabled(definition.availability)
        ]

    async def sandbox_available(self) -> bool:
        return await sandbox_health(self.http, self.settings.sandbox_url)

    async def run(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        user_id: str | None = None,
        confirmed: bool = False,
        action_key: str | None = None,
    ) -> ToolResult:
        start = time.perf_counter()
        result = ToolOutput("")
        try:
            definition = BY_NAME.get(name)
            handler = HANDLERS.get(name)
            if definition is None or handler is None:
                raise ValueError("Herramienta desconocida.")
            definition.validate(arguments)
            result = await handler(
                ToolContext(
                    name=name,
                    arguments=arguments,
                    settings=self.settings,
                    store=self.store,
                    business=self.business,
                    http=self.http,
                    user_id=user_id,
                    confirmed=confirmed,
                    action_key=action_key,
                )
            )
        except httpx.HTTPError:
            result = ToolOutput("Sandbox no disponible. Iniciá el servicio aislado.", failed=True)
        except BusinessValidationError as exc:
            result = ToolOutput(str(exc), failed=True)
        except (ValueError, SyntaxError, ZeroDivisionError, OverflowError):
            # Return a known fixed message rather than exception text that may contain input.
            result = ToolOutput("Entrada inválida o herramienta no disponible.", failed=True)
        except Exception:
            result = ToolOutput("La herramienta no pudo completarse.", failed=True)
        return ToolResult(
            trace=ToolTrace(
                id=str(uuid.uuid4()),
                tool=name,
                input=bounded_safe_input(arguments),
                output=redact(result.output)[:8000],
                status="error" if result.failed else "completed",
                duration_ms=round((time.perf_counter() - start) * 1000),
            ),
            sources=result.sources,
        )

    async def close(self) -> None:
        await self.http.aclose()
