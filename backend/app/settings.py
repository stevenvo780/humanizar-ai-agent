import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.company import HUMANIZAR_PRODUCTS, HUMANIZAR_QUESTIONS, ProductDefinition

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True
    )
    anthropic_api_key: SecretStr = SecretStr("")
    llm_mode: Literal["auto", "demo", "anthropic"] = "auto"
    anthropic_model: str = "claude-haiku-4-5"
    company_name: str = "Humanizar"
    company_description: str = "Software a medida y agentes de IA para operación empresarial."
    assistant_name: str = "Humanizar IA"
    company_website: str = Field(default="", max_length=500)
    company_suggested_questions: list[str] | None = Field(default=None, max_length=8)
    company_products: list[ProductDefinition] | None = Field(default=None, max_length=40)
    data_dir: Path = ROOT / "backend" / "data"
    seed_demo: bool = True
    knowledge_dir: Path | None = None
    auth_enabled: bool = True
    database_url: SecretStr = SecretStr("")
    database_schema: str = "lumen"
    jwt_secret: SecretStr = SecretStr("")
    auth_bootstrap_token: SecretStr = SecretStr("")
    embedding_provider: Literal["hash", "fastembed"] = "hash"
    fastembed_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    fastembed_threads: int = Field(default=2, ge=1, le=8)
    qdrant_url: str | None = None
    qdrant_api_key: SecretStr = SecretStr("")
    sandbox_url: str = "http://127.0.0.1:8001"
    mcp_enabled: bool = True
    lumen_api_url: str = "http://127.0.0.1:8000"
    lumen_api_token: SecretStr = SecretStr("")
    lumen_api_token_file: Path | None = None
    max_upload_mb: int = Field(default=15, ge=1, le=100)
    max_decompressed_mb: int = Field(default=40, ge=1, le=200)
    max_archive_files: int = Field(default=100, ge=1, le=500)
    max_zip_ratio: int = Field(default=100, ge=1, le=1000)
    max_agent_iterations: int = Field(default=5, ge=1, le=10)
    max_tool_calls: int = Field(default=8, ge=1, le=20)
    max_concurrent_chats: int = Field(default=4, ge=1, le=32)
    anthropic_timeout_seconds: float = Field(default=45, ge=1, le=120)
    max_output_tokens: int = Field(default=1500, ge=128, le=4096)
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:3000",
    ]

    @field_validator("database_schema")
    @classmethod
    def dedicated_schema(cls, value: str) -> str:
        if (
            not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", value)
            or value in {"public", "information_schema"}
            or value.startswith("pg_")
        ):
            raise ValueError("DATABASE_SCHEMA debe ser un schema dedicado válido.")
        return value

    @field_validator("company_website")
    @classmethod
    def public_website(cls, value: str) -> str:
        if not value:
            return ""
        try:
            parsed = urlsplit(value)
            valid = (
                parsed.scheme in {"https", "http"}
                and parsed.hostname
                and parsed.username is None
                and parsed.password is None
                and not parsed.fragment
                and (parsed.port is None or 1 <= parsed.port <= 65535)
                and not any(char.isspace() for char in value)
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("COMPANY_WEBSITE debe ser una URL pública HTTP(S) sin credenciales.")
        return value

    @field_validator("company_suggested_questions")
    @classmethod
    def bounded_questions(cls, values: list[str] | None) -> list[str] | None:
        if values is not None and any(not value.strip() or len(value) > 300 for value in values):
            raise ValueError("Las preguntas sugeridas deben tener entre 1 y 300 caracteres.")
        return [value.strip() for value in values] if values is not None else None

    @property
    def is_humanizar(self) -> bool:
        return self.company_name.strip().casefold() == "humanizar"

    @property
    def website(self) -> str | None:
        return self.company_website or ("https://humanizar.tech/" if self.is_humanizar else None)

    @property
    def suggested_questions(self) -> list[str]:
        if self.company_suggested_questions is not None:
            return list(self.company_suggested_questions)
        return list(HUMANIZAR_QUESTIONS) if self.is_humanizar else []

    @property
    def products(self) -> tuple[ProductDefinition, ...]:
        if self.company_products is not None:
            return tuple(self.company_products)
        return HUMANIZAR_PRODUCTS if self.is_humanizar else ()

    @field_validator("jwt_secret", "auth_bootstrap_token")
    @classmethod
    def private_secret(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value() and len(value.get_secret_value()) < 32:
            raise ValueError("Los secretos privados deben tener al menos 32 caracteres.")
        return value

    @model_validator(mode="after")
    def verify_mode(self) -> "Settings":
        if not self.is_humanizar:
            if "assistant_name" not in self.model_fields_set:
                self.assistant_name = "Lumen"
            if "company_description" not in self.model_fields_set:
                self.company_description = ""
        if self.llm_mode == "anthropic" and not self.anthropic_api_key.get_secret_value():
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_MODE=anthropic")
        return self

    @property
    def mode(self) -> Literal["demo", "anthropic"]:
        if self.llm_mode == "demo":
            return "demo"
        return "anthropic" if self.anthropic_api_key.get_secret_value() else "demo"

    @property
    def embedding_label(self) -> str:
        if self.embedding_provider == "hash":
            return "Vectores léxicos hash (sin descarga, no semánticos)"
        return f"FastEmbed semántico · {self.fastembed_model}"
