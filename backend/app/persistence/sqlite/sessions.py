"""SQLite refresh sessions: hashed tokens, rotation within a family and family revocation."""

import hashlib
import time
import uuid

from app.persistence.models import REFRESH_SECONDS, User
from app.persistence.sqlite.base import SQLiteRepository


class SQLiteSessions(SQLiteRepository):
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
