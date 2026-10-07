"""PostgreSQL business requests with idempotent, advisory-locked confirmation keys."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import RowMapping

from app.business.requests import (
    ACTION_KEY_PATTERN,
    BusinessValidationError,
    RequestKind,
    validate_details,
    validate_user_id,
)
from app.persistence.postgres.base import PostgresRepository
from app.persistence.postgres.connection import advisory_lock


class PostgresBusinessStore:
    """Uses the identity repository's bounded pool; only that owner disposes the pool."""

    def __init__(self, database: PostgresRepository) -> None:
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
                advisory_lock(connection, self.database.schema, f"request:{user_id}:{action_key}")
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
