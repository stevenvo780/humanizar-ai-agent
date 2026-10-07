"""Loaders and synthetic fixtures shared by the deployment helper tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
DATABASE = (
    "postgresql://fixture:fixture@database.example.com/lumen?sslmode=verify-full&sslrootcert=system"
)
HEADER_FIXTURE = "fixture-header-value-" + "a" * 32


def load_helper(filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        filename.replace("-", "_"), ROOT / "scripts" / filename
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Deployment helper could not be loaded.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def environment() -> dict[str, str]:
    return {
        "DATABASE_URL": DATABASE,
        "DATABASE_SCHEMA": "lumen",
        "CORS_ORIGINS": '["https://frontend.example.com"]',
        "AUTH_ENABLED": "true",
        "JWT_SECRET": "fixture-signing-value-" + "a" * 32,
        "AUTH_BOOTSTRAP_TOKEN": "fixture-bootstrap-value-" + "b" * 32,
    }
