"""deploy-vps.py: private literal env-file ownership, location and format."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from .support import load_helper

VPS = load_helper("deploy-vps.py")


class PrivateEnvironmentFileTests(unittest.TestCase):
    def test_literal_file_preserves_dollar_and_spaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="deployment fixture ") as directory:
            path = Path(directory) / "production.env"
            path.write_text("FIXTURE_VALUE=literal$dollar and spaces\n", encoding="utf-8")
            path.chmod(0o600)
            self.assertEqual(
                VPS.read_private_environment(path)["FIXTURE_VALUE"], "literal$dollar and spaces"
            )

    def test_file_rejects_public_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "production.env"
            path.write_text("FIXTURE_VALUE=value\n", encoding="utf-8")
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                VPS.read_private_environment(path)

    def test_file_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source"
            path.write_text("FIXTURE_VALUE=value\n", encoding="utf-8")
            path.chmod(0o600)
            link = Path(directory) / "production.env"
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                VPS.read_private_environment(link)

    def test_file_rejects_source_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "production.env"
            path.write_text("FIXTURE_VALUE=value\n", encoding="utf-8")
            path.chmod(0o600)
            with mock.patch.object(VPS, "ROOT", Path(directory)), self.assertRaises(ValueError):
                VPS.read_private_environment(path)

    def test_file_rejects_duplicate_control_and_shell_export(self) -> None:
        for content in (
            "FIXTURE_VALUE=one\nFIXTURE_VALUE=two\n",
            "FIXTURE_VALUE=tab\tvalue\n",
            "export FIXTURE_VALUE=value\n",
        ):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "production.env"
                path.write_text(content, encoding="utf-8")
                path.chmod(0o600)
                with self.assertRaises(ValueError):
                    VPS.read_private_environment(path)
