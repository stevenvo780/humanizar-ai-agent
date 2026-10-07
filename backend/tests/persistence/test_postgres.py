"""Real probes use ONLY the explicitly supplied isolated loopback test database."""

import os
import secrets
import threading
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
import test_authenticated_app as contract_tests
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, event, func, inspect, select
from sqlalchemy.schema import CreateSchema, DropSchema

from app.business.requests import BusinessValidationError
from app.core.settings import Settings
from app.main import create_app
from app.persistence.contracts import PersistenceUnavailable
from app.persistence.factory import create_business_store, create_identity_store
from app.persistence.postgres import (
    PostgresApplicationDatabase,
    PostgresBusinessStore,
    connection_options,
)
from app.persistence.sqlite import SetupAlreadyComplete


@pytest.fixture
def postgres_settings(settings: Settings) -> Iterator[Settings]:
    value = os.environ.get("LUMEN_TEST_DATABASE_URL", "")
    if not value:
        pytest.skip("LUMEN_TEST_DATABASE_URL not set; isolated PostgreSQL integration unavailable")
    url, options = connection_options(value)
    if url.host not in {"127.0.0.1", "localhost", "::1"} or url.database != "lumen_test":
        pytest.fail("Integration tests require the dedicated loopback lumen_test database")
    schema = "lumen_test_" + uuid.uuid4().hex
    config = settings.model_copy(
        update={
            "database_url": SecretStr(value),
            "database_schema": schema,
            "jwt_secret": SecretStr(secrets.token_urlsafe(48)),
        }
    )
    try:
        yield config
    finally:
        engine = create_engine(url, connect_args=options, hide_parameters=True)
        try:
            with engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True, if_exists=True))
        finally:
            engine.dispose()


@pytest.fixture
def postgres(postgres_settings: Settings) -> Iterator[PostgresApplicationDatabase]:
    database = PostgresApplicationDatabase(postgres_settings)
    try:
        yield database
    finally:
        database.close()


def users(database: PostgresApplicationDatabase) -> tuple[str, str]:
    admin = database.bootstrap_admin("Admin", "admin@example.test", "synthetic-hash")
    customer = database.register_customer("Customer", "customer@example.test", "synthetic-hash")
    return admin.id, customer.id


def test_postgres_persists_users_sessions_history_and_requests(
    postgres: PostgresApplicationDatabase, postgres_settings: Settings
) -> None:
    owner, customer = users(postgres)
    session = postgres.create_session(owner, secrets.token_urlsafe(40))
    conversation = postgres.create_conversation(owner, "synthetic-conversation", "Title")
    postgres.save_exchange(
        owner,
        conversation,
        "Question",
        {"answer": "Answer [S1]", "sources": [{"id": "s1"}], "trace": [{"status": "ok"}]},
    )
    business = create_business_store(postgres_settings, postgres)
    assert isinstance(business, PostgresBusinessStore)
    request = business.create_request(
        owner, "support", {"subject": "Example", "description": "Synthetic"}, "confirmation"
    )
    business.close()
    assert postgres.session_user(session, owner) is not None
    reopened = create_identity_store(postgres_settings)
    try:
        assert reopened.get_user(owner) is not None
        assert reopened.session_user(session, owner) is not None
        assert reopened.jwt_secret == postgres.jwt_secret
        assert reopened.conversation_history(owner, conversation) == [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer [S1]"},
        ]
        saved = reopened.list_conversations(owner)
        assert saved[0]["messages"][1]["sources"] == [{"id": "s1"}]
        assert saved[0]["messages"][1]["trace"] == [{"status": "ok"}]
        assert saved[0]["sessionId"] == conversation
        assert isinstance(saved[0]["updatedAt"], int)
        assert reopened.list_conversations(customer) == []
        other_business = create_business_store(postgres_settings, reopened)
        assert other_business.list_requests(owner) == [request]
        assert other_business.list_requests(customer) == []
        assert other_business.list_all_requests()[0]["user_id"] == owner
        other_business.close()
        with pytest.raises(PermissionError):
            reopened.conversation_history(customer, conversation)
        with pytest.raises(PermissionError):
            reopened.delete_conversation(customer, conversation)
        with pytest.raises(PermissionError):
            reopened.create_conversation(customer, conversation, "Other title")
        assert reopened.delete_conversation(owner, conversation)
        assert not reopened.delete_conversation(owner, conversation)
    finally:
        reopened.close()


