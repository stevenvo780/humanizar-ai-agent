"""User-scoped local business requests; these records never send external messages."""

import json
import re
import sqlite3
import threading
import uuid
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.core.security import safe_input

RequestKind = Literal["demo", "support"]
REQUEST_FIELDS: dict[RequestKind, dict[str, int]] = {
    "demo": {"name": 120, "email": 254, "company": 160, "interest": 200, "needs": 2000},
    "support": {"subject": 160, "description": 2000},
}
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
ACTION_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


class BusinessValidationError(ValueError):
    """A fixed public error message; never includes supplied content."""


def validate_details(kind: RequestKind, details: dict[str, Any]) -> dict[str, str]:
    if kind not in REQUEST_FIELDS or set(details) != set(REQUEST_FIELDS[kind]):
        raise BusinessValidationError("Los campos de la solicitud son inválidos.")
    clean: dict[str, str] = {}
    for key, maximum in REQUEST_FIELDS[kind].items():
        value = details[key]
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value) > maximum
            or any(ord(char) < 32 and char not in {"\n", "\t"} for char in value)
        ):
            raise BusinessValidationError("Completa todos los campos dentro del límite permitido.")
        clean[key] = value.strip()
    if kind == "demo" and not EMAIL_PATTERN.fullmatch(clean["email"]):
        raise BusinessValidationError("Introduce un correo electrónico válido.")
    safe = safe_input(clean)
    return {key: str(value) for key, value in safe.items()}


def validate_user_id(user_id: str) -> None:
    if not isinstance(user_id, str) or not user_id.strip() or len(user_id) > 100:
        raise BusinessValidationError("Inicia sesión para consultar o registrar tus solicitudes.")


class BusinessStore:
    def __init__(self, data_dir: Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with ExitStack() as resources:
            self._db = sqlite3.connect(
                data_dir / "application.sqlite3", timeout=5, check_same_thread=False
            )
            resources.callback(self._db.close)
            self._initialize_schema()
            resources.pop_all()

    def _initialize_schema(self) -> None:
        self._db.row_factory = sqlite3.Row
        self._db.executescript(
            "PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;"
            "CREATE TABLE IF NOT EXISTS business_requests ("
            "id TEXT PRIMARY KEY, user_id TEXT NOT NULL, "
            "kind TEXT NOT NULL CHECK(kind IN ('demo','support')), "
            "status TEXT NOT NULL DEFAULT 'received' CHECK(status='received'), "
            "details TEXT NOT NULL, created_at TEXT NOT NULL, action_key TEXT);"
            "CREATE INDEX IF NOT EXISTS requests_user_date "
            "ON business_requests(user_id, created_at DESC, id);"
        )
        # Supports a restart from the previous local request schema without replacing data.
        columns = {row["name"] for row in self._db.execute("PRAGMA table_info(business_requests)")}
        if "action_key" not in columns:
            self._db.execute("ALTER TABLE business_requests ADD COLUMN action_key TEXT")
        self._db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS requests_user_action "
            "ON business_requests(user_id, action_key)"
        )
        self._db.commit()

    @staticmethod
    def _public(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "kind": str(row["kind"]),
            "status": str(row["status"]),
            "created_at": str(row["created_at"]),
            "details": json.loads(str(row["details"])),
        }

    def create_request(
        self,
        user_id: str,
        kind: RequestKind,
        details: dict[str, Any],
        action_key: str | None = None,
    ) -> dict[str, Any]:
        validate_user_id(user_id)
        clean = validate_details(kind, details)
        if action_key is not None and (
            not isinstance(action_key, str) or not ACTION_KEY_PATTERN.fullmatch(action_key)
        ):
            raise BusinessValidationError("La clave de confirmación es inválida.")
        serialized = json.dumps(clean, ensure_ascii=False, sort_keys=True)
        with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE")
                if action_key is not None:
                    prior = self._db.execute(
                        "SELECT * FROM business_requests WHERE user_id=? AND action_key=?",
                        (user_id, action_key),
                    ).fetchone()
                    if prior is not None:
                        if prior["kind"] != kind or prior["details"] != serialized:
                            raise BusinessValidationError(
                                "Esta confirmación ya corresponde a otra solicitud."
                            )
                        self._db.commit()
                        return self._public(prior)
                identifier = str(uuid.uuid4())
                created_at = datetime.now(UTC).isoformat()
                self._db.execute(
                    "INSERT INTO business_requests "
                    "(id,user_id,kind,status,details,created_at,action_key) "
                    "VALUES (?,?,?,'received',?,?,?)",
                    (identifier, user_id, kind, serialized, created_at, action_key),
                )
                self._db.commit()
                return {
                    "id": identifier,
                    "kind": kind,
                    "status": "received",
                    "created_at": created_at,
                    "details": clean,
                }
            except Exception:
                self._db.rollback()
                raise

    def list_requests(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        validate_user_id(user_id)
        if type(limit) is not int or not 1 <= limit <= 20:
            raise BusinessValidationError("El límite de solicitudes es inválido.")
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM business_requests WHERE user_id=? "
                "ORDER BY created_at DESC,id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
            return [self._public(row) for row in rows]

    def list_all_requests(self, limit: int = 50) -> list[dict[str, Any]]:
        """Administrative inbox; the API caller must enforce the administrator role."""
        if type(limit) is not int or not 1 <= limit <= 50:
            raise BusinessValidationError("El límite de solicitudes es inválido.")
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM business_requests ORDER BY created_at DESC,id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [{**self._public(row), "user_id": str(row["user_id"])} for row in rows]

    def close(self) -> None:
        with self._lock:
            self._db.close()
