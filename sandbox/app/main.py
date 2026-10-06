"""Fixed command presets with bounded subprocess output and Linux resource limits."""

from __future__ import annotations

import os
import resource
import selectors
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
TIMEOUT_SECONDS = 2.0
OUTPUT_LIMIT_BYTES = 16_384
MINIMAL_ENV = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC"}
PRESETS: dict[str, tuple[str, ...]] = {
    "pwd": ("/usr/bin/pwd",),
    "ls": ("/usr/bin/ls", "-1", "--"),
    "date": ("/usr/bin/date", "-u", "+%Y-%m-%dT%H:%M:%SZ"),
    "python --version": (sys.executable, "--version"),
    "wc": ("/usr/bin/wc", "--", "example.txt"),
}
RUN_SLOTS = threading.BoundedSemaphore(4)
app = FastAPI(title="Lumen isolated sandbox", docs_url=None, redoc_url=None)


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: str = Field(min_length=1, max_length=64)


class RunResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int


def isolated_runtime() -> bool:
    """Require the explicit container marker and a non-root runtime."""
    return os.environ.get("LUMEN_SANDBOX_CONTAINER") == "1" and os.geteuid() != 0


def limit_child() -> None:
    """Applied only to a newly forked child before exec, never to the web server."""
    os.umask(0o077)
    for limit, maximum in (
        (resource.RLIMIT_CPU, 1),
        (resource.RLIMIT_AS, 128 * 1024 * 1024),
        (resource.RLIMIT_FSIZE, 0),
        (resource.RLIMIT_CORE, 0),
        (resource.RLIMIT_NOFILE, 32),
        (resource.RLIMIT_NPROC, 16),
    ):
        resource.setrlimit(limit, (maximum, maximum))


def stop_process(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=1)


def execute_preset(command: str) -> RunResponse:
    argv = PRESETS[command]
    output: dict[str, bytearray] = {"stdout": bytearray(), "stderr": bytearray()}
    failure: Literal["timeout", "output"] | None = None
    with subprocess.Popen(
        argv,
        cwd=FIXTURES,
        env=MINIMAL_ENV,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        close_fds=True,
        start_new_session=True,
        preexec_fn=limit_child,
    ) as process:
        assert process.stdout is not None and process.stderr is not None
        deadline = time.monotonic() + TIMEOUT_SECONDS
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    failure = "timeout"
                    break
                for key, _ in selector.select(timeout=min(remaining, 0.1)):
                    data = os.read(key.fd, 4096)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    room = OUTPUT_LIMIT_BYTES - sum(len(value) for value in output.values())
                    output[key.data].extend(data[:room])
                    if len(data) > room:
                        failure = "output"
                        break
                if failure:
                    break
        if failure:
            stop_process(process)
        else:
            try:
                process.wait(timeout=max(0.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                failure = "timeout"
                stop_process(process)
        stderr = output["stderr"].decode("utf-8", errors="replace")
        if failure:
            stderr = f"{stderr}\nSandbox {failure} limit reached.".strip()
        return RunResponse(
            stdout=output["stdout"].decode("utf-8", errors="replace"),
            stderr=stderr,
            exit_code=(124 if failure == "timeout" else 125)
            if failure
            else int(process.returncode),
        )


@app.get("/health")
def health() -> dict[str, str]:
    if not isolated_runtime():
        raise HTTPException(503, "Sandbox requires its dedicated non-root container.")
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse)
def run(request: RunRequest) -> RunResponse:
    if request.command not in PRESETS:
        raise HTTPException(
            400, "Unsupported command. Choose pwd, ls, date, python --version or wc."
        )
    if not isolated_runtime():
        raise HTTPException(503, "Sandbox requires its dedicated non-root container.")
    if not RUN_SLOTS.acquire(blocking=False):
        raise HTTPException(429, "Sandbox is busy.")
    try:
        return execute_preset(request.command)
    except OSError as exc:
        raise HTTPException(503, "Sandbox preset could not start.") from exc
    finally:
        RUN_SLOTS.release()
