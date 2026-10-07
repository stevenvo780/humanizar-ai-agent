"""Inspect examiner ZIPs without extracting or executing their code.

Run with ``uv run --project backend --extra semantic python scripts/import-material.py ZIP``.
The default saves material locally without network requests. Explicit ``--upload``
requires the private LUMEN_API_TOKEN environment variable for an administrator.
Only sanitized text is persisted. PDF/DOCX company documents are converted to text;
PDF support uses the backend's pypdf dependency. No project dependencies are imported.
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from pathlib import Path
from urllib import error

from .archive import UnsafeArchive
from .collect import collect_documents
from .store import store_documents
from .upload import (
    UploadAuthenticationError,
    upload_document,
    validate_api_token,
    validate_backend_url,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    upload_mode = parser.add_mutually_exclusive_group()
    upload_mode.add_argument(
        "--upload",
        action="store_true",
        help="Upload reviewed company documents to the local API using LUMEN_API_TOKEN.",
    )
    upload_mode.add_argument(
        "--no-upload",
        action="store_false",
        dest="upload",
        help="Inspect and save sanitized material only (the default).",
    )
    parser.set_defaults(upload=False)
    args = parser.parse_args(argv)
    try:
        backend_url = validate_backend_url(args.backend_url)
        api_token = validate_api_token(os.environ.get("LUMEN_API_TOKEN")) if args.upload else None
    except ValueError:
        print(
            "Upload configuration rejected: use an HTTP numeric loopback origin and "
            "set LUMEN_API_TOKEN to an administrator JWT for --upload.",
            file=sys.stderr,
        )
        return 2
    try:
        documents, report = collect_documents(args.zip_path)
        # Repository root: scripts/material_import/cli.py -> parents[2].
        destination = Path(__file__).resolve().parents[2] / "material"
        target = store_documents(documents, report, destination)
        uploaded = 0
        failures = 0
        if api_token is not None:
            for document in documents:
                if document.project_document:
                    continue
                try:
                    upload_document(document, backend_url, api_token)
                    uploaded += 1
                except UploadAuthenticationError as exc:
                    failures += 1
                    print(str(exc), file=sys.stderr)
                    break
                except (OSError, ValueError, error.URLError):
                    failures += 1
        print(f"Saved {len(documents)} sanitized documents to {target}.")
        for item in report["skipped"]:
            if "name" in item:
                print(f"Not imported ({item['reason']}): {item['name']}")
        print(
            f"Skipped {len(report['skipped'])} entries; uploaded {uploaded}; "
            f"upload failures {failures}."
        )
        return 1 if failures else 0
    except UnsafeArchive as exc:
        # Fixed validation messages never contain archive content.
        print(
            f"Import rejected: {exc} Inspect it with: python3 -I -m zipfile -l ZIP", file=sys.stderr
        )
        return 2
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError):
        print(
            "Import rejected: invalid archive, unsafe member, size limit or unavailable path.",
            file=sys.stderr,
        )
        return 2
