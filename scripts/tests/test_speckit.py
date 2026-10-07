"""Prerequisite inspection validates the candidate without selecting it."""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def checkout(tmp_path: Path) -> Path:
    scripts = tmp_path / ".specify/scripts/bash"
    scripts.mkdir(parents=True)
    for name in ("common.sh", "check-prerequisites.sh", "resolve-template.sh"):
        shutil.copyfile(ROOT / ".specify/scripts/bash" / name, scripts / name)
    feature = tmp_path / "specs/002-exam-adaptation"
    feature.mkdir(parents=True)
    for name in ("spec.md", "plan.md", "tasks.md"):
        (feature / name).write_text("Synthetic assessment artifact.\n", encoding="utf-8")
    return tmp_path


def inspect_feature(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            str(root / ".specify/scripts/bash/check-prerequisites.sh"),
            "--json",
            "--require-spec",
            "--require-tasks",
            "--include-tasks",
        ],
        cwd=root,
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "SPECIFY_FEATURE": "002-exam-adaptation",
            "SPECIFY_FEATURE_DIRECTORY": "specs/002-exam-adaptation",
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_inspection_preserves_a_different_selected_feature(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    pointer = root / ".specify/feature.json"
    original = b'{"feature_directory":"specs/001-company-agent"}\n'
    pointer.write_bytes(original)
    timestamp = pointer.stat().st_mtime_ns
    result = inspect_feature(root)
    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "FEATURE_DIR": str(root / "specs/002-exam-adaptation"),
        "AVAILABLE_DOCS": ["tasks.md"],
    }
    assert pointer.read_bytes() == original
    assert pointer.stat().st_mtime_ns == timestamp


def test_inspection_does_not_create_a_feature_pointer(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    assert inspect_feature(root).returncode == 0
    assert not (root / ".specify/feature.json").exists()


def test_read_only_validation_still_rejects_missing_tasks(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    (root / "specs/002-exam-adaptation/tasks.md").unlink()
    result = inspect_feature(root)
    assert result.returncode == 1
    assert "tasks.md not found" in result.stderr
    assert not (root / ".specify/feature.json").exists()


def test_scaffold_hashes_match_upstream_or_documented_local_overrides() -> None:
    overrides = json.loads((ROOT / ".specify/local-overrides.json").read_text())
    seen: set[str] = set()
    for name in ("claude", "speckit"):
        manifest = json.loads((ROOT / f".specify/integrations/{name}.manifest.json").read_text())
        for relative, upstream in manifest["files"].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            override = overrides["files"].get(relative)
            if override is None:
                assert actual == upstream
            else:
                seen.add(relative)
                assert override["upstream_sha256"] == upstream
                assert override["local_sha256"] == actual
                assert override["reason"]
    assert seen == set(overrides["files"])
