"""Application identities, revocable sessions, private conversations and reserved legacy config."""

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import stat
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.core.security import redact, safe_input

Role = Literal["admin", "customer"]
REFRESH_SECONDS = 7 * 24 * 60 * 60


@dataclass(frozen=True)
class User:
    id: str
    name: str
    email: str
    role: Role
    password_hash: str = field(repr=False)


@dataclass(frozen=True)
class Customer:
    id: str
    name: str
    email: str
    created_at: datetime
    role: Literal["customer"] = "customer"


def validate_customer_page(limit: int, offset: int) -> None:
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
        raise ValueError("La paginación de clientes es inválida.")


class SetupAlreadyComplete(ValueError):
    pass


class RegistrationUnavailable(ValueError):
    pass


def _master_secret(directory: Path) -> bytes:
    """Link a fully written private random file into place, never replace an existing secret."""
    target = directory / ".application-secret"
    temporary = directory / f".application-secret-{uuid.uuid4().hex}.tmp"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(secrets.token_bytes(32))
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary, target)
            parent = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(parent)
            finally:
                os.close(parent)
        except FileExistsError:
            pass
    finally:
        temporary.unlink(missing_ok=True)
    descriptor = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise RuntimeError("El archivo de seguridad debe ser regular y privado (0600).")
        with os.fdopen(descriptor, "rb") as source:
            descriptor = -1
            value = source.read(33)
        if len(value) != 32:
            raise RuntimeError("El archivo de seguridad no es válido.")
        return value
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def signing_secret(data_dir: Path, override: bytes | None = None) -> bytes:
    data_dir.mkdir(parents=True, exist_ok=True)
    if override is not None:
        return override
    return hmac.digest(_master_secret(data_dir), b"humanizar.access.v1", "sha256")


