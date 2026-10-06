import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, cast

import pytest

from app.business import BusinessStore, BusinessValidationError
from app.ingestion import ParsedDocument
from app.settings import Settings
from app.storage import KnowledgeStore
from app.tools import ToolRegistry

DEMO: dict[str, str] = {
    "name": "Ana",
    "email": "ana@example.test",
    "company": "Distribuidora",
    "interest": "Deméter",
    "needs": "Organizar pedidos y rutas de reparto.",
}
SUPPORT = {"subject": "Acceso al catálogo", "description": "La página no muestra mis pedidos."}


def test_store_preserves_auth_and_survives_restart(tmp_path: Path) -> None:
    with sqlite3.connect(tmp_path / "application.sqlite3") as auth:
        auth.execute("CREATE TABLE users (id TEXT PRIMARY KEY)")
        auth.execute("INSERT INTO users VALUES ('alice')")
    business = BusinessStore(tmp_path)
    record = business.create_request("alice", "demo", DEMO)
    business.close()
    restored = BusinessStore(tmp_path)
    try:
        assert restored.list_requests("alice") == [record]
        assert record["status"] == "received" and record["kind"] == "demo"
        assert set(record) == {"id", "kind", "status", "created_at", "details"}
        with sqlite3.connect(tmp_path / "application.sqlite3") as auth:
            assert auth.execute("SELECT id FROM users").fetchone() == ("alice",)
    finally:
        restored.close()


def test_records_are_strictly_user_scoped(tmp_path: Path) -> None:
    business = BusinessStore(tmp_path)
    try:
        alice = business.create_request("alice", "demo", DEMO)
        bob = business.create_request("bob", "support", SUPPORT)
        assert business.list_requests("alice") == [alice]
        assert business.list_requests("bob") == [bob]
        assert business.list_requests("alice' OR '1'='1") == []
        assert "user_id" not in alice
    finally:
        business.close()


def test_admin_inbox_lists_all_accounts_recent_first_without_affecting_user_scope(
    tmp_path: Path,
) -> None:
    business = BusinessStore(tmp_path)
    try:
        alice_demo = business.create_request("alice", "demo", DEMO)
        bob_support = business.create_request("bob", "support", SUPPORT)
        alice_support = business.create_request("alice", "support", SUPPORT)
        expected = sorted(
            [
                {**alice_demo, "user_id": "alice"},
                {**bob_support, "user_id": "bob"},
                {**alice_support, "user_id": "alice"},
            ],
            key=lambda item: (item["created_at"], item["id"]),
            reverse=True,
        )
        assert business.list_all_requests() == expected
        assert business.list_all_requests(2) == expected[:2]
        assert business.list_requests("bob") == [bob_support]
        assert {item["id"] for item in business.list_requests("alice")} == {
            alice_demo["id"],
            alice_support["id"],
        }
        assert all("user_id" not in item for item in business.list_requests("alice"))
        assert all("action_key" not in item for item in business.list_all_requests())
    finally:
        business.close()


@pytest.mark.parametrize("limit", [0, -1, 51, True, False, "5", None])
def test_admin_inbox_rejects_invalid_limits(tmp_path: Path, limit: Any) -> None:
    business = BusinessStore(tmp_path)
    try:
        with pytest.raises(BusinessValidationError):
            business.list_all_requests(limit)
    finally:
        business.close()


def test_admin_inbox_default_is_bounded_at_fifty(tmp_path: Path) -> None:
    business = BusinessStore(tmp_path)
    try:
        for index in range(51):
            business.create_request(f"user-{index % 2}", "support", SUPPORT)
        assert len(business.list_all_requests()) == 50
        assert len(business.list_all_requests(1)) == 1
    finally:
        business.close()


def test_confirmation_retries_are_idempotent_and_scoped(tmp_path: Path) -> None:
    business = BusinessStore(tmp_path)
    second_connection = BusinessStore(tmp_path)
    try:
        record = business.create_request("alice", "demo", DEMO, "same-action")
        assert second_connection.create_request("alice", "demo", DEMO, "same-action") == record
        bob = business.create_request("bob", "demo", DEMO, "same-action")
        assert bob["id"] != record["id"]
        with pytest.raises(BusinessValidationError):
            business.create_request("alice", "support", SUPPORT, "same-action")
        with pytest.raises(BusinessValidationError):
            business.create_request(
                "alice", "demo", {**DEMO, "needs": "Different need."}, "same-action"
            )
        assert len(business.list_requests("alice")) == 1
    finally:
        second_connection.close()
        business.close()


