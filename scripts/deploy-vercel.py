#!/usr/bin/env python3
"""Validate Vercel routing or deploy using server-only environment configuration."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def validate_origin(origin: str) -> str:
    try:
        parsed = urlsplit(origin)
        host = parsed.hostname or ""
        port = parsed.port
        canonical = f"https://{host}" + (f":{port}" if port not in {None, 443} else "")
        valid = (
            parsed.scheme == "https"
            and bool(host)
            and len(host) <= 253
            and re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", host)
            and not parsed.username
            and not parsed.password
            and parsed.path in {"", "/"}
            and not parsed.query
            and not parsed.fragment
            and not host.endswith(
                (
                    ".localhost",
                    ".local",
                    ".internal",
                    ".lan",
                    ".home",
                    ".test",
                    ".invalid",
                    ".example",
                    ".onion",
                    ".arpa",
                )
            )
            and origin in {canonical, f"{canonical}/"}
        )
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            valid = False
        if port is not None and not 1 <= port <= 65535:
            valid = False
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("API_ORIGIN must be a public HTTPS origin without credentials or a path.")
    return canonical


def linked_project(checkout: Path) -> tuple[str, str]:
    path = checkout / ".vercel" / "project.json"
    if (
        path.parent.is_symlink()
        or path.is_symlink()
        or not path.is_file()
        or path.stat().st_size > 65536
    ):
        raise ValueError("Link the Vercel project from the repository root first.")
    metadata = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("Invalid local Vercel project link.")
    project_id = metadata.get("projectId", "")
    organization_id = metadata.get("orgId", "")
    if (
        not isinstance(project_id, str)
        or not re.fullmatch(r"prj_[A-Za-z0-9]{1,100}", project_id)
        or not isinstance(organization_id, str)
        or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", organization_id)
    ):
        raise ValueError("Invalid local Vercel project identifiers.")
    return project_id, organization_id


def run_private(command: list[str], *, input_value: str | None = None) -> None:
    result = subprocess.run(
        command,
        cwd=ROOT,
        input=input_value,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=1800,
    )
    if result.returncode:
        raise ValueError("Vercel operation failed; inspect deployment diagnostics privately.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate locally without deploying")
    parser.add_argument(
        "--production", action="store_true", help="deploy production instead of preview"
    )
    parser.add_argument(
        "--configure-env", action="store_true", help="add API_ORIGIN and protected ORIGIN_SECRET"
    )
    parser.add_argument(
        "--update-env",
        action="store_true",
        help="explicitly replace those existing Vercel variables",
    )
    args = parser.parse_args()
    if args.update_env and not args.configure_env:
        parser.error("--update-env requires --configure-env.")
    try:
        origin = validate_origin(os.environ.get("API_ORIGIN", ""))
        origin_secret = os.environ.get("ORIGIN_SECRET", "")
        if not re.fullmatch(r"[!-~]{32,512}", origin_secret):
            raise ValueError(
                "ORIGIN_SECRET requires 32–512 printable ASCII characters without spaces."
            )
        if "VITE_ORIGIN_SECRET" in os.environ or "VITE_ANTHROPIC_API_KEY" in os.environ:
            raise ValueError("Private credentials cannot use public VITE_ variables.")
        if not (FRONTEND / "vercel.ts").is_file():
            raise ValueError("The versioned frontend/vercel.ts routing configuration is missing.")
        if args.check:
            print("Vercel environment shape valid; no API, login or deployment requests were made.")
            return 0
        vercel = shutil.which("vercel")
        if vercel is None:
            raise ValueError("Install Vercel CLI and authenticate/link this frontend separately.")
        project_id, organization_id = linked_project(ROOT)
        target = "production" if args.production else "preview"
        if args.configure_env:
            endpoint = f"/v10/projects/{project_id}/env"
            if args.update_env:
                endpoint += "?upsert=true"
            for name, value, sensitivity in (
                ("API_ORIGIN", origin, "encrypted"),
                ("ORIGIN_SECRET", origin_secret, "sensitive"),
            ):
                payload = json.dumps(
                    {"key": name, "value": value, "type": sensitivity, "target": [target]}
                )
                # API avoids the CLI's preview branch prompt. Values are stdin only.
                run_private(
                    [
                        vercel,
                        "api",
                        endpoint,
                        "--method",
                        "POST",
                        "--input",
                        "-",
                        "--silent",
                        "--header",
                        "Content-Type: application/json",
                        "--scope",
                        organization_id,
                    ],
                    input_value=payload,
                )
        command = [
            vercel,
            "deploy",
            "--yes",
            "--build-env",
            f"API_ORIGIN={origin}",
            "--scope",
            organization_id,
        ]
        if args.production:
            command.append("--prod")
        run_private(command)
        print("Vercel deployment completed. Check its URL and routing in the project dashboard.")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError):
        print(
            "Vercel action could not complete. Verify public HTTPS API_ORIGIN, private "
            "ORIGIN_SECRET, CLI login/project link and protected target variables privately.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
