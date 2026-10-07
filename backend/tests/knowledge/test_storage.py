import sqlite3
import uuid
from typing import Any

import pytest

from app.core.settings import Settings
from app.knowledge.embeddings import HashEmbedder
from app.knowledge.ingestion import ParsedDocument, chunks
from app.knowledge.sample_data import DEMO_DOCUMENTS
from app.knowledge.store import KnowledgeStore


def test_lexical_hash_deterministic_and_accents() -> None:
    embedder = HashEmbedder()
    assert embedder.embed(["Integración Madrid"]) == embedder.embed(["integracion madrid"])
    vector = embedder.embed(["precio starter"])[0]
    assert len(vector) == 384
    assert abs(sum(value * value for value in vector) - 1) < 0.00001


def test_persistence_search_and_delete(settings: Settings) -> None:
    store = KnowledgeStore(settings)
    document = store.add_documents([ParsedDocument("precios.md", "Plan Starter cuesta 29 euros")])[
        0
    ]
    initial = store.search("Starter precio")
    assert initial[0].document_id == document.id
    identifier = initial[0].chunk_id
    store.close()
    reopened = KnowledgeStore(settings)
    try:
        assert reopened.list_documents().total_chunks == 1
        assert reopened.search("Starter")[0].chunk_id == identifier
        assert reopened.search("nebulosa galactica") == []
        assert reopened.delete(document.id)
        assert not reopened.delete(document.id)
        assert reopened.search("Starter") == []
        assert reopened.list_documents().total_chunks == 0
    finally:
        reopened.close()


def test_seed_not_readded_after_user_delete(store: KnowledgeStore) -> None:
    store.seed(DEMO_DOCUMENTS)
    for document in store.list_documents().documents:
        assert store.delete(document.id)
    store.seed(DEMO_DOCUMENTS)
    assert store.list_documents().documents == []


def test_metadata_survives_embedding_change(settings: Settings) -> None:
    store = KnowledgeStore(settings)
    document = store.add_documents([ParsedDocument("support.md", "Soporte lunes a viernes")])[0]
    store.close()

    class NewHash(HashEmbedder):
        signature = "hash-next-version"

    reopened = KnowledgeStore(settings, NewHash())
    try:
        assert reopened.search("Soporte")[0].document_id == document.id
        second = reopened.add_documents([ParsedDocument("extra.txt", "Zebras adaptadas")])[0]
    finally:
        reopened.close()
    original_provider = KnowledgeStore(settings)
    try:
        assert original_provider.search("Zebras")[0].document_id == second.id
        assert original_provider.list_documents().total_chunks == 2
    finally:
        original_provider.close()


