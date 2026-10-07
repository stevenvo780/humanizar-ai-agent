"""PostgreSQL repositories: qualified Core statements, bounded pool and transaction locks."""

import hashlib
import ipaddress
import re
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlsplit

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
    create_engine,
    delete,
    func,
    inspect,
    select,
    update,
)
from sqlalchemy.engine import URL, Connection, RowMapping, make_url
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.schema import CreateSchema

from app.business.requests import (
    ACTION_KEY_PATTERN,
    BusinessValidationError,
    RequestKind,
    validate_details,
    validate_user_id,
)
from app.core.security import redact, safe_input
from app.core.settings import Settings
from app.persistence.contracts import PersistenceUnavailable
from app.persistence.sqlite import (
    REFRESH_SECONDS,
    Customer,
    RegistrationUnavailable,
    Role,
    SetupAlreadyComplete,
    User,
    signing_secret,
    validate_customer_page,
)

APPLICATION_ID = "humanizar-lumen-v1"


def connection_options(value: str) -> tuple[URL, dict[str, str | int]]:
    """Only loopback permits cleartext; remote TLS always verifies CA and hostname."""
    try:
        fields = parse_qsl(
            urlsplit(value).query,
            keep_blank_values=True,
            max_num_fields=2,
            strict_parsing=True,
        )
        query = dict(fields)
        if len(query) != len(fields) or any(
            key not in {"sslmode", "sslrootcert"} or not parameter for key, parameter in fields
        ):
            raise ValueError
        url = make_url(value)
        if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
            raise ValueError
        if not url.host or not url.database:
            raise ValueError
        if url.port is not None and not 1 <= url.port <= 65535:
            raise ValueError
        if any(not isinstance(item, str) for item in url.query.values()):
            raise ValueError
        if set(url.query) - {"sslmode", "sslrootcert"}:
            raise ValueError
        host = url.host.casefold()
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = host == "localhost"
        requested = query.get("sslmode", "verify-full")
        if not loopback and requested != "verify-full":
            raise ValueError
        if requested not in {"disable", "verify-full"}:
            raise ValueError
        options: dict[str, str | int] = {
            "connect_timeout": 5,
            "sslmode": str(requested),
            "options": (
                "-c statement_timeout=10000 -c lock_timeout=5000 "
                "-c idle_in_transaction_session_timeout=15000"
            ),
        }
        if requested == "verify-full":
            options["sslrootcert"] = query.get("sslrootcert", "system")
        elif "sslrootcert" in query:
            raise ValueError
        return url.set(drivername="postgresql+psycopg", query={}), options
    except (ValueError, TypeError, SQLAlchemyError):
        raise ValueError(
            "DATABASE_URL debe ser PostgreSQL con TLS verify-full fuera de loopback."
        ) from None


def _lock(connection: Connection, schema: str, resource: str) -> None:
    digest = hashlib.sha256(f"{APPLICATION_ID}:{schema}:{resource}".encode()).digest()
    key = int.from_bytes(digest[:8], "big", signed=True)
    connection.execute(select(func.pg_advisory_xact_lock(key)))


