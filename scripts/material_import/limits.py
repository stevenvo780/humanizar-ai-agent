"""Size and count bounds shared by archive inspection, extraction and redaction."""

from __future__ import annotations

MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_ENTRY_BYTES = 8 * 1024 * 1024
MAX_ENTRIES = 2000
MAX_RATIO = 100
MAX_TEXT_CHARS = 1_000_000
