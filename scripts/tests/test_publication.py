import importlib.util
import subprocess
import zipfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "audit_public", Path(__file__).resolve().parents[1] / "audit-public.py"
)
assert SPEC is not None and SPEC.loader is not None
auditor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(auditor)

PACKAGER_SPEC = importlib.util.spec_from_file_location(
    "source_packager", Path(__file__).resolve().parents[1] / "package.py"
)
assert PACKAGER_SPEC is not None and PACKAGER_SPEC.loader is not None
packager = importlib.util.module_from_spec(PACKAGER_SPEC)
PACKAGER_SPEC.loader.exec_module(packager)


@pytest.mark.parametrize(
    "filename",
    [
        ".env",
        "backend/.env.production",
        "backend/.env.example",
        "backend/.env.private/.env.example",
        "data/application.sqlite3",
        ".codex/agent-parity-manifest.json",
        "frontend/.vercel/project.json",
        "backend/private.key",
        ".application-secret",
        ".claude/settings.local.json",
        ".claude/sessions/session.json",
        ".CLAUDE/Sessions/session.json",
        ".specify/feature.json",
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
        "backend/knowledge/softop/faq-10-como-cierro-caja-al-final-del-dia.md",
        "frontend/src/features/docs/DocsPage.tsx",
    ],
)
def test_accepts_public_source(filename: str) -> None:
    assert not auditor.private_path(filename)


def test_rejects_symlinks_and_submodules() -> None:
    assert auditor.private_path("frontend/src/link.ts", "120000")
    assert auditor.private_path("external/private", "160000")


def test_audit_rejects_private_files_forced_into_git_index(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True, capture_output=True)
    filenames = [".env.example", "config/env.example", ".CLAUDE/Sessions/session.json"]
    for filename in filenames:
        target = tmp_path / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("synthetic fixture\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "--force", "--", *filenames],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    assert auditor.audit_index(tmp_path) == [".CLAUDE/Sessions/session.json"]


def test_packager_allowlist_and_no_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    allowed = [
        "README.md",
        "CLAUDE.md",
        ".mcp.json",
        "compose.local.yaml",
        "compose.production.yaml",
        ".vercelignore",
        ".claude/settings.json",
        ".claude/skills/speckit-specify/SKILL.md",
        ".agents/skills/speckit-specify/SKILL.md",
        ".github/workflows/quality.yml",
        "config/env.example",
        "config/production.env.example",
        "frontend/nginx.conf",
        "frontend/.vercelignore",
        ".env.example",
        "backend/app/main.py",
        "backend/uv.lock",
        ".specify/templates/spec-template.md",
    ]
    blocked = [
        ".env",
        "backend/.env.production",
        "config/production.env",
        "backend/data/database.json",
        "frontend/node_modules/pkg/index.js",
        ".vercel/project.json",
        "frontend/.vercel/project.json",
        ".claude/settings.local.json",
        ".specify/feature.json",
        ".git/config",
        "backend/secrets/token.txt",
    ]
    for filename in allowed + blocked:
        path = source / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("example", encoding="utf-8")
    (source / "backend/app/link.py").symlink_to(source / ".env")
    output = tmp_path / "portable source.zip"
    assert packager.build_package(source, output) == len(allowed)
    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == {f"Lumen/{name}" for name in allowed}
    with pytest.raises(FileExistsError):
        packager.build_package(source, output)
