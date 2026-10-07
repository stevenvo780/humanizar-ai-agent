"""deploy-vercel.py: public HTTPS API origin and local project-link validation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from .support import load_helper

VERCEL = load_helper("deploy-vercel.py")


class VercelOriginTests(unittest.TestCase):
    def test_normalizes_root_slash(self) -> None:
        self.assertEqual(
            VERCEL.validate_origin("https://api.example.com/"), "https://api.example.com"
        )

    def test_refuses_unsafe_or_noncanonical_origins(self) -> None:
        for origin in (
            "http://api.example.com",
            "https://localhost",
            "https://127.0.0.1",
            "https://8.8.8.8",
            "https://[::1]",
            "https://api.local",
            "https://api.internal",
            "https://api.example.com/path",
            "https://api.example.com?q=1",
            "https://api.example.com#x",
            "https://name:password@api.example.com",
            "https://api.example.com:443",
            "HTTPS://api.example.com",
            "https://API.example.com",
            " https://api.example.com",
            "https://api.example.com\n",
            "https://api.example.com:",
            "https://api.-example.com",
        ):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                VERCEL.validate_origin(origin)

    def test_rejects_link_metadata_injection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            frontend = Path(directory)
            (frontend / ".vercel").mkdir()
            (frontend / ".vercel/project.json").write_text(
                '{"projectId":"prj_fixture/../../other","orgId":"team_fixture"}', encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                VERCEL.linked_project(frontend)
