#!/usr/bin/env python3
"""Inspect examiner ZIPs without extracting or executing their code.

Run with ``uv run --project backend --extra semantic python scripts/import-material.py ZIP``.
The default saves material locally without network requests. Explicit ``--upload``
requires the private LUMEN_API_TOKEN environment variable for an administrator.
Only sanitized text is persisted. PDF/DOCX company documents are converted to text;
PDF support uses the backend's pypdf dependency. No project dependencies are imported.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import logging
import os
import re
import resource
import stat
import subprocess
import sys
import unicodedata
import uuid
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from urllib import error, parse, request
from xml.etree import ElementTree

MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_ENTRY_BYTES = 8 * 1024 * 1024
MAX_ENTRIES = 256
MAX_RATIO = 100
MAX_TEXT_CHARS = 1_000_000
SUPPORTED = {".txt", ".md", ".csv", ".json", ".pdf", ".docx"}
FORBIDDEN_PARTS = {
    ".git",
    ".svn",
    ".hg",
    ".ssh",
    ".aws",
    ".kube",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "credentials",
    "secrets",
    "settings.local.json",
    "id_rsa",
    "id_ed25519",
    ".npmrc",
    ".pypirc",
    ".netrc",
    ".password-store",
    ".codex",
    ".credentials.json",
}
CLAUDE_PRIVATE_PARTS = {"projects", "sessions", "transcripts", "history", "debug"}
CLAUDE_PRIVATE_FILES = {"settings.json", "settings.local.json", "history.jsonl"}
PROJECT_DOCUMENT = re.compile(
    r"(?:^|[/_. -])(?:readme|requirements?|requisitos?|consignas?|enunciado|spec|"
    r"specification|instructions?|instrucciones|architecture|arquitectura|tasks?|plan|"
    r"r[uú]bricas?|rubrics?|brief|goals?|objetivos?|docs|documentation)"
    r"(?:[/_. -]|$)",
    re.IGNORECASE,
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(
        r"\b(?:sk-ant-[\w-]{8,}|sk-[\w-]{16,}|gh[pousr]_[\w]{16,}|github_pat_[\w]{16,}|AKIA[A-Z0-9]{16})\b"
    ),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"""(?im)\b(?:proxy[-_ ]?)?authorization\b[ \t*`"']*[:=][ \t]*[^\r\n]+"""),
    re.compile(
        r"""(?im)(["']?\b(?:[A-Z_]*(?:API_KEY|ACCESS_TOKEN|AUTH_TOKEN|SECRET|PASSWORD)|token|cookie)["']?\s*[:=,]\s*)(["']?)[^\r\n,;]+"""
    ),
)
SENSITIVE_FIELD = re.compile(r"(?i)(?:api[_-]?key|password|secret|token|cookie|authorization)")


class UnsafeArchive(ValueError):
    """An archive failed structural validation; no members may be imported."""


class UploadAuthenticationError(ValueError):
    """An upload was rejected; its message never includes response bodies or tokens."""


@dataclass(frozen=True)
class AcceptedDocument:
    name: str
    data: bytes
    project_document: bool


def clean_path(info: zipfile.ZipInfo) -> str:
    raw = info.orig_filename
    name = unicodedata.normalize("NFKC", raw)
    pieces = name.rstrip("/").split("/")
    if (
        not name
        or len(name) > 240
        or "\\" in name
        or ":" in name
        or any(ord(char) < 32 or ord(char) == 127 for char in name)
        or PurePosixPath(name).is_absolute()
        or PureWindowsPath(name).drive
        or any(piece in {"", ".", ".."} or len(piece.encode("utf-8")) > 180 for piece in pieces)
        or len(pieces) > 12
    ):
        raise UnsafeArchive("Archive contains an unsafe path.")
    return "/".join(pieces)


def inspect_archive(archive: zipfile.ZipFile) -> list[tuple[zipfile.ZipInfo, str]]:
    entries = archive.infolist()
    if len(entries) > MAX_ENTRIES:
        raise UnsafeArchive("Archive contains too many entries.")
    seen: set[str] = set()
    total = 0
    result: list[tuple[zipfile.ZipInfo, str]] = []
    for info in entries:
        name = clean_path(info)
        normalized = name.casefold()
        if normalized in seen:
            raise UnsafeArchive("Archive contains duplicate or equivalent paths.")
        seen.add(normalized)
        mode = info.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if kind not in {0, stat.S_IFREG, stat.S_IFDIR}:
            raise UnsafeArchive("Archive contains a symlink or special file.")
        if info.flag_bits & 1:
            raise UnsafeArchive("Encrypted archives are not supported.")
        if info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
            raise UnsafeArchive("Archive uses unsupported compression.")
        total += info.file_size
        if (
            info.file_size > MAX_ENTRY_BYTES
            or total > MAX_TOTAL_BYTES
            or info.file_size > max(1, info.compress_size) * MAX_RATIO
        ):
            raise UnsafeArchive("Archive exceeds size or compression limits.")
        if not info.is_dir():
            result.append((info, name))
    return result


def forbidden(name: str) -> bool:
    parts = unicodedata.normalize("NFKC", name).casefold().split("/")
    for index, part in enumerate(parts[:-1]):
        if part == ".claude" and (
            parts[index + 1] in CLAUDE_PRIVATE_PARTS or parts[index + 1] in CLAUDE_PRIVATE_FILES
        ):
            return True
    return any(
        part in FORBIDDEN_PARTS
        or part.startswith(".env")
        or part.endswith((".pem", ".key", ".token", ".p12", ".pfx", ".log"))
        or part.startswith("credentials.")
        or part.startswith("secrets.")
        for part in parts
    )


def bounded_read(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
    with archive.open(info) as stream:
        data = stream.read(MAX_ENTRY_BYTES + 1)
        if len(data) > MAX_ENTRY_BYTES or len(data) != info.file_size:
            raise UnsafeArchive("Archive member exceeded its declared size.")
        return data


def sanitize(text: str) -> str:
    if len(text) > MAX_TEXT_CHARS or "\x00" in text:
        raise ValueError("Document exceeds text limits or contains null bytes.")
    for pattern in SECRET_PATTERNS:
        if pattern is SECRET_PATTERNS[-1]:
            text = pattern.sub(lambda match: f'{match.group(1)}"[REDACTED]"', text)
        else:
            text = pattern.sub("[REDACTED]", text)
    return text


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
                [sys.executable, "-I", str(Path(__file__).resolve()), "--internal-pdf-text"],
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
        (resource.RLIMIT_AS, 256 * 1024 * 1024),
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


def sanitize_document(text: str, suffix: str) -> str:
    if suffix == ".json":
        if len(text) > MAX_TEXT_CHARS:
            raise ValueError("JSON exceeds text limit.")

        def clean(value: Any, depth: int = 0) -> Any:
            if depth > 32:
                raise ValueError("JSON nesting exceeds limit.")
            if isinstance(value, dict):
                return {
                    sanitize(str(key)): "[REDACTED]"
                    if SENSITIVE_FIELD.search(str(key))
                    else clean(item, depth + 1)
                    for key, item in value.items()
                }
            if isinstance(value, list):
                return [clean(item, depth + 1) for item in value]
            if isinstance(value, str):
                return sanitize(value)
            return value

        return json.dumps(clean(json.loads(text)), ensure_ascii=False, indent=2)
    if suffix == ".csv":
        if len(text) > MAX_TEXT_CHARS:
            raise ValueError("CSV exceeds text limit.")
        rows = csv.reader(io.StringIO(text))
        output = io.StringIO()
        writer = csv.writer(output)
        header = next(rows, [])
        sensitive = {index for index, value in enumerate(header) if SENSITIVE_FIELD.search(value)}
        writer.writerow([sanitize(value) for value in header])
        for row in rows:
            writer.writerow(
                [
                    "[REDACTED]" if index in sensitive else sanitize(value)
                    for index, value in enumerate(row)
                ]
            )
        return output.getvalue()
    return sanitize(text)


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
            if forbidden(name) or suffix not in SUPPORTED:
                report["skipped"].append(
                    {"entry": index, "reason": "unsupported or sensitive file"}
                )
                continue
            data = bounded_read(archive, info)
            try:
                text = sanitize_document(document_text(data, suffix), suffix)
            except UnsafeArchive:
                raise
            except Exception:
                report["skipped"].append(
                    {"entry": index, "reason": "invalid or unsupported document"}
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


def store_documents(
    documents: list[AcceptedDocument], report: dict[str, Any], destination: Path
) -> Path:
    if destination.is_symlink():
        raise ValueError("Material directory cannot be a symlink.")
    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = destination / f"import-{stamp}-{uuid.uuid4().hex[:12]}"
    target.mkdir(mode=0o700, exist_ok=False)
    for document in documents:
        with (target / document.name).open("xb") as stream:
            stream.write(document.data)
    with (target / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return target


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def validate_backend_url(url: str) -> str:
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in url):
        raise ValueError("Backend URL must be an HTTP numeric loopback origin.")
    parsed = parse.urlsplit(url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "::1"}
        or parsed.username is not None
        or parsed.password is not None
        or "?" in url
        or "#" in url
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("Backend URL must be an HTTP numeric loopback origin.")
    try:
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("Invalid backend port.")
    except ValueError as exc:
        raise ValueError("Invalid backend port.") from exc
    return url.rstrip("/")


def validate_api_token(token: str | None) -> str:
    if (
        token is None
        or re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", token) is None
    ):
        raise ValueError("Set LUMEN_API_TOKEN to an administrator JWT access token for --upload.")
    return token


def upload_document(document: AcceptedDocument, backend_url: str, api_token: str) -> None:
    backend_url = validate_backend_url(backend_url)
    api_token = validate_api_token(api_token)
    boundary = f"lumen-{uuid.uuid4().hex}"
    # Filename is generated, but quote it to ASCII for multipart interoperability.
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", document.name)
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: text/plain; charset=utf-8\r\n\r\n"
    ).encode("ascii")
    payload = head + document.data + f"\r\n--{boundary}--\r\n".encode("ascii")
    message = request.Request(
        f"{backend_url}/api/documents",
        data=payload,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {api_token}",
        },
    )
    # Proxy environment and redirects cannot send document bodies to another service.
    opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(message, timeout=20) as response:
            if response.status != 200:
                raise ValueError("Backend rejected document upload.")
            response.read(64 * 1024)
    except error.HTTPError as exc:
        if exc.code == 401:
            raise UploadAuthenticationError(
                "Upload authentication failed (401); refresh the administrator LUMEN_API_TOKEN."
            ) from None
        if exc.code == 403:
            raise UploadAuthenticationError(
                "Upload forbidden (403); LUMEN_API_TOKEN must belong to an administrator."
            ) from None
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    upload_mode = parser.add_mutually_exclusive_group()
    upload_mode.add_argument(
        "--upload",
        action="store_true",
        help="Upload reviewed company documents to the local API using LUMEN_API_TOKEN.",
    )
    upload_mode.add_argument(
        "--no-upload",
        action="store_false",
        dest="upload",
        help="Inspect and save sanitized material only (the default).",
    )
    parser.set_defaults(upload=False)
    args = parser.parse_args(argv)
    try:
        backend_url = validate_backend_url(args.backend_url)
        api_token = validate_api_token(os.environ.get("LUMEN_API_TOKEN")) if args.upload else None
    except ValueError:
        print(
            "Upload configuration rejected: use an HTTP numeric loopback origin and "
            "set LUMEN_API_TOKEN to an administrator JWT for --upload.",
            file=sys.stderr,
        )
        return 2
    try:
        documents, report = collect_documents(args.zip_path)
        destination = Path(__file__).resolve().parent.parent / "material"
        target = store_documents(documents, report, destination)
        uploaded = 0
        failures = 0
        if api_token is not None:
            for document in documents:
                if document.project_document:
                    continue
                try:
                    upload_document(document, backend_url, api_token)
                    uploaded += 1
                except UploadAuthenticationError as exc:
                    failures += 1
                    print(str(exc), file=sys.stderr)
                    break
                except (OSError, ValueError, error.URLError):
                    failures += 1
        print(f"Saved {len(documents)} sanitized documents to {target}.")
        print(
            f"Skipped {len(report['skipped'])} entries; uploaded {uploaded}; "
            f"upload failures {failures}."
        )
        return 1 if failures else 0
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError):
        print(
            "Import rejected: invalid archive, unsafe member, size limit or unavailable path.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(internal_pdf_text() if sys.argv[1:] == ["--internal-pdf-text"] else main())
