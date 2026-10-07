"""deploy-vps.py: production database, authentication and CORS validation."""

from __future__ import annotations

import json
import unittest

from .support import DATABASE, environment, load_helper

VPS = load_helper("deploy-vps.py")


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
