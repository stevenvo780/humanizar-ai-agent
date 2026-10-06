from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

import pytest
from app import main
from fastapi.testclient import TestClient

client = TestClient(main.app)


@pytest.mark.parametrize(
    "command",
    [
        "ls /",
        "pwd; cat /etc/passwd",
        "$(id)",
        "python -c 'print(1)'",
        "curl example.com",
        "wc x",
        " ls",
        "ls\n",
    ],
)
def test_rejects_arguments_and_shell_injection(command: str) -> None:
    with patch.object(main.subprocess, "Popen") as spawn:
        response = client.post("/run", json={"command": command})
    assert response.status_code == 400
    spawn.assert_not_called()


def test_refuses_host_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LUMEN_SANDBOX_CONTAINER", raising=False)
    assert client.get("/health").status_code == 503
    with patch.object(main.subprocess, "Popen") as spawn:
        assert client.post("/run", json={"command": "pwd"}).status_code == 503
    spawn.assert_not_called()


def test_refuses_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMEN_SANDBOX_CONTAINER", "1")
    monkeypatch.setattr(main.os, "geteuid", lambda: 0)
    assert not main.isolated_runtime()


def test_extra_fields_forbidden() -> None:
    assert client.post("/run", json={"command": "pwd", "cwd": "/"}).status_code == 422


@contextmanager
def fake_process(payload: bytes, *, keep_open: bool = False) -> Iterator[Any]:
    """Exercise bounded pipe reading without executing any subprocess on the host."""
    from types import SimpleNamespace

    descriptors: list[int] = []
    streams = []
    for data in (payload, b""):
        reader, writer = os.pipe()
        descriptors.append(writer)
        if data:
            os.write(writer, data)
        streams.append(os.fdopen(reader, "rb"))
        if not keep_open:
            os.close(writer)
            descriptors.pop()
    process = SimpleNamespace(
        stdout=streams[0], stderr=streams[1], pid=99999999, returncode=0, wait=lambda **_: 0
    )
    try:
        yield process
    finally:
        for stream in streams:
            stream.close()
        for descriptor in descriptors:
            os.close(descriptor)


def test_fixed_exec_and_environment() -> None:
    with patch.object(main.subprocess, "Popen", return_value=fake_process(b"fixture\n")) as spawn:
        result = main.execute_preset("pwd")
    assert result.stdout == "fixture\n"
    assert result.exit_code == 0
    options = spawn.call_args.kwargs
    assert spawn.call_args.args[0] == ("/usr/bin/pwd",)
    assert options["shell"] is False
    assert options["cwd"] == main.FIXTURES
    assert options["env"] == main.MINIMAL_ENV
    assert options["stdin"] == main.subprocess.DEVNULL
    assert options["preexec_fn"] is main.limit_child


def test_output_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "OUTPUT_LIMIT_BYTES", 8)
    with (
        patch.object(main.subprocess, "Popen", return_value=fake_process(b"a" * 30)),
        patch.object(main, "stop_process") as stop,
    ):
        result = main.execute_preset("ls")
    assert result.stdout == "a" * 8
    assert result.exit_code == 125
    assert "output limit" in result.stderr
    stop.assert_called_once()


def test_timeout_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "TIMEOUT_SECONDS", 0.01)
    with (
        patch.object(main.subprocess, "Popen", return_value=fake_process(b"", keep_open=True)),
        patch.object(main, "stop_process") as stop,
    ):
        result = main.execute_preset("date")
    assert result.exit_code == 124
    assert "timeout limit" in result.stderr
    stop.assert_called_once()


def test_resource_limits_are_child_only() -> None:
    with patch.object(main.resource, "setrlimit") as limits, patch.object(main.os, "umask"):
        main.limit_child()
    applied = {call.args[0]: call.args[1] for call in limits.call_args_list}
    assert applied[main.resource.RLIMIT_CPU] == (1, 1)
    assert applied[main.resource.RLIMIT_FSIZE] == (0, 0)
    assert applied[main.resource.RLIMIT_AS] == (128 * 1024 * 1024,) * 2
    assert applied[main.resource.RLIMIT_NPROC] == (16, 16)
