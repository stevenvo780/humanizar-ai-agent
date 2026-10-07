"""Schema-qualified PostgreSQL tables and the identity marker that refuses foreign schemas."""

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    inspect,
    select,
)
from sqlalchemy.engine import Connection
from sqlalchemy.schema import CreateSchema

from app.persistence.postgres.connection import APPLICATION_ID, advisory_lock


class PostgresTables:
    def __init__(self, schema: str) -> None:
        self.schema = schema
        self.metadata = MetaData(schema=schema)
        self.marker = Table(
            "_lumen_schema_identity",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("application", String(80), nullable=False),
            CheckConstraint("id = 1"),
        )
        self.users = Table(
            "users",
            self.metadata,
            Column("id", String(36), primary_key=True),
            Column("name", String(120), nullable=False),
            Column("email", String(254), nullable=False, unique=True),
            Column("role", String(8), nullable=False),
            Column("password_hash", Text, nullable=False),
            Column("created_at", Float, nullable=False),
            CheckConstraint("role IN ('admin','customer')"),
        )
        Index(
            "one_admin",
            self.users.c.role,
            unique=True,
            postgresql_where=self.users.c.role == "admin",
        )
        self.sessions = Table(
            "sessions",
            self.metadata,
            Column("id", String(36), primary_key=True),
            Column(
                "user_id",
                String(36),
                ForeignKey(self.users.c.id, ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            Column("family_id", String(36), nullable=False, index=True),
            Column("refresh_hash", String(64), nullable=False, unique=True),
            Column("created_at", Float, nullable=False),
            Column("expires_at", Float, nullable=False),
            Column("revoked_at", Float),
        )
        self.conversations = Table(
            "conversations",
            self.metadata,
            Column("id", String(100), primary_key=True),
            Column(
                "user_id",
                String(36),
                ForeignKey(self.users.c.id, ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            Column("title", String(120), nullable=False),
            Column("created_at", Float, nullable=False),
            Column("updated_at", Float, nullable=False),
        )
        self.messages = Table(
            "messages",
            self.metadata,
            Column("seq", Integer, primary_key=True, autoincrement=True),
            Column("id", String(36), nullable=False, unique=True),
            Column(
                "conversation_id",
                String(100),
                ForeignKey(self.conversations.c.id, ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            Column("role", String(9), nullable=False),
            Column("content", Text, nullable=False),
            Column("sources", JSON, nullable=False),
            Column("trace", JSON, nullable=False),
            Column("created_at", Float, nullable=False),
            CheckConstraint("role IN ('user','assistant')"),
        )
        self.requests = Table(
            "business_requests",
            self.metadata,
            Column("id", String(36), primary_key=True),
            Column(
                "user_id",
                String(36),
                ForeignKey(self.users.c.id, ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            Column("kind", String(7), nullable=False),
            Column("status", String(8), nullable=False),
            Column("details", JSON, nullable=False),
            Column("created_at", String(40), nullable=False),
            Column("action_key", String(100)),
            CheckConstraint("kind IN ('demo','support')"),
            CheckConstraint("status = 'received'"),
            UniqueConstraint("user_id", "action_key"),
        )

    def initialize(self, connection: Connection) -> None:
        """Create a new schema or reuse ours; never write into another application's tables."""
        advisory_lock(connection, self.schema, "initialize")
        inspector = inspect(connection)
        existing = set(inspector.get_table_names(schema=self.schema))
        if existing:
            if self.marker.name not in existing:
                raise ValueError("DATABASE_SCHEMA contiene tablas de otra aplicación.")
            identity = connection.execute(select(self.marker.c.application)).scalar_one_or_none()
            if identity != APPLICATION_ID:
                raise ValueError("DATABASE_SCHEMA pertenece a otra aplicación.")
        connection.execute(CreateSchema(self.schema, if_not_exists=True))
        self.metadata.create_all(connection)
        if not existing:
            connection.execute(self.marker.insert().values(id=1, application=APPLICATION_ID))
