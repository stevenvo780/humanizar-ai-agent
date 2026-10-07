"""Tool catalog, administrator playground and user-confirmed business actions."""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import RegistryDep, RequiredUser, ScopedAdmin, ScopedUser, bearer
from app.api.schemas import ActionConfirmation, ToolRequest, ToolTrace

router = APIRouter(prefix="/api", tags=["tools"])


@router.get("/tools")
def tools(_user: ScopedUser, registry: RegistryDep) -> dict[str, Any]:
    return {"tools": registry.catalog()}


@router.post("/tools/run", response_model=ToolTrace)
async def tool_run(request: ToolRequest, user: ScopedAdmin, registry: RegistryDep) -> ToolTrace:
    result = await registry.run(
        request.name,
        request.input,
        user_id=user.id if user else None,
        confirmed=request.confirmed,
    )
    return result.trace


@router.post("/actions/confirm", response_model=ToolTrace, dependencies=[Depends(bearer)])
async def confirm_action(
    request: ActionConfirmation, user: RequiredUser, registry: RegistryDep
) -> ToolTrace:
    result = await registry.run(
        request.tool,
        request.input,
        user_id=user.id,
        confirmed=True,
        action_key=request.action_key,
    )
    return result.trace
