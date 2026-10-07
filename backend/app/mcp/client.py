"""Authenticated, read-only Lumen API client used by the MCP server and ``mcp-login``."""

import asyncio
import ipaddress
import os
from contextlib import suppress
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
from pydantic import SecretStr

from app.accounts.tokens import REFRESH_COOKIE
from app.core.concurrency import run_sync
from app.mcp.errors import MCPAuthenticationRequired, MCPForbidden, MCPUnavailable
from app.mcp.sessions import (
    PrivateSession,
    default_session_path,
    read_session,
    session_lock,
    write_session,
)


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
            async with session_lock(token_file):
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
        async with session_lock(self._file):
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
