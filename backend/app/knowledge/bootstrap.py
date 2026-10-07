import logging
from pathlib import Path

from app.core.settings import Settings
from app.knowledge.ingestion import SUPPORTED, IngestionError, ParsedDocument, parse_upload
from app.knowledge.store import KnowledgeStore

logger = logging.getLogger(__name__)


def load_initial_knowledge(store: KnowledgeStore, settings: Settings) -> None:
    """Load a configured public corpus once per filename, preserving uploaded documents.

    Top-level TXT, MD, PDF, DOCX, CSV and JSON files are read. A file that cannot be ingested
    is logged and skipped so one bad document does not stop the API. Editing a file that was
    already loaded does not reload it: delete it from the UI first or use a new DATA_DIR.
    """
    directory = settings.knowledge_dir
    if directory is None:
        return
    if not directory.is_absolute():
        directory = Path(__file__).resolve().parents[2] / directory
    if not directory.is_dir() or directory.is_symlink():
        raise IngestionError("El directorio de conocimiento inicial no está disponible.")
    candidates = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and not path.is_symlink() and path.suffix.lower() in SUPPORTED
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
        try:
            parsed, _ = parse_upload(path.name, content, settings)
        except IngestionError as exc:
            logger.warning("Skipped initial knowledge file %s: %s", path.name, exc)
            continue
        documents.extend(parsed)
    if documents:
        store.add_documents(documents)
