#!/usr/bin/env python3
"""Create a portable source ZIP from an explicit allowlist, never runtime files."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

ROOT_FILES = {
    "README.md",
    "CLAUDE.md",
    "AGENTS.md",
    "LICENSE",
    "LICENSE.md",
    ".env.example",
    ".gitignore",
    ".mcp.json",
    ".editorconfig",
    ".dockerignore",
    "compose.yml",
    "compose.yaml",
    "compose.local.yaml",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Makefile",
    "package.json",
    "package-lock.json",
    "pyproject.toml",
    "uv.lock",
}
ALLOWED_TREES = {
    ".github",
    "config",
    "backend",
    "frontend",
    "sandbox",
    "scripts",
    "docs",
    "specs",
    ".specify",
}
ALLOWED_SUFFIXES = {
    ".py",
    ".sh",
    ".toml",
    ".lock",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".csv",
    ".html",
    ".css",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".ico",
    ".woff",
    ".woff2",
}
BLOCKED_PARTS = {
    ".git",
    ".codex",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "dist",
    "build",
    "coverage",
    "data",
    "logs",
    "material",
    "artifacts",
    "secrets",
    "credentials",
    "playwright-report",
    "test-results",
    "settings.local.json",
}


def allowed_path(relative: Path) -> bool:
    parts = relative.parts
    if relative.as_posix() == ".specify/feature.json":
        return False
    if any(part.casefold() in BLOCKED_PARTS for part in parts):
        return False
    if any(
        (part.casefold().startswith(".env") and relative.as_posix() != ".env.example")
        or part.casefold().endswith((".pem", ".key", ".token", ".p12", ".pfx", ".log"))
        or part.casefold().startswith(("credentials.", "secrets."))
        for part in parts
    ):
        return False
    if len(parts) == 1:
        return parts[0] in ROOT_FILES
    if relative.as_posix() in {"config/env.example", "frontend/nginx.conf"}:
        return True
    if parts[0] in {".claude", ".agents"}:
        return relative.as_posix() == ".claude/settings.json" or (
            len(parts) >= 3
            and parts[1] == "skills"
            and relative.suffix.casefold() in {".md", ".yaml", ".yml"}
        )
    return (
        parts[0] in ALLOWED_TREES
        and (
            relative.suffix.casefold() in ALLOWED_SUFFIXES
            or relative.name in {"Dockerfile", ".dockerignore", ".gitignore", ".prettierignore"}
        )
        and relative.name != ".npmrc"
    )


def build_package(root: Path, destination: Path) -> int:
    # Exclusive mode protects existing user work and prevents accidental replacement.
    count = 0
    with zipfile.ZipFile(
        destination, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as archive:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if (
                not path.is_file()
                or path.is_symlink()
                or not allowed_path(relative)
                or any(parent.is_symlink() for parent in path.parents if parent != root)
            ):
                continue
            archive.write(path, arcname=f"Lumen/{relative.as_posix()}")
            count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=Path("Lumen-source.zip"))
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    try:
        count = build_package(root, args.output)
    except (OSError, ValueError):
        print(
            "Packaging failed: output exists or destination is unavailable.",
            file=sys.stderr,
        )
        return 1
    print(f"Packaged {count} source files in {args.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