def test_concurrent_retries_create_one_record(tmp_path: Path) -> None:
    business = BusinessStore(tmp_path)
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(
                pool.map(
                    lambda _: business.create_request("alice", "support", SUPPORT, "retry-action"),
                    range(8),
                )
            )
        assert len({item["id"] for item in results}) == 1
        assert len(business.list_requests("alice")) == 1
    finally:
        business.close()


@pytest.mark.parametrize(
    "details",
    [
        {**DEMO, "email": "invalid"},
        {**DEMO, "name": " "},
        {**DEMO, "needs": "x" * 2001},
        {**DEMO, "user_id": "bob"},
        {**DEMO, "confirmed": True},
        {**DEMO, "name": "A\x00B"},
    ],
)
def test_invalid_request_fields_are_rejected(tmp_path: Path, details: dict[str, Any]) -> None:
    business = BusinessStore(tmp_path)
    try:
        with pytest.raises(BusinessValidationError):
            business.create_request("alice", "demo", details)
        assert business.list_requests("alice") == []
    finally:
        business.close()


def test_redaction_happens_before_persistence(tmp_path: Path) -> None:
    business = BusinessStore(tmp_path)
    try:
        record = business.create_request(
            "alice", "support", {**SUPPORT, "description": "API_TOKEN=private-secret-value"}
        )
        assert "private-secret-value" not in json.dumps(record)
        with sqlite3.connect(tmp_path / "application.sqlite3") as db:
            saved = db.execute("SELECT details FROM business_requests").fetchone()[0]
            assert "private-secret-value" not in saved
    finally:
        business.close()


async def test_write_requires_authentication_and_explicit_confirmation(
    settings: Settings,
    store: KnowledgeStore,
) -> None:
    business = BusinessStore(settings.data_dir)
    registry = ToolRegistry(settings, store, business)
    try:
        anonymous = await registry.run("create_demo_request", DEMO, confirmed=True)
        assert anonymous.trace.status == "error" and "sesión" in anonymous.trace.output
        pending = await registry.run("create_demo_request", DEMO, user_id="alice")
        payload = json.loads(pending.trace.output)
        assert pending.trace.status == "completed"
        assert payload["requires_confirmation"] is True
        assert payload["action"] == {"tool": "create_demo_request", "input": DEMO}
        assert business.list_requests("alice") == [] and pending.sources == []
        confirmed = await registry.run(
            "create_demo_request",
            DEMO,
            user_id="alice",
            confirmed=True,
            action_key=pending.trace.id,
        )
        assert confirmed.trace.status == "completed"
        saved = json.loads(confirmed.trace.output)["request"]
        assert business.list_requests("alice") == [saved]
        repeated = await registry.run(
            "create_demo_request",
            DEMO,
            user_id="alice",
            confirmed=True,
            action_key=pending.trace.id,
        )
        assert json.loads(repeated.trace.output)["request"] == saved
        assert (
            "localmente" in confirmed.trace.output and "No se ha enviado" in confirmed.trace.output
        )
    finally:
        await registry.close()
        business.close()


async def test_model_cannot_supply_confirmation_or_another_user(
    settings: Settings,
    store: KnowledgeStore,
) -> None:
    business = BusinessStore(settings.data_dir)
    registry = ToolRegistry(settings, store, business)
    try:
        for extra in ({"user_id": "bob"}, {"confirmed": True}, {"action_key": "forged"}):
            result = await registry.run(
                "create_support_ticket", {**SUPPORT, **extra}, user_id="alice", confirmed=True
            )
            assert result.trace.status == "error"
        forged_list = await registry.run("list_my_requests", {"user_id": "bob"}, user_id="alice")
        assert forged_list.trace.status == "error"
        assert business.list_requests("alice") == []
    finally:
        await registry.close()
        business.close()


