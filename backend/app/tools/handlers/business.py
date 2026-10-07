"""Business tools: user-confirmed local demo/support requests and the caller's own records."""

import json
from typing import Any

from app.business.requests import (
    BusinessValidationError,
    RequestKind,
    validate_details,
    validate_user_id,
)
from app.core.concurrency import run_sync
from app.persistence.contracts import BusinessRepository
from app.tools.handlers.base import ToolContext, ToolOutput

# Tools that write a business request, and the request kind each one stores.
BUSINESS_WRITES: dict[str, RequestKind] = {
    "create_demo_request": "demo",
    "create_support_ticket": "support",
}


def _business_for_user(context: ToolContext) -> tuple[BusinessRepository, str]:
    if context.user_id is None:
        raise BusinessValidationError("Inicia sesión para consultar o registrar tus solicitudes.")
    validate_user_id(context.user_id)
    if context.business is None:
        raise BusinessValidationError("El registro local de solicitudes no está disponible.")
    return context.business, context.user_id


async def create_request(context: ToolContext) -> ToolOutput:
    """Without ``confirmed`` only propose the action; the UI confirms it in a separate call."""
    business, user_id = _business_for_user(context)
    kind = BUSINESS_WRITES[context.name]
    details = validate_details(kind, context.arguments)
    if context.confirmed is not True:
        return ToolOutput(
            json.dumps(
                {
                    "requires_confirmation": True,
                    "action": {"tool": context.name, "input": details},
                    "message": "Confirma para guardar esta solicitud en tu cuenta. "
                    "Es un registro local; no envía mensajes ni agenda una cita externa.",
                },
                ensure_ascii=False,
            )
        )
    record = await run_sync(business.create_request, user_id, kind, details, context.action_key)
    return ToolOutput(
        json.dumps(
            {
                "request": record,
                "message": "Solicitud registrada localmente. "
                "No se ha enviado ninguna notificación ni confirmado una cita externa.",
            },
            ensure_ascii=False,
        )
    )


async def list_my_requests(context: ToolContext) -> ToolOutput:
    if context.arguments:
        raise BusinessValidationError("Esta consulta no admite identificadores ni parámetros.")
    business, user_id = _business_for_user(context)
    records = await run_sync(business.list_requests, user_id)
    visible: list[dict[str, Any]] = []
    for record in records:
        if len(json.dumps(visible + [record], ensure_ascii=False)) > 7000:
            break
        visible.append(record)
    return ToolOutput(
        json.dumps(
            {
                "requests": visible,
                "has_more": len(visible) < len(records) or len(records) == 20,
                "message": "Registros locales de tu cuenta; no acreditan envío externo.",
            },
            ensure_ascii=False,
        )
    )
