from pathlib import Path

from app.ingestion import IngestionError, ParsedDocument, parse_upload
from app.settings import Settings
from app.storage import KnowledgeStore


def load_initial_knowledge(store: KnowledgeStore, settings: Settings) -> None:
    """Load a configured public corpus once per filename, preserving uploaded documents."""
    directory = settings.knowledge_dir
    if directory is None:
        return
    if not directory.is_absolute():
        directory = Path(__file__).resolve().parents[1] / directory
    if not directory.is_dir() or directory.is_symlink():
        raise IngestionError("El directorio de conocimiento inicial no está disponible.")
    candidates = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and not path.is_symlink() and path.suffix.lower() in {".md", ".txt"}
    )
    if len(candidates) > settings.max_archive_files:
        raise IngestionError("El corpus inicial excede el límite de documentos.")
    existing = {document.name for document in store.list_documents().documents}
    documents: list[ParsedDocument] = []
    for path in candidates:
        if path.name in existing:
            continue
        with path.open("rb") as stream:
            content = stream.read(settings.max_upload_mb * 1024 * 1024 + 1)
        parsed, _ = parse_upload(path.name, content, settings)
        documents.extend(parsed)
    if documents:
        store.add_documents(documents)
