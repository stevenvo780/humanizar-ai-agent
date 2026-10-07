#!/usr/bin/env python3
"""Offline security regressions for deployment helpers; never contact Docker or Vercel."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_helper(filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        filename.replace("-", "_"), ROOT / "scripts" / filename
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Deployment helper could not be loaded.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VPS = load_helper("deploy-vps.py")
VERCEL = load_helper("deploy-vercel.py")
DATABASE = (
    "postgresql://fixture:fixture@database.example.com/lumen?sslmode=verify-full&sslrootcert=system"
)
HEADER_FIXTURE = "fixture-header-value-" + "a" * 32


def environment() -> dict[str, str]:
    return {
        "DATABASE_URL": DATABASE,
        "DATABASE_SCHEMA": "lumen",
        "CORS_ORIGINS": '["https://frontend.example.com"]',
        "AUTH_ENABLED": "true",
        "JWT_SECRET": "fixture-signing-value-" + "a" * 32,
        "AUTH_BOOTSTRAP_TOKEN": "fixture-bootstrap-value-" + "b" * 32,
    }


class ProductionEnvironmentTests(unittest.TestCase):
    def test_postgresql_and_psycopg_driver_url(self) -> None:
        for scheme in ("postgresql", "postgres", "postgresql+psycopg"):
            with self.subTest(scheme=scheme):
                values = environment()
                values["DATABASE_URL"] = DATABASE.replace("postgresql:", f"{scheme}:")
                VPS.validate_environment(values)

    def test_refuses_sqlite_and_weak_tls(self) -> None:
        for value in (
            "sqlite:///fixture.sqlite3",
            "",
            DATABASE.replace("verify-full", "require"),
            DATABASE.replace("verify-full", "disable"),
            DATABASE.replace("&sslrootcert=system", ""),
            DATABASE + "&sslmode=require",
            DATABASE.replace("fixture:fixture@", ""),
        ):
            with self.subTest(value=value):
                values = environment()
                values["DATABASE_URL"] = value
                with self.assertRaises(ValueError):
                    VPS.validate_environment(values)

    def test_refuses_nondedicated_schema(self) -> None:
        for schema in (
            "",
            "public",
            "information_schema",
            "pg_catalog",
            "public; DROP SCHEMA",
            "UPPER",
            "a" * 64,
        ):
            with self.subTest(schema=schema):
                values = environment()
                values["DATABASE_SCHEMA"] = schema
                with self.assertRaises(ValueError):
                    VPS.validate_environment(values)

    def test_rejects_query_options_outside_backend_allowlist(self) -> None:
        for suffix in (
            "&options=-csearch_path%3Dpublic",
            "&options=",
            "&host=another.example.com",
            "&sslmode=verify-full",
            "&sslmode=",
            "&sslrootcert=system",
            "&sslrootcert=",
            "&unknown",
            "&connect_timeout=999",
        ):
            with self.subTest(suffix=suffix):
                values = environment()
                values["DATABASE_URL"] = DATABASE + suffix
                with self.assertRaises(ValueError):
                    VPS.validate_environment(values)

    def test_rejects_invalid_ports_like_backend_connection_policy(self) -> None:
        for port in ("0", "-1", "65536", "invalid"):
            with self.subTest(port=port):
                values = environment()
                values["DATABASE_URL"] = DATABASE.replace(
                    "database.example.com/", f"database.example.com:{port}/"
                )
                with self.assertRaises(ValueError):
                    VPS.validate_environment(values)

    def test_accepts_port_boundaries(self) -> None:
        for port in (1, 5432, 65535):
            values = environment()
            values["DATABASE_URL"] = DATABASE.replace(
                "database.example.com/", f"database.example.com:{port}/"
            )
            VPS.validate_environment(values)

    def test_refuses_disabled_authentication(self) -> None:
        values = environment()
        values["AUTH_ENABLED"] = "false"
        with self.assertRaises(ValueError):
            VPS.validate_environment(values)

    def test_refuses_missing_anthropic_key_in_live_mode(self) -> None:
        values = environment()
        values["LLM_MODE"] = "anthropic"
        with self.assertRaises(ValueError):
            VPS.validate_environment(values)

    def test_refuses_weak_explicit_signing_or_bootstrap_secret(self) -> None:
        for key in ("JWT_SECRET", "AUTH_BOOTSTRAP_TOKEN"):
            values = environment()
            values[key] = "short-fixture"
            with self.assertRaises(ValueError):
                VPS.validate_environment(values)

    def test_requires_both_production_authentication_secrets(self) -> None:
        for key in ("JWT_SECRET", "AUTH_BOOTSTRAP_TOKEN"):
            for missing in (False, True):
                with self.subTest(key=key, missing=missing):
                    values = environment()
                    if missing:
                        values.pop(key)
                    else:
                        values[key] = ""
                    with self.assertRaises(ValueError):
                        VPS.validate_environment(values)

    def test_refuses_wildcard_http_and_path_cors(self) -> None:
        for origin in ("*", "http://frontend.example.com", "https://frontend.example.com/path"):
            values = environment()
            values["CORS_ORIGINS"] = json.dumps([origin])
            with self.assertRaises(ValueError):
                VPS.validate_environment(values)

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


class VercelRoutingTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
