#!/usr/bin/env python3
"""Exercise a fresh demo Compose stack; never point this at an existing database."""

from __future__ import annotations

import json
import secrets
import urllib.error
import urllib.request
from typing import Any

BASE_URL = "http://127.0.0.1:8080"


def request(
    path: str, payload: dict[str, Any] | None = None, token: str | None = None
) -> tuple[int, bytes]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode() if payload is not None else None
    call = urllib.request.Request(BASE_URL + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(call, timeout=30) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def main() -> None:
    status, body = request("/api/auth/status")
    assert status == 200 and json.loads(body)["setup_required"], "Requires a fresh CI database."
    assert request("/api/conversations")[0] == 401, "Private history must require a session."
    for path in ("/", "/docs", "/docs/", "/api/docs", "/api/openapi.json"):
        assert request(path)[0] == 200, f"Route failed: {path}"
    status, body = request("/api/health")
    assert status == 200 and json.loads(body)["mode"] == "demo", "CI must use the demo provider."
    status, body = request(
        "/api/auth/setup",
        {
            "name": "CI administrator",
            "email": "ci@example.test",
            "password": "Ci1!" + secrets.token_urlsafe(24),
        },
    )
    assert status == 200, "Administrator setup failed."
    session = json.loads(body)
    token = str(session["access_token"])
    assert session["user"]["role"] == "admin"
    status, body = request("/api/search?query=Humanizar", token=token)
    assert status == 200 and json.loads(body)["sources"], "Company corpus retrieval failed."
    status, body = request("/api/chat", {"message": "¿Qué ofrece Humanizar?"}, token)
    answer = json.loads(body)
    assert status == 200 and answer["answer"] and answer["sources"], "Grounded demo chat failed."
    status, body = request(
        "/api/tools/run", {"name": "calculate", "input": {"expression": "29*12"}}, token
    )
    assert status == 200 and json.loads(body)["output"] == "348", "Calculator failed."
    status, body = request(
        "/api/tools/run", {"name": "terminal", "input": {"command": "wc"}}, token
    )
    trace = json.loads(body)
    assert status == 200 and trace["status"] == "completed", "Isolated terminal failed."
    assert "example.txt" in trace["output"], "Sandbox fixture command did not execute."
    status, body = request(
        "/api/tools/run", {"name": "terminal", "input": {"command": "cat /etc/passwd"}}, token
    )
    assert status == 200 and json.loads(body)["status"] == "error", (
        "Terminal must reject arbitrary commands."
    )
    print("Docker passed: public docs, JWT, corpus, demo chat, calculator and isolated terminal.")


if __name__ == "__main__":
    main()
