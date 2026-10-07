"""Administrator customer management: paginated listing and account creation."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.accounts.auth import (
    CustomerCreatedResponse,
    CustomerListResponse,
    PublicCustomer,
    SignupRequest,
    hash_password,
)
from app.api.dependencies import DatabaseDep, RequiredAdmin, bearer
from app.core.concurrency import run_sync
from app.persistence.contracts import PersistenceUnavailable

router = APIRouter(prefix="/api/admin", tags=["customers"], dependencies=[Depends(bearer)])


@router.get("/customers", response_model=CustomerListResponse)
async def admin_customers(
    response: Response,
    _user: RequiredAdmin,
    database: DatabaseDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CustomerListResponse:
    customers, total = await run_sync(database.list_customers, limit, offset)
    response.headers["Cache-Control"] = "no-store"
    return CustomerListResponse(
        customers=[PublicCustomer.model_validate(customer) for customer in customers],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/customers", response_model=CustomerCreatedResponse, status_code=201)
async def create_customer(
    payload: SignupRequest, response: Response, _user: RequiredAdmin, database: DatabaseDep
) -> CustomerCreatedResponse:
    password_hash = await run_sync(hash_password, payload.password.get_secret_value())
    try:
        user = await run_sync(
            database.register_customer, payload.name, payload.email, password_hash
        )
    except ValueError:
        raise HTTPException(409, "No se pudo crear la cuenta.") from None
    customer = await run_sync(database.get_customer, user.id)
    if customer is None:
        raise PersistenceUnavailable()
    response.headers["Cache-Control"] = "no-store"
    return CustomerCreatedResponse(customer=PublicCustomer.model_validate(customer))
