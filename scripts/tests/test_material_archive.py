"""Archive safety, private-path filtering and document classification for ZIP imports."""

from __future__ import annotations

import stat
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from material_import import archive, collect, limits, store
from material_support import write_zip


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
        with pytest.raises(archive.UnsafeArchive):
            archive.clean_path(zipfile.ZipInfo(name))
        return
    write_zip(path, [(name, b"test")])
    with pytest.raises(archive.UnsafeArchive):
        collect.collect_documents(path)
    assert not (tmp_path / "escape.txt").exists()


def test_rejects_symlink(tmp_path: Path) -> None:
    path = tmp_path / "symlink.zip"
    info = zipfile.ZipInfo("innocent.txt")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    write_zip(path, [(info, b"/etc/passwd")])
    with pytest.raises(archive.UnsafeArchive):
        collect.collect_documents(path)


def test_rejects_duplicate_equivalent_names(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.zip"
    write_zip(path, [("Docs/Info.md", b"a"), ("docs/info.md", b"b")])
    with pytest.raises(archive.UnsafeArchive):
        collect.collect_documents(path)


def test_rejects_compression_bomb(tmp_path: Path) -> None:
    path = tmp_path / "bomb.zip"
    write_zip(path, [("company.txt", b"a" * 200_000)])
    with pytest.raises(archive.UnsafeArchive):
        collect.collect_documents(path)


def test_rejects_many_entries(tmp_path: Path) -> None:
    path = tmp_path / "entries.zip"
    write_zip(path, [(f"{index}.txt", b"test") for index in range(limits.MAX_ENTRIES + 1)])
    with pytest.raises(archive.UnsafeArchive):
        collect.collect_documents(path)


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
    documents, report = collect.collect_documents(path)
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
    original_read = collect.bounded_read
    with patch.object(collect, "bounded_read", wraps=original_read) as read:
        documents, report = collect.collect_documents(path)
    assert len(documents) == 1 and documents[0].name.endswith("README.md")
    assert len(report["skipped"]) == 1
    assert [call.args[1].filename for call in read.call_args_list] == ["README.md"]
    saved = store.store_documents(documents, report, tmp_path / "material")
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
    documents, report = collect.collect_documents(path)
    assert len(documents) == 3 and not report["skipped"]


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
    documents, _ = collect.collect_documents(path)
    assert len(documents) == 1 and documents[0].project_document


def test_skipped_inputs_are_named_in_report(tmp_path: Path) -> None:
    path = tmp_path / "brief.zip"
    write_zip(path, [("README.md", b"Brief."), ("api/openapi.yaml", b"openapi: 3.1.0")])
    documents, report = collect.collect_documents(path)
    assert [document.name for document in documents] == ["001-README.md"]
    assert report["skipped"] == [
        {"entry": 2, "name": "api/openapi.yaml", "reason": "unsupported format"}
    ]
