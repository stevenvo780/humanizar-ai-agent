"""Progress callback contract: (event, data) pairs streamed to the caller as SSE."""

from collections.abc import Awaitable, Callable
from typing import Any

Emit = Callable[[str, dict[str, Any]], Awaitable[None]]


async def no_emit(_event: str, _data: dict[str, Any]) -> None:
    return None
