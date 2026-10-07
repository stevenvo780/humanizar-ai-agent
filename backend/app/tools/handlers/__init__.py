"""Dispatch table: one async handler per ToolDefinition name.

To add a tool, declare its ToolDefinition in ``app.tools.definitions`` and register an
``async def handler(context: ToolContext) -> ToolOutput`` here. The registry validates
arguments first and applies redaction, truncation, timing and error mapping afterwards.
"""

from app.tools.handlers.arithmetic import calculate
from app.tools.handlers.base import Handler, ToolContext, ToolOutput
from app.tools.handlers.business import create_request, list_my_requests
from app.tools.handlers.knowledge import recommend_product, search_knowledge
from app.tools.handlers.mcp_stdio import mcp_company_info
from app.tools.handlers.sandbox import terminal

HANDLERS: dict[str, Handler] = {
    "search_knowledge": search_knowledge,
    "calculate": calculate,
    "recommend_product": recommend_product,
    "create_demo_request": create_request,
    "create_support_ticket": create_request,
    "list_my_requests": list_my_requests,
    "terminal": terminal,
    "mcp_company_info": mcp_company_info,
}

__all__ = ["HANDLERS", "Handler", "ToolContext", "ToolOutput"]
