"""Synthetic ZIP writer shared by the material import tests."""

from __future__ import annotations

import zipfile
from pathlib import Path


def write_zip(path: Path, entries: list[tuple[str | zipfile.ZipInfo, bytes]]) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
