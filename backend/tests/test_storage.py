from app.embeddings import HashEmbedder
from app.ingestion import ParsedDocument
from app.sample_data import DEMO_DOCUMENTS
from app.settings import Settings
from app.storage import KnowledgeStore


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
