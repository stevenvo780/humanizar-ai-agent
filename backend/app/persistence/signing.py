"""Private per-installation master secret and the access-token key derived from it."""

import hmac
import os
import secrets
import stat
import uuid
from pathlib import Path


def master_secret(directory: Path) -> bytes:
    """Link a fully written private random file into place, never replace an existing secret."""
    target = directory / ".application-secret"
    temporary = directory / f".application-secret-{uuid.uuid4().hex}.tmp"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(secrets.token_bytes(32))
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary, target)
            parent = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(parent)
            finally:
                os.close(parent)
        except FileExistsError:
            pass
    finally:
        temporary.unlink(missing_ok=True)
    descriptor = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise RuntimeError("El archivo de seguridad debe ser regular y privado (0600).")
        with os.fdopen(descriptor, "rb") as source:
            descriptor = -1
            value = source.read(33)
        if len(value) != 32:
            raise RuntimeError("El archivo de seguridad no es válido.")
        return value
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def access_key(master: bytes) -> bytes:
    return hmac.digest(master, b"humanizar.access.v1", "sha256")


def signing_secret(data_dir: Path, override: bytes | None = None) -> bytes:
    data_dir.mkdir(parents=True, exist_ok=True)
    if override is not None:
        return override
    return access_key(master_secret(data_dir))
