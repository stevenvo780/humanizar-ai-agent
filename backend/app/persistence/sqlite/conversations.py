"""SQLite private conversations: ownership checks, redacted messages and stored evidence."""

import json
import re
import sqlite3
import time
import uuid
from typing import Any

from app.core.security import redact, safe_input
from app.persistence.sqlite.base import SQLiteRepository


class SQLiteConversations(SQLiteRepository):
    def _owned_conversation(self, user_id: str, identifier: str) -> sqlite3.Row:
        row: sqlite3.Row | None = self._db.execute(
            "SELECT * FROM conversations WHERE id=?", (identifier,)
        ).fetchone()
        if row is None or row["user_id"] != user_id:
            raise PermissionError("Conversación no disponible.")
        return row

    def create_conversation(self, user_id: str, session_id: str | None, title: str) -> str:
        identifier = session_id or str(uuid.uuid4())
        if not re.fullmatch(r"[\w-]{1,100}", identifier):
            raise ValueError("Identificador de conversación inválido.")
        with self._transaction():
            existing = self._db.execute(
                "SELECT * FROM conversations WHERE id=?", (identifier,)
            ).fetchone()
            if existing is not None:
                self._owned_conversation(user_id, identifier)
                return identifier
            now = time.time()
            self._db.execute(
                "INSERT INTO conversations VALUES (?, ?, ?, ?, ?)",
                (identifier, user_id, redact(title.strip())[:120] or "Conversación", now, now),
            )
            return identifier

    def conversation_history(self, user_id: str, identifier: str) -> list[dict[str, str]]:
        with self._lock:
            self._owned_conversation(user_id, identifier)
            return [
                {"role": str(row["role"]), "content": str(row["content"])}
                for row in self._db.execute(
                    "SELECT role,content FROM messages WHERE conversation_id=? ORDER BY seq",
                    (identifier,),
                )
            ]

    def save_exchange(
        self, user_id: str, identifier: str, message: str, response: dict[str, Any]
    ) -> None:
        answer = response.get("answer")
        if not isinstance(answer, str):
            raise ValueError("Respuesta de conversación inválida.")
        evidence = safe_input(
            {"sources": response.get("sources", []), "trace": response.get("trace", [])}
        )
        with self._transaction():
            self._owned_conversation(user_id, identifier)
            now = time.time()
            self._db.executemany(
                "INSERT INTO messages (id,conversation_id,role,content,sources_json,trace_json,"
                "created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (str(uuid.uuid4()), identifier, "user", redact(message), "[]", "[]", now),
                    (
                        str(uuid.uuid4()),
                        identifier,
                        "assistant",
                        redact(answer),
                        json.dumps(evidence["sources"], ensure_ascii=False),
                        json.dumps(evidence["trace"], ensure_ascii=False),
                        now,
                    ),
                ],
            )
            self._db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, identifier))

    def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            conversations: list[dict[str, Any]] = []
            rows = self._db.execute(
                "SELECT * FROM conversations WHERE user_id=? ORDER BY updated_at DESC,id",
                (user_id,),
            ).fetchall()
            for conversation in rows:
                messages = [
                    {
                        "id": str(row["id"]),
                        "role": str(row["role"]),
                        "content": str(row["content"]),
                        "sources": json.loads(row["sources_json"]),
                        "trace": json.loads(row["trace_json"]),
                    }
                    for row in self._db.execute(
                        "SELECT * FROM messages WHERE conversation_id=? ORDER BY seq",
                        (conversation["id"],),
                    )
                ]
                conversations.append(
                    {
                        "id": str(conversation["id"]),
                        "title": str(conversation["title"]),
                        "messages": messages,
                        "sessionId": str(conversation["id"]),
                        "updatedAt": int(conversation["updated_at"] * 1000),
                    }
                )
            return conversations

    def delete_conversation(self, user_id: str, identifier: str) -> bool:
        with self._transaction():
            if not self._db.execute(
                "SELECT 1 FROM conversations WHERE id=?", (identifier,)
            ).fetchone():
                return False
            self._owned_conversation(user_id, identifier)
            self._db.execute("DELETE FROM conversations WHERE id=?", (identifier,))
            return True
