"""Authenticated API access for read-only MCP, with private origin-bound sessions."""

import asyncio
import fcntl
import ipaddress
import json
import os
import stat
import tempfile
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, SecretStr

from app.accounts.auth import REFRESH_COOKIE
from app.core.concurrency import run_sync


class MCPAuthenticationRequired(ValueError):
    def __init__(self) -> None:
        super().__init__(
            "API authentication required (401). Run the private mcp-login CLI "
            "or renew LUMEN_API_TOKEN."
        )


class MCPForbidden(ValueError):
    def __init__(self) -> None:
        super().__init__("API access forbidden (403) for this account.")


class MCPUnavailable(ValueError):
    def __init__(self) -> None:
        super().__init__(
            "Lumen API unavailable. Verify the API connection privately; "
            "the saved session is preserved."
        )


def default_session_path() -> Path:
    directory = Path(os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share"))
    if not directory.is_absolute():
        directory = Path.home() / ".local" / "share"
    return directory / "lumen" / "mcp-session.json"


def _session_path(path: Path) -> None:
    source = Path(__file__).resolve().parents[2]
    if source.name == "backend":
        source = source.parent
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError):
        raise MCPAuthenticationRequired from None
    if resolved == source or source in resolved.parents or source in path.absolute().parents:
        raise MCPAuthenticationRequired


def api_origin(value: str) -> str:
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname or ""
        loopback = hostname.casefold() == "localhost"
        with suppress(ValueError):
            loopback = loopback or ipaddress.ip_address(hostname).is_loopback
        valid = (
            hostname
            and parsed.username is None
            and parsed.password is None
            and "?" not in value
            and "#" not in value
            and not any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)
            and not parsed.query
            and not parsed.fragment
            and parsed.path in {"", "/"}
            and (parsed.port is None or 1 <= parsed.port <= 65535)
            and (parsed.scheme == "https" or (parsed.scheme == "http" and loopback))
        )
        if not valid:
            raise ValueError
        return str(httpx.URL(value)).rstrip("/")
    except (ValueError, httpx.InvalidURL):
        raise ValueError(
            "Use an HTTPS API origin or HTTP loopback, without credentials or paths."
        ) from None


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
async def _refresh_lock(path: Path) -> AsyncIterator[None]:
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


class MCPAPIClient:
    def __init__(
        self,
        origin: str,
        token: str = "",
        token_file: Path | None = None,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self.origin = api_origin(origin)
        self._token = token
        self._file = token_file
        self.http = http or httpx.AsyncClient(timeout=8, follow_redirects=False, trust_env=False)
        self._lock = asyncio.Lock()

    @classmethod
    def from_environment(cls, *, read_auth: bool = True) -> "MCPAPIClient":
        if not read_auth:
            return cls(os.environ.get("LUMEN_API_URL", "http://127.0.0.1:8000"))
        token = os.environ.get("LUMEN_API_TOKEN", "")
        if token:
            return cls(os.environ.get("LUMEN_API_URL", "http://127.0.0.1:8000"), token)
        filename = os.environ.get("LUMEN_API_TOKEN_FILE", "")
        token_file = Path(filename) if filename else default_session_path()
        return cls(
            os.environ.get("LUMEN_API_URL", "http://127.0.0.1:8000"),
            "",
            token_file if filename or token_file.exists() else None,
        )

    def _check(self, response: httpx.Response) -> None:
        if response.status_code == 401:
            raise MCPAuthenticationRequired
        if response.status_code == 403:
            raise MCPForbidden
        if not response.is_success:
            raise MCPUnavailable

    async def login(self, email: str, password: str, token_file: Path) -> None:
        try:
            async with _refresh_lock(token_file):
                if token_file.exists():
                    await run_sync(read_session, token_file, self.origin)
                response = await self.http.post(
                    self.origin + "/api/auth/login", json={"email": email, "password": password}
                )
                self._check(response)
                session = self._response_session(response)
                await run_sync(write_session, token_file, session)
        except (httpx.HTTPError, OSError):
            raise MCPUnavailable from None

    def _response_session(self, response: httpx.Response) -> PrivateSession:
        try:
            payload: Any = response.json()
            access = payload["access_token"]
            refresh = response.cookies.get(REFRESH_COOKIE)
            if not isinstance(access, str) or not access or not refresh:
                raise ValueError
            return PrivateSession(
                origin=self.origin, access_token=SecretStr(access), refresh_token=SecretStr(refresh)
            )
        except (ValueError, KeyError, TypeError, httpx.CookieConflict):
            raise MCPUnavailable from None

    async def _refresh(self, previous: PrivateSession) -> PrivateSession:
        assert self._file is not None
        async with _refresh_lock(self._file):
            current = await run_sync(read_session, self._file, self.origin)
            if current.access_token != previous.access_token:
                return current
            response = await self.http.post(
                self.origin + "/api/auth/refresh",
                headers={
                    "X-Requested-With": "Humanizar",
                    "Cookie": f"{REFRESH_COOKIE}={current.refresh_token.get_secret_value()}",
                },
            )
            self._check(response)
            replacement = self._response_session(response)
            await run_sync(write_session, self._file, replacement)
            return replacement

    async def get(self, path: str, params: dict[str, str] | None = None) -> str:
        if path not in {"/api/company", "/api/search"}:
            raise MCPForbidden
        try:
            async with self._lock:
                session = None
                if path != "/api/company" and self._file is not None and not self._token:
                    session = await run_sync(read_session, self._file, self.origin)
                token = (
                    ""
                    if path == "/api/company"
                    else self._token or (session.access_token.get_secret_value() if session else "")
                )
                response = await self.http.get(
                    self.origin + path,
                    params=params,
                    headers={"Authorization": f"Bearer {token}"} if token else {},
                )
                if response.status_code == 401 and session is not None:
                    session = await self._refresh(session)
                    response = await self.http.get(
                        self.origin + path,
                        params=params,
                        headers={
                            "Authorization": f"Bearer {session.access_token.get_secret_value()}"
                        },
                    )
                self._check(response)
                return response.text
        except (httpx.HTTPError, OSError):
            raise MCPUnavailable from None

    async def close(self) -> None:
        await self.http.aclose()
