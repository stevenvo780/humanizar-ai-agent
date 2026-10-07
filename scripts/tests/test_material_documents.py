"""DOCX XML hardening and the bounded, isolated PDF parser subprocess."""

from __future__ import annotations

import io
import sys
import zipfile
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from material_import import archive, documents


def test_rejects_nested_docx_traversal() -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as docx:
        docx.writestr("[Content_Types].xml", "<Types/>")
        docx.writestr("word/document.xml", "<document/>")
        docx.writestr("../../unsafe.xml", "<unsafe/>")
    with pytest.raises(archive.UnsafeArchive):
        documents.document_text(stream.getvalue(), ".docx")


def test_rejects_xml_entities() -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as docx:
        docx.writestr("[Content_Types].xml", "<Types/>")
        docx.writestr("word/document.xml", '<!DOCTYPE a [<!ENTITY x "secret">]><a>&x;</a>')
    with pytest.raises(ValueError):
        documents.document_text(stream.getvalue(), ".docx")


def test_pdf_parser_is_bounded_and_uses_only_trusted_script() -> None:
    with patch.object(
        documents.subprocess,
        "run",
        return_value=SimpleNamespace(returncode=0, stdout=b"safe company text"),
    ) as run:
        assert documents.document_text(b"%PDF-fake", ".pdf") == "safe company text"
    args = run.call_args.args[0]
    assert args[0] == sys.executable and args[1] == "-I" and args[-1] == "--internal-pdf-text"
    assert run.call_args.kwargs["timeout"] == 6
    assert run.call_args.kwargs["preexec_fn"] is documents.limit_pdf_parser
    assert "ANTHROPIC_API_KEY" not in run.call_args.kwargs["env"]


def test_rejects_utf16_xml_entity_bypass() -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as docx:
        docx.writestr("[Content_Types].xml", "<Types/>")
        docx.writestr(
            "word/document.xml", '<!DOCTYPE a [<!ENTITY x "secret">]><a>&x;</a>'.encode("utf-16")
        )
    with pytest.raises((ValueError, UnicodeDecodeError)):
        documents.document_text(stream.getvalue(), ".docx")
