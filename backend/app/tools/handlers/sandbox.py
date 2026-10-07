"""Sandbox tool: named presets executed by the separate terminal service over HTTP."""

import json

import httpx

from app.tools.definitions import PRESETS
from app.tools.handlers.base import ToolContext, ToolOutput, string_argument


async def sandbox_health(http: httpx.AsyncClient, sandbox_url: str) -> bool:
    if not sandbox_url:
        return False
    try:
        result = await http.get(sandbox_url.rstrip("/") + "/health", timeout=0.6)
        return result.status_code == 200
    except httpx.HTTPError:
        return False


async def terminal(context: ToolContext) -> ToolOutput:
    command = string_argument(context.arguments, "command", 40)
    if command not in PRESETS:
        raise ValueError("Solo se admiten los presets del sandbox.")
    if not context.settings.sandbox_url:
        raise ValueError("Sandbox no configurado.")
    response = await context.http.post(
        context.settings.sandbox_url.rstrip("/") + "/run", json={"command": command}
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
    return ToolOutput(output, failed=payload["exit_code"] != 0)
