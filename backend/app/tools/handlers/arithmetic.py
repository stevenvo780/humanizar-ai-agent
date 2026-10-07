"""Arithmetic tool: the bounded AST calculator, never code execution."""

from app.tools.calculator import calculate as evaluate
from app.tools.handlers.base import ToolContext, ToolOutput, string_argument


async def calculate(context: ToolContext) -> ToolOutput:
    return ToolOutput(evaluate(string_argument(context.arguments, "expression", 200)))
