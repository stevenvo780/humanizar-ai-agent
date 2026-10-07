"""Persist accepted documents and the manifest in a new private import directory."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .collect import AcceptedDocument


def store_documents(
    documents: list[AcceptedDocument], report: dict[str, Any], destination: Path
) -> Path:
    if destination.is_symlink():
        raise ValueError("Material directory cannot be a symlink.")
    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = destination / f"import-{stamp}-{uuid.uuid4().hex[:12]}"
    target.mkdir(mode=0o700, exist_ok=False)
    for document in documents:
        with (target / document.name).open("xb") as stream:
            stream.write(document.data)
    with (target / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return target
