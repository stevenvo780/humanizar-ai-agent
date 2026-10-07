"""Signed access tokens (HS256 JWT) and the HttpOnly refresh-cookie transport."""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, Request, Response
from jwt import InvalidTokenError

from app.persistence.contracts import IdentityStore
from app.persistence.models import REFRESH_SECONDS, User

ISSUER = "lumen-assistant"
AUDIENCE = "lumen-api"
ACCESS_MINUTES = 30
REFRESH_COOKIE = "lumen_refresh"
# Cookie-authenticated session calls (refresh/logout) must carry X-Requested-With: Lumen.
CSRF_HEADER_VALUE = "Lumen"


def unauthorized() -> HTTPException:
    return HTTPException(
        401, "No se pudo validar la sesión.", headers={"WWW-Authenticate": "Bearer"}
    )


def issue_access(database: IdentityStore, user: User, session_id: str) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": user.id,
            "sid": session_id,
            "iat": now,
            "exp": now + timedelta(minutes=ACCESS_MINUTES),
        },
        database.jwt_secret,
        algorithm="HS256",
    )


def access_claims(database: IdentityStore, token: str) -> tuple[str, str]:
    """Return ``(user_id, session_id)`` from a valid token or raise a 401."""
    if len(token) > 8192:
        raise unauthorized()
    try:
        payload = jwt.decode(
            token,
            database.jwt_secret,
            algorithms=["HS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={"require": ["iss", "aud", "sub", "sid", "exp", "iat"]},
        )
        user_id, session_id = payload["sub"], payload["sid"]
        if not isinstance(user_id, str) or not isinstance(session_id, str):
            raise unauthorized()
        return user_id, session_id
    except InvalidTokenError:
        raise unauthorized() from None


def set_refresh_cookie(request: Request, response: Response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=REFRESH_SECONDS,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
        path="/api/auth",
    )
    response.headers["Cache-Control"] = "no-store"


def clear_refresh_cookie(request: Request, response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE,
        path="/api/auth",
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
    )