class PostgresApplicationDatabase:
    def __init__(self, settings: Settings) -> None:
        url, options = connection_options(settings.database_url.get_secret_value())
        self.schema = settings.database_schema
        private_key = settings.jwt_secret.get_secret_value()
        self._jwt_secret = signing_secret(
            settings.data_dir, private_key.encode() if private_key else None
        )
        self._metadata = MetaData(schema=self.schema)
        self.marker = Table(
            "_lumen_schema_identity",
            self._metadata,
            Column("id", Integer, primary_key=True),
            Column("application", String(80), nullable=False),
            CheckConstraint("id = 1"),
        )
        self.users = Table(
            "users",
            self._metadata,
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
            self._metadata,
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
            self._metadata,
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
            self._metadata,
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
            self._metadata,
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
        self.engine = create_engine(
            url,
            connect_args=options,
            pool_size=5,
            max_overflow=2,
            pool_timeout=5,
            pool_recycle=300,
            pool_pre_ping=True,
            echo=False,
            hide_parameters=True,
        )
        try:
            with self.transaction() as connection:
                _lock(connection, self.schema, "initialize")
                inspector = inspect(connection)
                existing = set(inspector.get_table_names(schema=self.schema))
                if existing:
                    if self.marker.name not in existing:
                        raise ValueError("DATABASE_SCHEMA contiene tablas de otra aplicación.")
                    identity = connection.execute(
                        select(self.marker.c.application)
                    ).scalar_one_or_none()
                    if identity != APPLICATION_ID:
                        raise ValueError("DATABASE_SCHEMA pertenece a otra aplicación.")
                connection.execute(CreateSchema(self.schema, if_not_exists=True))
                self._metadata.create_all(connection)
                if not existing:
                    connection.execute(
                        self.marker.insert().values(id=1, application=APPLICATION_ID)
                    )
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

    @staticmethod
    def _user(row: RowMapping) -> User:
        return User(
            id=str(row["id"]),
            name=str(row["name"]),
            email=str(row["email"]),
            role="admin" if row["role"] == "admin" else "customer",
            password_hash=str(row["password_hash"]),
        )

    def setup_required(self) -> bool:
        with self.transaction() as connection:
            return (
                connection.execute(
                    select(self.users.c.id).where(self.users.c.role == "admin")
                ).first()
                is None
            )

    def get_user(self, user_id: str) -> User | None:
        with self.transaction() as connection:
            row = (
                connection.execute(select(self.users).where(self.users.c.id == user_id))
                .mappings()
                .first()
            )
            return self._user(row) if row is not None else None

    def get_user_by_email(self, email: str) -> User | None:
        with self.transaction() as connection:
            row = (
                connection.execute(
                    select(self.users).where(self.users.c.email == email.strip().casefold())
                )
                .mappings()
                .first()
            )
            return self._user(row) if row is not None else None

    def _create_user(self, name: str, email: str, password_hash: str, role: Role) -> User:
        with self.transaction() as connection:
            _lock(connection, self.schema, "bootstrap")
            admin = connection.execute(
                select(self.users.c.id).where(self.users.c.role == "admin")
            ).first()
            if role == "admin" and admin is not None:
                raise SetupAlreadyComplete("La configuración inicial ya está completa.")
            if role == "customer" and admin is None:
                raise RegistrationUnavailable("La configuración inicial está pendiente.")
            user = User(
                str(uuid.uuid4()), name.strip(), email.strip().casefold(), role, password_hash
            )
            try:
                connection.execute(
                    self.users.insert().values(
                        id=user.id,
                        name=user.name,
                        email=user.email,
                        role=role,
                        password_hash=password_hash,
                        created_at=time.time(),
                    )
                )
            except IntegrityError:
                raise ValueError("No se pudo crear la cuenta.") from None
            return user

    def bootstrap_admin(self, name: str, email: str, password_hash: str) -> User:
        return self._create_user(name, email, password_hash, "admin")

    def register_customer(self, name: str, email: str, password_hash: str) -> User:
        return self._create_user(name, email, password_hash, "customer")

    @staticmethod
    def _customer(row: RowMapping) -> Customer:
        return Customer(
            id=str(row["id"]),
            name=str(row["name"]),
            email=str(row["email"]),
            created_at=datetime.fromtimestamp(float(row["created_at"]), UTC),
        )

    def get_customer(self, user_id: str) -> Customer | None:
        with self.transaction() as connection:
            row = (
                connection.execute(
                    select(
                        self.users.c.id,
                        self.users.c.name,
                        self.users.c.email,
                        self.users.c.created_at,
                    ).where(self.users.c.id == user_id, self.users.c.role == "customer")
                )
                .mappings()
                .first()
            )
            return self._customer(row) if row is not None else None

    def list_customers(self, limit: int = 25, offset: int = 0) -> tuple[list[Customer], int]:
        validate_customer_page(limit, offset)
        with self.transaction() as connection:
            connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            total = int(
                connection.execute(
                    select(func.count())
                    .select_from(self.users)
                    .where(self.users.c.role == "customer")
                ).scalar_one()
            )
            if offset >= total:
                return [], total
            rows = (
                connection.execute(
                    select(
                        self.users.c.id,
                        self.users.c.name,
                        self.users.c.email,
                        self.users.c.created_at,
                    )
                    .where(self.users.c.role == "customer")
                    .order_by(self.users.c.created_at.desc(), self.users.c.id)
                    .limit(limit)
                    .offset(offset)
                )
                .mappings()
                .all()
            )
            return [self._customer(row) for row in rows], total

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
            _lock(connection, self.schema, f"session:{family}")
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
        _lock(connection, self.schema, f"session:{family}")
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

    def _owned_conversation(
        self, connection: Connection, user_id: str, identifier: str
    ) -> RowMapping:
        row = (
            connection.execute(
                select(self.conversations)
                .where(self.conversations.c.id == identifier)
                .with_for_update()
            )
            .mappings()
            .first()
        )
        if row is None or row["user_id"] != user_id:
            raise PermissionError("Conversación no disponible.")
        return row

    def create_conversation(self, user_id: str, session_id: str | None, title: str) -> str:
        identifier = session_id or str(uuid.uuid4())
        if not re.fullmatch(r"[\w-]{1,100}", identifier):
            raise ValueError("Identificador de conversación inválido.")
        with self.transaction() as connection:
            _lock(connection, self.schema, f"conversation:{identifier}")
            existing = connection.execute(
                select(self.conversations.c.user_id).where(self.conversations.c.id == identifier)
            ).scalar_one_or_none()
            if existing is not None:
                if existing != user_id:
                    raise PermissionError("Conversación no disponible.")
                return identifier
            now = time.time()
            connection.execute(
                self.conversations.insert().values(
                    id=identifier,
                    user_id=user_id,
                    title=redact(title.strip())[:120] or "Conversación",
                    created_at=now,
                    updated_at=now,
                )
            )
            return identifier

    def conversation_history(self, user_id: str, identifier: str) -> list[dict[str, str]]:
        with self.transaction() as connection:
            self._owned_conversation(connection, user_id, identifier)
            rows = connection.execute(
                select(self.messages.c.role, self.messages.c.content)
                .where(self.messages.c.conversation_id == identifier)
                .order_by(self.messages.c.seq)
            ).mappings()
            return [{"role": str(row["role"]), "content": str(row["content"])} for row in rows]

    def save_exchange(
        self, user_id: str, identifier: str, message: str, response: dict[str, Any]
    ) -> None:
        answer = response.get("answer")
        if not isinstance(answer, str):
            raise ValueError("Respuesta de conversación inválida.")
        evidence = safe_input(
            {"sources": response.get("sources", []), "trace": response.get("trace", [])}
        )
        with self.transaction() as connection:
            self._owned_conversation(connection, user_id, identifier)
            now = time.time()
            connection.execute(
                self.messages.insert(),
                [
                    {
                        "id": str(uuid.uuid4()),
                        "conversation_id": identifier,
                        "role": "user",
                        "content": redact(message),
                        "sources": [],
                        "trace": [],
                        "created_at": now,
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "conversation_id": identifier,
                        "role": "assistant",
                        "content": redact(answer),
                        "sources": evidence["sources"],
                        "trace": evidence["trace"],
                        "created_at": now,
                    },
                ],
            )
            connection.execute(
                update(self.conversations)
                .where(self.conversations.c.id == identifier)
                .values(updated_at=now)
            )

    def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            conversations: list[dict[str, Any]] = []
            rows = (
                connection.execute(
                    select(self.conversations)
                    .where(self.conversations.c.user_id == user_id)
                    .order_by(self.conversations.c.updated_at.desc(), self.conversations.c.id)
                )
                .mappings()
                .all()
            )
            for row in rows:
                messages = [
                    {
                        "id": str(message["id"]),
                        "role": str(message["role"]),
                        "content": str(message["content"]),
                        "sources": message["sources"],
                        "trace": message["trace"],
                    }
                    for message in connection.execute(
                        select(self.messages)
                        .where(self.messages.c.conversation_id == row["id"])
                        .order_by(self.messages.c.seq)
                    ).mappings()
                ]
                conversations.append(
                    {
                        "id": str(row["id"]),
                        "title": str(row["title"]),
                        "messages": messages,
                        "sessionId": str(row["id"]),
                        "updatedAt": int(float(row["updated_at"]) * 1000),
                    }
                )
            return conversations

    def delete_conversation(self, user_id: str, identifier: str) -> bool:
        with self.transaction() as connection:
            if (
                connection.execute(
                    select(self.conversations.c.id).where(self.conversations.c.id == identifier)
                ).first()
                is None
            ):
                return False
            self._owned_conversation(connection, user_id, identifier)
            connection.execute(
                delete(self.conversations).where(self.conversations.c.id == identifier)
            )
            return True

    def close(self) -> None:
        self.engine.dispose()


class PostgresBusinessStore:
    """Uses the identity repository's bounded pool; only that owner disposes the pool."""

    def __init__(self, database: PostgresApplicationDatabase) -> None:
        self.database = database
        self.requests = database.requests

    @staticmethod
    def _public(row: RowMapping) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "kind": str(row["kind"]),
            "status": str(row["status"]),
            "created_at": str(row["created_at"]),
            "details": row["details"],
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
        if action_key is not None and not ACTION_KEY_PATTERN.fullmatch(action_key):
            raise BusinessValidationError("La clave de confirmación es inválida.")
        with self.database.transaction() as connection:
            if action_key is not None:
                _lock(connection, self.database.schema, f"request:{user_id}:{action_key}")
                prior = (
                    connection.execute(
                        select(self.requests).where(
                            self.requests.c.user_id == user_id,
                            self.requests.c.action_key == action_key,
                        )
                    )
                    .mappings()
                    .first()
                )
                if prior is not None:
                    if prior["kind"] != kind or prior["details"] != clean:
                        raise BusinessValidationError(
                            "Esta confirmación ya corresponde a otra solicitud."
                        )
                    return self._public(prior)
            record = {
                "id": str(uuid.uuid4()),
                "kind": kind,
                "status": "received",
                "details": clean,
                "created_at": datetime.now(UTC).isoformat(),
            }
            connection.execute(
                self.requests.insert().values(**record, user_id=user_id, action_key=action_key)
            )
            return record

    def list_requests(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        validate_user_id(user_id)
        if type(limit) is not int or not 1 <= limit <= 20:
            raise BusinessValidationError("El límite de solicitudes es inválido.")
        with self.database.transaction() as connection:
            rows = connection.execute(
                select(self.requests)
                .where(self.requests.c.user_id == user_id)
                .order_by(self.requests.c.created_at.desc(), self.requests.c.id.desc())
                .limit(limit)
            ).mappings()
            return [self._public(row) for row in rows]

    def list_all_requests(self, limit: int = 50) -> list[dict[str, Any]]:
        if type(limit) is not int or not 1 <= limit <= 50:
            raise BusinessValidationError("El límite de solicitudes es inválido.")
        with self.database.transaction() as connection:
            rows = connection.execute(
                select(self.requests)
                .order_by(self.requests.c.created_at.desc(), self.requests.c.id.desc())
                .limit(limit)
            ).mappings()
            return [{**self._public(row), "user_id": str(row["user_id"])} for row in rows]

    def close(self) -> None:
        pass
