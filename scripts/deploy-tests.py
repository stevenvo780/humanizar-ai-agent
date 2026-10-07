#!/usr/bin/env python3
"""Offline security regressions for deployment helpers; never contact Docker or Vercel.

Thin runner: the unittest modules live in ``deploy_tests/`` next to this file.
"""

from __future__ import annotations

import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def load_tests(
    loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None
) -> unittest.TestSuite:
    return loader.discover(
        str(SCRIPTS / "deploy_tests"), pattern="test_*.py", top_level_dir=str(SCRIPTS)
    )


if __name__ == "__main__":
    unittest.main()
