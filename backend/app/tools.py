import asyncio
import json
import os
import re
import sys
import time
import unicodedata
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from anthropic.types import ToolParam
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from app.business import (
    BusinessValidationError,
    RequestKind,
    validate_details,
    validate_user_id,
)
from app.calculator import calculate
from app.concurrency import run_sync
from app.models import Source, ToolTrace
from app.persistence import BusinessRepository
from app.security import redact, safe_input
from app.settings import Settings
from app.storage import KnowledgeStore
from app.tool_definitions import BY_NAME, DEFINITIONS, PRESETS

BUSINESS_WRITES = {"create_demo_request": "demo", "create_support_ticket": "support"}


def normalized(text: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(char)
    )


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
        if not self.settings.sandbox_url:
            return False
        try:
            result = await self.http.get(
                self.settings.sandbox_url.rstrip("/") + "/health", timeout=0.6
            )
            return result.status_code == 200
        except httpx.HTTPError:
            return False

    async def _mcp_company_info(self) -> str:
        # Never inherit API keys or the entire host environment into another runtime.
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "app.mcp_server"],
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "LUMEN_API_URL": self.settings.lumen_api_url,
                "PYTHONUNBUFFERED": "1",
            },
        )
        async with asyncio.timeout(12):
            async with (
                stdio_client(parameters) as (reader, writer),
                ClientSession(reader, writer) as session,
            ):
                await session.initialize()
                result = await session.call_tool("company_info", {})
                if result.isError:
                    raise ValueError("MCP company_info no disponible.")
                text = "\n".join(
                    block.text for block in result.content if isinstance(block, TextContent)
                )
                return text[:8000]

    @staticmethod
    def _string(arguments: dict[str, Any], key: str, limit: int) -> str:
        if set(arguments) != {key}:
            raise ValueError("Parámetros no admitidos.")
        value = arguments.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError("Parámetro vacío, inválido o demasiado extenso.")
        return value.strip()

    def _business_for_user(self, user_id: str | None) -> BusinessRepository:
        if user_id is None:
            raise BusinessValidationError(
                "Inicia sesión para consultar o registrar tus solicitudes."
            )
        validate_user_id(user_id)
        if self.business is None:
            raise BusinessValidationError("El registro local de solicitudes no está disponible.")
        return self.business

    async def _recommend(self, process: str) -> tuple[dict[str, Any], list[Source]]:
        evidence = await run_sync(self.store.search, process, 5)
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
        for definition in self.settings.products:
            product, topics = definition.name, definition.keywords
            matching = [
                source for source in sources if normalized(product) in normalized(source.text)
            ]
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
        while sources and len(json.dumps(payload, ensure_ascii=False)) > 7500:
            sources.pop()
            identifiers = {source.chunk_id for source in sources}
            payload["sources"] = [source.model_dump() for source in sources]
            payload["recommendations"] = [
                item
                for item in payload["recommendations"]
                if any(identifier in identifiers for identifier in item["source_ids"])
            ]
        return payload, sources

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
        sources: list[Source] = []
        status: str = "completed"
        output = ""
        try:
            definition = BY_NAME.get(name)
            if definition is None:
                raise ValueError("Herramienta desconocida.")
            definition.validate(arguments)
            if name == "search_knowledge":
                query = self._string(arguments, "query", 1000)
                sources = [
                    source.model_copy(
                        update={
                            "text": redact(source.text),
                            "document_name": redact(source.document_name),
                        }
                    )
                    for source in await run_sync(self.store.search, query)
                ]
                output = json.dumps(
                    {"sources": [source.model_dump() for source in sources]}, ensure_ascii=False
                )
            elif name == "recommend_product":
                payload, sources = await self._recommend(self._string(arguments, "process", 1000))
                output = json.dumps(payload, ensure_ascii=False)
            elif name in BUSINESS_WRITES:
                business = self._business_for_user(user_id)
                assert user_id is not None
                kind: RequestKind = "demo" if name == "create_demo_request" else "support"
                details = validate_details(kind, arguments)
                if confirmed is not True:
                    output = json.dumps(
                        {
                            "requires_confirmation": True,
                            "action": {"tool": name, "input": details},
                            "message": "Confirma para guardar esta solicitud en tu cuenta. "
                            "Es un registro local; no envía mensajes ni agenda una cita externa.",
                        },
                        ensure_ascii=False,
                    )
                else:
                    record = await run_sync(
                        business.create_request, user_id, kind, details, action_key
                    )
                    output = json.dumps(
                        {
                            "request": record,
                            "message": "Solicitud registrada localmente. "
                            "No se ha enviado ninguna notificación ni confirmado una cita externa.",
                        },
                        ensure_ascii=False,
                    )
            elif name == "list_my_requests":
                if arguments:
                    raise BusinessValidationError(
                        "Esta consulta no admite identificadores ni parámetros."
                    )
                business = self._business_for_user(user_id)
                assert user_id is not None
                records = await run_sync(business.list_requests, user_id)
                visible: list[dict[str, Any]] = []
                for record in records:
                    if len(json.dumps(visible + [record], ensure_ascii=False)) > 7000:
                        break
                    visible.append(record)
                output = json.dumps(
                    {
                        "requests": visible,
                        "has_more": len(visible) < len(records) or len(records) == 20,
                        "message": "Registros locales de tu cuenta; no acreditan envío externo.",
                    },
                    ensure_ascii=False,
                )
            elif name == "calculate":
                output = calculate(self._string(arguments, "expression", 200))
            elif name == "terminal":
                command = self._string(arguments, "command", 40)
                if command not in PRESETS:
                    raise ValueError("Solo se admiten los presets del sandbox.")
                if not self.settings.sandbox_url:
                    raise ValueError("Sandbox no configurado.")
                response = await self.http.post(
                    self.settings.sandbox_url.rstrip("/") + "/run", json={"command": command}
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict) or type(payload.get("exit_code")) is not int:
                    raise ValueError("Respuesta del sandbox inválida.")
                output = json.dumps(
                    {
                        "stdout": str(payload.get("stdout", ""))[:6000],
                        "stderr": str(payload.get("stderr", ""))[:2000],
                        "exit_code": payload["exit_code"],
                    },
                    ensure_ascii=False,
                )
                if payload["exit_code"] != 0:
                    status = "error"
            elif name == "mcp_company_info":
                if arguments or not self.settings.mcp_enabled:
                    raise ValueError("MCP deshabilitado o parámetros inválidos.")
                output = await self._mcp_company_info()
            else:
                raise ValueError("Herramienta desconocida.")
        except httpx.HTTPError:
            status, output = "error", "Sandbox no disponible. Iniciá el servicio aislado."
        except BusinessValidationError as exc:
            status, output = "error", str(exc)
        except (ValueError, SyntaxError, ZeroDivisionError, OverflowError):
            # Return a known fixed message rather than exception text that may contain input.
            status, output = "error", "Entrada inválida o herramienta no disponible."
        except Exception:
            status, output = "error", "La herramienta no pudo completarse."
        return ToolResult(
            trace=ToolTrace(
                id=str(uuid.uuid4()),
                tool=name,
                input=bounded_safe_input(arguments),
                output=redact(output)[:8000],
                status="completed" if status == "completed" else "error",
                duration_ms=round((time.perf_counter() - start) * 1000),
            ),
            sources=sources,
        )

    async def close(self) -> None:
        await self.http.aclose()
