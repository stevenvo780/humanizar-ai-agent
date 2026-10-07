"""deploy-vercel.py: secrets stay out of argv/output and the CLI runs from the root."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from .support import HEADER_FIXTURE, ROOT, load_helper

VERCEL = load_helper("deploy-vercel.py")


class VercelDeployCommandTests(unittest.TestCase):
    def test_check_does_not_call_cli_or_read_private_link(self) -> None:
        output = io.StringIO()
        with (
            mock.patch.dict(
                os.environ,
                {"API_ORIGIN": "https://api.example.com", "ORIGIN_SECRET": HEADER_FIXTURE},
                clear=True,
            ),
            mock.patch("sys.argv", ["deploy-vercel.py", "--check"]),
            mock.patch.object(VERCEL, "run_private") as run,
            mock.patch.object(VERCEL, "linked_project") as link,
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(VERCEL.main(), 0)
            run.assert_not_called()
            link.assert_not_called()
        self.assertNotIn(HEADER_FIXTURE, output.getvalue())

    def test_rejects_bad_secret_without_disclosure(self) -> None:
        for header in ("short", "x" * 513, "x" * 31 + "\n", "x" * 31 + "é", "x" * 31 + " "):
            output = io.StringIO()
            with (
                mock.patch.dict(
                    os.environ,
                    {"API_ORIGIN": "https://api.example.com", "ORIGIN_SECRET": header},
                    clear=True,
                ),
                mock.patch("sys.argv", ["deploy-vercel.py", "--check"]),
                contextlib.redirect_stderr(output),
            ):
                self.assertEqual(VERCEL.main(), 1)
            self.assertNotIn(header, output.getvalue())

    def test_rejects_public_secret_prefix(self) -> None:
        with (
            mock.patch.dict(
                os.environ,
                {
                    "API_ORIGIN": "https://api.example.com",
                    "ORIGIN_SECRET": HEADER_FIXTURE,
                    "VITE_ORIGIN_SECRET": HEADER_FIXTURE,
                },
                clear=True,
            ),
            mock.patch("sys.argv", ["deploy-vercel.py", "--check"]),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(VERCEL.main(), 1)

    def test_configuration_values_only_in_stdin(self) -> None:
        with (
            mock.patch.dict(
                os.environ,
                {"API_ORIGIN": "https://api.example.com", "ORIGIN_SECRET": HEADER_FIXTURE},
                clear=True,
            ),
            mock.patch("sys.argv", ["deploy-vercel.py", "--configure-env", "--update-env"]),
            mock.patch.object(VERCEL.shutil, "which", return_value="vercel"),
            mock.patch.object(
                VERCEL, "linked_project", return_value=("prj_fixture", "team_fixture")
            ),
            mock.patch.object(VERCEL, "run_private") as run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(VERCEL.main(), 0)
        self.assertEqual(run.call_count, 3)
        for call in run.call_args_list:
            self.assertNotIn(HEADER_FIXTURE, " ".join(call.args[0]))
        secret_call = run.call_args_list[1]
        self.assertIn("?upsert=true", secret_call.args[0][2])
        self.assertIn("Content-Type: application/json", secret_call.args[0])
        payload = json.loads(secret_call.kwargs["input_value"])
        self.assertEqual(payload["value"], HEADER_FIXTURE)
        self.assertEqual(payload["type"], "sensitive")
        self.assertEqual(payload["target"], ["preview"])

    def test_existing_configuration_not_overwritten_by_default(self) -> None:
        with (
            mock.patch.dict(
                os.environ,
                {"API_ORIGIN": "https://api.example.com", "ORIGIN_SECRET": HEADER_FIXTURE},
                clear=True,
            ),
            mock.patch("sys.argv", ["deploy-vercel.py", "--production", "--configure-env"]),
            mock.patch.object(VERCEL.shutil, "which", return_value="vercel"),
            mock.patch.object(
                VERCEL, "linked_project", return_value=("prj_fixture", "team_fixture")
            ),
            mock.patch.object(VERCEL, "run_private") as run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(VERCEL.main(), 0)
        self.assertNotIn("upsert", run.call_args_list[0].args[0][2])
        self.assertEqual(
            json.loads(run.call_args_list[1].kwargs["input_value"])["target"], ["production"]
        )
        self.assertIn("--prod", run.call_args_list[2].args[0])

    def test_vercel_cli_runs_from_repository_root(self) -> None:
        with mock.patch.object(VERCEL.subprocess, "run") as run:
            run.return_value.returncode = 0
            VERCEL.run_private(["vercel", "deploy"])
        self.assertEqual(run.call_args.kwargs["cwd"], ROOT)

    def test_project_link_is_read_from_repository_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)
            (checkout / ".vercel").mkdir()
            (checkout / ".vercel/project.json").write_text(
                '{"projectId":"prj_fixture","orgId":"team_fixture"}', encoding="utf-8"
            )
            self.assertEqual(VERCEL.linked_project(checkout), ("prj_fixture", "team_fixture"))
        with (
            mock.patch.dict(
                os.environ,
                {"API_ORIGIN": "https://api.example.com", "ORIGIN_SECRET": HEADER_FIXTURE},
                clear=True,
            ),
            mock.patch("sys.argv", ["deploy-vercel.py"]),
            mock.patch.object(VERCEL.shutil, "which", return_value="vercel"),
            mock.patch.object(
                VERCEL, "linked_project", return_value=("prj_fixture", "team_fixture")
            ) as linked,
            mock.patch.object(VERCEL, "run_private"),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(VERCEL.main(), 0)
            linked.assert_called_once_with(ROOT)
