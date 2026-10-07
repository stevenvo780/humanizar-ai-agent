"""Request identity: the bound user id plus bearer-token user and admin dependencies."""

from contextvars import ContextVar

from fastapi import HTTPException, Request

from app.accounts.tokens import access_claims, unauthorized
from app.persistence.contracts import IdentityStore
from app.persistence.models import User

CURRENT_USER_ID: ContextVar[str | None] = ContextVar("current_user_id", default=None)


def identity_store(request: Request) -> IdentityStore:
    database: IdentityStore = request.app.state.database
    return database


def require_user(request: Request) -> User:
    authorization = request.headers.get("Authorization", "")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].casefold() != "bearer" or len(parts[1]) > 8192:
        raise unauthorized()
    database = identity_store(request)
    user_id, session_id = access_claims(database, parts[1])
    user = database.session_user(session_id, user_id)
    if user is None:
        raise unauthorized()
    return user


def require_admin(request: Request) -> User:
    user = require_user(request)
    if user.role != "admin":
        raise HTTPException(403, "Se requiere una cuenta administradora.")
    return user
