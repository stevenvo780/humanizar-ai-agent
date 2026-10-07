#!/usr/bin/env python3
"""Manage this project's isolated VPS stack without printing private configuration."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "compose.production.yaml"
PROJECT_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,62}\Z")
# Copied into images whose processes run as non-root users.
IMAGE_SOURCES = ("backend", "sandbox")


def read_private_environment(path: Path) -> dict[str, str]:
    """Read a bounded literal env file; error messages never include its contents."""
    if path.is_symlink():
        raise ValueError("Private environment must be a regular file, not a symlink.")
    resolved = path.resolve(strict=True)
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError("Keep the private environment outside the source checkout.")
    metadata = resolved.stat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 65536:
        raise ValueError("Private environment must be a regular file smaller than 64 KiB.")
    if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
        raise ValueError("Private environment must be owned by the current user with mode 0600.")
    environment: dict[str, str] = {}
    for line in resolved.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if not separator or not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
            raise ValueError("Use literal KEY=value lines without export or shell quoting.")
        if name in environment or any(ord(character) < 32 for character in value):
            raise ValueError("Duplicate environment keys and control characters are forbidden.")
        environment[name] = value
    return environment


def validate_environment(environment: dict[str, str]) -> None:
    """Require authenticated PostgreSQL with certificate and hostname verification."""
    database_url = environment.get("DATABASE_URL", "")
    try:
        database = urlsplit(database_url)
        port = database.port
        options = parse_qs(
            database.query, keep_blank_values=True, strict_parsing=True, max_num_fields=2
        )
        valid_database = (
            database.scheme in {"postgresql", "postgres", "postgresql+psycopg"}
            and database.hostname
            and database.username
            and database.password
            and database.path not in {"", "/"}
            and not database.fragment
            and (port is None or 1 <= port <= 65535)
            and set(options) == {"sslmode", "sslrootcert"}
            and options.get("sslmode") == ["verify-full"]
            and options.get("sslrootcert") == ["system"]
        )
    except ValueError:
        valid_database = False
    if not valid_database:
        raise ValueError("Production DATABASE_URL requires PostgreSQL, verify-full and system CA.")
    schema = environment.get("DATABASE_SCHEMA", "")
    if (
        not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", schema)
        or schema in {"public", "information_schema"}
        or schema.startswith("pg_")
    ):
        raise ValueError("Set a dedicated lowercase DATABASE_SCHEMA, such as lumen.")
    if environment.get("AUTH_ENABLED", "true").casefold() != "true":
        raise ValueError("Production authentication must remain enabled.")
    if environment.get("LLM_MODE", "auto") == "anthropic" and not environment.get(
        "ANTHROPIC_API_KEY"
    ):
        raise ValueError("Anthropic mode requires a private backend API key.")
    if len(environment.get("JWT_SECRET", "")) < 32:
        raise ValueError("Production requires JWT_SECRET with at least 32 characters.")
    if len(environment.get("AUTH_BOOTSTRAP_TOKEN", "")) < 32:
        raise ValueError("Production requires AUTH_BOOTSTRAP_TOKEN with at least 32 characters.")
    try:
        origins = json.loads(environment.get("CORS_ORIGINS", "[]"))
        if not isinstance(origins, list) or not origins:
            raise ValueError
        for origin in origins:
            if not isinstance(origin, str):
                raise ValueError
            parsed = urlsplit(origin)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError
    except (ValueError, TypeError):
        raise ValueError(
            "CORS_ORIGINS must be a JSON array of exact HTTPS frontend origins."
        ) from None


def unreadable_image_sources(root: Path = ROOT) -> list[str]:
    """Tracked image sources (and their folders) that a non-root container could not read.

    A restrictive umask during `git merge` (e.g. 077) writes files as 0600 and the API then
    fails at startup with PermissionError, so the check runs before any build.
    """
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--", *IMAGE_SOURCES],
        cwd=root,
        capture_output=True,
        check=True,
        timeout=60,
    )
    names = [name for name in listed.stdout.decode("utf-8").split("\0") if name]
    folders = {str(Path(name).parent) for name in names}
    unreadable = [name for name in names if not (root / name).stat().st_mode & stat.S_IROTH]
    unreadable += [
        folder
        for folder in sorted(folders)
        if (root / folder).stat().st_mode & (stat.S_IROTH | stat.S_IXOTH)
        != (stat.S_IROTH | stat.S_IXOTH)
    ]
    return unreadable


def run_quiet(command: list[str], environment: dict[str, str], *, timeout: int = 60) -> None:
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=timeout,
    )
    if result.returncode:
        raise ValueError("Docker operation failed; inspect diagnostics privately on the VPS.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["check", "up", "stop", "status"])
    parser.add_argument("--env-file", type=Path, required=True)
    # Legacy resource name of the deployed Compose project and its volume; renaming it would
    # start a new stack without the existing knowledge volume.
    parser.add_argument("--project", default="humanizar-ai-agent")
    parser.add_argument("--port", type=int, default=8087)
    args = parser.parse_args()
    if not PROJECT_PATTERN.fullmatch(args.project) or not 1024 <= args.port <= 65535:
        parser.error("Use a valid dedicated project name and a port from 1024 to 65535.")
    if shutil.which("docker") is None:
        print("Install Docker with Compose v2.30 or newer on the VPS.", file=sys.stderr)
        return 2
    try:
        private_environment = read_private_environment(args.env_file)
        if args.action in {"check", "up"}:
            validate_environment(private_environment)
            unreadable = unreadable_image_sources()
            if unreadable:
                print(
                    f"{len(unreadable)} checkout paths are not world-readable (restrictive "
                    "umask?). Fix with: git ls-files -z | xargs -0 chmod a+r",
                    file=sys.stderr,
                )
                return 1
        # Compose interpolation receives paths and public settings only. The raw env_file
        # passes backend secrets directly to the API container, never to the sandbox.
        compose_environment = dict(os.environ)
        compose_environment.update(
            LUMEN_PRODUCTION_ENV=str(args.env_file.resolve(strict=True)),
            LUMEN_API_PORT=str(args.port),
            COMPOSE_DISABLE_ENV_FILE="1",
        )
        command = ["docker", "compose", "--project-name", args.project, "-f", str(COMPOSE)]
        run_quiet(command + ["config", "--quiet"], compose_environment)
        if args.action == "check":
            print(
                "Production configuration valid. No containers or external requests were started."
            )
            return 0
        run_quiet(["docker", "info"], compose_environment)
        if args.action == "up":
            print(
                "Building and starting the dedicated project; private diagnostics are suppressed."
            )
            run_quiet(
                command + ["up", "--build", "--detach", "--wait", "--wait-timeout", "240"],
                compose_environment,
                timeout=1800,
            )
            print("API and sandbox healthy. Configure/verify the HTTPS proxy separately.")
        elif args.action == "stop":
            run_quiet(command + ["stop"], compose_environment)
            print("Dedicated API and sandbox stopped; volumes and PostgreSQL data preserved.")
        else:
            result = subprocess.run(
                command + ["ps", "--format", "json"],
                cwd=ROOT,
                env=compose_environment,
                capture_output=True,
                check=True,
                timeout=60,
            )
            for line in result.stdout.decode("utf-8").splitlines():
                item = json.loads(line)
                print(f"{item['Service']}: {item['State']} / {item.get('Health', 'unknown')}")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError, UnicodeError, KeyError):
        # Exceptions from parsers/processes can embed credential-bearing configuration.
        print(
            "Production action could not complete. Verify file ownership/mode, literal env format, "
            "PostgreSQL verify-full/system CA, HTTPS origins and Docker privately.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
