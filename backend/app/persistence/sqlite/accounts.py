"""SQLite accounts: first-admin bootstrap, customer signup and paginated customer listing."""

import sqlite3
import time
import uuid
from datetime import UTC, datetime

from app.persistence.models import (
    Customer,
    RegistrationUnavailable,
    Role,
    SetupAlreadyComplete,
    User,
    validate_customer_page,
)
from app.persistence.sqlite.base import SQLiteRepository


class SQLiteAccounts(SQLiteRepository):
    def setup_required(self) -> bool:
        with self._lock:
            return self._db.execute("SELECT 1 FROM users WHERE role='admin'").fetchone() is None

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
