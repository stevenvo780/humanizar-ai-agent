"""Local storage, explicit loopback upload and the import-material.py command line."""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from material_import import cli, documents, store, upload
from material_import.collect import AcceptedDocument
from material_support import write_zip

TEST_API_TOKEN = "test_header.test_payload.test_signature"
ENTRY = Path(__file__).resolve().parents[1] / "import-material.py"


def redirect_material(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    # The CLI saves to <repository>/material, derived from scripts/material_import/cli.py.
    monkeypatch.setattr(cli, "__file__", str(root / "scripts" / "material_import" / "cli.py"))


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
        upload.validate_backend_url(url)
    assert upload.validate_backend_url("http://127.0.0.1:8000/") == "http://127.0.0.1:8000"


def test_upload_multipart_never_uses_original_archive_path() -> None:
    document = AcceptedDocument("001-company.txt", b"clean text", False)
    with patch.object(upload.request, "build_opener") as build:
        response = build.return_value.open.return_value.__enter__.return_value
        response.status = 200
        upload.upload_document(document, "http://127.0.0.1:8000", TEST_API_TOKEN)
    message = build.return_value.open.call_args.args[0]
    assert message.full_url == "http://127.0.0.1:8000/api/documents"
    assert b'name="file"' in message.data
    assert b"clean text" in message.data
    assert message.get_header("Authorization") == f"Bearer {TEST_API_TOKEN}"
    assert TEST_API_TOKEN.encode() not in message.data
    assert build.return_value.open.call_args.kwargs["timeout"] == 20
    assert any(isinstance(arg, upload.NoRedirect) for arg in build.call_args.args)
    proxy_handler = next(
        arg for arg in build.call_args.args if isinstance(arg, upload.request.ProxyHandler)
    )
    assert proxy_handler.proxies == {}


@pytest.mark.parametrize(
    "url", ["http://evil.test", "https://evil.test", "http://127.0.0.1@evil.test"]
)
def test_upload_validates_origin_before_attaching_authentication(url: str) -> None:
    document = AcceptedDocument("001-company.txt", b"clean text", False)
    with patch.object(upload.request, "Request") as make_request:
        with pytest.raises(ValueError):
            upload.upload_document(document, url, TEST_API_TOKEN)
    make_request.assert_not_called()


@pytest.mark.parametrize(
    "token", [None, "", "invalid", "header.payload.signature\r\nInjected: value"]
)
def test_upload_token_requires_safe_jwt_shape(token: str | None) -> None:
    with pytest.raises(ValueError):
        upload.validate_api_token(token)


@pytest.mark.parametrize("flags", [[], ["--no-upload"]])
def test_default_and_no_upload_do_not_request_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    flags: list[str],
) -> None:
    path = tmp_path / "exam.zip"
    write_zip(path, [("company.md", b"Public company facts.")])
    redirect_material(monkeypatch, tmp_path)
    monkeypatch.setenv("LUMEN_API_TOKEN", TEST_API_TOKEN)
    with patch.object(upload.request, "build_opener") as build:
        assert cli.main([str(path), *flags]) == 0
    build.assert_not_called()
    captured = capsys.readouterr()
    assert "uploaded 0" in captured.out
    assert TEST_API_TOKEN not in captured.out + captured.err


def test_explicit_upload_requires_environment_token_before_reading_archive(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("LUMEN_API_TOKEN", raising=False)
    with patch.object(cli, "collect_documents") as collect:
        assert cli.main(["synthetic.zip", "--upload"]) == 2
    collect.assert_not_called()
    assert "LUMEN_API_TOKEN" in capsys.readouterr().err


def test_explicit_upload_uses_private_token_and_skips_requirements(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "exam.zip"
    write_zip(path, [("company.md", b"Public facts."), ("requirements.md", b"Exam criteria.")])
    redirect_material(monkeypatch, tmp_path)
    monkeypatch.setenv("LUMEN_API_TOKEN", TEST_API_TOKEN)
    with patch.object(cli, "upload_document") as upload_document:
        assert cli.main([str(path), "--upload"]) == 0
    assert upload_document.call_count == 1
    assert upload_document.call_args.args[0].name.endswith("company.md")
    assert upload_document.call_args.args[2] == TEST_API_TOKEN
    captured = capsys.readouterr()
    assert "uploaded 1" in captured.out
    assert TEST_API_TOKEN not in captured.out + captured.err


@pytest.mark.parametrize("status", [401, 403])
def test_upload_auth_failure_is_specific_without_token_or_response_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], status: int
) -> None:
    path = tmp_path / "exam.zip"
    write_zip(path, [("company.md", b"Public facts."), ("second.md", b"More public facts.")])
    redirect_material(monkeypatch, tmp_path)
    monkeypatch.setenv("LUMEN_API_TOKEN", TEST_API_TOKEN)
    failure = upload.error.HTTPError(
        "http://127.0.0.1:8000/api/documents",
        status,
        "Denied",
        None,
        io.BytesIO(TEST_API_TOKEN.encode()),
    )
    with patch.object(upload.request, "build_opener") as build:
        build.return_value.open.side_effect = failure
        assert cli.main([str(path), "--upload"]) == 1
    assert build.return_value.open.call_count == 1
    captured = capsys.readouterr()
    assert str(status) in captured.err and "LUMEN_API_TOKEN" in captured.err
    assert TEST_API_TOKEN not in captured.out + captured.err


def test_upload_modes_are_mutually_exclusive() -> None:
    with pytest.raises(SystemExit) as failure:
        cli.main(["synthetic.zip", "--upload", "--no-upload"])
    assert failure.value.code == 2


def test_material_directory_symlink_rejected(tmp_path: Path) -> None:
    destination = tmp_path / "material"
    destination.symlink_to(tmp_path)
    with pytest.raises(ValueError):
        store.store_documents([], {}, destination)


def test_entry_point_runs_under_isolated_python() -> None:
    # ``python3 -I`` omits the script directory; the entry point must still find its package.
    assert documents.ENTRY_SCRIPT == ENTRY
    shown = subprocess.run(
        [sys.executable, "-I", str(ENTRY), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert shown.returncode == 0 and "--no-upload" in shown.stdout
    worker = subprocess.run(
        [sys.executable, "-I", str(ENTRY), "--internal-pdf-text"],
        input=b"not a PDF",
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert worker.returncode == 2 and worker.stdout == b"" and worker.stderr == b""
