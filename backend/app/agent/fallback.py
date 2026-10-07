"""Deterministic answer when the model cites nothing: real tool results, never model prose."""

import json
import re

from app.api.schemas import ChatRequest, ToolTrace
from app.core.security import redact
from app.core.settings import Settings
from app.core.text import normalized
from app.tools.definitions import BY_NAME
from app.tools.registry import ToolRegistry

# Tools whose output are company facts: shown only through validated [S#] citations.
FACT_TOOLS = frozenset({"search_knowledge", "recommend_product"})
REQUEST_INTENTS = (
    ("create_demo_request", "solicitud de demo", ("demo", "demostracion")),
    (
        "create_support_ticket",
        "caso de soporte",
        ("soporte", "ticket", "incidencia", "no puedo", "no funciona"),
    ),
)
# Tools with a dedicated deterministic rendering in without_sources.
RENDERED_TOOLS = frozenset(
    {
        "calculate",
        "create_demo_request",
        "create_support_ticket",
        "list_my_requests",
        "terminal",
        "mcp_company_info",
    }
)


def readable(output: str) -> str:
    try:
        return json.dumps(json.loads(output), ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return output


def without_sources(
    request: ChatRequest, trace: list[ToolTrace], settings: Settings, registry: ToolRegistry
) -> str:
    """Replace unsupported prose with concrete results, not a truth-detecting regex."""
    query = normalized(request.message)
    identity = re.fullmatch(
        r"[\s¿¡]*(?:hola|hello|hi|buenos dias|buenas tardes|gracias|quien eres|"
        r"como te llamas|informacion de la empresa|company info)[!?¿¡.\s]*",
        query,
    )
    arithmetic = any(char.isdigit() for char in query) and (
        any(operator in query for operator in ("+", "-", "*", "/", "%"))
        or any(
            word in query for word in ("calcula", "calculate", "iva", "total", "importe", "anual")
        )
    )
    outputs: list[str] = []
    for item in trace:
        if item.status != "completed":
            continue
        if item.tool == "calculate" and arithmetic:
            outputs.append(
                f"Resultado del cálculo: {item.input.get('expression', '')} = {item.output}"
            )
            continue
        if item.tool not in FACT_TOOLS | RENDERED_TOOLS:
            # Any other tool output is deterministic application data, not model prose.
            outputs.append(f"Resultado de {item.tool}:\n```\n{readable(item.output)}\n```")
            continue
        try:
            value = json.loads(item.output)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict):
            continue
        if item.tool in {"create_demo_request", "create_support_ticket"}:
            if value.get("requires_confirmation") is True:
                outputs.append(
                    "La solicitud está pendiente de tu confirmación. Usa el botón de la "
                    "interfaz para registrarla; todavía no se ha guardado ni enviado."
                )
            elif isinstance(value.get("request"), dict):
                outputs.append(
                    "Solicitud registrada localmente. No se ha enviado ninguna "
                    "notificación ni confirmado una cita externa."
                )
        elif item.tool == "list_my_requests" and isinstance(value.get("requests"), list):
            records = value["requests"]
            outputs.append(
                "Tus solicitudes locales:\n"
                + "\n".join(
                    f"{record.get('kind', '')}: {record.get('status', '')}"
                    for record in records
                    if isinstance(record, dict)
                )
                if records
                else "No tienes solicitudes locales registradas."
            )
        elif item.tool == "terminal":
            outputs.append("Resultado del preset en el sandbox:\n" + item.output)
        elif item.tool == "mcp_company_info" and identity:
            name = value.get("company_name")
            description = value.get("company_description")
            if isinstance(name, str) and isinstance(description, str):
                outputs.append(f"Identidad configurada: {name}. {description}")
    if outputs:
        return redact("\n\n".join(outputs))
    if identity:
        return (
            f"Hola. Soy {redact(settings.assistant_name)}, asistente de "
            f"{redact(settings.company_name)}. ¿En qué puedo ayudarte?"
        )
    enabled = {tool["name"] for tool in registry.catalog() if tool["enabled"]}
    for tool, label, keywords in REQUEST_INTENTS:
        if tool in enabled and any(keyword in query for keyword in keywords):
            fields = [
                str(rules.get("title", name)) for name, rules in BY_NAME[tool].properties.items()
            ]
            listed = ", ".join(fields[:-1]) + f" y {fields[-1]}" if len(fields) > 1 else ""
            return (
                f"Para preparar tu {label} necesito: {listed or fields[0]}. "
                "Compártelos y te mostraré la solicitud para que la confirmes."
            )
    return (
        "No encontré evidencia suficiente en los documentos para responder. "
        "Prueba a reformular la consulta o carga la información que falta."
    )