def test_document_detail_preserves_full_text_whitespace_and_reopens(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = (
        "\t  \n"
        + "\n".join(f"Fila {number}: conocimiento con espacios  y\ttabs." for number in range(80))
        + "\n  \t"
    )
    store = KnowledgeStore(settings)
    document = store.add_documents([ParsedDocument("complete.md", text)])[0]
    assert document.chunks > 1

    def vector_access_forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("Reading text must not contact vector storage")

    with monkeypatch.context() as scoped:
        scoped.setattr(store._vectors, "query_points", vector_access_forbidden)
        scoped.setattr(store._vectors, "upsert", vector_access_forbidden)
        scoped.setattr(store._vectors, "delete", vector_access_forbidden)
        detail = store.get_document(document.id)
        assert detail is not None and detail.content == text and not detail.reconstructed
        assert detail.characters == len(text)
        assert "content" not in store.list_documents().documents[0].model_dump()
        assert store.get_document("missing") is None
    store.close()
    reopened = KnowledgeStore(settings)
    try:
        persisted = reopened.get_document(document.id)
        assert persisted is not None and persisted.content == text and not persisted.reconstructed
    finally:
        reopened.close()


def legacy_database(settings: Settings, text: str, fragments: list[str]) -> str:
    identifier = str(uuid.uuid4())
    with sqlite3.connect(settings.data_dir / "metadata.sqlite3") as database:
        database.executescript(
            "CREATE TABLE documents (id TEXT PRIMARY KEY,name TEXT NOT NULL,"
            "chunks INTEGER NOT NULL,"
            "characters INTEGER NOT NULL,created_at TEXT NOT NULL);"
            "CREATE TABLE chunks (id TEXT PRIMARY KEY,document_id TEXT NOT NULL "
            "REFERENCES documents(id) ON DELETE CASCADE,text TEXT NOT NULL);"
            "CREATE TABLE flags (key TEXT PRIMARY KEY,value TEXT NOT NULL);"
        )
        database.execute(
            "INSERT INTO documents VALUES (?,?,?,?,?)",
            (
                identifier,
                "legacy.md",
                len(fragments),
                len(text),
                "2026-10-07T00:00:00+00:00",
            ),
        )
        # Reverse UUID order proves that the reader uses historical insertion order.
        database.executemany(
            "INSERT INTO chunks VALUES (?,?,?)",
            [
                (str(uuid.UUID(int=10000 - number)), identifier, fragment)
                for number, fragment in enumerate(fragments)
            ],
        )
        database.execute("INSERT INTO flags VALUES ('demo_seeded','true')")
    return identifier


def test_legacy_schema_migrates_idempotently_without_data_loss(settings: Settings) -> None:
    text = (
        "\t \n"
        + "\n".join(
            f"Registro{number:04d} contiene datos públicos de la empresa." for number in range(90)
        )
        + "\n \t"
    )
    fragments = chunks(text)
    identifier = legacy_database(settings, text, fragments)
    assert len(fragments) > 1
    prior_content: str | None = None
    for _ in range(2):
        store = KnowledgeStore(settings)
        try:
            detail = store.get_document(identifier)
            assert detail is not None and detail.reconstructed
            assert detail.content != text  # Chunk trimming did not retain original formatting.
            assert all(detail.content.count(f"Registro{number:04d}") == 1 for number in range(90))
            assert prior_content is None or detail.content == prior_content
            prior_content = detail.content
            assert detail.characters == len(text) and detail.chunks == len(fragments)
            assert (
                store._db.execute("SELECT value FROM flags WHERE key='demo_seeded'").fetchone()[0]
                == "true"
            )
            assert [
                row[0] for row in store._db.execute("SELECT text FROM chunks ORDER BY rowid")
            ] == fragments
            assert [row["name"] for row in store._db.execute("PRAGMA table_info(documents)")] == [
                "id",
                "name",
                "chunks",
                "characters",
                "created_at",
            ]
            assert store._db.execute("SELECT COUNT(*) FROM document_contents").fetchone()[0] == 0
        finally:
            store.close()
    # The old five-value insertion remains valid after the additive migration.
    with sqlite3.connect(settings.data_dir / "metadata.sqlite3") as database:
        database.execute(
            "INSERT INTO documents VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), "old-writer.md", 0, 0, "2026-10-07T00:00:00+00:00"),
        )


@pytest.mark.parametrize(
    "fragments,expected",
    [
        (["Primera sección", "Segunda diferente"], "Primera sección\n\nSegunda diferente"),
        (["x" * 1000, "x" * 1000, "x" * 320], "x" * 2020),
    ],
)
def test_legacy_reconstruction_is_ordered_and_uses_bounded_overlap(
    settings: Settings, fragments: list[str], expected: str
) -> None:
    identifier = legacy_database(settings, expected, fragments)
    store = KnowledgeStore(settings)
    try:
        detail = store.get_document(identifier)
        assert detail is not None and detail.reconstructed and detail.content == expected
    finally:
        store.close()


def test_intermediate_content_column_is_preserved_and_copied_once(settings: Settings) -> None:
    text = "Texto intermedio\n  con formato\t exacto."
    identifier = legacy_database(settings, text, chunks(text))
    with sqlite3.connect(settings.data_dir / "metadata.sqlite3") as database:
        database.execute("ALTER TABLE documents ADD COLUMN content TEXT")
        database.execute("UPDATE documents SET content=? WHERE id=?", (text, identifier))
    for _ in range(2):
        store = KnowledgeStore(settings)
        try:
            detail = store.get_document(identifier)
            assert detail is not None and detail.content == text and not detail.reconstructed
            assert (
                store._db.execute(
                    "SELECT content FROM documents WHERE id=?", (identifier,)
                ).fetchone()[0]
                == text
            )
            assert store._db.execute("SELECT COUNT(*) FROM document_contents").fetchone()[0] == 1
        finally:
            store.close()


def test_document_content_rolls_back_with_failed_vector_insertion(
    store: KnowledgeStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    previous = store.add_documents([ParsedDocument("existing.md", "Existing content")])[0]
    attempted: set[str] = set()

    def fail_upsert(_collection: str, points: Any, **_kwargs: Any) -> None:
        attempted.update(str(point.payload["document_id"]) for point in points)
        raise RuntimeError("Synthetic vector failure")

    with monkeypatch.context() as scoped:
        scoped.setattr(store._vectors, "upsert", fail_upsert)
        with pytest.raises(RuntimeError, match="Synthetic vector failure"):
            store.add_documents(
                [ParsedDocument("new.md", "New content"), ParsedDocument("next.md", "Next content")]
            )
    assert attempted and all(store.get_document(identifier) is None for identifier in attempted)
    assert [document.id for document in store.list_documents().documents] == [previous.id]
    assert store._db.execute("SELECT COUNT(*) FROM document_contents").fetchone()[0] == 1


def test_content_survives_failed_delete_and_cascades_after_success(
    store: KnowledgeStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = store.add_documents([ParsedDocument("delete.md", "Document content")])[0]

    def fail_delete(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("Synthetic vector failure")

    with monkeypatch.context() as scoped:
        scoped.setattr(store._vectors, "delete", fail_delete)
        with pytest.raises(RuntimeError, match="Synthetic vector failure"):
            store.delete(document.id)
    detail = store.get_document(document.id)
    assert detail is not None and detail.content == "Document content"
    assert store.delete(document.id)
    assert store.get_document(document.id) is None
    assert not store.delete(document.id)
    assert store._db.execute("SELECT COUNT(*) FROM document_contents").fetchone()[0] == 0
    assert store._db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 0


def test_remote_corpus_namespace_prevents_cross_store_top_n_starvation(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    from qdrant_client import QdrantClient

    shared = QdrantClient(":memory:")
    real_close = shared.close
    monkeypatch.setattr(shared, "close", lambda: None)
    monkeypatch.setattr("app.knowledge.store.QdrantClient", lambda **_kwargs: shared)
    first_settings = settings.model_copy(
        update={
            "qdrant_url": "https://vectors.example.invalid",
            "data_dir": settings.data_dir / "first",
        }
    )
    second_settings = settings.model_copy(
        update={
            "qdrant_url": "https://vectors.example.invalid",
            "data_dir": settings.data_dir / "second",
        }
    )
    first = KnowledgeStore(first_settings)
    second = KnowledgeStore(second_settings)
    try:
        document = first.add_documents(
            [ParsedDocument("first.md", "Inventario y control de existencias")]
        )[0]
        second.add_documents(
            [ParsedDocument(f"other-{index}.md", "Inventario") for index in range(40)]
        )
        assert first.collection != second.collection
        assert first.search("inventario", 1)[0].document_id == document.id
        assert all(
            source.document_name.startswith("other-") for source in second.search("inventario")
        )
        namespace = first.collection
        first.close()
        first = KnowledgeStore(first_settings)
        assert first.collection == namespace
        assert first.search("inventario")[0].document_id == document.id
        assert first.delete(document.id)
        assert second.search("inventario")
        assert shared.collection_exists(second.collection)
    finally:
        first.close()
        second.close()
        real_close()


def test_legacy_vectors_are_preserved_while_new_collection_reindexes(settings: Settings) -> None:
    from qdrant_client import QdrantClient, models

    text = "Conocimiento legado público"
    identifier = legacy_database(settings, text, chunks(text))
    vectors = QdrantClient(path=str(settings.data_dir / "qdrant"))
    old_collection = "lumen_" + HashEmbedder.signature.replace("-", "_")
    vectors.create_collection(
        old_collection,
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    )
    foreign_id = str(uuid.uuid4())
    vectors.upsert(
        old_collection,
        [
            models.PointStruct(
                id=foreign_id,
                vector=HashEmbedder().embed([text])[0],
                payload={"document_id": "foreign"},
            )
        ],
    )
    vectors.close()
    store = KnowledgeStore(settings)
    try:
        assert store.collection != old_collection
        assert store.search("legado")[0].document_id == identifier
        assert store._vectors.retrieve(old_collection, [foreign_id])
        namespace = store._db.execute(
            "SELECT value FROM flags WHERE key='qdrant_namespace'"
        ).fetchone()[0]
        assert namespace in store.collection
    finally:
        store.close()
