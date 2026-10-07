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
TEST_API_TOKEN = "test_header.test_payload.test_signature"


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


@pytest.mark.parametrize(
    "name",
    [
        ".codex/sessions/demo.json",
        "project/.CoDeX/Sessions/demo.json",
        "project/.ＣＯＤＥＸ/sessions/demo.json",
        ".codex/auth.json",
        ".claude/projects/demo/transcript.json",
        ".CLAUDE/PROJECTS/demo/transcript.json",
        ".claude/sessions/demo.json",
        ".claude/settings.json",
        ".claude/settings.local.json",
        ".claude/.credentials.json",
    ],
)
def test_runtime_material_is_skipped_before_reading(tmp_path: Path, name: str) -> None:
    path = tmp_path / "exam.zip"
    write_zip(path, [(name, b'{"message":"synthetic private runtime"}'), ("README.md", b"Brief.")])
    original_read = importer.bounded_read
    with patch.object(importer, "bounded_read", wraps=original_read) as read:
        documents, report = importer.collect_documents(path)
    assert len(documents) == 1 and documents[0].name.endswith("README.md")
    assert len(report["skipped"]) == 1
    assert [call.args[1].filename for call in read.call_args_list] == ["README.md"]
    saved = importer.store_documents(documents, report, tmp_path / "material")
    assert all(b"synthetic private runtime" not in item.read_bytes() for item in saved.iterdir())


def test_public_skill_and_company_readmes_remain_importable(tmp_path: Path) -> None:
    path = tmp_path / "exam.zip"
    write_zip(
        path,
        [
            ("README.md", b"Exam brief."),
            ("company/README.md", b"Public company information."),
            (".claude/skills/example/SKILL.md", b"Public skill instructions as data."),
        ],
    )
    documents, report = importer.collect_documents(path)
    assert len(documents) == 3 and not report["skipped"]


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


@pytest.mark.parametrize("header", ["Authorization", "Proxy-Authorization", "aUtHoRiZaTiOn"])
@pytest.mark.parametrize(
    "scheme,value", [("Basic", "YQ=="), ("Basic", "ZmFrZTphdXRo" * 20), ("Bearer", "x")]
)
def test_redacts_auth_headers_in_text_and_markdown(header: str, scheme: str, value: str) -> None:
    text = f"Useful company facts.\n**{header}**: {scheme} {value}\nMore useful facts."
    result = importer.sanitize_document(text, ".md")
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
    result = json.loads(importer.sanitize_document(source, ".json"))
    assert result["Authorization"] == result["Proxy-Authorization"] == "[REDACTED]"
    assert "YQ==" not in result["notes"]
    assert result["plan"] == "Basic company plan"


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
        "http://127.0.0.1:8000?",
        "http://127.0.0.1:8000#",
        "http://@127.0.0.1:8000",
        "http://127.0.0.1\n:8000",
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
        importer.upload_document(document, "http://127.0.0.1:8000", TEST_API_TOKEN)
    message = build.return_value.open.call_args.args[0]
    assert message.full_url == "http://127.0.0.1:8000/api/documents"
    assert b'name="file"' in message.data
    assert b"clean text" in message.data
    assert message.get_header("Authorization") == f"Bearer {TEST_API_TOKEN}"
    assert TEST_API_TOKEN.encode() not in message.data
    assert build.return_value.open.call_args.kwargs["timeout"] == 20
    assert any(isinstance(arg, importer.NoRedirect) for arg in build.call_args.args)
    proxy_handler = next(
        arg for arg in build.call_args.args if isinstance(arg, importer.request.ProxyHandler)
    )
    assert proxy_handler.proxies == {}


@pytest.mark.parametrize(
    "url", ["http://evil.test", "https://evil.test", "http://127.0.0.1@evil.test"]
)
def test_upload_validates_origin_before_attaching_authentication(url: str) -> None:
    document = importer.AcceptedDocument("001-company.txt", b"clean text", False)
    with patch.object(importer.request, "Request") as make_request:
        with pytest.raises(ValueError):
            importer.upload_document(document, url, TEST_API_TOKEN)
    make_request.assert_not_called()


