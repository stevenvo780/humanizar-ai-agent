import asyncio
from collections.abc import Callable
from contextlib import suppress
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


async def run_sync(operation: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    """Retain resource ownership until an uncancellable worker thread actually finishes."""
    task = asyncio.create_task(asyncio.to_thread(operation, *args, **kwargs))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        with suppress(Exception, asyncio.CancelledError):
            task.result()
        raise
