"""Structural ZIP validation: safe paths, member types, size limits and private paths."""

from __future__ import annotations

import stat
import unicodedata
import zipfile
from pathlib import PurePosixPath, PureWindowsPath

from .limits import MAX_ENTRIES, MAX_ENTRY_BYTES, MAX_RATIO, MAX_TOTAL_BYTES

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


class UnsafeArchive(ValueError):
    """An archive failed structural validation; no members may be imported."""


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
        if not forbidden(name):
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
