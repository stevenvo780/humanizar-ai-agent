"""deploy-vps.py: Docker Compose commands receive no backend secrets and keep volumes."""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from .support import environment, load_helper

VPS = load_helper("deploy-vps.py")


class ComposeCommandTests(unittest.TestCase):
    def test_check_uses_no_daemon_and_passes_no_backend_secrets_to_compose(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "production.env"
            path.touch(mode=0o600)
            private = environment()
            private["JWT_SECRET"] = "fixture-jwt-value-" + "a" * 32
            output = io.StringIO()
            with (
                mock.patch.dict(os.environ, {}, clear=True),
                mock.patch("sys.argv", ["deploy-vps.py", "check", "--env-file", str(path)]),
                mock.patch.object(VPS.shutil, "which", return_value="docker"),
                mock.patch.object(VPS, "read_private_environment", return_value=private),
                mock.patch.object(VPS, "run_quiet") as run,
                contextlib.redirect_stdout(output),
            ):
                self.assertEqual(VPS.main(), 0)
            run.assert_called_once()
            command, compose_environment = run.call_args.args
            self.assertEqual(command[-2:], ["config", "--quiet"])
            self.assertEqual(compose_environment["COMPOSE_DISABLE_ENV_FILE"], "1")
            self.assertNotIn("JWT_SECRET", compose_environment)
            self.assertNotIn(private["JWT_SECRET"], output.getvalue())

    def test_stop_preserves_volumes_after_database_credentials_are_removed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "production.env"
            path.touch(mode=0o600)
            with (
                mock.patch("sys.argv", ["deploy-vps.py", "stop", "--env-file", str(path)]),
                mock.patch.object(VPS.shutil, "which", return_value="docker"),
                mock.patch.object(VPS, "read_private_environment", return_value={}),
                mock.patch.object(VPS, "run_quiet") as run,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(VPS.main(), 0)
            self.assertEqual(run.call_args.args[0][-1], "stop")
            self.assertNotIn("down", run.call_args.args[0])
            self.assertNotIn("--volumes", run.call_args.args[0])
