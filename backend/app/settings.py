from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )
    anthropic_api_key: SecretStr = SecretStr("")
    llm_mode: Literal["auto", "demo", "anthropic"] = "auto"
    anthropic_model: str = "claude-haiku-4-5"
    company_name: str = "Forma"
    company_description: str = "Plataforma SaaS de operaciones para equipos, Madrid, desde 2019."
    assistant_name: str = "Lumen"
    data_dir: Path = ROOT / "backend" / "data"
    seed_demo: bool = True
    knowledge_dir: Path | None = None
    auth_enabled: bool = True
    embedding_provider: Literal["hash", "fastembed"] = "hash"
    fastembed_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    fastembed_threads: int = Field(default=2, ge=1, le=8)
    qdrant_url: str | None = None
    qdrant_api_key: SecretStr = SecretStr("")
    sandbox_url: str = "http://127.0.0.1:8001"
    mcp_enabled: bool = True
    lumen_api_url: str = "http://127.0.0.1:8000"
    max_upload_mb: int = Field(default=15, ge=1, le=100)
    max_decompressed_mb: int = Field(default=40, ge=1, le=200)
    max_archive_files: int = Field(default=100, ge=1, le=500)
    max_zip_ratio: int = Field(default=100, ge=1, le=1000)
    max_agent_iterations: int = Field(default=5, ge=1, le=10)
    max_tool_calls: int = Field(default=8, ge=1, le=20)
    anthropic_timeout_seconds: float = Field(default=45, ge=1, le=120)
    max_output_tokens: int = Field(default=1500, ge=128, le=4096)
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:3000",
    ]

    @model_validator(mode="after")
    def verify_mode(self) -> "Settings":
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
