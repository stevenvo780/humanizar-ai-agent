from pathlib import Path

import pytest

from app.core.settings import Settings
from app.knowledge.bootstrap import load_initial_knowledge
from app.knowledge.ingestion import IngestionError, ParsedDocument
from app.knowledge.store import KnowledgeStore


def test_initial_corpus_idempotent_preserves_uploads(
    settings: Settings, store: KnowledgeStore, tmp_path: Path
) -> None:
    directory = tmp_path / "corpus"
    directory.mkdir()
    (directory / "company.md").write_text("Humanizar ofrece software a medida.")
    (directory / "existing.md").write_text("No reemplazar la versión subida.")
    (directory / "unsafe.md").symlink_to(directory / "company.md")
    (directory / ".env").write_text("Not a corpus document.")
    store.add_documents([ParsedDocument("existing.md", "Versión del usuario con soporte.")])
    config = settings.model_copy(update={"knowledge_dir": directory})
    load_initial_knowledge(store, config)
    first = store.list_documents()
    load_initial_knowledge(store, config)
    assert store.list_documents() == first
    assert {document.name for document in first.documents} == {"company.md", "existing.md"}
    assert "Versión del usuario" in store.search("soporte")[0].text


def test_initial_corpus_rejects_missing_directory(
    settings: Settings, store: KnowledgeStore
) -> None:
    config = settings.model_copy(update={"knowledge_dir": settings.data_dir / "missing"})
    with pytest.raises(IngestionError, match="no está disponible"):
        load_initial_knowledge(store, config)