def test_bootstrap_two_instances_has_one_winner(
    postgres: PostgresApplicationDatabase, postgres_settings: Settings
) -> None:
    other = PostgresApplicationDatabase(postgres_settings)
    barrier = threading.Barrier(2)

    def setup(database: PostgresApplicationDatabase, email: str) -> str:
        barrier.wait(timeout=5)
        try:
            return database.bootstrap_admin("Owner", email, "synthetic-hash").role
        except SetupAlreadyComplete:
            return "already-configured"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(setup, postgres, "one@example.test")
            second = pool.submit(setup, other, "two@example.test")
            assert sorted([first.result(timeout=10), second.result(timeout=10)]) == [
                "admin",
                "already-configured",
            ]
    finally:
        other.close()


def test_refresh_two_instances_has_one_winner_and_stale_logout_revokes_family(
    postgres: PostgresApplicationDatabase, postgres_settings: Settings
) -> None:
    owner, customer = users(postgres)
    previous = secrets.token_urlsafe(40)
    old_session = postgres.create_session(owner, previous)
    other = PostgresApplicationDatabase(postgres_settings)
    barrier = threading.Barrier(2)

    def rotate(database: PostgresApplicationDatabase) -> tuple[str, str] | None:
        replacement = secrets.token_urlsafe(40)
        barrier.wait(timeout=5)
        rotated = database.rotate_refresh(previous, replacement)
        return (rotated[1], replacement) if rotated is not None else None

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = pool.submit(rotate, postgres), pool.submit(rotate, other)
            winners = [
                value
                for value in [first.result(timeout=10), second.result(timeout=10)]
                if value is not None
            ]
        assert len(winners) == 1
        identifier, refresh = winners[0]
        assert other.session_user(identifier, owner) is not None
        other.revoke_session(old_session, customer)
        assert postgres.session_user(identifier, owner) is not None
        other.revoke_session(old_session, owner)
        assert postgres.session_user(identifier, owner) is None
        assert postgres.rotate_refresh(refresh, secrets.token_urlsafe(40)) is None
    finally:
        other.close()


