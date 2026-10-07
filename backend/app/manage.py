"""Private operator CLI. Credentials arrive via terminal prompts or bounded stdin JSON."""

import argparse
import getpass
import json
import sys
from typing import Any

from pydantic import ValidationError

from app.auth import SignupRequest, hash_password
from app.database import SetupAlreadyComplete
from app.persistence import PersistenceUnavailable
from app.persistence_factory import create_identity_store
from app.settings import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Administración privada de Lumen")
    parser.add_argument("command", choices=["create-admin"])
    parser.add_argument(
        "--stdin-json", action="store_true", help="Leer name, email y password por stdin"
    )
    options = parser.parse_args(argv)
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
