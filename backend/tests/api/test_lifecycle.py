import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.agent.company_agent import CompanyAgent
from app.business.requests import BusinessStore
from app.core.settings import Settings
from app.knowledge.store import KnowledgeStore
from app.main import create_app
from app.persistence.sqlite import ApplicationDatabase
from app.tools.registry import ToolRegistry


@pytest.mark.parametrize("store_class", [ApplicationDatabase, BusinessStore])
def test_database_constructor_failure_closes_connection(
    store_class: type[ApplicationDatabase] | type[BusinessStore],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connections: list[sqlite3.Connection] = []
    original_connect = sqlite3.connect

    def tracked_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        connection: sqlite3.Connection = original_connect(*args, **kwargs)
        connections.append(connection)
        return connection

    def broken_schema(_self: Any, *_args: Any) -> None:
        raise RuntimeError("Simulated schema failure")

    monkeypatch.setattr(sqlite3, "connect", tracked_connect)
    monkeypatch.setattr(store_class, "_initialize_schema", broken_schema)
    with pytest.raises(RuntimeError, match="Simulated schema failure"):
        store_class(tmp_path)
    assert len(connections) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connections[0].execute("SELECT 1")


def test_knowledge_constructor_failure_releases_qdrant_lock(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: list[KnowledgeStore] = []

    def failed_reindex(store: KnowledgeStore) -> None:
        observed.append(store)
        raise RuntimeError("Simulated indexing failure")

    with monkeypatch.context() as scoped:
        scoped.setattr(KnowledgeStore, "_reindex", failed_reindex)
        with pytest.raises(RuntimeError, match="Simulated indexing failure"):
            KnowledgeStore(settings)
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        observed[0]._db.execute("SELECT 1")
    # Reopening the same local Qdrant directory fails if its previous lock survived.
    replacement = KnowledgeStore(settings)
    replacement.close()


@pytest.mark.parametrize(
    ("failure_stage", "expected_closed"),
    [
        ("KnowledgeStore", {"database"}),
        ("create_business_store", {"database", "knowledge"}),
        ("CompanyAgent", {"database", "knowledge", "business", "registry"}),
    ],
)
def test_lifespan_failure_closes_previous_resources(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    failure_stage: str,
    expected_closed: set[str],
) -> None:
    closed: set[str] = set()
    database_close, knowledge_close = ApplicationDatabase.close, KnowledgeStore.close
    business_close, registry_close = BusinessStore.close, ToolRegistry.close

    def close_database(database: ApplicationDatabase) -> None:
        database_close(database)
        closed.add("database")

    def close_knowledge(store: KnowledgeStore) -> None:
        knowledge_close(store)
        closed.add("knowledge")

    def close_business(store: BusinessStore) -> None:
        business_close(store)
        closed.add("business")

    async def close_registry(registry: ToolRegistry) -> None:
        await registry_close(registry)
        assert registry.http.is_closed
        closed.add("registry")

    def failed_constructor(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("Simulated startup failure")

    monkeypatch.setattr(ApplicationDatabase, "close", close_database)
    monkeypatch.setattr(KnowledgeStore, "close", close_knowledge)
    monkeypatch.setattr(BusinessStore, "close", close_business)
    monkeypatch.setattr(ToolRegistry, "close", close_registry)
    monkeypatch.setattr(main_module, failure_stage, failed_constructor)
    with (
        pytest.raises(RuntimeError, match="Simulated startup failure"),
        TestClient(create_app(settings)),
    ):
        pass
    assert closed == expected_closed


def test_shutdown_continues_after_agent_close_failure(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = create_app(settings)

    async def failed_close(_agent: CompanyAgent) -> None:
        raise RuntimeError("Simulated close failure")

    monkeypatch.setattr(CompanyAgent, "close", failed_close)
    with pytest.raises(RuntimeError, match="Simulated close failure"), TestClient(application):
        pass
    assert application.state.registry.http.is_closed
    for connection in (
        application.state.database._db,
        application.state.store._db,
        application.state.business._db,
    ):
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")
    replacement = KnowledgeStore(settings)
    replacement.close()
