from __future__ import annotations

import secrets
from datetime import datetime, timezone
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


def _integration_from_row(row) -> dict[str, Any]:
    keys = row.keys()
    return {
        "id":            row["id"],
        "vendor_id":     row["vendor_id"],
        "provider":      row["provider"] or "",
        "access_token":  row["access_token"] or "",
        "refresh_token": row["refresh_token"] or "",
        "expires_at":    row["expires_at"] or "",
        "calendar_id":   row["calendar_id"] if "calendar_id" in keys else "primary",
        "created_at":    row["created_at"] or "",
        "updated_at":    row["updated_at"] or "",
    }


# ── Schema ─────────────────────────────────────────────────────────────────────

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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_integrations (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_id    INTEGER NOT NULL,
                provider     TEXT NOT NULL DEFAULT 'google',
                access_token  TEXT,
                refresh_token TEXT,
                expires_at   TEXT,
                calendar_id  TEXT NOT NULL DEFAULT 'primary',
                created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (vendor_id, provider)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vendor_feed_tokens (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_id INTEGER NOT NULL UNIQUE,
                token     TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


# ── vendor_calendar CRUD ───────────────────────────────────────────────────────

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
    clean_end   = str(end_time or "").strip()
    clean_type  = str(type or "").strip().lower() or "reminder"

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
                user_id, event_id, title, start_time, end_time, type, notes, created_at
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
            SELECT * FROM vendor_calendar
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


# ── calendar_integrations CRUD ─────────────────────────────────────────────────

def get_calendar_integration(vendor_id: int, provider: str = "google") -> dict[str, Any] | None:
    init_calendar_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM calendar_integrations WHERE vendor_id = ? AND provider = ?",
            (int(vendor_id), provider),
        ).fetchone()
    finally:
        conn.close()
    return _integration_from_row(row) if row else None


def upsert_calendar_integration(
    vendor_id: int,
    provider: str,
    access_token: str,
    refresh_token: str,
    expires_at: str,
    calendar_id: str = "primary",
) -> dict[str, Any]:
    init_calendar_db()
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO calendar_integrations
                (vendor_id, provider, access_token, refresh_token, expires_at, calendar_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(vendor_id, provider) DO UPDATE SET
                access_token  = excluded.access_token,
                refresh_token = CASE WHEN excluded.refresh_token != '' THEN excluded.refresh_token ELSE refresh_token END,
                expires_at    = excluded.expires_at,
                calendar_id   = excluded.calendar_id,
                updated_at    = excluded.updated_at
            """,
            (int(vendor_id), provider, access_token, refresh_token, expires_at, calendar_id, now, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM calendar_integrations WHERE vendor_id = ? AND provider = ?",
            (int(vendor_id), provider),
        ).fetchone()
    finally:
        conn.close()
    return _integration_from_row(row)  # type: ignore[arg-type]


def update_integration_tokens(
    vendor_id: int,
    provider: str,
    *,
    access_token: str,
    expires_at: str,
) -> None:
    """Update only the access token + expiry (called after auto-refresh)."""
    init_calendar_db()
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    try:
        conn.execute(
            """
            UPDATE calendar_integrations
            SET access_token = ?, expires_at = ?, updated_at = ?
            WHERE vendor_id = ? AND provider = ?
            """,
            (access_token, expires_at, now, int(vendor_id), provider),
        )
        conn.commit()
    finally:
        conn.close()


def delete_calendar_integration(vendor_id: int, provider: str = "google") -> bool:
    init_calendar_db()
    conn = _connect()
    try:
        existing = conn.execute(
            "SELECT id FROM calendar_integrations WHERE vendor_id = ? AND provider = ?",
            (int(vendor_id), provider),
        ).fetchone()
        if not existing:
            return False
        conn.execute(
            "DELETE FROM calendar_integrations WHERE vendor_id = ? AND provider = ?",
            (int(vendor_id), provider),
        )
        conn.commit()
    finally:
        conn.close()
    return True


# ── Feed tokens ────────────────────────────────────────────────────────────────

def get_or_create_feed_token(vendor_id: int) -> str:
    """Return (or create) the ICS feed token for this vendor."""
    init_calendar_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT token FROM vendor_feed_tokens WHERE vendor_id = ?",
            (int(vendor_id),),
        ).fetchone()
        if row:
            return str(row["token"])
        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO vendor_feed_tokens (vendor_id, token, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (int(vendor_id), token),
        )
        conn.commit()
        return token
    finally:
        conn.close()


def get_vendor_id_by_feed_token(token: str) -> int | None:
    """Resolve a feed token back to a vendor_id. Returns None if not found."""
    init_calendar_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT vendor_id FROM vendor_feed_tokens WHERE token = ?",
            (token,),
        ).fetchone()
        return int(row["vendor_id"]) if row else None
    finally:
        conn.close()


def rotate_feed_token(vendor_id: int) -> str:
    """Generate a fresh feed token (invalidates the old URL)."""
    init_calendar_db()
    token = secrets.token_urlsafe(32)
    now   = datetime.now(timezone.utc).isoformat()
    conn  = _connect()
    try:
        conn.execute(
            """
            INSERT INTO vendor_feed_tokens (vendor_id, token, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(vendor_id) DO UPDATE SET token = excluded.token, created_at = excluded.created_at
            """,
            (int(vendor_id), token, now),
        )
        conn.commit()
    finally:
        conn.close()
    return token
