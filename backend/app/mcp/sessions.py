"""Private, origin-bound MCP session file: 0600 storage outside the repository and its lock."""

import asyncio
import fcntl
import json
import os
import stat
import tempfile
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from pydantic import BaseModel, ConfigDict, SecretStr

from app.mcp.errors import MCPAuthenticationRequired, MCPUnavailable


def default_session_path() -> Path:
    directory = Path(os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share"))
    if not directory.is_absolute():
        directory = Path.home() / ".local" / "share"
    return directory / "lumen" / "mcp-session.json"


def _session_path(path: Path) -> None:
    """Refuse any session path inside the source checkout (``backend/app/mcp`` -> repo)."""
    source = Path(__file__).resolve().parents[2]
    if source.name == "backend":
        source = source.parent
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError):
        raise MCPAuthenticationRequired from None
    if resolved == source or source in resolved.parents or source in path.absolute().parents:
        raise MCPAuthenticationRequired


class PrivateSession(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    origin: str
    access_token: SecretStr
    refresh_token: SecretStr


def _private_descriptor(path: Path, *, create: bool = False) -> int:
    _session_path(path)
    flags = os.O_RDWR | os.O_CREAT if create else os.O_RDONLY
    descriptor = os.open(path, flags | os.O_NOFOLLOW, 0o600)
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
    ):
        os.close(descriptor)
        raise MCPAuthenticationRequired
    return descriptor


def read_session(path: Path, origin: str) -> PrivateSession:
    try:
        with os.fdopen(_private_descriptor(path), "r", encoding="utf-8") as stream:
            value = stream.read(16385)
        if len(value) > 16384:
            raise ValueError
        session = PrivateSession.model_validate_json(value)
        if (
            session.origin != origin
            or not session.access_token.get_secret_value()
            or not session.refresh_token.get_secret_value()
        ):
            raise ValueError
        return session
    except (OSError, UnicodeError, ValueError):
        raise MCPAuthenticationRequired from None


def write_session(path: Path, session: PrivateSession) -> None:
    """Atomic 0600 replacement; do not follow links or overwrite another user's file."""
    _session_path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    parent = path.parent.stat()
    if parent.st_uid != os.geteuid() or stat.S_IMODE(parent.st_mode) & 0o022:
        raise MCPAuthenticationRequired
    if path.exists() or path.is_symlink():
        read_session(path, session.origin)
    descriptor, temporary = tempfile.mkstemp(prefix=".lumen-session-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(
                {
                    "origin": session.origin,
                    "access_token": session.access_token.get_secret_value(),
                    "refresh_token": session.refresh_token.get_secret_value(),
                },
                stream,
            )
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@asynccontextmanager
async def session_lock(path: Path) -> AsyncIterator[None]:
    """Exclusive cross-process lock beside the session file, bounded to about 8 seconds."""
    _session_path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    parent = path.parent.stat()
    if parent.st_uid != os.geteuid() or stat.S_IMODE(parent.st_mode) & 0o022:
        raise MCPAuthenticationRequired
    if path.exists() or path.is_symlink():
        os.close(_private_descriptor(path))
    descriptor = _private_descriptor(path.with_name(path.name + ".lock"), create=True)
    try:
        deadline = time.monotonic() + 8
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() > deadline:
                    raise MCPUnavailable from None
                await asyncio.sleep(0.02)
        yield
    finally:
        os.close(descriptor)
