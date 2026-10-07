"""PostgreSQL private conversations: row-locked ownership, redacted messages and evidence."""

import re
import time
import uuid
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.engine import Connection, RowMapping

from app.core.security import redact, safe_input
from app.persistence.postgres.base import PostgresRepository


class PostgresConversations(PostgresRepository):
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
            self._lock(connection, f"conversation:{identifier}")
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
