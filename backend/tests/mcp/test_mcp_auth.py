import json
import os
import secrets
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from app import manage
from app.core.settings import ROOT, Settings
from app.knowledge.ingestion import ParsedDocument
from app.main import create_app
from app.mcp.auth import (
    MCPAPIClient,
    MCPAuthenticationRequired,
    MCPForbidden,
    MCPUnavailable,
    PrivateSession,
    api_origin,
    default_session_path,
    read_session,
    write_session,
)


def session(
    origin: str = "http://127.0.0.1:8000",
    access: str = "synthetic-access",
    refresh: str = "synthetic-refresh",
) -> PrivateSession:
    return PrivateSession(
        origin=origin, access_token=SecretStr(access), refresh_token=SecretStr(refresh)
    )


@pytest.mark.parametrize(
    "origin",
    [
        "http://api.example",
        "https://user:password@example.invalid",
        "https://example.invalid/api",
        "https://example.invalid?token=placeholder",
        "http://127.0.0.1:99999",
        "https://@example.invalid",
        "https://example.invalid?",
        "https://example.invalid#",
        " https://example.invalid",
        "https://example.invalid\n",
    ],
)
def test_api_origin_rejects_insecure_or_credential_bearing_urls(origin: str) -> None:
    with pytest.raises(ValueError):
        api_origin(origin)


def test_session_file_is_private_origin_bound_and_not_a_configuration_overwrite(
    tmp_path: Path,
) -> None:
    filename = tmp_path / "session.json"
    write_session(filename, session())
    assert filename.stat().st_mode & 0o777 == 0o600
    assert read_session(filename, "http://127.0.0.1:8000").access_token == SecretStr(
        "synthetic-access"
    )
    with pytest.raises(MCPAuthenticationRequired):
        read_session(filename, "https://other.example")
    previous = filename.read_bytes()
    with pytest.raises(MCPAuthenticationRequired):
        write_session(filename, session("https://other.example"))
    assert filename.read_bytes() == previous
    foreign = tmp_path / "unrelated.env"
    foreign.write_text("PUBLIC_SETTING=keep-this-file\n")
    foreign.chmod(0o600)
    with pytest.raises(MCPAuthenticationRequired):
        write_session(foreign, session())
    assert foreign.read_text() == "PUBLIC_SETTING=keep-this-file\n"
    linked = tmp_path / "linked.json"
    linked.symlink_to(filename)
    with pytest.raises(MCPAuthenticationRequired):
        write_session(linked, session())
    filename.chmod(0o644)
    with pytest.raises(MCPAuthenticationRequired):
        read_session(filename, "http://127.0.0.1:8000")
    forbidden = ROOT / "backend" / "synthetic-session-must-not-be-created.json"
    with pytest.raises(MCPAuthenticationRequired):
        write_session(forbidden, session())
    assert not forbidden.exists()


async def test_refresh_rotates_file_and_retries_search_without_printing_secrets(
    tmp_path: Path,
) -> None:
    filename = tmp_path / "session.json"
    write_session(filename, session())
    methods: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if request.url.path == "/api/auth/refresh":
            assert request.headers["X-Requested-With"] == "Humanizar"
            assert request.headers["Cookie"] == "humanizar_refresh=synthetic-refresh"
            return httpx.Response(
                200,
                json={"access_token": "replacement-access"},
                headers={
                    "Set-Cookie": "humanizar_refresh=replacement-refresh; HttpOnly; Path=/api/auth"
                },
            )
        if request.headers.get("Authorization") == "Bearer replacement-access":
            return httpx.Response(200, json={"sources": []})
        return httpx.Response(401)

    client = MCPAPIClient(
        "http://127.0.0.1:8000",
        token_file=filename,
        http=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
    )
    try:
        assert json.loads(await client.get("/api/search", {"query": "support"})) == {"sources": []}
        current = read_session(filename, client.origin)
        assert current.refresh_token == SecretStr("replacement-refresh")
        assert current.access_token == SecretStr("replacement-access")
        assert methods == ["GET", "POST", "GET"]
    finally:
        await client.close()


async def test_two_mcp_clients_share_one_refresh_and_preserve_rotated_family(
    tmp_path: Path,
) -> None:
    import asyncio

    filename = tmp_path / "session.json"
    write_session(filename, session())
    refreshes = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal refreshes
        if request.url.path == "/api/auth/refresh":
            refreshes += 1
            await asyncio.sleep(0.03)
            return httpx.Response(
                200,
                json={"access_token": "replacement-access"},
                headers={
                    "Set-Cookie": "humanizar_refresh=replacement-refresh; HttpOnly; Path=/api/auth"
                },
            )
        if request.headers.get("Authorization") == "Bearer replacement-access":
            return httpx.Response(200, json={"sources": []})
        return httpx.Response(401)

    clients = [
        MCPAPIClient(
            "http://127.0.0.1:8000",
            token_file=filename,
            http=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
        )
        for _ in range(2)
    ]
    try:
        results = await asyncio.gather(*(client.get("/api/search") for client in clients))
        assert all(json.loads(result) == {"sources": []} for result in results)
        assert refreshes == 1
    finally:
        await asyncio.gather(*(client.close() for client in clients))


