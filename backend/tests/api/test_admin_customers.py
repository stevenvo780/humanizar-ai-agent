import secrets
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.accounts.auth import REFRESH_COOKIE
from app.core.settings import Settings
from app.main import create_app
from app.persistence.sqlite import ApplicationDatabase


def create_account(client: TestClient, route: str, email: str) -> dict[str, Any]:
    response = client.post(
        route,
        json={"name": "Synthetic account", "email": email, "password": secrets.token_urlsafe(24)},
    )
    assert response.status_code == 200
    result: dict[str, Any] = response.json()
    return result


def authorization(account: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": "Bearer " + str(account["access_token"])}


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings.model_copy(update={"auth_enabled": True}))) as value:
        yield value


@pytest.fixture
def administrator(client: TestClient) -> dict[str, Any]:
    return create_account(client, "/api/auth/setup", "owner@example.test")


def customer_payload(email: str = "customer@example.test") -> dict[str, str]:
    return {"name": "  Example customer  ", "email": email, "password": secrets.token_urlsafe(24)}


def test_only_admin_can_manage_customers_even_when_auth_flag_is_disabled(
    settings: Settings,
) -> None:
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/admin/customers").status_code == 401
        assert client.post("/api/admin/customers", json=customer_payload()).status_code == 401
        create_account(client, "/api/auth/setup", "owner@example.test")
        customer = create_account(client, "/api/auth/register", "existing@example.test")
        headers = authorization(customer)
        assert client.get("/api/admin/customers", headers=headers).status_code == 403
        assert (
            client.post(
                "/api/admin/customers", headers=headers, json=customer_payload()
            ).status_code
            == 403
        )


def test_customer_creation_does_not_replace_admin_session(
    client: TestClient, administrator: dict[str, Any]
) -> None:
    headers = authorization(administrator)
    refresh = client.cookies.get(REFRESH_COOKIE)
    assert isinstance(client.app, FastAPI)
    database: ApplicationDatabase = client.app.state.database
    sessions_before = database._db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    payload = customer_payload(" CUSTOMER@EXAMPLE.TEST ")
    created = client.post("/api/admin/customers", json=payload, headers=headers)
    assert created.status_code == 201
    assert "set-cookie" not in created.headers
    assert created.headers["cache-control"] == "no-store"
    assert client.cookies.get(REFRESH_COOKIE) == refresh
    assert database._db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == sessions_before
    assert client.get("/api/auth/me", headers=headers).json()["id"] == administrator["user"]["id"]
    customer = created.json()["customer"]
    assert set(created.json()) == {"customer"}
    assert set(customer) == {"id", "name", "email", "role", "created_at"}
    assert customer["role"] == "customer" and customer["name"] == "Example customer"
    assert customer["email"] == "customer@example.test"
    assert datetime.fromisoformat(
        customer["created_at"].replace("Z", "+00:00")
    ).utcoffset() == timedelta(0)
    stored = database.get_user(customer["id"])
    assert stored is not None and stored.password_hash != payload["password"]
    assert stored.password_hash.startswith("$argon2")
    assert payload["password"] not in created.text and stored.password_hash not in created.text
    logged_in = client.post(
        "/api/auth/login", json={"email": customer["email"], "password": payload["password"]}
    )
    assert logged_in.status_code == 200 and logged_in.json()["user"]["role"] == "customer"


