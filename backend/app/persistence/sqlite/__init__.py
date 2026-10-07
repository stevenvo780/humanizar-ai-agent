"""Local SQLite identity store: accounts, revocable sessions and private conversations."""

from app.persistence.sqlite.accounts import SQLiteAccounts
from app.persistence.sqlite.conversations import SQLiteConversations
from app.persistence.sqlite.sessions import SQLiteSessions


class ApplicationDatabase(SQLiteAccounts, SQLiteSessions, SQLiteConversations):
    """IdentityStore over one serialized connection in ``DATA_DIR/application.sqlite3``."""


__all__ = ["ApplicationDatabase"]
