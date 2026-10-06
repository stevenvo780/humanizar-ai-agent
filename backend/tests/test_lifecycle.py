import asyncio
import secrets
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.agent import CompanyAgent, Emit, MessageProvider, no_emit
from app.business import BusinessStore
from app.database import ApplicationDatabase
from app.main import create_app
from app.models import ChatRequest, ChatResponse, Usage
from app.settings import Settings
from app.storage import KnowledgeStore
from app.tools import ToolRegistry


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
        ("BusinessStore", {"database", "knowledge"}),
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


def administrator(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/setup",
        json={
            "name": "Test owner",
            "email": "owner@example.invalid",
            "password": secrets.token_urlsafe(24),
        },
    )
    assert response.status_code == 200
    return {"Authorization": "Bearer " + str(response.json()["access_token"])}


def test_provider_replacement_closes_idle_and_defers_inflight_agents(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    started, released = threading.Event(), threading.Event()
    agents: list[CompanyAgent] = []
    closures: dict[CompanyAgent, int] = {}

    class TrackedAgent(CompanyAgent):
        def __init__(
            self,
            config: Settings,
            registry: ToolRegistry,
            provider: MessageProvider | None = None,
        ) -> None:
            # These tests exercise lifetime management without creating or calling an SDK client.
            super().__init__(config.model_copy(update={"llm_mode": "demo"}), registry, provider)
            agents.append(self)

        async def answer(self, request: ChatRequest, emit: Emit = no_emit) -> ChatResponse:
            assert not closures.get(self)
            started.set()
            assert await asyncio.to_thread(released.wait, 5)
            assert not closures.get(self)
            return ChatResponse(
                answer="Test response",
                sources=[],
                trace=[],
                mode="demo",
                model="test",
                usage=Usage(),
                session_id=request.session_id or "test-session",
            )

        async def close(self) -> None:
            closures[self] = closures.get(self, 0) + 1
            await super().close()

    monkeypatch.setattr(main_module, "CompanyAgent", TrackedAgent)
    application = create_app(settings.model_copy(update={"auth_enabled": True}))
    with TestClient(application) as client:
        owner = administrator(client)
        original = application.state.agent
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                client.post, "/api/chat", json={"message": "hello"}, headers=owner
            )
            try:
                assert started.wait(5)
                response = client.put(
                    "/api/settings/provider",
                    json={"api_key": secrets.token_urlsafe(32)},
                    headers=owner,
                )
                assert response.status_code == 200
                assert not closures.get(original)
                assert application.state.retired_agents == {original}
            finally:
                released.set()
            assert pending.result(timeout=5).status_code == 200
        assert closures[original] == 1
        assert not application.state.retired_agents
        replacement = application.state.agent
        response = client.put(
            "/api/settings/provider",
            json={"api_key": secrets.token_urlsafe(32)},
            headers=owner,
        )
        assert response.status_code == 200 and closures[replacement] == 1
        assert not application.state.retired_agents
    assert len(agents) == 3 and all(closures[agent] == 1 for agent in agents)


def test_failed_provider_persistence_closes_replacement_and_keeps_active_agent(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    closed: list[CompanyAgent] = []
    original_close = CompanyAgent.close

    async def observe_close(agent: CompanyAgent) -> None:
        closed.append(agent)
        await original_close(agent)

    def fail_save(_value: str) -> None:
        raise RuntimeError("Simulated storage failure")

    monkeypatch.setattr(CompanyAgent, "close", observe_close)
    application = create_app(settings.model_copy(update={"auth_enabled": True}))
    with TestClient(application) as client:
        owner = administrator(client)
        previous = application.state.agent
        monkeypatch.setattr(application.state.database, "set_provider_key", fail_save)
        response = client.put(
            "/api/settings/provider",
            json={"api_key": secrets.token_urlsafe(32)},
            headers=owner,
        )
        assert response.status_code == 500 and "Simulated" not in response.text
        assert application.state.agent is previous
        assert application.state.settings.mode == "demo"
        assert len(closed) == 1 and closed[0] is not previous
        assert not application.state.retired_agents
        assert client.post("/api/chat", json={"message": "hello"}, headers=owner).status_code == 200


def test_shutdown_continues_after_agent_close_failure(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = create_app(settings)

    async def failed_close() -> None:
        raise RuntimeError("Simulated close failure")

    with pytest.raises(RuntimeError, match="Simulated close failure"), TestClient(application):
        monkeypatch.setattr(application.state.agent, "close", failed_close)
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