def test_customer_list_is_public_fields_only_paginated_and_excludes_admin(
    client: TestClient, administrator: dict[str, Any]
) -> None:
    headers = authorization(administrator)
    assert client.get("/api/admin/customers", headers=headers).json() == {
        "customers": [],
        "total": 0,
        "limit": 25,
        "offset": 0,
    }
    identifiers = {
        client.post(
            "/api/admin/customers",
            json=customer_payload(f"customer{number}@example.test"),
            headers=headers,
        ).json()["customer"]["id"]
        for number in range(3)
    }
    first = client.get("/api/admin/customers", params={"limit": 2}, headers=headers)
    last = client.get("/api/admin/customers", params={"limit": 2, "offset": 2}, headers=headers)
    assert first.headers["cache-control"] == "no-store"
    assert first.json()["total"] == last.json()["total"] == 3
    assert len(first.json()["customers"]) == 2 and len(last.json()["customers"]) == 1
    records = first.json()["customers"] + last.json()["customers"]
    assert {record["id"] for record in records} == identifiers
    assert all(record["id"] != administrator["user"]["id"] for record in records)
    assert all(set(record) == {"id", "name", "email", "role", "created_at"} for record in records)
    assert client.get(
        "/api/admin/customers", params={"offset": 10**30}, headers=headers
    ).json() == {"customers": [], "total": 3, "limit": 25, "offset": 10**30}


@pytest.mark.parametrize(
    "query", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "invalid"}]
)
def test_customer_pagination_validation(
    client: TestClient, administrator: dict[str, Any], query: dict[str, int | str]
) -> None:
    assert (
        client.get(
            "/api/admin/customers", params=query, headers=authorization(administrator)
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", " "),
        ("email", "invalid"),
        ("password", "12345"),
        ("password", "x" * 129),
        ("role", "admin"),
    ],
)
def test_customer_creation_validation_is_safe_and_role_is_fixed(
    client: TestClient, administrator: dict[str, Any], field: str, value: str
) -> None:
    payload = customer_payload() | {field: value}
    rejected = client.post(
        "/api/admin/customers", json=payload, headers=authorization(administrator)
    )
    assert rejected.status_code == 422
    assert payload["password"] not in rejected.text
    assert "set-cookie" not in rejected.headers
    assert (
        client.get("/api/admin/customers", headers=authorization(administrator)).json()["total"]
        == 0
    )


def test_duplicate_customer_is_safe_and_normalized(
    client: TestClient, administrator: dict[str, Any]
) -> None:
    headers = authorization(administrator)
    original = customer_payload()
    assert client.post("/api/admin/customers", json=original, headers=headers).status_code == 201
    duplicate = client.post(
        "/api/admin/customers",
        json=original | {"email": " CUSTOMER@EXAMPLE.TEST "},
        headers=headers,
    )
    assert duplicate.status_code == 409
    assert (
        original["password"] not in duplicate.text and "customer@example.test" not in duplicate.text
    )
    assert "set-cookie" not in duplicate.headers
    assert client.get("/api/admin/customers", headers=headers).json()["total"] == 1


def test_sqlite_customer_page_snapshot_allows_concurrent_external_registration(
    tmp_path: Path,
) -> None:
    first, second = ApplicationDatabase(tmp_path), ApplicationDatabase(tmp_path)
    first.bootstrap_admin("Owner", "owner@example.test", "synthetic-hash")
    previous = first.register_customer("Before", "before@example.test", "synthetic-hash")
    reached_page, release_page = threading.Event(), threading.Event()

    def pause_page_query(statement: str) -> None:
        if statement.startswith("SELECT id,name,email,created_at FROM users WHERE role='customer'"):
            reached_page.set()
            release_page.wait(timeout=5)

    first._db.set_trace_callback(pause_page_query)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            page = pool.submit(first.list_customers)
            try:
                assert reached_page.wait(timeout=5)
                writer = pool.submit(
                    second.register_customer, "During", "during@example.test", "synthetic-hash"
                )
                # A WAL reader must not block the other connection's write transaction.
                writer.result(timeout=3)
            finally:
                release_page.set()
            customers, total = page.result(timeout=5)
        assert total == 1 and [customer.id for customer in customers] == [previous.id]
        first._db.set_trace_callback(None)
        assert first.list_customers()[1] == 2
    finally:
        release_page.set()
        first._db.set_trace_callback(None)
        first.close()
        second.close()
