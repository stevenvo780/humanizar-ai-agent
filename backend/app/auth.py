"""First-admin bootstrap, customer signup and signed access with revocable refresh sessions."""

import re
import secrets
import threading
import time
from collections import deque
from collections.abc import Callable, Coroutine
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.database import (
    REFRESH_SECONDS,
    ApplicationDatabase,
    RegistrationUnavailable,
    SetupAlreadyComplete,
)
from app.database import User as User

CURRENT_USER_ID: ContextVar[str | None] = ContextVar("current_user_id", default=None)
ISSUER = "humanizar-assistant"
AUDIENCE = "humanizar-api"
ACCESS_MINUTES = 30
REFRESH_COOKIE = "humanizar_refresh"
_passwords = PasswordHash.recommended()
_hash_slots = threading.BoundedSemaphore(2)
_dummy_hash = _passwords.hash(secrets.token_urlsafe(32))
_limiter_setup_lock = threading.Lock()


class PublicUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: str
    role: Literal["admin", "customer"]


class SessionResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: PublicUser


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def normalized_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Correo inválido.")
        return normalized

    @field_validator("name")
    @classmethod
    def stripped_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Nombre inválido.")
        return value.strip()


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=1, max_length=128)


class SafeAuthRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def safe_handler(request: Request) -> Response:
            try:
                return await original(request)
            except RequestValidationError:
                # FastAPI's default validation output can include plaintext password input.
                raise HTTPException(
                    422, "Datos inválidos. Revisá los campos y sus límites."
                ) from None

        return safe_handler


class LoginRateLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            if len(self._attempts) > 10000:
                self._attempts = {
                    address: attempts
                    for address, attempts in self._attempts.items()
                    if attempts and attempts[-1] > now - 300
                }
            attempts = self._attempts.setdefault(key, deque())
            while attempts and attempts[0] <= now - 300:
                attempts.popleft()
            if len(attempts) >= 10:
                raise HTTPException(
                    429, "Demasiados intentos. Probá más tarde.", headers={"Retry-After": "300"}
                )
            attempts.append(now)


router = APIRouter(prefix="/api/auth", tags=["authentication"], route_class=SafeAuthRoute)


def _database(request: Request) -> ApplicationDatabase:
    database: ApplicationDatabase = request.app.state.database
    return database


def hash_password(password: str) -> str:
    with _hash_slots:
        return _passwords.hash(password)


def _access(database: ApplicationDatabase, user: User, session_id: str) -> str:
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


def _cookie(request: Request, response: Response, token: str) -> None:
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


def _session(request: Request, response: Response, user: User) -> SessionResponse:
    database = _database(request)
    refresh = secrets.token_urlsafe(48)
    session_id = database.create_session(user.id, refresh)
    _cookie(request, response, refresh)
    return SessionResponse(
        access_token=_access(database, user, session_id), user=PublicUser.model_validate(user)
    )


def _unauthorized() -> HTTPException:
    return HTTPException(
        401, "No se pudo validar la sesión.", headers={"WWW-Authenticate": "Bearer"}
    )


def _claims(database: ApplicationDatabase, token: str) -> tuple[str, str]:
    if len(token) > 8192:
        raise _unauthorized()
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
            raise _unauthorized()
        return user_id, session_id
    except InvalidTokenError:
        raise _unauthorized() from None


def require_user(request: Request) -> User:
    authorization = request.headers.get("Authorization", "")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].casefold() != "bearer" or len(parts[1]) > 8192:
        raise _unauthorized()
    database = _database(request)
    user_id, session_id = _claims(database, parts[1])
    user = database.session_user(session_id, user_id)
    if user is None:
        raise _unauthorized()
    return user


def require_admin(request: Request) -> User:
    user = require_user(request)
    if user.role != "admin":
        raise HTTPException(403, "Se requiere una cuenta administradora.")
    return user


def _csrf(request: Request) -> None:
    if request.headers.get("X-Requested-With") != "Humanizar":
        raise HTTPException(403, "Solicitud de sesión no permitida.")


@router.get("/status")
def status(request: Request) -> dict[str, bool]:
    return {"setup_required": _database(request).setup_required()}


@router.post("/setup", response_model=SessionResponse)
def setup(payload: SignupRequest, request: Request, response: Response) -> SessionResponse:
    try:
        user = _database(request).bootstrap_admin(
            payload.name, payload.email, hash_password(payload.password.get_secret_value())
        )
    except SetupAlreadyComplete:
        raise HTTPException(409, "La configuración inicial ya está completa.") from None
    except ValueError:
        raise HTTPException(409, "No se pudo crear la cuenta.") from None
    return _session(request, response, user)


@router.post("/register", response_model=SessionResponse)
def register(payload: SignupRequest, request: Request, response: Response) -> SessionResponse:
    try:
        user = _database(request).register_customer(
            payload.name, payload.email, hash_password(payload.password.get_secret_value())
        )
    except RegistrationUnavailable:
        raise HTTPException(409, "La configuración inicial está pendiente.") from None
    except ValueError:
        raise HTTPException(409, "No se pudo crear la cuenta.") from None
    return _session(request, response, user)


@router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest, request: Request, response: Response) -> SessionResponse:
    with _limiter_setup_lock:
        if not hasattr(request.app.state, "auth_limiter"):
            request.app.state.auth_limiter = LoginRateLimiter()
        limiter: LoginRateLimiter = request.app.state.auth_limiter
    address = request.client.host if request.client else "unknown"
    limiter.check(address)
    user = _database(request).get_user_by_email(payload.email)
    with _hash_slots:
        try:
            correct = _passwords.verify(
                payload.password.get_secret_value(),
                user.password_hash if user is not None else _dummy_hash,
            )
        except Exception:
            correct = False
    if user is None or not correct:
        raise HTTPException(
            401, "Correo o contraseña inválidos.", headers={"WWW-Authenticate": "Bearer"}
        )
    return _session(request, response, user)


@router.post("/refresh", response_model=SessionResponse)
def refresh(request: Request, response: Response) -> SessionResponse:
    _csrf(request)
    previous = request.cookies.get(REFRESH_COOKIE, "")
    if not previous or len(previous) > 256:
        raise _unauthorized()
    replacement = secrets.token_urlsafe(48)
    database = _database(request)
    rotated = database.rotate_refresh(previous, replacement)
    if rotated is None:
        raise _unauthorized()
    user, session_id = rotated
    _cookie(request, response, replacement)
    return SessionResponse(
        access_token=_access(database, user, session_id), user=PublicUser.model_validate(user)
    )


@router.post("/logout", status_code=204)
def logout(request: Request) -> Response:
    _csrf(request)
    database = _database(request)
    previous = request.cookies.get(REFRESH_COOKIE, "")
    if previous and len(previous) <= 256:
        database.revoke_refresh(previous)
    authorization = request.headers.get("Authorization", "").split()
    if len(authorization) == 2 and authorization[0].casefold() == "bearer":
        try:
            user_id, session_id = _claims(database, authorization[1])
            database.revoke_session(session_id, user_id)
        except HTTPException:
            pass
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(
        REFRESH_COOKIE,
        path="/api/auth",
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
    )
    return response


@router.get("/me", response_model=PublicUser)
async def me(user: Annotated[User, Depends(require_user)]) -> PublicUser:
    return PublicUser.model_validate(user)