def test_logout_waits_for_inflight_refresh_then_revokes_replacement(
    postgres: PostgresApplicationDatabase,
    postgres_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner, _ = users(postgres)
    previous, replacement = secrets.token_urlsafe(40), secrets.token_urlsafe(40)
    old_session = postgres.create_session(owner, previous)
    other = PostgresApplicationDatabase(postgres_settings)
    entered, release = threading.Event(), threading.Event()
    original = postgres._insert_session

    def blocked_insert(*args: Any, **kwargs: Any) -> str:
        entered.set()
        assert release.wait(timeout=5)
        return original(*args, **kwargs)

    monkeypatch.setattr(postgres, "_insert_session", blocked_insert)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            rotated = pool.submit(postgres.rotate_refresh, previous, replacement)
            assert entered.wait(timeout=5)
            logout = pool.submit(other.revoke_session, old_session, owner)
            release.set()
            winner = rotated.result(timeout=10)
            logout.result(timeout=10)
        assert winner is not None
        assert other.session_user(winner[1], owner) is None
    finally:
        release.set()
        other.close()


def test_business_idempotency_two_instances_and_ownership(
    postgres: PostgresApplicationDatabase, postgres_settings: Settings
) -> None:
    owner, customer = users(postgres)
    other = PostgresApplicationDatabase(postgres_settings)
    first, second = PostgresBusinessStore(postgres), PostgresBusinessStore(other)
    details = {"subject": "Example", "description": "Synthetic"}
    barrier = threading.Barrier(2)

    def create(store: PostgresBusinessStore) -> dict[str, Any]:
        barrier.wait(timeout=5)
        return store.create_request(owner, "support", details, "confirmed-action")

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = pool.submit(create, first), pool.submit(create, second)
            assert a.result(timeout=10) == b.result(timeout=10)
        assert len(first.list_requests(owner)) == 1
        with pytest.raises(BusinessValidationError):
            second.create_request(
                owner, "support", details | {"description": "Different"}, "confirmed-action"
            )
        second.create_request(customer, "support", details, "confirmed-action")
        assert len(first.list_requests(customer)) == 1
    finally:
        other.close()


def test_schema_rejects_existing_unrelated_tables_without_modification(
    postgres_settings: Settings,
) -> None:
    url, options = connection_options(postgres_settings.database_url.get_secret_value())
    engine = create_engine(url, connect_args=options, hide_parameters=True)
    unrelated = Table(
        "unrelated",
        MetaData(schema=postgres_settings.database_schema),
        Column("id", Integer, primary_key=True),
    )
    try:
        with engine.begin() as connection:
            connection.execute(CreateSchema(postgres_settings.database_schema))
            unrelated.create(connection)
            connection.execute(unrelated.insert().values(id=42))
        with pytest.raises(ValueError, match="otra aplicación"):
            PostgresApplicationDatabase(postgres_settings)
        with engine.begin() as connection:
            assert set(
                inspect(connection).get_table_names(schema=postgres_settings.database_schema)
            ) == {"unrelated"}
            assert connection.execute(select(unrelated.c.id)).scalar_one() == 42
    finally:
        engine.dispose()


def test_postgres_factory_does_not_open_or_migrate_legacy_sqlite(
    postgres_settings: Settings, tmp_path: Path
) -> None:
    sentinel = tmp_path / "application.sqlite3"
    sentinel.write_bytes(b"synthetic opaque legacy sentinel")
    config = postgres_settings.model_copy(update={"data_dir": tmp_path})
    database = create_identity_store(config)
    try:
        assert isinstance(database, PostgresApplicationDatabase)
        assert sentinel.read_bytes() == b"synthetic opaque legacy sentinel"
        assert not (tmp_path / ".application-secret").exists()
    finally:
        database.close()


def test_postgres_api_login_history_and_business_are_compatible(
    postgres_settings: Settings,
) -> None:
    config = postgres_settings.model_copy(update={"auth_enabled": True})
    with TestClient(create_app(config)) as client:
        password = secrets.token_urlsafe(24)
        session = client.post(
            "/api/auth/setup",
            json={"name": "Owner", "email": "owner@example.test", "password": password},
        )
        assert session.status_code == 200
        headers = {"Authorization": "Bearer " + str(session.json()["access_token"])}
        assert client.get("/api/conversations", headers=headers).json() == {"conversations": []}
        assert client.get("/api/requests", headers=headers).json() == {"requests": []}
        login = client.post(
            "/api/auth/login", json={"email": "owner@example.test", "password": password}
        )
        assert login.status_code == 200
        refreshed = client.post("/api/auth/refresh", headers={"X-Requested-With": "Humanizar"})
        assert refreshed.status_code == 200
        assert (
            client.post("/api/auth/logout", headers={"X-Requested-With": "Humanizar"}).status_code
            == 204
        )
        invalidated = {"Authorization": "Bearer " + str(refreshed.json()["access_token"])}
        assert client.get("/api/conversations", headers=invalidated).status_code == 401


def test_postgres_connection_error_is_sanitized(
    postgres_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy.exc import OperationalError

    secret = secrets.token_urlsafe(32)
    database = PostgresApplicationDatabase(postgres_settings)

    def unavailable() -> Any:
        raise OperationalError("select", {}, Exception(secret))

    try:
        monkeypatch.setattr(database.engine, "begin", unavailable)
        with pytest.raises(PersistenceUnavailable) as error:
            database.setup_required()
        assert secret not in str(error.value)
        assert postgres_settings.database_url.get_secret_value() not in str(error.value)
    finally:
        database.close()


def test_postgres_reconnects_after_its_own_idle_connection_is_terminated(
    postgres: PostgresApplicationDatabase, postgres_settings: Settings
) -> None:
    with postgres.transaction() as connection:
        owned_backend: int = int(connection.execute(select(func.pg_backend_pid())).scalar_one())
    url, options = connection_options(postgres_settings.database_url.get_secret_value())
    controller = create_engine(url, connect_args=options, hide_parameters=True)
    try:
        with controller.begin() as connection:
            assert connection.execute(select(func.pg_terminate_backend(owned_backend))).scalar_one()
        assert postgres.setup_required()
        with postgres.transaction() as connection:
            assert connection.execute(select(func.pg_backend_pid())).scalar_one() != owned_backend
    finally:
        controller.dispose()


def test_postgres_authenticated_history_contract(postgres_settings: Settings) -> None:
    contract_tests.test_authenticated_history_is_server_owned_and_isolated(postgres_settings)


def test_postgres_authenticated_business_contract(postgres_settings: Settings) -> None:
    contract_tests.test_customer_confirmations_persist_once_and_do_not_expose_other_requests(
        postgres_settings
    )


def test_postgres_customer_pages_are_public_and_preserve_roles(
    postgres: PostgresApplicationDatabase,
) -> None:
    administrator, first_id = users(postgres)
    second = postgres.register_customer("  Second  ", " SECOND@EXAMPLE.TEST ", "synthetic-hash")
    assert postgres.get_customer(administrator) is None
    assert postgres.get_customer("missing") is None
    public = postgres.get_customer(second.id)
    assert public is not None and public.role == "customer"
    assert public.name == "Second" and public.email == "second@example.test"
    assert public.created_at.tzinfo is not None
    assert not hasattr(public, "password_hash")
    first, total = postgres.list_customers(limit=1, offset=0)
    last, same_total = postgres.list_customers(limit=1, offset=1)
    assert total == same_total == 2
    assert {customer.id for customer in first + last} == {first_id, second.id}
    assert postgres.list_customers(offset=10**30) == ([], 2)
    with pytest.raises(ValueError):
        postgres.list_customers(limit=101)
    with pytest.raises(ValueError):
        postgres.register_customer("Duplicate", " second@example.test ", "synthetic-hash")
    assert postgres.list_customers()[1] == 2


def test_postgres_customer_creation_api_preserves_admin_session(
    postgres_settings: Settings,
) -> None:
    with TestClient(
        create_app(postgres_settings.model_copy(update={"auth_enabled": True}))
    ) as client:
        password = secrets.token_urlsafe(24)
        admin = client.post(
            "/api/auth/setup",
            json={"name": "Owner", "email": "owner@example.test", "password": password},
        ).json()
        headers = {"Authorization": "Bearer " + str(admin["access_token"])}
        payload = {
            "name": "Customer",
            "email": " CUSTOMER@EXAMPLE.TEST ",
            "password": secrets.token_urlsafe(24),
        }
        response = client.post("/api/admin/customers", json=payload, headers=headers)
        assert response.status_code == 201 and "set-cookie" not in response.headers
        assert response.json()["customer"]["role"] == "customer"
        assert response.json()["customer"]["email"] == "customer@example.test"
        assert client.get("/api/auth/me", headers=headers).json()["id"] == admin["user"]["id"]
        listed = client.get("/api/admin/customers", params={"limit": 1}, headers=headers).json()
        assert listed == {
            "customers": [response.json()["customer"]],
            "total": 1,
            "limit": 1,
            "offset": 0,
        }
        assert client.post("/api/admin/customers", json=payload, headers=headers).status_code == 409
        assert (
            client.post(
                "/api/admin/customers", json=payload | {"role": "admin"}, headers=headers
            ).status_code
            == 422
        )


def test_postgres_customer_page_snapshot_survives_concurrent_registration(
    postgres: PostgresApplicationDatabase, postgres_settings: Settings
) -> None:
    _, previous = users(postgres)
    other = PostgresApplicationDatabase(postgres_settings)
    inserted = False

    def insert_after_count(
        _connection: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        nonlocal inserted
        if "count(*)" in statement and ".users" in statement and not inserted:
            inserted = True
            other.register_customer("During", "during@example.test", "synthetic-hash")

    event.listen(postgres.engine, "after_cursor_execute", insert_after_count)
    try:
        customers, total = postgres.list_customers()
        assert inserted
        assert total == 1 and [customer.id for customer in customers] == [previous]
        assert postgres.list_customers()[1] == 2
        # The snapshot policy applies to this method, never later writes or sessions.
        with postgres.transaction() as connection:
            assert (
                connection.exec_driver_sql("SHOW transaction_isolation").scalar_one()
                == "read committed"
            )
            assert connection.exec_driver_sql("SHOW transaction_read_only").scalar_one() == "off"
    finally:
        event.remove(postgres.engine, "after_cursor_execute", insert_after_count)
        other.close()
