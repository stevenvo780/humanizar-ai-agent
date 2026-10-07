import io
import json
import secrets

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from app import manage
from app.database import ApplicationDatabase
from app.main import create_app
from app.persistence_factory import create_business_store, create_identity_store
from app.postgres import connection_options
from app.settings import Settings


@pytest.mark.parametrize(
    "schema", ["public", "information_schema", "pg_private", "x.y", "x;drop", "Upper", ""]
)
def test_schema_rejects_shared_or_unqualified_names(schema: str, settings: Settings) -> None:
    with pytest.raises(ValidationError):
        type(settings)(database_schema=schema, llm_mode="demo")


def test_remote_tls_is_verified_and_connection_parameters_are_bounded() -> None:
    url, options = connection_options("postgresql://example@database.example.invalid/lumen")
    assert url.drivername == "postgresql+psycopg"
    assert not url.query
    assert options["sslmode"] == "verify-full"
    assert options["sslrootcert"] == "system"
    assert options["connect_timeout"] == 5
    assert "statement_timeout=10000" in str(options["options"])
    _, explicit = connection_options(
        "postgresql://example@database.example.invalid/lumen?sslmode=verify-full&sslrootcert=%2Fca.pem"
    )
    assert explicit["sslrootcert"] == "/ca.pem"


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///example.sqlite3",
        "postgresql://example@database.example.invalid/lumen?sslmode=disable",
        "postgresql://example@database.example.invalid/lumen?sslmode=require",
        "postgresql://example@localhost/lumen?host=database.example.invalid&sslmode=disable",
        "postgresql:///lumen",
        "postgresql://example@localhost/lumen?options=-c%20search_path%3Dpublic",
        "postgresql://example@localhost:0/lumen?sslmode=disable",
        "postgresql://example@localhost:-1/lumen?sslmode=disable",
        "postgresql://example@localhost:65536/lumen?sslmode=disable",
        "postgresql://example@localhost:invalid/lumen?sslmode=disable",
        "postgresql://example@localhost/lumen?sslmode=disable&sslmode=disable",
        "postgresql://example@localhost/lumen?options=",
        "postgresql://example@localhost/lumen?sslmode=",
        "postgresql://example@localhost/lumen?sslrootcert=",
        "postgresql://example@localhost/lumen?sslmode=disable&sslmode=",
        "postgresql://example@localhost/lumen?sslmode=verify-full&sslrootcert=system&options=",
        "postgresql://example@localhost/lumen?sslmode=verify-full&sslrootcert=system&sslrootcert=",
    ],
)
def test_invalid_connections_report_only_fixed_errors(url: str) -> None:
    with pytest.raises(ValueError) as error:
        connection_options(url)
    assert url not in str(error.value)
    assert "DATABASE_URL" in str(error.value)


def test_local_test_database_can_disable_tls() -> None:
    _, options = connection_options("postgresql://example@127.0.0.1/lumen?sslmode=disable")
    assert options["sslmode"] == "disable"
    assert "sslrootcert" not in options


def test_settings_secret_validation_never_echoes_input(settings: Settings) -> None:
    private_value = secrets.token_hex(8)
    with pytest.raises(ValidationError) as error:
        type(settings)(jwt_secret=SecretStr(private_value), llm_mode="demo")
    assert private_value not in str(error.value)


def test_sqlite_factory_preserves_legacy_signing_key(settings: Settings) -> None:
    database = create_identity_store(settings)
    assert isinstance(database, ApplicationDatabase)
    original_key = database.jwt_secret
    database.close()
    reopened = create_identity_store(settings)
    assert reopened.jwt_secret == original_key
    business = create_business_store(settings, reopened)
    business.close()
    reopened.close()
    alternate = settings.model_copy(update={"jwt_secret": SecretStr(secrets.token_urlsafe(48))})
    changed = create_identity_store(alternate)
    assert changed.jwt_secret == alternate.jwt_secret.get_secret_value().encode()
    changed.close()
    restored = create_identity_store(settings)
    assert restored.jwt_secret == original_key
    restored.close()


def test_private_bootstrap_header_required_before_account_creation(settings: Settings) -> None:
    protection = secrets.token_urlsafe(40)
    private_password = secrets.token_urlsafe(20)
    config = settings.model_copy(
        update={"auth_enabled": True, "auth_bootstrap_token": SecretStr(protection)}
    )
    application = create_app(config)
    payload = {
        "name": "Synthetic owner",
        "email": "owner@example.test",
        "password": private_password,
    }
    with TestClient(application) as client:
        assert client.post("/api/auth/setup", json=payload).status_code == 403
        wrong = client.post(
            "/api/auth/setup", json=payload, headers={"X-Bootstrap-Token": "incorrect"}
        )
        assert wrong.status_code == 403
        assert application.state.database.setup_required()
        created = client.post(
            "/api/auth/setup", json=payload, headers={"X-Bootstrap-Token": protection}
        )
        assert created.status_code == 200
        assert created.json()["user"]["role"] == "admin"
        assert protection not in created.text and private_password not in created.text
        assert not application.state.database.setup_required()
        assert (
            client.post(
                "/api/auth/setup", json=payload, headers={"X-Bootstrap-Token": protection}
            ).status_code
            == 409
        )


@pytest.mark.parametrize("stdin", [False, True])
def test_admin_cli_does_not_echo_credentials(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stdin: bool,
) -> None:
    password = secrets.token_urlsafe(32)
    monkeypatch.setattr(manage, "Settings", lambda: settings)
    if stdin:
        monkeypatch.setattr(
            "sys.stdin",
            io.StringIO(
                json.dumps(
                    {"name": "Operator", "email": "operator@example.test", "password": password}
                )
            ),
        )
    else:
        values = iter(["Operator", "operator@example.test"])
        monkeypatch.setattr("builtins.input", lambda _prompt: next(values))
        monkeypatch.setattr("app.manage.getpass.getpass", lambda _prompt: password)
    assert manage.main(["create-admin", *(["--stdin-json"] if stdin else [])]) == 0
    output = capsys.readouterr()
    assert password not in output.out + output.err
    assert "operator@example.test" not in output.out + output.err
    database = create_identity_store(settings)
    try:
        assert not database.setup_required()
        assert database.get_user_by_email("operator@example.test") is not None
    finally:
        database.close()


@pytest.mark.parametrize("payload", ["not JSON", json.dumps({"password": "invalid"}), "x" * 8193])
def test_admin_cli_rejects_invalid_stdin_without_echo(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    payload: str,
) -> None:
    monkeypatch.setattr(manage, "Settings", lambda: settings)
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    assert manage.main(["create-admin", "--stdin-json"]) == 1
    assert payload not in capsys.readouterr().err
