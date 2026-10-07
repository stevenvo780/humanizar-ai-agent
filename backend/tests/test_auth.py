import secrets
import sqlite3
import stat
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Annotated, Any

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth import (
    AUDIENCE,
    ISSUER,
    REFRESH_COOKIE,
    PublicUser,
    hash_password,
    require_admin,
    router,
)
from app.database import ApplicationDatabase, SetupAlreadyComplete, User

CSRF = {"X-Requested-With": "Humanizar"}


@pytest.fixture
def database(tmp_path: Path) -> Iterator[ApplicationDatabase]:
    value = ApplicationDatabase(tmp_path)
    try:
        yield value
    finally:
        value.close()


def create_test_app(database: ApplicationDatabase) -> FastAPI:
    app = FastAPI()
    app.state.database = database
    app.include_router(router)

    @app.get("/private/admin")
    def admin(user: Annotated[User, Depends(require_admin)]) -> PublicUser:
        return PublicUser.model_validate(user)

    return app


@pytest.fixture
def client(database: ApplicationDatabase) -> Iterator[TestClient]:
    with TestClient(create_test_app(database)) as value:
        yield value


def signup(
    client: TestClient, email: str = "owner@example.test", route: str = "setup"
) -> tuple[str, dict[str, Any]]:
    password = secrets.token_urlsafe(24)
    result = client.post(
        f"/api/auth/{route}", json={"name": "Example", "email": email, "password": password}
    )
    assert result.status_code == 200
    return password, result.json()


def bearer(session: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": "Bearer " + str(session["access_token"])}


def test_setup_registration_login_and_private_roles(
    client: TestClient, database: ApplicationDatabase
) -> None:
    assert client.get("/api/auth/status").json() == {"setup_required": True}
    assert (
        client.post(
            "/api/auth/register",
            json={
                "name": "Customer",
                "email": "c@example.test",
                "password": secrets.token_urlsafe(24),
            },
        ).status_code
        == 409
    )
    password, administrator = signup(client, " OWNER@EXAMPLE.TEST ")
    assert administrator["token_type"] == "bearer"
    assert administrator["user"]["role"] == "admin"
    assert administrator["user"]["email"] == "owner@example.test"
    assert "password" not in administrator["user"]
    persisted = database.get_user_by_email("owner@example.test")
    assert persisted is not None and persisted.password_hash.startswith("$argon2id$")
    assert password not in repr(persisted)
    assert client.get("/api/auth/status").json() == {"setup_required": False}
    assert client.get("/api/auth/me", headers=bearer(administrator)).status_code == 200
    assert client.get("/private/admin", headers=bearer(administrator)).status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    repeated = client.post(
        "/api/auth/setup",
        json={
            "name": "Other",
            "email": "other@example.test",
            "password": secrets.token_urlsafe(24),
        },
    )
    assert repeated.status_code == 409
    _, customer = signup(client, "customer@example.test", "register")
    assert customer["user"]["role"] == "customer"
    assert client.get("/private/admin", headers=bearer(customer)).status_code == 403
    login = client.post(
        "/api/auth/login", json={"email": "OWNER@EXAMPLE.TEST", "password": password}
    )
    assert login.status_code == 200 and login.json()["user"]["id"] == administrator["user"]["id"]
    bad = client.post(
        "/api/auth/login",
        json={"email": "owner@example.test", "password": secrets.token_urlsafe(24)},
    )
    missing = client.post(
        "/api/auth/login",
        json={"email": "unknown@example.test", "password": secrets.token_urlsafe(24)},
    )
    assert bad.status_code == missing.status_code == 401
    assert bad.json() == missing.json()


def test_bootstrap_race_across_connections(tmp_path: Path) -> None:
    first, second = ApplicationDatabase(tmp_path), ApplicationDatabase(tmp_path)
    password_hash = hash_password(secrets.token_urlsafe(24))

    def create(db: ApplicationDatabase, email: str) -> str:
        try:
            return db.bootstrap_admin("Owner", email, password_hash).id
        except SetupAlreadyComplete:
            return "already-complete"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(create, db, email)
                for db, email in [(first, "first@example.test"), (second, "second@example.test")]
            ]
            outcomes = [future.result() for future in futures]
        assert outcomes.count("already-complete") == 1
        with sqlite3.connect(tmp_path / "application.sqlite3") as connection:
            assert (
                connection.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
                == 1
            )
    finally:
        first.close()
        second.close()


