"""Private operator CLI. Credentials arrive via terminal prompts or bounded stdin JSON."""

import argparse
import asyncio
import getpass
import json
import os
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.accounts.auth import SignupRequest, hash_password
from app.core.settings import Settings
from app.mcp.auth import MCPAPIClient, default_session_path
from app.persistence.contracts import PersistenceUnavailable
from app.persistence.factory import create_identity_store
from app.persistence.sqlite import SetupAlreadyComplete


async def _mcp_login(origin: str, filename: Path) -> None:
    client = MCPAPIClient(origin)
    try:
        email = input("Email: ")
        password = getpass.getpass("Contraseña: ")
        await client.login(email, password, filename)
    finally:
        await client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Administración privada de Lumen")
    parser.add_argument("command", choices=["create-admin", "mcp-login"])
    parser.add_argument(
        "--api-url", default=os.environ.get("LUMEN_API_URL", "http://127.0.0.1:8000")
    )
    parser.add_argument("--token-file", type=Path, default=default_session_path())
    parser.add_argument(
        "--stdin-json", action="store_true", help="Leer name, email y password por stdin"
    )
    options = parser.parse_args(argv)
    if options.command == "mcp-login":
        if options.stdin_json:
            parser.error("mcp-login solicita credenciales interactivamente.")
        try:
            asyncio.run(_mcp_login(options.api_url, options.token_file))
        except (ValueError, OSError, EOFError):
            print(
                "No se pudo iniciar la sesión MCP. Revisa el acceso y el origen API en privado.",
                file=sys.stderr,
            )
            return 1
        print(
            "Sesión MCP guardada de forma privada. El servidor MCP la usa por defecto; "
            "si elegiste otra ruta configura LUMEN_API_TOKEN_FILE."
        )
        return 0
    try:
        if options.stdin_json:
            value = sys.stdin.read(8193)
            if len(value) > 8192:
                raise ValueError
            payload: Any = json.loads(value)
        else:
            name, email = input("Nombre: "), input("Email: ")
            password = getpass.getpass("Contraseña: ")
            if getpass.getpass("Repetir contraseña: ") != password:
                raise ValueError
            payload = {"name": name, "email": email, "password": password}
        signup = SignupRequest.model_validate(payload)
        database = create_identity_store(Settings())
        try:
            database.bootstrap_admin(
                signup.name, signup.email, hash_password(signup.password.get_secret_value())
            )
        finally:
            database.close()
    except SetupAlreadyComplete:
        print("La configuración inicial ya está completa.", file=sys.stderr)
        return 1
    except (ValidationError, ValueError, OSError, EOFError, PersistenceUnavailable):
        print(
            "No se pudo crear el administrador. Revisá los datos y la configuración privada.",
            file=sys.stderr,
        )
        return 1
    print("Administrador creado. Iniciá sesión desde la aplicación.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
