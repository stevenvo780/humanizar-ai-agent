"""Business requests (demo and support): the customer's own list and the admin inbox."""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import BusinessDep, RequiredAdmin, RequiredUser, bearer
from app.core.concurrency import run_sync

router = APIRouter(prefix="/api", tags=["requests"], dependencies=[Depends(bearer)])


@router.get("/requests")
async def my_requests(user: RequiredUser, business: BusinessDep) -> dict[str, Any]:
    return {"requests": await run_sync(business.list_requests, user.id)}


@router.get("/admin/requests")
async def admin_requests(_user: RequiredAdmin, business: BusinessDep) -> dict[str, Any]:
    return {"requests": await run_sync(business.list_all_requests)}