@pytest.mark.parametrize(("route", "role"), [("setup", "admin"), ("register", "customer")])
def test_six_character_password_boundary_for_setup_and_registration(
    client: TestClient,
    database: ApplicationDatabase,
    route: str,
    role: str,
) -> None:
    if route == "register":
        signup(client)
    payload = {"name": "Boundary test", "email": "boundary@example.test"}
    rejected = client.post(f"/api/auth/{route}", json={**payload, "password": "12345"})
    assert rejected.status_code == 422 and "12345" not in rejected.text
    assert database.get_user_by_email(payload["email"]) is None

    # This explicit boundary value is used only in an isolated synthetic test database.
    accepted = client.post(f"/api/auth/{route}", json={**payload, "password": "123456"})
    assert accepted.status_code == 200
    assert accepted.json()["user"]["role"] == role
    persisted = database.get_user_by_email(payload["email"])
    assert persisted is not None and persisted.password_hash.startswith("$argon2id$")
    login = client.post("/api/auth/login", json={"email": payload["email"], "password": "123456"})
    assert login.status_code == 200
    assert login.json()["user"]["id"] == accepted.json()["user"]["id"]


@pytest.mark.parametrize(
    "invalid",
    [
        "signature",
        "expired",
        "issuer",
        "audience",
        "missing_sid",
        "wrong_algorithm",
        "wrong_subject",
    ],
)
def test_jwt_claim_validation(
    client: TestClient, database: ApplicationDatabase, invalid: str
) -> None:
    _, session = signup(client)
    payload = jwt.decode(
        session["access_token"],
        database.jwt_secret,
        algorithms=["HS256"],
        audience=AUDIENCE,
        issuer=ISSUER,
    )
    key = database.jwt_secret
    algorithm = "HS256"
    if invalid == "signature":
        key = secrets.token_bytes(32)
    elif invalid == "expired":
        payload["exp"] = int(time.time()) - 10
    elif invalid == "issuer":
        payload["iss"] = "another-issuer"
    elif invalid == "audience":
        payload["aud"] = "another-audience"
    elif invalid == "missing_sid":
        del payload["sid"]
    elif invalid == "wrong_algorithm":
        algorithm = "HS384"
        key = secrets.token_bytes(48)
    elif invalid == "wrong_subject":
        payload["sub"] = "nonexistent"
    token = jwt.encode(payload, key, algorithm=algorithm)
    result = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert result.status_code == 401
    assert result.json()["detail"] == "No se pudo validar la sesión."


def test_refresh_rotation_csrf_logout_and_cookie_flags(client: TestClient, tmp_path: Path) -> None:
    _, initial = signup(client)
    cookie = client.cookies.get(REFRESH_COOKIE)
    assert cookie is not None
    assert client.post("/api/auth/refresh").status_code == 403
    refreshed = client.post("/api/auth/refresh", headers=CSRF)
    assert refreshed.status_code == 200
    current = refreshed.json()
    assert client.cookies.get(REFRESH_COOKIE) != cookie
    flags = refreshed.headers["set-cookie"].casefold()
    assert "httponly" in flags and "samesite=strict" in flags and "path=/api/auth" in flags
    assert "secure" not in flags
    assert client.get("/api/auth/me", headers=bearer(initial)).status_code == 401
    assert client.get("/api/auth/me", headers=bearer(current)).status_code == 200
    replay = client.post(
        "/api/auth/refresh", headers={**CSRF, "Cookie": f"{REFRESH_COOKIE}={cookie}"}
    )
    assert replay.status_code == 401
    assert client.post("/api/auth/logout").status_code == 403
    logout = client.post("/api/auth/logout", headers={**CSRF, **bearer(current)})
    assert logout.status_code == 204 and "max-age=0" in logout.headers["set-cookie"].casefold()
    assert client.get("/api/auth/me", headers=bearer(current)).status_code == 401
    assert client.post("/api/auth/refresh", headers=CSRF).status_code == 401
    with sqlite3.connect(tmp_path / "application.sqlite3") as connection:
        hashes = [row[0] for row in connection.execute("SELECT refresh_hash FROM sessions")]
    assert cookie not in hashes and all(len(value) == 64 for value in hashes)