@pytest.mark.parametrize(
    "token", [None, "", "invalid", "header.payload.signature\r\nInjected: value"]
)
def test_upload_token_requires_safe_jwt_shape(token: str | None) -> None:
    with pytest.raises(ValueError):
        importer.validate_api_token(token)


@pytest.mark.parametrize("flags", [[], ["--no-upload"]])
def test_default_and_no_upload_do_not_request_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    flags: list[str],
) -> None:
    path = tmp_path / "exam.zip"
    write_zip(path, [("company.md", b"Public company facts.")])
    monkeypatch.setattr(importer, "__file__", str(tmp_path / "scripts" / "import-material.py"))
    monkeypatch.setenv("LUMEN_API_TOKEN", TEST_API_TOKEN)
    with patch.object(importer.request, "build_opener") as build:
        assert importer.main([str(path), *flags]) == 0
    build.assert_not_called()
    captured = capsys.readouterr()
    assert "uploaded 0" in captured.out
    assert TEST_API_TOKEN not in captured.out + captured.err


def test_explicit_upload_requires_environment_token_before_reading_archive(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("LUMEN_API_TOKEN", raising=False)
    with patch.object(importer, "collect_documents") as collect:
        assert importer.main(["synthetic.zip", "--upload"]) == 2
    collect.assert_not_called()
    assert "LUMEN_API_TOKEN" in capsys.readouterr().err


def test_explicit_upload_uses_private_token_and_skips_requirements(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "exam.zip"
    write_zip(path, [("company.md", b"Public facts."), ("requirements.md", b"Exam criteria.")])
    monkeypatch.setattr(importer, "__file__", str(tmp_path / "scripts" / "import-material.py"))
    monkeypatch.setenv("LUMEN_API_TOKEN", TEST_API_TOKEN)
    with patch.object(importer, "upload_document") as upload:
        assert importer.main([str(path), "--upload"]) == 0
    assert upload.call_count == 1
    assert upload.call_args.args[0].name.endswith("company.md")
    assert upload.call_args.args[2] == TEST_API_TOKEN
    captured = capsys.readouterr()
    assert "uploaded 1" in captured.out
    assert TEST_API_TOKEN not in captured.out + captured.err


@pytest.mark.parametrize("status", [401, 403])
def test_upload_auth_failure_is_specific_without_token_or_response_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], status: int
) -> None:
    path = tmp_path / "exam.zip"
    write_zip(path, [("company.md", b"Public facts."), ("second.md", b"More public facts.")])
    monkeypatch.setattr(importer, "__file__", str(tmp_path / "scripts" / "import-material.py"))
    monkeypatch.setenv("LUMEN_API_TOKEN", TEST_API_TOKEN)
    failure = importer.error.HTTPError(
        "http://127.0.0.1:8000/api/documents",
        status,
        "Denied",
        None,
        io.BytesIO(TEST_API_TOKEN.encode()),
    )
    with patch.object(importer.request, "build_opener") as build:
        build.return_value.open.side_effect = failure
        assert importer.main([str(path), "--upload"]) == 1
    assert build.return_value.open.call_count == 1
    captured = capsys.readouterr()
    assert str(status) in captured.err and "LUMEN_API_TOKEN" in captured.err
    assert TEST_API_TOKEN not in captured.out + captured.err


def test_upload_modes_are_mutually_exclusive() -> None:
    with pytest.raises(SystemExit) as failure:
        importer.main(["synthetic.zip", "--upload", "--no-upload"])
    assert failure.value.code == 2


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
    assert importer.sanitize(requirement) == requirement


def test_skipped_inputs_are_named_in_report(tmp_path: Path) -> None:
    path = tmp_path / "brief.zip"
    write_zip(path, [("README.md", b"Brief."), ("api/openapi.yaml", b"openapi: 3.1.0")])
    documents, report = importer.collect_documents(path)
    assert [document.name for document in documents] == ["001-README.md"]
    assert report["skipped"] == [
        {"entry": 2, "name": "api/openapi.yaml", "reason": "unsupported format"}
    ]