async def test_real_support_record_and_user_scoped_listing(
    settings: Settings,
    store: KnowledgeStore,
) -> None:
    business = BusinessStore(settings.data_dir)
    registry = ToolRegistry(settings, store, business)
    try:
        business.create_request("bob", "demo", DEMO)
        saved = await registry.run(
            "create_support_ticket", SUPPORT, user_id="alice", confirmed=True
        )
        assert saved.trace.status == "completed"
        listing = await registry.run("list_my_requests", {}, user_id="alice")
        requests = json.loads(listing.trace.output)["requests"]
        assert len(requests) == 1 and requests[0]["kind"] == "support"
        assert "ana@example.test" not in listing.trace.output
        assert (await registry.run("list_my_requests", {})).trace.status == "error"
    finally:
        await registry.close()
        business.close()


async def test_business_catalog_and_schemas(settings: Settings, store: KnowledgeStore) -> None:
    business = BusinessStore(settings.data_dir)
    registry = ToolRegistry(settings, store, business)
    unavailable = ToolRegistry(settings, store)
    try:
        for tool in (
            "recommend_product",
            "create_demo_request",
            "create_support_ticket",
            "list_my_requests",
        ):
            assert (
                next(item for item in registry.catalog() if item["name"] == tool)["enabled"] is True
            )
            schema = cast(
                dict[str, Any],
                next(item for item in registry.schemas() if item["name"] == tool)["input_schema"],
            )
            assert schema["additionalProperties"] is False
            assert "user_id" not in schema["properties"] and "confirmed" not in schema["properties"]
        assert not next(
            item for item in unavailable.catalog() if item["name"] == "create_demo_request"
        )["enabled"]
        assert next(item for item in unavailable.catalog() if item["name"] == "recommend_product")[
            "enabled"
        ]
    finally:
        await registry.close()
        await unavailable.close()
        business.close()


async def test_recommendation_requires_retrieved_document_evidence(
    settings: Settings,
    store: KnowledgeStore,
) -> None:
    registry = ToolRegistry(settings, store)
    try:
        missing = await registry.run(
            "recommend_product", {"process": "Distribuidora de alimentos y rutas"}
        )
        assert json.loads(missing.trace.output)["recommendations"] == []
        assert missing.sources == []
        documents = store.add_documents(
            [
                ParsedDocument(
                    "catalogo.md",
                    "Deméter: pedidos, despacho por rutas y cartera para "
                    "distribuidoras alimentarias. "
                    "No hay precios publicados.",
                )
            ]
        )
        result = await registry.run(
            "recommend_product", {"process": "Distribuidora de alimentos, pedidos y rutas"}
        )
        payload = json.loads(result.trace.output)
        assert payload["recommendations"][0]["product"] == "Deméter"
        assert result.sources and result.sources[0].document_id == documents[0].id
        assert payload["recommendations"][0]["source_ids"] == [result.sources[0].chunk_id]
        assert "No hay precios publicados" in result.trace.output
        assert "no cotiza" in payload["message"]
    finally:
        await registry.close()


async def test_list_output_and_error_messages_are_bounded(
    settings: Settings,
    store: KnowledgeStore,
) -> None:
    business = BusinessStore(settings.data_dir)
    registry = ToolRegistry(settings, store, business)
    try:
        for _ in range(20):
            business.create_request(
                "alice", "support", {"subject": "Caso", "description": "x" * 2000}
            )
        result = await registry.run("list_my_requests", {}, user_id="alice")
        assert len(result.trace.output) <= 8000
        payload = json.loads(result.trace.output)
        assert payload["has_more"] is True and len(payload["requests"]) < 20
        invalid = await registry.run(
            "create_demo_request", {**DEMO, "email": "not-an-email"}, user_id="alice"
        )
        assert invalid.trace.status == "error" and "correo" in invalid.trace.output
        assert "not-an-email" not in invalid.trace.output
        oversized = await registry.run(
            "create_support_ticket",
            {"subject": "Caso", "description": "x" * 100_000},
            user_id="alice",
            confirmed=True,
        )
        assert oversized.trace.status == "error"
        assert len(json.dumps(oversized.trace.input, ensure_ascii=False)) <= 6000
    finally:
        await registry.close()
        business.close()
