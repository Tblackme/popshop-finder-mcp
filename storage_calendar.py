from __future__ import annotations

from typing import Any

from db_runtime import connect


def _connect():
    return connect()


def _calendar_from_row(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "event_id": row["event_id"],
        "title": row["title"] or "",
        "start_time": row["start_time"] or "",
        "end_time": row["end_time"] or "",
        "type": row["type"] or "reminder",
        "notes": row["notes"] or "",
        "created_at": row["created_at"] or "",
    }


def init_calendar_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vendor_calendar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_id TEXT,
                title TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                type TEXT NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_calendar_event(
    user_id: int,
    title: str,
    start_time: str,
    end_time: str,
    type: str,
    notes: str = "",
    event_id: str | None = None,
) -> dict[str, Any]:
    init_calendar_db()
    clean_title = str(title or "").strip()
    clean_start = str(start_time or "").strip()
    clean_end = str(end_time or "").strip()
    clean_type = str(type or "").strip().lower() or "reminder"

    if not clean_title:
        raise ValueError("Title is required.")
    if not clean_start:
        raise ValueError("Start time is required.")
    if not clean_end:
        raise ValueError("End time is required.")
    if clean_type not in {"event", "production", "reminder"}:
        raise ValueError("Type must be event, production, or reminder.")

    conn = _connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO vendor_calendar (
                user_id,
                event_id,
                title,
                start_time,
                end_time,
                type,
                notes,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                int(user_id),
                str(event_id).strip() if event_id else None,
                clean_title,
                clean_start,
                clean_end,
                clean_type,
                str(notes or "").strip(),
            ),
        )
        calendar_id = cursor.lastrowid
        conn.commit()
        row = conn.execute("SELECT * FROM vendor_calendar WHERE id = ?", (calendar_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        raise ValueError("Calendar event could not be created.")
    return _calendar_from_row(row)


def get_vendor_calendar(user_id: int) -> list[dict[str, Any]]:
    init_calendar_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM vendor_calendar
            WHERE user_id = ?
            ORDER BY start_time ASC, created_at ASC
            """,
            (int(user_id),),
        ).fetchall()
    finally:
        conn.close()

    return [_calendar_from_row(row) for row in rows]


def delete_calendar_event(id: int) -> bool:
    init_calendar_db()
    conn = _connect()
    try:
        existing = conn.execute("SELECT id FROM vendor_calendar WHERE id = ?", (int(id),)).fetchone()
        deleted = existing is not None
        if deleted:
            conn.execute("DELETE FROM vendor_calendar WHERE id = ?", (int(id),))
        conn.commit()
    finally:
        conn.close()

    return deleted
