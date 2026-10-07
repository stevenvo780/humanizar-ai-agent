"""PostgreSQL pool ownership, schema initialization, transactions and user row mapping."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import select
from sqlalchemy.engine import Connection, RowMapping
from sqlalchemy.exc import SQLAlchemyError

from app.core.settings import Settings
from app.persistence.contracts import PersistenceUnavailable
from app.persistence.models import User
from app.persistence.postgres.connection import advisory_lock, bounded_engine, connection_options
from app.persistence.postgres.schema import PostgresTables
from app.persistence.signing import signing_secret


class PostgresRepository:
    """Owns the bounded pool; every statement is qualified by ``DATABASE_SCHEMA``."""

    def __init__(self, settings: Settings) -> None:
        url, options = connection_options(settings.database_url.get_secret_value())
        self.schema = settings.database_schema
        private_key = settings.jwt_secret.get_secret_value()
        self._jwt_secret = signing_secret(
            settings.data_dir, private_key.encode() if private_key else None
        )
        tables = PostgresTables(self.schema)
        self._metadata = tables.metadata
        self.marker = tables.marker
        self.users = tables.users
        self.sessions = tables.sessions
        self.conversations = tables.conversations
        self.messages = tables.messages
        self.requests = tables.requests
        self.engine = bounded_engine(url, options)
        try:
            with self.transaction() as connection:
                tables.initialize(connection)
        except BaseException:
            self.engine.dispose()
            raise

    @property
    def jwt_secret(self) -> bytes:
        return self._jwt_secret

    @contextmanager
    def transaction(self) -> Iterator[Connection]:
        try:
            with self.engine.begin() as connection:
                yield connection
        except SQLAlchemyError:
            raise PersistenceUnavailable() from None

    def _lock(self, connection: Connection, resource: str) -> None:
        advisory_lock(connection, self.schema, resource)

    @staticmethod
    def _user(row: RowMapping) -> User:
        return User(
            id=str(row["id"]),
            name=str(row["name"]),
            email=str(row["email"]),
            role="admin" if row["role"] == "admin" else "customer",
            password_hash=str(row["password_hash"]),
        )

    def get_user(self, user_id: str) -> User | None:
        with self.transaction() as connection:
            row = (
                connection.execute(select(self.users).where(self.users.c.id == user_id))
                .mappings()
                .first()
            )
            return self._user(row) if row is not None else None

    def close(self) -> None:
        self.engine.dispose()
