"""Text extraction: bounded DOCX XML and PDF parsing in a resource-limited subprocess."""

from __future__ import annotations

import io
import logging
import resource
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .archive import bounded_read, inspect_archive
from .limits import MAX_ENTRY_BYTES, MAX_TEXT_CHARS

# The PDF worker re-runs this trusted entry script; archive content is only ever stdin.
ENTRY_SCRIPT = Path(__file__).resolve().parent.parent / "import-material.py"


def document_text(data: bytes, suffix: str) -> str:
    if suffix == ".docx":
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = inspect_archive(archive)
            document = next((info for info, name in entries if name == "word/document.xml"), None)
            if document is None or not any(name == "[Content_Types].xml" for _, name in entries):
                raise ValueError("Invalid DOCX document.")
            xml = bounded_read(archive, document).decode("utf-8-sig", errors="strict")
            if "\x00" in xml or "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
                raise ValueError("DOCX contains forbidden XML declarations.")
            tree = ElementTree.fromstring(xml)
            return "\n".join(node.text or "" for node in tree.iter() if node.tag.endswith("}t"))
    if suffix == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise ValueError("Invalid PDF document.")
        try:
            result = subprocess.run(
                [sys.executable, "-I", str(ENTRY_SCRIPT), "--internal-pdf-text"],
                input=data,
                capture_output=True,
                timeout=6,
                check=False,
                env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"},
                preexec_fn=limit_pdf_parser,
                start_new_session=True,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError("PDF conversion failed or exceeded its limit.") from exc
        if result.returncode != 0 or len(result.stdout) > MAX_TEXT_CHARS * 4:
            raise ValueError(
                "PDF conversion requires backend dependencies and a valid bounded PDF."
            )
        return result.stdout.decode("utf-8", errors="strict")
    return data.decode("utf-8-sig", errors="strict")


def limit_pdf_parser() -> None:
    for limit, maximum in (
        (resource.RLIMIT_CPU, 4),
        # Python with pypdf already maps ~255 MiB; 256 MiB made every PDF fail.
        (resource.RLIMIT_AS, 512 * 1024 * 1024),
        (resource.RLIMIT_FSIZE, 0),
        (resource.RLIMIT_CORE, 0),
        (resource.RLIMIT_NPROC, 16),
    ):
        resource.setrlimit(limit, (maximum, maximum))


def internal_pdf_text() -> int:
    """Trusted parser process: bounded bytes in, bounded text out, no user code or files."""
    try:
        logging.disable(logging.CRITICAL)
        from pypdf import PdfReader  # type: ignore[import-not-found]

        data = sys.stdin.buffer.read(MAX_ENTRY_BYTES + 1)
        if len(data) > MAX_ENTRY_BYTES or not data.startswith(b"%PDF-"):
            return 2
        reader = PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted or len(reader.pages) > 64:
            return 2
        parts = []
        size = 0
        for page in reader.pages:
            text = page.extract_text() or ""
            size += len(text)
            if size > MAX_TEXT_CHARS:
                return 2
            parts.append(text)
        sys.stdout.buffer.write("\n".join(parts).encode("utf-8"))
        return 0
    except Exception:
        return 2
