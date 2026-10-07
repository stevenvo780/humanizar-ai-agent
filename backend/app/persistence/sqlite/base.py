"""SQLite connection, schema, transactions and the user row mapping shared by its stores."""

import os
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path

from app.persistence.models import User
from app.persistence.signing import access_key, master_secret


class SQLiteRepository:
    """One serialized connection; the reserved legacy ``config`` table is preserved."""

    def __init__(self, data_dir: Path, jwt_secret: bytes | None = None) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        master = master_secret(data_dir)
        self._jwt_secret = jwt_secret or access_key(master)
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

    def get_user(self, user_id: str) -> User | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            return self._user(row) if row is not None else None

    def close(self) -> None:
        with self._lock:
            self._db.close()
