import sqlite3
import threading
import uuid
from contextlib import ExitStack
from datetime import UTC, datetime
from typing import Any

from qdrant_client import QdrantClient, models

from app.api.schemas import Document, DocumentDetail, DocumentList, Source
from app.core.settings import Settings
from app.knowledge.embeddings import Embedder, create_embedder, terms
from app.knowledge.ingestion import ParsedDocument, chunks


class KnowledgeStore:
    def __init__(self, settings: Settings, embedder: Embedder | None = None) -> None:
        self.settings = settings
        self.embedder = embedder or create_embedder(settings)
        self._lock = threading.RLock()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        with ExitStack() as resources:
            self._db = sqlite3.connect(
                settings.data_dir / "metadata.sqlite3", check_same_thread=False
            )
            resources.callback(self._db.close)
            self._db.row_factory = sqlite3.Row
            self._db.executescript(
                "PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;"
                "CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, name TEXT NOT NULL, "
                "chunks INTEGER NOT NULL, characters INTEGER NOT NULL, created_at TEXT NOT NULL);"
                "CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, document_id TEXT NOT NULL "
                "REFERENCES documents(id) ON DELETE CASCADE, text TEXT NOT NULL);"
                "CREATE TABLE IF NOT EXISTS document_contents (document_id TEXT PRIMARY KEY "
                "REFERENCES documents(id) ON DELETE CASCADE, content TEXT NOT NULL);"
                "CREATE TABLE IF NOT EXISTS flags (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
            )
            # Preserve an optional column from an intermediate version without altering it.
            with self._db:
                self._db.execute("BEGIN IMMEDIATE")
                self._db.execute(
                    "INSERT INTO flags (key,value) VALUES ('qdrant_namespace',?) "
                    "ON CONFLICT(key) DO NOTHING",
                    (uuid.uuid4().hex,),
                )
                namespace = str(
                    self._db.execute(
                        "SELECT value FROM flags WHERE key='qdrant_namespace'"
                    ).fetchone()[0]
                )
                if len(namespace) != 32 or any(
                    char not in "0123456789abcdef" for char in namespace
                ):
                    raise ValueError("La identidad persistente del corpus no es válida.")
                self.collection = (
                    "lumen_" + namespace + "_" + self.embedder.signature.replace("-", "_")
                )
                columns = {
                    str(row["name"]) for row in self._db.execute("PRAGMA table_info(documents)")
                }
                if "content" in columns:
                    self._db.execute(
                        "INSERT INTO document_contents (document_id,content) "
                        "SELECT id,content FROM documents WHERE content IS NOT NULL "
                        "ON CONFLICT(document_id) DO NOTHING"
                    )
            if settings.qdrant_url:
                self._vectors = QdrantClient(
                    url=settings.qdrant_url,
                    api_key=settings.qdrant_api_key.get_secret_value() or None,
                    timeout=15,
                )
            else:
                self._vectors = QdrantClient(path=str(settings.data_dir / "qdrant"))
            resources.callback(self._vectors.close)
            if not self._vectors.collection_exists(self.collection):
                self._vectors.create_collection(
                    collection_name=self.collection,
                    vectors_config=models.VectorParams(
                        size=self.embedder.dimension, distance=models.Distance.COSINE
                    ),
                )
            # Reconcile also when switching back to an existing provider's collection.
            # SQLite is authoritative after an interrupted operation.
            self._reindex()
            resources.pop_all()

    def _points(self, records: list[dict[str, Any]]) -> list[models.PointStruct]:
        vectors = self.embedder.embed([str(record["text"]) for record in records])
        return [
            models.PointStruct(id=record["id"], vector=vector, payload=record)
            for record, vector in zip(records, vectors, strict=True)
        ]

    def _reindex(self) -> None:
        rows = self._db.execute(
            "SELECT c.id, c.document_id, c.text, d.name AS document_name "
            "FROM chunks c JOIN documents d ON d.id=c.document_id"
        ).fetchall()
        for start in range(0, len(rows), 64):
            self._vectors.upsert(
                self.collection,
                self._points([dict(row) for row in rows[start : start + 64]]),
                wait=True,
            )

    def list_documents(self) -> DocumentList:
        with self._lock:
            documents = [
                Document.model_validate(dict(row))
                for row in self._db.execute(
                    "SELECT id,name,chunks,characters,created_at FROM documents "
                    "ORDER BY created_at,id"
                )
            ]
            return DocumentList(
                documents=documents, total_chunks=sum(document.chunks for document in documents)
            )

    @staticmethod
    def _reconstruct(fragments: list[str]) -> str:
        if not fragments:
            return ""
        # Historical ingestion used a 150-character overlap. Trimming lost formatting,
        # so this is an explicitly approximate reconstruction rather than an original.
        parts = [fragments[0]]
        previous = fragments[0]
        for fragment in fragments[1:]:
            maximum = min(150, len(previous), len(fragment))
            overlap = next(
                (size for size in range(maximum, 0, -1) if previous.endswith(fragment[:size])),
                0,
            )
            parts.append(fragment[overlap:] if overlap else "\n\n" + fragment)
            previous = fragment
        return "".join(parts)

    def get_document(self, document_id: str) -> DocumentDetail | None:
        """Read complete extracted text from metadata, without contacting vector storage."""
        with self._lock:
            row = self._db.execute(
                "SELECT d.id,d.name,d.chunks,d.characters,d.created_at,c.content FROM documents d "
                "LEFT JOIN document_contents c ON c.document_id=d.id WHERE d.id=?",
                (document_id,),
            ).fetchone()
            if row is None:
                return None
            record = dict(row)
            reconstructed = record["content"] is None
            if reconstructed:
                fragments = [
                    str(chunk["text"])
                    for chunk in self._db.execute(
                        "SELECT text FROM chunks WHERE document_id=? ORDER BY rowid", (document_id,)
                    )
                ]
                record["content"] = self._reconstruct(fragments)
            return DocumentDetail.model_validate({**record, "reconstructed": reconstructed})

    def add_documents(self, parsed: list[ParsedDocument]) -> list[Document]:
        with self._lock:
            documents: list[Document] = []
            points: list[models.PointStruct] = []
            try:
                self._db.execute("BEGIN IMMEDIATE")
                for item in parsed:
                    fragments = chunks(item.text)
                    document = Document(
                        id=str(uuid.uuid4()),
                        name=item.name,
                        chunks=len(fragments),
                        characters=len(item.text),
                        created_at=datetime.now(UTC).isoformat(),
                    )
                    self._db.execute(
                        "INSERT INTO documents (id,name,chunks,characters,created_at) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            document.id,
                            document.name,
                            document.chunks,
                            document.characters,
                            document.created_at,
                        ),
                    )
                    self._db.execute(
                        "INSERT INTO document_contents (document_id,content) VALUES (?, ?)",
                        (document.id, item.text),
                    )
                    records = [
                        {
                            "id": str(uuid.uuid4()),
                            "document_id": document.id,
                            "document_name": document.name,
                            "text": fragment,
                        }
                        for fragment in fragments
                    ]
                    self._db.executemany(
                        "INSERT INTO chunks (id,document_id,text) VALUES (?, ?, ?)",
                        [(row["id"], row["document_id"], row["text"]) for row in records],
                    )
                    points.extend(self._points(records))
                    documents.append(document)
                for start in range(0, len(points), 64):
                    self._vectors.upsert(self.collection, points[start : start + 64], wait=True)
                self._db.commit()
            except Exception:
                self._db.rollback()
                if points:
                    self._vectors.delete(
                        self.collection,
                        models.PointIdsList(points=[point.id for point in points]),
                        wait=True,
                    )
                raise
            return documents

    def search(self, query: str, limit: int = 5) -> list[Source]:
        with self._lock:
            query_terms = set(terms(query))
            if not query_terms:
                return []
            result = self._vectors.query_points(
                collection_name=self.collection,
                query=self.embedder.embed([query])[0],
                limit=limit * 3,
                score_threshold=0.08 if self.settings.embedding_provider == "hash" else 0.25,
                with_payload=True,
            )
            sources: list[Source] = []
            for point in result.points:
                payload = point.payload or {}
                document_id = str(payload.get("document_id", ""))
                row = self._db.execute(
                    "SELECT c.text, d.name FROM chunks c JOIN documents d ON d.id=c.document_id "
                    "WHERE c.id=? AND d.id=?",
                    (str(point.id), document_id),
                ).fetchone()
                if row is None:
                    continue  # Ignore points left by an interrupted insertion/deletion.
                text, name = str(row["text"]), str(row["name"])
                if self.settings.embedding_provider == "hash" and not query_terms.intersection(
                    terms(text)
                ):
                    continue  # Hash collisions cannot become invented citations.
                sources.append(
                    Source(
                        document_id=document_id,
                        document_name=name,
                        chunk_id=str(point.id),
                        text=text,
                        score=round(float(point.score), 5),
                    )
                )
                if len(sources) == limit:
                    break
            return sources

    def delete(self, document_id: str) -> bool:
        with self._lock:
            if not self._db.execute(
                "SELECT 1 FROM documents WHERE id=?", (document_id,)
            ).fetchone():
                return False
            identifiers = [
                row[0]
                for row in self._db.execute(
                    "SELECT id FROM chunks WHERE document_id=?", (document_id,)
                )
            ]
            self._vectors.delete(
                self.collection,
                models.PointIdsList(points=identifiers),
                wait=True,
            )
            self._db.execute("DELETE FROM documents WHERE id=?", (document_id,))
            self._db.commit()
            return True

    def seed(self, documents: list[ParsedDocument]) -> None:
        with self._lock:
            if self._db.execute("SELECT 1 FROM flags WHERE key='demo_seeded'").fetchone():
                return
            if not self.list_documents().documents:
                self.add_documents(documents)
            self._db.execute("INSERT INTO flags VALUES ('demo_seeded', 'true')")
            self._db.commit()

    def close(self) -> None:
        with self._lock:
            try:
                self._vectors.close()
            finally:
                self._db.close()
