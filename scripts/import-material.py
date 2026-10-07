#!/usr/bin/env python3
"""Inspect examiner ZIPs without extracting or executing their code.

Run with ``uv run --project backend --extra semantic python scripts/import-material.py ZIP``.
The default saves material locally without network requests. Explicit ``--upload``
requires the private LUMEN_API_TOKEN environment variable for an administrator.
Only sanitized text is persisted. PDF/DOCX company documents are converted to text;
PDF support uses the backend's pypdf dependency. No project dependencies are imported.

Thin entry point: the implementation lives in ``material_import/`` next to this file.
``--internal-pdf-text`` is the bounded PDF worker that ``material_import.documents`` spawns.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __name__ == "__main__":
    # ``python3 -I`` omits the script directory from sys.path; add only this trusted one.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if sys.argv[1:] == ["--internal-pdf-text"]:
        from material_import.documents import internal_pdf_text

        raise SystemExit(internal_pdf_text())
    from material_import.cli import main

    raise SystemExit(main())
