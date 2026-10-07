from __future__ import annotations

import importlib.util
import io
import json
import stat
import sys
import zipfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


def load_script(name: str, filename: str) -> Any:
    path = Path(__file__).resolve().parent.parent / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


importer = load_script("material_importer", "import-material.py")
packager = load_script("source_packager", "package.py")


def write_zip(path: Path, entries: list[tuple[str | zipfile.ZipInfo, bytes]]) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)


@pytest.mark.parametrize(
    "name",
    [
        "../escape.txt",
        "/absolute.txt",
        "a/../../escape.md",
        "C:/secrets.txt",
        "a\\b.txt",
        "a/./b.md",
        "a//b.md",
        "a\x00b.txt",
    ],
)
def test_rejects_zip_slip(tmp_path: Path, name: str) -> None:
    path = tmp_path / "unsafe.zip"
    if "\x00" in name:
        # ZipFile writing strips NULs; inspect the original ZipInfo directly.
        with pytest.raises(importer.UnsafeArchive):
            importer.clean_path(zipfile.ZipInfo(name))
        return
    write_zip(path, [(name, b"test")])
    with pytest.raises(importer.UnsafeArchive):
        importer.collect_documents(path)
    assert not (tmp_path / "escape.txt").exists()


def test_rejects_symlink(tmp_path: Path) -> None:
    path = tmp_path / "symlink.zip"
    info = zipfile.ZipInfo("innocent.txt")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    write_zip(path, [(info, b"/etc/passwd")])
    with pytest.raises(importer.UnsafeArchive):
        importer.collect_documents(path)


def test_rejects_duplicate_equivalent_names(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.zip"
    write_zip(path, [("Docs/Info.md", b"a"), ("docs/info.md", b"b")])
    with pytest.raises(importer.UnsafeArchive):
        importer.collect_documents(path)


def test_rejects_compression_bomb(tmp_path: Path) -> None:
    path = tmp_path / "bomb.zip"
    write_zip(path, [("company.txt", b"a" * 200_000)])
    with pytest.raises(importer.UnsafeArchive):
        importer.collect_documents(path)


def test_rejects_many_entries(tmp_path: Path) -> None:
    path = tmp_path / "entries.zip"
    write_zip(path, [(f"{index}.txt", b"test") for index in range(importer.MAX_ENTRIES + 1)])
    with pytest.raises(importer.UnsafeArchive):
        importer.collect_documents(path)


def test_skips_secrets_and_executable_code(tmp_path: Path) -> None:
    path = tmp_path / "material with spaces.zip"
    write_zip(
        path,
        [
            (".env", b"secret"),
            (".git/config", b"secret"),
            ("credentials.json", b"secret"),
            ("node_modules/package/readme.md", b"code"),
            ("run.py", b"raise Exception()"),
            ("requirements.md", b"Use Python and React."),
            ("company/about.md", b"Company info."),
        ],
    )
    documents, report = importer.collect_documents(path)
    assert len(documents) == 2
    assert len(report["skipped"]) == 5
    assert documents[0].project_document is True
    assert documents[1].project_document is False


def test_redacts_credentials_before_saving(tmp_path: Path) -> None:
    path = tmp_path / "material.zip"
    write_zip(path, [("requirements.md", b"API_KEY=exam-secret-value\nUseful requirements.")])
    documents, report = importer.collect_documents(path)
    assert b"exam-secret-value" not in documents[0].data
    assert b"[REDACTED]" in documents[0].data
    first = importer.store_documents(documents, report, tmp_path / "material")
    second = importer.store_documents(documents, report, tmp_path / "material")
    assert first != second
    assert (first / documents[0].name).read_bytes() == documents[0].data


def test_json_csv_redaction_preserves_structure() -> None:
    result = json.loads(
        importer.sanitize_document('{"api_key": "private", "name": "Company"}', ".json")
    )
    assert result == {"api_key": "[REDACTED]", "name": "Company"}
    csv = importer.sanitize_document("name,password\nCompany,private\n", ".csv")
    assert "private" not in csv and "Company" in csv


def test_rejects_nested_docx_traversal() -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
        archive.writestr("../../unsafe.xml", "<unsafe/>")
    with pytest.raises(importer.UnsafeArchive):
        importer.document_text(stream.getvalue(), ".docx")


def test_rejects_xml_entities() -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", '<!DOCTYPE a [<!ENTITY x "secret">]><a>&x;</a>')
    with pytest.raises(ValueError):
        importer.document_text(stream.getvalue(), ".docx")


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8000",
        "http://localhost:8000",
        "http://example.com",
        "http://127.0.0.1@evil.test",
        "http://127.0.0.1:8000/api",
        "http://127.0.0.1:8000?x=1",
    ],
)
def test_upload_only_numeric_loopback(url: str) -> None:
    with pytest.raises(ValueError):
        importer.validate_backend_url(url)
    assert importer.validate_backend_url("http://127.0.0.1:8000/") == "http://127.0.0.1:8000"


