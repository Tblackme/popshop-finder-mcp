from __future__ import annotations

import time
import uuid
from typing import Any

from db_runtime import connect


def _connect():
    return connect()


def init_feedback_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                message TEXT NOT NULL,
                page_url TEXT,
                user_id INTEGER,
                user_email TEXT,
                created_at REAL NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_feedback(
    message: str,
    page_url: str = "",
    user_id: int | None = None,
    user_email: str = "",
) -> str:
    init_feedback_db()
    feedback_id = str(uuid.uuid4())
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO feedback (id, message, page_url, user_id, user_email, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (feedback_id, message.strip(), page_url, user_id, user_email, time.time()),
        )
        conn.commit()
    finally:
        conn.close()
    return feedback_id


def list_feedback(limit: int = 100) -> list[dict[str, Any]]:
    init_feedback_db()
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, message, page_url, user_id, user_email, created_at FROM feedback ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": row["id"],
            "message": row["message"],
            "page_url": row["page_url"],
            "user_id": row["user_id"],
            "user_email": row["user_email"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
