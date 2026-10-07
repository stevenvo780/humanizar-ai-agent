"""``/api/auth``: first-admin setup, customer signup, login, refresh rotation and logout."""

import secrets
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from app.accounts.dependencies import identity_store, require_user
from app.accounts.passwords import hash_password, verify_password
from app.accounts.rate_limit import request_limiter
from app.accounts.schemas import LoginRequest, PublicUser, SessionResponse, SignupRequest
from app.accounts.tokens import (
    REFRESH_COOKIE,
    access_claims,
    clear_refresh_cookie,
    issue_access,
    set_refresh_cookie,
    unauthorized,
)
from app.core.settings import Settings
from app.persistence.contracts import PersistenceUnavailable
from app.persistence.models import RegistrationUnavailable, SetupAlreadyComplete, User


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
            except PersistenceUnavailable:
                raise HTTPException(503, "El almacenamiento no está disponible.") from None

        return safe_handler


router = APIRouter(prefix="/api/auth", tags=["authentication"], route_class=SafeAuthRoute)


def _session(request: Request, response: Response, user: User) -> SessionResponse:
    database = identity_store(request)
    refresh = secrets.token_urlsafe(48)
    session_id = database.create_session(user.id, refresh)
    set_refresh_cookie(request, response, refresh)
    return SessionResponse(
        access_token=issue_access(database, user, session_id),
        user=PublicUser.model_validate(user),
    )


def _csrf(request: Request) -> None:
    if request.headers.get("X-Requested-With") != "Humanizar":
        raise HTTPException(403, "Solicitud de sesión no permitida.")


@router.get("/status")
def status(request: Request) -> dict[str, bool]:
    return {"setup_required": identity_store(request).setup_required()}


@router.post("/setup", response_model=SessionResponse)
def setup(payload: SignupRequest, request: Request, response: Response) -> SessionResponse:
    settings: Settings | None = getattr(request.app.state, "settings", None)
    expected = settings.auth_bootstrap_token.get_secret_value() if settings is not None else ""
    supplied = request.headers.get("X-Bootstrap-Token", "")
    request_limiter(request).check(
        "setup:" + (request.client.host if request.client else "unknown")
    )
    if expected and not secrets.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(403, "La configuración inicial requiere autorización privada.")
    try:
        user = identity_store(request).bootstrap_admin(
            payload.name, payload.email, hash_password(payload.password.get_secret_value())
        )
    except SetupAlreadyComplete:
        raise HTTPException(409, "La configuración inicial ya está completa.") from None
    except ValueError:
        raise HTTPException(409, "No se pudo crear la cuenta.") from None
    return _session(request, response, user)


@router.post("/register", response_model=SessionResponse)
def register(payload: SignupRequest, request: Request, response: Response) -> SessionResponse:
    # Public signup hashes with Argon2: bound it per client like failed logins.
    request_limiter(request).check(
        "register:" + (request.client.host if request.client else "unknown")
    )
    try:
        user = identity_store(request).register_customer(
            payload.name, payload.email, hash_password(payload.password.get_secret_value())
        )
    except RegistrationUnavailable:
        raise HTTPException(409, "La configuración inicial está pendiente.") from None
    except ValueError:
        raise HTTPException(409, "No se pudo crear la cuenta.") from None
    return _session(request, response, user)


@router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest, request: Request, response: Response) -> SessionResponse:
    limiter = request_limiter(request)
    address = request.client.host if request.client else "unknown"
    # Only failed logins count, so a presenter can sign in and out without a lockout.
    limiter.check(address, record=False)
    user = identity_store(request).get_user_by_email(payload.email)
    correct = verify_password(
        payload.password.get_secret_value(), user.password_hash if user is not None else None
    )
    if user is None or not correct:
        limiter.record(address)
        raise HTTPException(
            401, "Correo o contraseña inválidos.", headers={"WWW-Authenticate": "Bearer"}
        )
    return _session(request, response, user)


@router.post("/refresh", response_model=SessionResponse)
def refresh(request: Request, response: Response) -> SessionResponse:
    _csrf(request)
    previous = request.cookies.get(REFRESH_COOKIE, "")
    if not previous or len(previous) > 256:
        raise unauthorized()
    replacement = secrets.token_urlsafe(48)
    database = identity_store(request)
    rotated = database.rotate_refresh(previous, replacement)
    if rotated is None:
        raise unauthorized()
    user, session_id = rotated
    set_refresh_cookie(request, response, replacement)
    return SessionResponse(
        access_token=issue_access(database, user, session_id),
        user=PublicUser.model_validate(user),
    )


@router.post("/logout", status_code=204)
def logout(request: Request) -> Response:
    _csrf(request)
    database = identity_store(request)
    previous = request.cookies.get(REFRESH_COOKIE, "")
    if previous and len(previous) <= 256:
        database.revoke_refresh(previous)
    authorization = request.headers.get("Authorization", "").split()
    if len(authorization) == 2 and authorization[0].casefold() == "bearer":
        try:
            user_id, session_id = access_claims(database, authorization[1])
            database.revoke_session(session_id, user_id)
        except HTTPException:
            pass
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    clear_refresh_cookie(request, response)
    return response


@router.get("/me", response_model=PublicUser)
async def me(user: Annotated[User, Depends(require_user)]) -> PublicUser:
    return PublicUser.model_validate(user)