def test_stale_logout_revokes_rotated_family(client: TestClient) -> None:
    _, initial = signup(client)
    previous = client.cookies.get(REFRESH_COOKIE)
    refreshed = client.post("/api/auth/refresh", headers=CSRF)
    assert refreshed.status_code == 200
    current = refreshed.json()
    replacement = client.cookies.get(REFRESH_COOKIE)
    stale_logout = client.post(
        "/api/auth/logout",
        headers={**CSRF, **bearer(initial), "Cookie": f"{REFRESH_COOKIE}={previous}"},
    )
    assert stale_logout.status_code == 204
    assert client.get("/api/auth/me", headers=bearer(current)).status_code == 401
    assert (
        client.post(
            "/api/auth/refresh", headers={**CSRF, "Cookie": f"{REFRESH_COOKIE}={replacement}"}
        ).status_code
        == 401
    )


def test_https_cookie_secure(database: ApplicationDatabase) -> None:
    with TestClient(create_test_app(database), base_url="https://testserver") as client:
        result = client.post(
            "/api/auth/setup",
            json={
                "name": "Owner",
                "email": "owner@example.test",
                "password": secrets.token_urlsafe(24),
            },
        )
        assert result.status_code == 200 and "secure" in result.headers["set-cookie"].casefold()


def test_validation_never_echoes_password(client: TestClient) -> None:
    password = secrets.token_urlsafe(110)
    result = client.post(
        "/api/auth/setup",
        json={"name": "Owner", "email": "owner@example.test", "password": password},
    )
    assert result.status_code == 422 and password not in result.text
    weak = secrets.token_hex(3)[:5]
    result = client.post(
        "/api/auth/setup", json={"name": "Owner", "email": "owner@example.test", "password": weak}
    )
    assert result.status_code == 422 and weak not in result.text
    result = client.post(
        "/api/auth/setup",
        json={
            "name": "Owner",
            "email": "owner@example.test",
            "password": secrets.token_urlsafe(24),
            "role": "admin",
        },
    )
    assert result.status_code == 422


def test_login_rate_limit(client: TestClient) -> None:
    for _ in range(10):
        result = client.post(
            "/api/auth/login",
            json={"email": "unknown@example.test", "password": secrets.token_urlsafe(24)},
        )
        assert result.status_code == 401
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "unknown@example.test", "password": secrets.token_urlsafe(24)},
        ).status_code
        == 429
    )


def test_successful_login_does_not_reset_rate_budget(client: TestClient) -> None:
    password, _session = signup(client)
    for _ in range(8):
        assert (
            client.post(
                "/api/auth/login",
                json={"email": "unknown@example.test", "password": secrets.token_urlsafe(24)},
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/auth/login", json={"email": "owner@example.test", "password": password}
        ).status_code
        == 200
    )
    # Only failures consume the budget: two more failures fit, the eleventh is rejected.
    for _ in range(2):
        assert (
            client.post(
                "/api/auth/login",
                json={"email": "unknown@example.test", "password": secrets.token_urlsafe(24)},
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "unknown@example.test", "password": secrets.token_urlsafe(24)},
        ).status_code
        == 429
    )


def test_refresh_expiry_is_checked_in_database(client: TestClient, tmp_path: Path) -> None:
    _, session = signup(client)
    with sqlite3.connect(tmp_path / "application.sqlite3") as connection:
        connection.execute("UPDATE sessions SET expires_at=?", (time.time() - 1,))
    assert client.get("/api/auth/me", headers=bearer(session)).status_code == 401
    assert client.post("/api/auth/refresh", headers=CSRF).status_code == 401


def test_authentication_survives_database_restart(tmp_path: Path) -> None:
    database = ApplicationDatabase(tmp_path)
    with TestClient(create_test_app(database)) as first:
        _, session = signup(first)
        refresh = first.cookies.get(REFRESH_COOKIE)
    database.close()
    reopened = ApplicationDatabase(tmp_path)
    try:
        with TestClient(create_test_app(reopened)) as second:
            assert second.get("/api/auth/me", headers=bearer(session)).status_code == 200
            assert (
                second.post(
                    "/api/auth/refresh", headers={**CSRF, "Cookie": f"{REFRESH_COOKIE}={refresh}"}
                ).status_code
                == 200
            )
    finally:
        reopened.close()


