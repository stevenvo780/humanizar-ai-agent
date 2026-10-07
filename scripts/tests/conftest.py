"""Make scripts/ importable so tests exercise the ``material_import`` package directly."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = str(Path(__file__).resolve().parents[1])
if SCRIPTS not in sys.path:
    sys.path.append(SCRIPTS)