async def test_real_stdio_mcp_authenticates_to_protected_api(settings: Settings) -> None:
    import sys
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from fastapi.testclient import TestClient
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import TextContent

    application = create_app(settings.model_copy(update={"auth_enabled": True}))
    with TestClient(application) as api:
        setup = api.post(
            "/api/auth/setup",
            json={
                "name": "Synthetic",
                "email": "synthetic@example.test",
                "password": secrets.token_urlsafe(18),
            },
        )
        token = setup.json()["access_token"]
        application.state.store.add_documents([ParsedDocument("known.md", "Soporte documentado")])

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, _format: str, *_args: Any) -> None:
                pass

            def do_GET(self) -> None:
                result = api.get(
                    self.path, headers={"Authorization": self.headers.get("Authorization", "")}
                )
                self.send_response(result.status_code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(result.content)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            for supplied, expected_error in ((token, False), ("invalid-synthetic-jwt", True)):
                parameters = StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "app.mcp.server"],
                    env={
                        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                        "LUMEN_API_URL": f"http://127.0.0.1:{server.server_port}",
                        "LUMEN_API_TOKEN": supplied,
                    },
                )
                async with (
                    stdio_client(parameters) as (reader, writer),
                    ClientSession(reader, writer) as connection,
                ):
                    await connection.initialize()
                    result = await connection.call_tool("search_knowledge", {"query": "Soporte"})
                    text = "\n".join(
                        block.text for block in result.content if isinstance(block, TextContent)
                    )
                    assert bool(result.isError) is expected_error
                    assert "401" in text if expected_error else "known.md" in text
                    assert supplied not in text
                    identity = await connection.call_tool("company_info", {})
                    assert not identity.isError
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)


@pytest.mark.parametrize(
    "status,error", [(401, MCPAuthenticationRequired), (403, MCPForbidden), (503, MCPUnavailable)]
)
async def test_refresh_errors_preserve_private_session(
    tmp_path: Path, status: int, error: type[ValueError]
) -> None:
    filename = tmp_path / "session.json"
    write_session(filename, session())
    previous = filename.read_bytes()

    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status if request.method == "POST" else 401)

    client = MCPAPIClient(
        "http://127.0.0.1:8000",
        token_file=filename,
        http=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
    )
    try:
        with pytest.raises(error) as failure:
            await client.get("/api/search")
        assert filename.read_bytes() == previous
        assert "synthetic-refresh" not in str(failure.value)
        assert "synthetic-access" not in str(failure.value)
    finally:
        await client.close()


async def test_public_company_identity_never_reads_invalid_auth_file(tmp_path: Path) -> None:
    filename = tmp_path / "missing.json"

    def handle(request: httpx.Request) -> httpx.Response:
        assert "Authorization" not in request.headers
        return httpx.Response(200, json={"company_name": "Synthetic"})

    client = MCPAPIClient(
        "http://127.0.0.1:8000",
        token_file=filename,
        http=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
    )
    try:
        assert "Synthetic" in await client.get("/api/company")
    finally:
        await client.close()


async def test_cli_and_mcp_share_xdg_session_location(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.delenv("LUMEN_API_TOKEN", raising=False)
    monkeypatch.delenv("LUMEN_API_TOKEN_FILE", raising=False)
    filename = default_session_path()
    write_session(filename, session())
    client = MCPAPIClient.from_environment()
    try:
        assert client._file == filename
        assert filename == tmp_path / "lumen" / "mcp-session.json"
    finally:
        await client.close()


async def test_mcp_real_api_search_requires_auth_and_refresh_works(
    settings: Settings, tmp_path: Path
) -> None:
    application = create_app(settings.model_copy(update={"auth_enabled": True}))
    async with application.router.lifespan_context(application):
        application.state.store.add_documents([ParsedDocument("support.md", "Soporte documentado")])
        http = httpx.AsyncClient(transport=httpx.ASGITransport(app=application))
        client = MCPAPIClient("http://127.0.0.1:8000", http=http)
        filename = tmp_path / "auth" / "session.json"
        try:
            with pytest.raises(MCPAuthenticationRequired):
                await client.get("/api/search", {"query": "Soporte"})
            password = secrets.token_urlsafe(18)
            bootstrap = await http.post(
                client.origin + "/api/auth/setup",
                json={
                    "name": "Synthetic operator",
                    "email": "owner@example.test",
                    "password": password,
                },
            )
            assert bootstrap.status_code == 200
            await client.login("owner@example.test", password, filename)
            private = read_session(filename, client.origin)
            write_session(
                filename,
                private.model_copy(update={"access_token": SecretStr("expired-placeholder")}),
            )
            client._file = filename
            result = json.loads(await client.get("/api/search", {"query": "Soporte"}))
            assert result["sources"][0]["document_name"] == "support.md"
            assert read_session(filename, client.origin).access_token != SecretStr(
                "expired-placeholder"
            )
        finally:
            await client.close()


def test_cli_login_uses_hidden_input_and_generic_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    filename = tmp_path / "session.json"
    monkeypatch.setattr("builtins.input", lambda _prompt: "synthetic@example.test")
    monkeypatch.setattr("app.manage.getpass.getpass", lambda _prompt: "synthetic-password")

    async def login(self: MCPAPIClient, email: str, password: str, path: Path) -> None:
        assert email == "synthetic@example.test" and password == "synthetic-password"
        write_session(path, session(self.origin))

    monkeypatch.setattr(MCPAPIClient, "login", login)
    assert manage.main(["mcp-login", "--token-file", str(filename)]) == 0
    output = capsys.readouterr()
    assert "synthetic-password" not in output.out + output.err
    assert "synthetic-access" not in output.out + output.err
    assert filename.exists()


async def test_login_never_overwrites_non_session_or_changes_origin(tmp_path: Path) -> None:
    filename = tmp_path / "private.env"
    filename.write_text("KEEP=existing-config")
    filename.chmod(0o600)
    calls: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200)

    client = MCPAPIClient(
        "http://127.0.0.1:8000", http=httpx.AsyncClient(transport=httpx.MockTransport(handle))
    )
    try:
        with pytest.raises(MCPAuthenticationRequired):
            await client.login("owner@example.test", "synthetic-password", filename)
        assert calls == [] and filename.read_text() == "KEEP=existing-config"
    finally:
        await client.close()
