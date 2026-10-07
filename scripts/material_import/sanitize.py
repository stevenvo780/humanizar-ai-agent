"""Credential redaction for text and structure-preserving JSON/CSV sanitizing."""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Any

from .limits import MAX_TEXT_CHARS

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(
        r"\b(?:sk-ant-[\w-]{8,}|sk-[\w-]{16,}|gh[pousr]_[\w]{16,}|github_pat_[\w]{16,}|AKIA[A-Z0-9]{16})\b"
    ),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    # Placeholders such as "Authorization: Bearer <token>" are requirements, not credentials.
    re.compile(
        r"""(?im)\b(?:proxy[-_ ]?)?authorization\b[ \t*`"']*[:=][ \t]*"""
        r"""(?![ \t]*(?:basic|bearer|token)?[ \t]*[<{$])[^\r\n]+"""
    ),
)
_CREDENTIAL_KEY = (
    r"""(["']?\b(?:[A-Z_]*(?:API_KEY|ACCESS_TOKEN|AUTH_TOKEN|SECRET|PASSWORD)|token|cookie)["']?"""
)
# Key/value credentials keep their key and get a quoted marker. Prose such as
# "Password: mínimo 8 caracteres" or "Token: se envía por correo" is preserved.
KEY_VALUE_PATTERNS = (
    re.compile(rf"""(?im){_CREDENTIAL_KEY}\s*=\s*)(?!["']?\[REDACTED)[^\r\n,;]+"""),
    re.compile(rf"""(?im){_CREDENTIAL_KEY}\s*:\s*)(["'])(?!\[REDACTED)[^"'\r\n]+\2"""),
    re.compile(rf"""(?im){_CREDENTIAL_KEY}\s*:\s*)(?=[^\s,;]*\d)[^\s"',;]{{8,}}"""),
)
SENSITIVE_FIELD = re.compile(r"(?i)(?:api[_-]?key|password|secret|token|cookie|authorization)")


def sanitize(text: str) -> str:
    if len(text) > MAX_TEXT_CHARS or "\x00" in text:
        raise ValueError("Document exceeds text limits or contains null bytes.")
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    for pattern in KEY_VALUE_PATTERNS:
        text = pattern.sub(lambda match: f'{match.group(1)}"[REDACTED]"', text)
    return text


def sanitize_document(text: str, suffix: str) -> str:
    if suffix == ".json":
        if len(text) > MAX_TEXT_CHARS:
            raise ValueError("JSON exceeds text limit.")

        def clean(value: Any, depth: int = 0) -> Any:
            if depth > 32:
                raise ValueError("JSON nesting exceeds limit.")
            if isinstance(value, dict):
                return {
                    sanitize(str(key)): "[REDACTED]"
                    if SENSITIVE_FIELD.search(str(key))
                    else clean(item, depth + 1)
                    for key, item in value.items()
                }
            if isinstance(value, list):
                return [clean(item, depth + 1) for item in value]
            if isinstance(value, str):
                return sanitize(value)
            return value

        return json.dumps(clean(json.loads(text)), ensure_ascii=False, indent=2)
    if suffix == ".csv":
        if len(text) > MAX_TEXT_CHARS:
            raise ValueError("CSV exceeds text limit.")
        rows = csv.reader(io.StringIO(text))
        output = io.StringIO()
        writer = csv.writer(output)
        header = next(rows, [])
        sensitive = {index for index, value in enumerate(header) if SENSITIVE_FIELD.search(value)}
        writer.writerow([sanitize(value) for value in header])
        for row in rows:
            writer.writerow(
                [
                    "[REDACTED]" if index in sensitive else sanitize(value)
                    for index, value in enumerate(row)
                ]
            )
        return output.getvalue()
    return sanitize(text)
