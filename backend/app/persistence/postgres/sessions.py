"""PostgreSQL refresh sessions: family-locked rotation and revocation of hashed tokens."""

import hashlib
import time
import uuid

from sqlalchemy import select, update
from sqlalchemy.engine import Connection

from app.persistence.models import REFRESH_SECONDS, User
from app.persistence.postgres.base import PostgresRepository


class PostgresSessions(PostgresRepository):
    @staticmethod
    def _refresh_hash(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    def _insert_session(
        self, connection: Connection, user_id: str, refresh: str, family_id: str | None = None
    ) -> str:
        identifier, now = str(uuid.uuid4()), time.time()
        connection.execute(
            self.sessions.insert().values(
                id=identifier,
                user_id=user_id,
                family_id=family_id or identifier,
                refresh_hash=self._refresh_hash(refresh),
                created_at=now,
                expires_at=now + REFRESH_SECONDS,
                revoked_at=None,
            )
        )
        return identifier

    def create_session(self, user_id: str, refresh_token: str) -> str:
        with self.transaction() as connection:
            return self._insert_session(connection, user_id, refresh_token)

    def session_user(self, session_id: str, user_id: str) -> User | None:
        with self.transaction() as connection:
            row = (
                connection.execute(
                    select(self.users)
                    .join(self.sessions)
                    .where(
                        self.sessions.c.id == session_id,
                        self.sessions.c.user_id == user_id,
                        self.sessions.c.revoked_at.is_(None),
                        self.sessions.c.expires_at > time.time(),
                    )
                )
                .mappings()
                .first()
            )
            return self._user(row) if row is not None else None

    def rotate_refresh(self, previous: str, replacement: str) -> tuple[User, str] | None:
        with self.transaction() as connection:
            lookup = self.sessions.c.refresh_hash == self._refresh_hash(previous)
            family = connection.execute(
                select(self.sessions.c.family_id).where(lookup)
            ).scalar_one_or_none()
            if family is None:
                return None
            # Acquire family lock BEFORE row locks; logout sees the committed replacement.
            self._lock(connection, f"session:{family}")
            row = (
                connection.execute(
                    select(self.sessions)
                    .where(
                        lookup,
                        self.sessions.c.revoked_at.is_(None),
                        self.sessions.c.expires_at > time.time(),
                    )
                    .with_for_update()
                )
                .mappings()
                .first()
            )
            if row is None:
                return None
            user_row = (
                connection.execute(select(self.users).where(self.users.c.id == row["user_id"]))
                .mappings()
                .one()
            )
            user = self._user(user_row)
            connection.execute(
                update(self.sessions)
                .where(self.sessions.c.id == row["id"])
                .values(revoked_at=time.time())
            )
            identifier = self._insert_session(connection, user.id, replacement, str(family))
            return user, identifier

    def _revoke_family(self, connection: Connection, family: str | None) -> None:
        if family is None:
            return
        self._lock(connection, f"session:{family}")
        connection.execute(
            update(self.sessions)
            .where(self.sessions.c.family_id == family, self.sessions.c.revoked_at.is_(None))
            .values(revoked_at=time.time())
        )

    def revoke_session(self, session_id: str, user_id: str | None = None) -> None:
        with self.transaction() as connection:
            statement = select(self.sessions.c.family_id).where(self.sessions.c.id == session_id)
            if user_id is not None:
                statement = statement.where(self.sessions.c.user_id == user_id)
            family = connection.execute(statement).scalar_one_or_none()
            self._revoke_family(connection, str(family) if family is not None else None)

    def revoke_refresh(self, refresh_token: str) -> None:
        with self.transaction() as connection:
            family = connection.execute(
                select(self.sessions.c.family_id).where(
                    self.sessions.c.refresh_hash == self._refresh_hash(refresh_token)
                )
            ).scalar_one_or_none()
            self._revoke_family(connection, str(family) if family is not None else None)
