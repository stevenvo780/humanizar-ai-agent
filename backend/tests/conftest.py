from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.settings import Settings
from app.storage import KnowledgeStore


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    class TestSettings(Settings):
        model_config = Settings.model_config | {"env_file": None}

    return TestSettings(
        data_dir=tmp_path,
        company_name="Forma",
        embedding_provider="hash",
        llm_mode="demo",
        seed_demo=False,
        auth_enabled=False,
        database_url=SecretStr(""),
        jwt_secret=SecretStr(""),
        auth_bootstrap_token=SecretStr(""),
        mcp_enabled=False,
        sandbox_url="http://127.0.0.1:1",
    )


@pytest.fixture
def store(settings: Settings) -> Iterator[KnowledgeStore]:
    knowledge = KnowledgeStore(settings)
    try:
        yield knowledge
    finally:
        knowledge.close()
