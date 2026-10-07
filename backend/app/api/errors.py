"""Exception handlers: stable, non-leaking error bodies for the whole API."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.agent.company_agent import AgentFailure
from app.persistence.contracts import PersistenceUnavailable


def register_exception_handlers(api: FastAPI) -> None:
    @api.exception_handler(AgentFailure)
    async def agent_error(_request: Request, exc: AgentFailure) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": exc.message, "code": exc.code})

    @api.exception_handler(PersistenceUnavailable)
    async def persistence_error(_request: Request, _exc: PersistenceUnavailable) -> JSONResponse:
        return JSONResponse(
            status_code=503, content={"detail": "El almacenamiento no está disponible."}
        )

    @api.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        # Validation payloads may contain passwords or a rejected provider credential.
        return JSONResponse(
            status_code=422, content={"detail": "Los datos enviados no son válidos."}
        )

    @api.exception_handler(Exception)
    async def safe_error(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500, content={"detail": "No se pudo completar la operación."}
        )
