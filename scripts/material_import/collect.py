"""Turn one ZIP into sanitized, flat-named documents plus a content-free report."""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .archive import UnsafeArchive, bounded_read, forbidden, inspect_archive
from .documents import document_text
from .limits import MAX_ARCHIVE_BYTES
from .sanitize import sanitize, sanitize_document

SUPPORTED = {".txt", ".md", ".csv", ".json", ".pdf", ".docx"}
PROJECT_DOCUMENT = re.compile(
    r"(?:^|[/_. -])(?:readme|requirements?|requisitos?|consignas?|enunciado|spec|"
    r"specification|instructions?|instrucciones|architecture|arquitectura|tasks?|plan|"
    r"r[uú]bricas?|rubrics?|brief|goals?|objetivos?|docs|documentation)"
    r"(?:[/_. -]|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AcceptedDocument:
    name: str
    data: bytes
    project_document: bool


def collect_documents(source: Path) -> tuple[list[AcceptedDocument], dict[str, Any]]:
    if source.stat().st_size > MAX_ARCHIVE_BYTES:
        raise UnsafeArchive("ZIP exceeds 20 MiB compressed limit.")
    with source.open("rb") as stream:
        raw_zip = stream.read(MAX_ARCHIVE_BYTES + 1)
    if len(raw_zip) > MAX_ARCHIVE_BYTES:
        raise UnsafeArchive("ZIP exceeds 20 MiB compressed limit.")
    fingerprint = hashlib.sha256(raw_zip).hexdigest()
    documents = []
    report: dict[str, Any] = {"sha256": fingerprint, "accepted": [], "skipped": []}
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
        entries = inspect_archive(archive)
        report["entries"] = len(entries)
        for index, (info, name) in enumerate(entries, start=1):
            suffix = PurePosixPath(name).suffix.casefold()
            if forbidden(name):
                report["skipped"].append({"entry": index, "reason": "sensitive or runtime file"})
                continue
            if suffix not in SUPPORTED:
                # Report the sanitized name so input/output examples (YAML, SQL, images,
                # code) are visible to the reader instead of silently disappearing.
                report["skipped"].append(
                    {"entry": index, "name": sanitize(name)[:160], "reason": "unsupported format"}
                )
                continue
            data = bounded_read(archive, info)
            try:
                text = sanitize_document(document_text(data, suffix), suffix)
            except UnsafeArchive:
                raise
            except Exception:
                report["skipped"].append(
                    {
                        "entry": index,
                        "name": sanitize(name)[:160],
                        "reason": "invalid document or missing parser (use uv --project backend)",
                    }
                )
                continue
            if not text.strip():
                report["skipped"].append({"entry": index, "reason": "empty document"})
                continue
            # Generated flat filenames avoid all archive path and header ambiguities.
            leaf = PurePosixPath(name).stem
            leaf = re.sub(r"[^\w.-]", "_", sanitize(leaf), flags=re.UNICODE)[:80] or "document"
            output_suffix = suffix if suffix in {".md", ".csv", ".json", ".txt"} else ".txt"
            filename = f"{index:03d}-{leaf}{output_suffix}"
            project = bool(PROJECT_DOCUMENT.search(name))
            documents.append(AcceptedDocument(filename, text.encode("utf-8"), project))
            report["accepted"].append({"name": filename, "project_document": project})
    return documents, report