def test_upload_multipart_never_uses_original_archive_path() -> None:
    document = importer.AcceptedDocument("001-company.txt", b"clean text", False)
    with patch.object(importer.request, "build_opener") as build:
        response = build.return_value.open.return_value.__enter__.return_value
        response.status = 200
        importer.upload_document(document, "http://127.0.0.1:8000")
    message = build.return_value.open.call_args.args[0]
    assert message.full_url == "http://127.0.0.1:8000/api/documents"
    assert b'name="file"' in message.data
    assert b"clean text" in message.data
    assert build.return_value.open.call_args.kwargs["timeout"] == 20
    assert any(isinstance(arg, importer.NoRedirect) for arg in build.call_args.args)


def test_packager_allowlist_and_no_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    allowed = [
        "README.md",
        "CLAUDE.md",
        ".mcp.json",
        "compose.local.yaml",
        "compose.production.yaml",
        ".vercelignore",
        ".claude/settings.json",
        ".claude/skills/speckit-specify/SKILL.md",
        ".agents/skills/speckit-specify/SKILL.md",
        ".github/workflows/quality.yml",
        "config/env.example",
        "config/production.env.example",
        "frontend/nginx.conf",
        "frontend/.vercelignore",
        ".env.example",
        "backend/app/main.py",
        "backend/uv.lock",
        ".specify/templates/spec-template.md",
    ]
    blocked = [
        ".env",
        "backend/.env.production",
        "config/production.env",
        "backend/data/database.json",
        "frontend/node_modules/pkg/index.js",
        ".vercel/project.json",
        "frontend/.vercel/project.json",
        ".claude/settings.local.json",
        ".specify/feature.json",
        ".git/config",
        "backend/secrets/token.txt",
    ]
    for filename in allowed + blocked:
        path = source / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("example", encoding="utf-8")
    (source / "backend/app/link.py").symlink_to(source / ".env")
    output = tmp_path / "portable source.zip"
    assert packager.build_package(source, output) == len(allowed)
    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == {f"Lumen/{name}" for name in allowed}
    with pytest.raises(FileExistsError):
        packager.build_package(source, output)


def test_material_directory_symlink_rejected(tmp_path: Path) -> None:
    destination = tmp_path / "material"
    destination.symlink_to(tmp_path)
    with pytest.raises(ValueError):
        importer.store_documents([], {}, destination)


def test_pdf_parser_is_bounded_and_uses_only_trusted_script() -> None:
    from types import SimpleNamespace

    with patch.object(
        importer.subprocess,
        "run",
        return_value=SimpleNamespace(returncode=0, stdout=b"safe company text"),
    ) as run:
        assert importer.document_text(b"%PDF-fake", ".pdf") == "safe company text"
    args = run.call_args.args[0]
    assert args[0] == sys.executable and args[1] == "-I" and args[-1] == "--internal-pdf-text"
    assert run.call_args.kwargs["timeout"] == 6
    assert run.call_args.kwargs["preexec_fn"] is importer.limit_pdf_parser
    assert "ANTHROPIC_API_KEY" not in run.call_args.kwargs["env"]


def test_rejects_utf16_xml_entity_bypass() -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "word/document.xml", '<!DOCTYPE a [<!ENTITY x "secret">]><a>&x;</a>'.encode("utf-16")
        )
    with pytest.raises((ValueError, UnicodeDecodeError)):
        importer.document_text(stream.getvalue(), ".docx")


@pytest.mark.parametrize(
    "name",
    [
        "rubrica.md",
        "rúbrica.txt",
        "rubric.md",
        "brief.md",
        "GOAL.md",
        "requirements/company.md",
        "docs/api.md",
    ],
)
def test_exam_documents_are_saved_without_becoming_company_facts(tmp_path: Path, name: str) -> None:
    path = tmp_path / "exam.zip"
    write_zip(path, [(name, b"Exam criteria and implementation details.")])
    documents, _ = importer.collect_documents(path)
    assert len(documents) == 1 and documents[0].project_document
