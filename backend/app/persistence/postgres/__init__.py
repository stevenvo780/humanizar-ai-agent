"""Remote PostgreSQL stores: qualified Core statements, bounded pool and transaction locks."""

from app.persistence.postgres.accounts import PostgresAccounts
from app.persistence.postgres.business import PostgresBusinessStore
from app.persistence.postgres.connection import connection_options
from app.persistence.postgres.conversations import PostgresConversations
from app.persistence.postgres.sessions import PostgresSessions


class PostgresApplicationDatabase(PostgresAccounts, PostgresSessions, PostgresConversations):
    """IdentityStore over the schema named by ``DATABASE_SCHEMA``; owns the shared pool."""


__all__ = ["PostgresApplicationDatabase", "PostgresBusinessStore", "connection_options"]
