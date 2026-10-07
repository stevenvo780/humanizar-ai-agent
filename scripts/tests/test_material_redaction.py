"""Credential redaction in text, Markdown, JSON and CSV without losing requirement prose."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from material_import import collect, sanitize, store
from material_support import write_zip


def test_redacts_credentials_before_saving(tmp_path: Path) -> None:
    path = tmp_path / "material.zip"
    write_zip(path, [("requirements.md", b"API_KEY=exam-secret-value\nUseful requirements.")])
    documents, report = collect.collect_documents(path)
    assert b"exam-secret-value" not in documents[0].data
    assert b"[REDACTED]" in documents[0].data
    first = store.store_documents(documents, report, tmp_path / "material")
    second = store.store_documents(documents, report, tmp_path / "material")
    assert first != second
    assert (first / documents[0].name).read_bytes() == documents[0].data


def test_json_csv_redaction_preserves_structure() -> None:
    result = json.loads(
        sanitize.sanitize_document('{"api_key": "private", "name": "Company"}', ".json")
    )
    assert result == {"api_key": "[REDACTED]", "name": "Company"}
    csv = sanitize.sanitize_document("name,password\nCompany,private\n", ".csv")
    assert "private" not in csv and "Company" in csv


@pytest.mark.parametrize("header", ["Authorization", "Proxy-Authorization", "aUtHoRiZaTiOn"])
@pytest.mark.parametrize(
    "scheme,value", [("Basic", "YQ=="), ("Basic", "ZmFrZTphdXRo" * 20), ("Bearer", "x")]
)
def test_redacts_auth_headers_in_text_and_markdown(header: str, scheme: str, value: str) -> None:
    text = f"Useful company facts.\n**{header}**: {scheme} {value}\nMore useful facts."
    result = sanitize.sanitize_document(text, ".md")
    assert value not in result and "[REDACTED]" in result
    assert "Useful company facts." in result and "More useful facts." in result


def test_auth_redaction_preserves_json_structure_and_nonsecret_basic_text() -> None:
    source = json.dumps(
        {
            "Authorization": "Basic YQ==",
            "Proxy-Authorization": "Basic ZmFrZTphdXRo",
            "notes": "Authorization: Basic YQ==",
            "plan": "Basic company plan",
        }
    )
    result = json.loads(sanitize.sanitize_document(source, ".json"))
    assert result["Authorization"] == result["Proxy-Authorization"] == "[REDACTED]"
    assert "YQ==" not in result["notes"]
    assert result["plan"] == "Basic company plan"


@pytest.mark.parametrize(
    "requirement",
    [
        "Para cambiar tu password: ingresa a Ajustes > Seguridad.",
        "Password: mínimo 8 caracteres, una mayúscula.",
        "JWT con access token, refresh token y cookie HttpOnly segura.",
        "El endpoint usa Authorization: Bearer <token> en cada llamada.",
        "Token: el usuario recibe un token válido por 15 minutos.",
    ],
)
def test_requirement_prose_is_not_redacted(requirement: str) -> None:
    assert sanitize.sanitize(requirement) == requirement
