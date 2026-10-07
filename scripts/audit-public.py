#!/usr/bin/env python3
"""Reject private/runtime paths in the Git index without opening their contents."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path, PurePosixPath

BLOCKED_DIRECTORIES = frozenset(
    {
        ".codex",
        ".vercel",
        ".venv",
        "venv",
        "node_modules",
        "data",
        "material",
        "artifacts",
        "logs",
        "credentials",
        "secrets",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "coverage",
        "playwright-report",
        "test-results",
    }
)
BLOCKED_SUFFIXES = (".token", ".pem", ".key", ".p12", ".pfx", ".sqlite", ".sqlite3", ".db", ".log")
BLOCKED_CLAUDE = frozenset(
    {"sessions", "history", "cache", "debug", "projects", "todos", "statsig", "telemetry"}
)


def private_path(name: str, mode: str = "100644") -> bool:
    path = PurePosixPath(name)
    parts = tuple(part.casefold() for part in path.parts)
    if path.is_absolute() or ".." in path.parts or mode not in {"100644", "100755"}:
        return True
    if any(part in BLOCKED_DIRECTORIES for part in parts):
        return True
    if parts == (".specify", "feature.json"):
        return True
    if path.name.casefold().startswith((".application-secret", "settings.local", "credentials.")):
        return True
    if path.name.casefold().endswith(BLOCKED_SUFFIXES + (".sqlite3-wal", ".sqlite3-shm")):
        return True
    if any(part.startswith(".env") for part in parts) and name != ".env.example":
        return True
    if ".claude" in parts:
        return any(part in BLOCKED_CLAUDE or part.startswith("history") for part in parts)
    return False


def audit_index(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--stage", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    rejected: list[str] = []
    for entry in result.stdout.split(b"\0"):
        if not entry:
            continue
        metadata, filename = entry.split(b"\t", 1)
        mode = metadata.split(b" ", 1)[0].decode("ascii")
        name = filename.decode("utf-8", errors="surrogateescape")
        if private_path(name, mode):
            rejected.append(name)
    return rejected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        rejected = audit_index(args.root)
    except (OSError, subprocess.CalledProcessError, ValueError):
        print("Publication audit could not inspect the Git index.")
        return 2
    if rejected:
        print("Publication audit rejected private paths (contents were not read):")
        for name in rejected:
            print(f"  {name}")
        return 1
    print("Publication path audit passed; no private or runtime paths tracked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