def test_session_family_migration_preserves_existing_session(tmp_path: Path) -> None:
    database = ApplicationDatabase(tmp_path)
    user = database.bootstrap_admin(
        "Owner", "owner@example.test", hash_password(secrets.token_urlsafe(24))
    )
    refresh = secrets.token_urlsafe(48)
    session_id = database.create_session(user.id, refresh)
    database.close()
    with sqlite3.connect(tmp_path / "application.sqlite3") as connection:
        connection.execute("DROP INDEX sessions_family")
        connection.execute("ALTER TABLE sessions DROP COLUMN family_id")
    reopened = ApplicationDatabase(tmp_path)
    try:
        assert reopened.session_user(session_id, user.id) is not None
        rotated = reopened.rotate_refresh(refresh, secrets.token_urlsafe(48))
        assert rotated is not None
        reopened.revoke_session(session_id, user.id)
        assert reopened.session_user(rotated[1], user.id) is None
    finally:
        reopened.close()


def test_conversation_isolation_and_persistence(tmp_path: Path) -> None:
    database = ApplicationDatabase(tmp_path)
    password_hash = hash_password(secrets.token_urlsafe(24))
    administrator = database.bootstrap_admin("Owner", "owner@example.test", password_hash)
    customer = database.register_customer("Customer", "customer@example.test", password_hash)
    identifier = database.create_conversation(administrator.id, None, "Project question")
    assert database.create_conversation(administrator.id, identifier, "Ignored title") == identifier
    operations: list[Callable[[], object]] = [
        lambda: database.create_conversation(customer.id, identifier, "other"),
        lambda: database.conversation_history(customer.id, identifier),
        lambda: database.save_exchange(customer.id, identifier, "forbidden", {"answer": "no"}),
        lambda: database.delete_conversation(customer.id, identifier),
    ]
    for operation in operations:
        with pytest.raises(PermissionError):
            operation()
    response = {
        "answer": "A grounded answer",
        "sources": [{"document_name": "source"}],
        "trace": [{"tool": "search_knowledge"}],
    }
    database.save_exchange(administrator.id, identifier, "A question", response)
    assert database.conversation_history(administrator.id, identifier) == [
        {"role": "user", "content": "A question"},
        {"role": "assistant", "content": "A grounded answer"},
    ]
    assert database.list_conversations(customer.id) == []
    database.close()
    reopened = ApplicationDatabase(tmp_path)
    try:
        conversations = reopened.list_conversations(administrator.id)
        assert len(conversations) == 1
        assert conversations[0]["id"] == conversations[0]["sessionId"] == identifier
        assert conversations[0]["title"] == "Project question"
        assert conversations[0]["messages"][1]["sources"] == response["sources"]
        assert conversations[0]["messages"][1]["trace"] == response["trace"]
        assert isinstance(conversations[0]["updatedAt"], int)
        assert reopened.delete_conversation(administrator.id, identifier)
        assert not reopened.delete_conversation(administrator.id, identifier)
        assert reopened.list_conversations(administrator.id) == []
    finally:
        reopened.close()


def test_private_master_secret_and_legacy_config_survive_restart(tmp_path: Path) -> None:
    value = "legacy-ciphertext-placeholder"
    database = ApplicationDatabase(tmp_path)
    database._db.execute("INSERT INTO config VALUES ('anthropic_api_key', ?)", (value,))
    initial_signing = database.jwt_secret
    database.close()
    metadata = (tmp_path / ".application-secret").stat()
    assert stat.S_IMODE(metadata.st_mode) == 0o600
    reopened = ApplicationDatabase(tmp_path)
    try:
        assert reopened.jwt_secret == initial_signing
        assert (
            reopened._db.execute(
                "SELECT value FROM config WHERE key='anthropic_api_key'"
            ).fetchone()[0]
            == value
        )
    finally:
        reopened.close()


def test_secret_symlink_rejected(tmp_path: Path) -> None:
    target = tmp_path / "outside"
    target.write_bytes(secrets.token_bytes(32))
    target.chmod(0o600)
    (tmp_path / ".application-secret").symlink_to(target)
    with pytest.raises(OSError):
        ApplicationDatabase(tmp_path)
