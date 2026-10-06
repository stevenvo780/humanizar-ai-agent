import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "audit_public", Path(__file__).resolve().parents[1] / "audit-public.py"
)
assert SPEC is not None and SPEC.loader is not None
auditor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(auditor)


@pytest.mark.parametrize(
    "filename",
    [
        ".env",
        "backend/.env.production",
        "data/application.sqlite3",
        ".codex/agent-parity-manifest.json",
        "backend/private.key",
        ".application-secret",
        ".claude/settings.local.json",
        ".claude/sessions/session.json",
        "material/customer.md",
        "artifacts/customer.png",
        "frontend/node_modules/pkg/package.json",
        "credentials/account.txt",
    ],
)
def test_rejects_private_paths_without_reading_them(filename: str) -> None:
    assert auditor.private_path(filename)


@pytest.mark.parametrize(
    "filename",
    [
        ".env.example",
        "config/env.example",
        ".claude/settings.json",
        ".mcp.json",
        ".claude/skills/speckit-plan/SKILL.md",
        ".github/workflows/quality.yml",
        "backend/knowledge/humanizar/humanizar-empresa.md",
        "frontend/src/DocsPage.tsx",
    ],
)
def test_accepts_public_source(filename: str) -> None:
    assert not auditor.private_path(filename)


def test_rejects_symlinks_and_submodules() -> None:
    assert auditor.private_path("frontend/src/link.ts", "120000")
    assert auditor.private_path("external/private", "160000")
