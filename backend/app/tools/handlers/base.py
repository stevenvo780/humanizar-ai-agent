"""Handler contract: what a tool receives (ToolContext) and returns (ToolOutput)."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.api.schemas import Source
from app.core.settings import Settings
from app.knowledge.store import KnowledgeStore
from app.persistence.contracts import BusinessRepository


@dataclass(frozen=True)
class ToolContext:
    """Arguments already validated against the ToolDefinition, plus the caller's scope."""

    name: str
    arguments: dict[str, Any]
    settings: Settings
    store: KnowledgeStore
    business: BusinessRepository | None
    http: httpx.AsyncClient
    user_id: str | None = None
    confirmed: bool = False
    action_key: str | None = None


@dataclass
class ToolOutput:
    """Raw output (the registry redacts and truncates it); ``failed`` marks an error trace."""

    output: str
    sources: list[Source] = field(default_factory=list)
    failed: bool = False


Handler = Callable[[ToolContext], Awaitable[ToolOutput]]


def string_argument(arguments: dict[str, Any], key: str, limit: int) -> str:
    """The single non-empty string parameter ``key``; any other parameter is rejected."""
    if set(arguments) != {key}:
        raise ValueError("Parámetros no admitidos.")
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("Parámetro vacío, inválido o demasiado extenso.")
    return value.strip()
