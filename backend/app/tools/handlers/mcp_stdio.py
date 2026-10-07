"""MCP tool: a real stdio session to ``python -m app.mcp.server``, which calls the API."""

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from app.tools.handlers.base import ToolContext, ToolOutput


async def query_company_info(api_url: str) -> str:
    # Never inherit API keys or the entire host environment into another runtime.
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp.server"],
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LUMEN_API_URL": api_url,
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


async def mcp_company_info(context: ToolContext) -> ToolOutput:
    if context.arguments or not context.settings.mcp_enabled:
        raise ValueError("MCP deshabilitado o parámetros inválidos.")
    return ToolOutput(await query_company_info(context.settings.lumen_api_url))