class ApplicationDatabase:
    def __init__(self, data_dir: Path, jwt_secret: bytes | None = None) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        master = _master_secret(data_dir)
        self._jwt_secret = jwt_secret or hmac.digest(master, b"humanizar.access.v1", "sha256")
        self._lock = threading.RLock()
        path = data_dir / "application.sqlite3"
        if path.is_symlink():
            raise RuntimeError("La base de datos de aplicación no puede ser un enlace.")
        with ExitStack() as resources:
            self._db = sqlite3.connect(
                path, timeout=10, isolation_level=None, check_same_thread=False
            )
            resources.callback(self._db.close)
            self._initialize_schema(path)
            resources.pop_all()

    def _initialize_schema(self, path: Path) -> None:
        self._db.row_factory = sqlite3.Row
        os.chmod(path, 0o600)
        self._db.executescript(
            "PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON; PRAGMA busy_timeout=10000;"
            "CREATE TABLE IF NOT EXISTS users ("
            "id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, "
            "role TEXT NOT NULL CHECK(role IN ('admin','customer')), password_hash TEXT NOT NULL, "
            "created_at REAL NOT NULL);"
            "CREATE UNIQUE INDEX IF NOT EXISTS one_admin ON users(role) WHERE role='admin';"
            "CREATE TABLE IF NOT EXISTS sessions ("
            "id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
            "family_id TEXT NOT NULL, "
            "refresh_hash TEXT NOT NULL UNIQUE, created_at REAL NOT NULL, "
            "expires_at REAL NOT NULL, "
            "revoked_at REAL);"
            "CREATE INDEX IF NOT EXISTS sessions_owner ON sessions(user_id);"
            "CREATE TABLE IF NOT EXISTS conversations ("
            "id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
            "title TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL);"
            "CREATE INDEX IF NOT EXISTS conversations_owner ON conversations(user_id);"
            "CREATE TABLE IF NOT EXISTS messages ("
            "seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE, "
            "conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE, "
            "role TEXT NOT NULL CHECK(role IN ('user','assistant')), content TEXT NOT NULL, "
            "sources_json TEXT NOT NULL DEFAULT '[]', trace_json TEXT NOT NULL DEFAULT '[]', "
            "created_at REAL NOT NULL);"
            "CREATE INDEX IF NOT EXISTS messages_conversation ON messages(conversation_id,seq);"
            "CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
        )
        with self._transaction():
            columns = {str(row["name"]) for row in self._db.execute("PRAGMA table_info(sessions)")}
            if "family_id" not in columns:
                self._db.execute("ALTER TABLE sessions ADD COLUMN family_id TEXT")
            self._db.execute(
                "UPDATE sessions SET family_id=id WHERE family_id IS NULL OR family_id=''"
            )
            self._db.execute("CREATE INDEX IF NOT EXISTS sessions_family ON sessions(family_id)")

    @property
    def jwt_secret(self) -> bytes:
        return self._jwt_secret

    @contextmanager
    def _transaction(self, *, immediate: bool = True) -> Iterator[None]:
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            try:
                yield
            except BaseException:
                self._db.rollback()
                raise
            else:
                self._db.commit()

    @staticmethod
    def _user(row: sqlite3.Row) -> User:
        return User(
            id=str(row["id"]),
            name=str(row["name"]),
            email=str(row["email"]),
            role="admin" if row["role"] == "admin" else "customer",
            password_hash=str(row["password_hash"]),
        )

    def setup_required(self) -> bool:
        with self._lock:
            return self._db.execute("SELECT 1 FROM users WHERE role='admin'").fetchone() is None

    def get_user(self, user_id: str) -> User | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            return self._user(row) if row is not None else None

    def get_user_by_email(self, email: str) -> User | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM users WHERE email=?", (email.strip().casefold(),))
            value = row.fetchone()
            return self._user(value) if value is not None else None

    def _insert_user(self, name: str, email: str, password_hash: str, role: Role) -> User:
        user = User(
            id=str(uuid.uuid4()),
            name=name.strip(),
            email=email.strip().casefold(),
            role=role,
            password_hash=password_hash,
        )
        try:
            self._db.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                (user.id, user.name, user.email, user.role, password_hash, time.time()),
            )
        except sqlite3.IntegrityError:
            raise ValueError("No se pudo crear la cuenta.") from None
        return user

    def bootstrap_admin(self, name: str, email: str, password_hash: str) -> User:
        with self._transaction():
            if not self.setup_required():
                raise SetupAlreadyComplete("La configuración inicial ya está completa.")
            return self._insert_user(name, email, password_hash, "admin")

    def register_customer(self, name: str, email: str, password_hash: str) -> User:
        with self._transaction():
            if self.setup_required():
                raise RegistrationUnavailable("La configuración inicial está pendiente.")
            return self._insert_user(name, email, password_hash, "customer")

    @staticmethod
    def _customer(row: sqlite3.Row) -> Customer:
        return Customer(
            id=str(row["id"]),
            name=str(row["name"]),
            email=str(row["email"]),
            created_at=datetime.fromtimestamp(float(row["created_at"]), UTC),
        )

    def get_customer(self, user_id: str) -> Customer | None:
        with self._lock:
            row = self._db.execute(
                "SELECT id,name,email,created_at FROM users WHERE id=? AND role='customer'",
                (user_id,),
            ).fetchone()
            return self._customer(row) if row is not None else None

    def list_customers(self, limit: int = 25, offset: int = 0) -> tuple[list[Customer], int]:
        validate_customer_page(limit, offset)
        with self._transaction(immediate=False):
            total = int(
                self._db.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0]
            )
            if offset >= total:
                return [], total
            rows = self._db.execute(
                "SELECT id,name,email,created_at FROM users WHERE role='customer' "
                "ORDER BY created_at DESC,id LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [self._customer(row) for row in rows], total

    @staticmethod
    def _refresh_hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def create_session(self, user_id: str, refresh_token: str) -> str:
        with self._transaction():
            identifier, now = str(uuid.uuid4()), time.time()
            self._db.execute(
                "INSERT INTO sessions (id,user_id,family_id,refresh_hash,created_at,expires_at,"
                "revoked_at) VALUES (?, ?, ?, ?, ?, ?, NULL)",
                (
                    identifier,
                    user_id,
                    identifier,
                    self._refresh_hash(refresh_token),
                    now,
                    now + REFRESH_SECONDS,
                ),
            )
            return identifier

    def session_user(self, session_id: str, user_id: str) -> User | None:
        with self._lock:
            row = self._db.execute(
                "SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id "
                "WHERE s.id=? AND s.user_id=? AND s.revoked_at IS NULL AND s.expires_at>?",
                (session_id, user_id, time.time()),
            ).fetchone()
            return self._user(row) if row is not None else None

    def rotate_refresh(self, previous: str, replacement: str) -> tuple[User, str] | None:
        with self._transaction():
            now = time.time()
            row = self._db.execute(
                "SELECT * FROM sessions WHERE refresh_hash=? AND revoked_at IS NULL "
                "AND expires_at>?",
                (self._refresh_hash(previous), now),
            ).fetchone()
            if row is None:
                return None
            user = self.get_user(str(row["user_id"]))
            if user is None:
                return None
            self._db.execute("UPDATE sessions SET revoked_at=? WHERE id=?", (now, row["id"]))
            identifier = str(uuid.uuid4())
            self._db.execute(
                "INSERT INTO sessions (id,user_id,family_id,refresh_hash,created_at,expires_at,"
                "revoked_at) VALUES (?, ?, ?, ?, ?, ?, NULL)",
                (
                    identifier,
                    user.id,
                    str(row["family_id"]),
                    self._refresh_hash(replacement),
                    now,
                    now + REFRESH_SECONDS,
                ),
            )
            return user, identifier

    def revoke_session(self, session_id: str, user_id: str | None = None) -> None:
        with self._lock:
            ownership = " AND user_id=?" if user_id is not None else ""
            parameters: tuple[float | str, ...] = (time.time(), session_id)
            if user_id is not None:
                parameters += (user_id,)
            self._db.execute(
                "UPDATE sessions SET revoked_at=? WHERE family_id=(SELECT family_id FROM "
                "sessions WHERE id=?" + ownership + ") AND revoked_at IS NULL",
                parameters,
            )

    def revoke_refresh(self, refresh_token: str) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE sessions SET revoked_at=? WHERE family_id=(SELECT family_id FROM "
                "sessions WHERE refresh_hash=?) AND revoked_at IS NULL",
                (time.time(), self._refresh_hash(refresh_token)),
            )

    def _owned_conversation(self, user_id: str, identifier: str) -> sqlite3.Row:
        row: sqlite3.Row | None = self._db.execute(
            "SELECT * FROM conversations WHERE id=?", (identifier,)
        ).fetchone()
        if row is None or row["user_id"] != user_id:
            raise PermissionError("Conversación no disponible.")
        return row

    def create_conversation(self, user_id: str, session_id: str | None, title: str) -> str:
        identifier = session_id or str(uuid.uuid4())
        if not re.fullmatch(r"[\w-]{1,100}", identifier):
            raise ValueError("Identificador de conversación inválido.")
        with self._transaction():
            existing = self._db.execute(
                "SELECT * FROM conversations WHERE id=?", (identifier,)
            ).fetchone()
            if existing is not None:
                self._owned_conversation(user_id, identifier)
                return identifier
            now = time.time()
            self._db.execute(
                "INSERT INTO conversations VALUES (?, ?, ?, ?, ?)",
                (identifier, user_id, redact(title.strip())[:120] or "Conversación", now, now),
            )
            return identifier

    def conversation_history(self, user_id: str, identifier: str) -> list[dict[str, str]]:
        with self._lock:
            self._owned_conversation(user_id, identifier)
            return [
                {"role": str(row["role"]), "content": str(row["content"])}
                for row in self._db.execute(
                    "SELECT role,content FROM messages WHERE conversation_id=? ORDER BY seq",
                    (identifier,),
                )
            ]

    def save_exchange(
        self, user_id: str, identifier: str, message: str, response: dict[str, Any]
    ) -> None:
        answer = response.get("answer")
        if not isinstance(answer, str):
            raise ValueError("Respuesta de conversación inválida.")
        evidence = safe_input(
            {"sources": response.get("sources", []), "trace": response.get("trace", [])}
        )
        with self._transaction():
            self._owned_conversation(user_id, identifier)
            now = time.time()
            self._db.executemany(
                "INSERT INTO messages (id,conversation_id,role,content,sources_json,trace_json,"
                "created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (str(uuid.uuid4()), identifier, "user", redact(message), "[]", "[]", now),
                    (
                        str(uuid.uuid4()),
                        identifier,
                        "assistant",
                        redact(answer),
                        json.dumps(evidence["sources"], ensure_ascii=False),
                        json.dumps(evidence["trace"], ensure_ascii=False),
                        now,
                    ),
                ],
            )
            self._db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, identifier))

    def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            conversations: list[dict[str, Any]] = []
            rows = self._db.execute(
                "SELECT * FROM conversations WHERE user_id=? ORDER BY updated_at DESC,id",
                (user_id,),
            ).fetchall()
            for conversation in rows:
                messages = [
                    {
                        "id": str(row["id"]),
                        "role": str(row["role"]),
                        "content": str(row["content"]),
                        "sources": json.loads(row["sources_json"]),
                        "trace": json.loads(row["trace_json"]),
                    }
                    for row in self._db.execute(
                        "SELECT * FROM messages WHERE conversation_id=? ORDER BY seq",
                        (conversation["id"],),
                    )
                ]
                conversations.append(
                    {
                        "id": str(conversation["id"]),
                        "title": str(conversation["title"]),
                        "messages": messages,
                        "sessionId": str(conversation["id"]),
                        "updatedAt": int(conversation["updated_at"] * 1000),
                    }
                )
            return conversations

    def delete_conversation(self, user_id: str, identifier: str) -> bool:
        with self._transaction():
            if not self._db.execute(
                "SELECT 1 FROM conversations WHERE id=?", (identifier,)
            ).fetchone():
                return False
            self._owned_conversation(user_id, identifier)
            self._db.execute("DELETE FROM conversations WHERE id=?", (identifier,))
            return True

    def close(self) -> None:
        with self._lock:
            self._db.close()
