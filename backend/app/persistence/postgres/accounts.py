"""PostgreSQL accounts: locked first-admin bootstrap, customer signup and customer listing."""

import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError

from app.persistence.models import (
    Customer,
    RegistrationUnavailable,
    Role,
    SetupAlreadyComplete,
    User,
    validate_customer_page,
)
from app.persistence.postgres.base import PostgresRepository


class PostgresAccounts(PostgresRepository):
    def setup_required(self) -> bool:
        with self.transaction() as connection:
            return (
                connection.execute(
                    select(self.users.c.id).where(self.users.c.role == "admin")
                ).first()
                is None
            )

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
            self._lock(connection, "bootstrap")
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
