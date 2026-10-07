"""Conversation history owned by the authenticated user."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.dependencies import DatabaseDep, RequiredUser, bearer
from app.core.concurrency import run_sync

router = APIRouter(prefix="/api", tags=["conversations"], dependencies=[Depends(bearer)])


@router.get("/conversations")
async def conversations(user: RequiredUser, database: DatabaseDep) -> dict[str, Any]:
    return {"conversations": await run_sync(database.list_conversations, user.id)}


@router.delete("/conversations/{identifier}", status_code=204)
async def remove_conversation(
    identifier: str, user: RequiredUser, database: DatabaseDep
) -> Response:
    try:
        removed = await run_sync(database.delete_conversation, user.id, identifier)
    except PermissionError as exc:
        raise HTTPException(404, "Conversación no encontrada.") from exc
    if not removed:
        raise HTTPException(404, "Conversación no encontrada.")
    return Response(status_code=204)
