"""Public service metadata: health, configuration, company profile and docs redirects."""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.api.dependencies import RegistryDep, SettingsDep
from app.api.schemas import CompanyInfo, HealthResponse, HealthTools
from app.core.security import redact

router = APIRouter(tags=["system"])


@router.get("/docs", include_in_schema=False)
def legacy_docs() -> RedirectResponse:
    return RedirectResponse("/api/docs", status_code=307)


@router.get("/redoc", include_in_schema=False)
def legacy_redoc() -> RedirectResponse:
    return RedirectResponse("/api/redoc", status_code=307)


@router.get("/api/health", response_model=HealthResponse)
async def health(config: SettingsDep, registry: RegistryDep) -> HealthResponse:
    return HealthResponse(
        mode=config.mode,
        model=config.anthropic_model,
        embedding=config.embedding_label,
        tools=HealthTools(sandbox=await registry.sandbox_available(), mcp=config.mcp_enabled),
    )


@router.get("/api/config")
def public_config(config: SettingsDep) -> dict[str, Any]:
    return {
        "company_name": redact(config.company_name),
        "company_description": redact(config.company_description),
        "assistant_name": redact(config.assistant_name),
        "model": config.anthropic_model,
        "mode": config.mode,
        "embedding": config.embedding_label,
        "max_upload_mb": config.max_upload_mb,
    }


@router.get("/api/company", response_model=CompanyInfo, response_model_exclude_none=True)
def company(config: SettingsDep) -> CompanyInfo:
    return CompanyInfo(
        company_name=redact(config.company_name),
        company_description=redact(config.company_description),
        assistant_name=redact(config.assistant_name),
        website=redact(config.website) if config.website else None,
        suggested_questions=None
        if config.suggested_questions is None
        else [redact(item) for item in config.suggested_questions],
    )
