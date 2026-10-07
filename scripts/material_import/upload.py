"""Explicit, authenticated upload of sanitized documents to the loopback API only."""

from __future__ import annotations

import re
import uuid
from typing import Any
from urllib import error, parse, request

from .collect import AcceptedDocument


class UploadAuthenticationError(ValueError):
    """An upload was rejected; its message never includes response bodies or tokens."""


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
