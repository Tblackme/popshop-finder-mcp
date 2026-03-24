"""
Direct-message & group-conversation storage for Vendor Atlas.

Tables
------
conversations           — a thread (direct, group, event, application)
conversation_participants — who belongs to each conversation
messages                — individual messages within a conversation
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from db_runtime import connect


def _connect():
    conn = connect()
    if getattr(conn, "kind", "") == "sqlite":
        conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row(row) -> dict[str, Any] | None:
    if not row:
        return None
    return {k: row[k] for k in row.keys()}


def _rows(rows) -> list[dict[str, Any]]:
    return [{k: r[k] for k in r.keys()} for r in rows]


# ── SCHEMA ───────────────────────────────────────────────────────────────────

def init_messages_db() -> None:
    conn = _connect()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          TEXT PRIMARY KEY,
                type        TEXT NOT NULL DEFAULT 'direct',
                title       TEXT,
                event_id    TEXT,
                created_by  INTEGER,
                created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_participants (
                conversation_id TEXT NOT NULL,
                user_id         INTEGER NOT NULL,
                joined_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_read_at    TEXT,
                PRIMARY KEY (conversation_id, user_id),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id              TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                sender_id       INTEGER NOT NULL,
                body            TEXT NOT NULL,
                reply_to_id     TEXT,
                read_by         TEXT NOT NULL DEFAULT '[]',
                created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cp_user ON conversation_participants(user_id)"
        )
        conn.commit()
    finally:
        conn.close()


# ── CONVERSATIONS ─────────────────────────────────────────────────────────────

def create_conversation(
    creator_id: int,
    participant_ids: list[int],
    conv_type: str = "direct",
    title: str | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Create a new conversation and add all participants (including creator)."""
    conn = _connect()
    try:
        # For direct (1-to-1) conversations, deduplicate and check existing.
        all_ids = sorted(set([creator_id] + participant_ids))
        if conv_type == "direct" and len(all_ids) == 2:
            existing = _find_direct_conversation(conn, all_ids[0], all_ids[1])
            if existing:
                return existing

        conv_id = _uuid()
        now = _now()
        conn.execute(
            "INSERT INTO conversations (id, type, title, event_id, created_by, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (conv_id, conv_type, title, event_id, creator_id, now, now),
        )
        for uid in all_ids:
            conn.execute(
                "INSERT OR IGNORE INTO conversation_participants (conversation_id, user_id, joined_at) "
                "VALUES (?, ?, ?)",
                (conv_id, uid, now),
            )
        conn.commit()
        return get_conversation(conv_id, viewer_id=creator_id)  # type: ignore[return-value]
    finally:
        conn.close()


def _find_direct_conversation(conn, user_a: int, user_b: int) -> dict[str, Any] | None:
    """Return existing direct conversation between exactly two users, or None."""
    row = conn.execute(
        """
        SELECT c.id FROM conversations c
        JOIN conversation_participants pa ON pa.conversation_id = c.id AND pa.user_id = ?
        JOIN conversation_participants pb ON pb.conversation_id = c.id AND pb.user_id = ?
        WHERE c.type = 'direct'
        AND (SELECT COUNT(*) FROM conversation_participants cp2 WHERE cp2.conversation_id = c.id) = 2
        LIMIT 1
        """,
        (user_a, user_b),
    ).fetchone()
    if not row:
        return None
    # We need to return without closing the outer connection
    conv_id = row["id"]
    r = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    return _row(r)


def get_conversation(conv_id: str, viewer_id: int | None = None) -> dict[str, Any] | None:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        if not row:
            return None
        result = _row(row)
        # Attach participants
        prows = conn.execute(
            "SELECT cp.user_id, u.username, u.name, cp.last_read_at "
            "FROM conversation_participants cp "
            "LEFT JOIN users u ON u.id = cp.user_id "
            "WHERE cp.conversation_id = ?",
            (conv_id,),
        ).fetchall()
        result["participants"] = _rows(prows)
        # Attach last message preview
        last = conn.execute(
            "SELECT id, sender_id, body, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1",
            (conv_id,),
        ).fetchone()
        result["last_message"] = _row(last)
        # Unread count for viewer
        if viewer_id is not None:
            lr = conn.execute(
                "SELECT last_read_at FROM conversation_participants "
                "WHERE conversation_id = ? AND user_id = ?",
                (conv_id, viewer_id),
            ).fetchone()
            last_read = lr["last_read_at"] if lr and lr["last_read_at"] else "1970-01-01"
            unread = conn.execute(
                "SELECT COUNT(*) as cnt FROM messages "
                "WHERE conversation_id = ? AND created_at > ? AND sender_id != ?",
                (conv_id, last_read, viewer_id),
            ).fetchone()
            result["unread_count"] = unread["cnt"] if unread else 0
        return result
    finally:
        conn.close()


def list_conversations_for_user(user_id: int) -> list[dict[str, Any]]:
    """Return all conversations the user participates in, newest first."""
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT c.* FROM conversations c
            JOIN conversation_participants cp ON cp.conversation_id = c.id
            WHERE cp.user_id = ?
            ORDER BY c.updated_at DESC
            """,
            (user_id,),
        ).fetchall()
        results = []
        for row in rows:
            conv_id = row["id"]
            result = {k: row[k] for k in row.keys()}
            # Participants
            prows = conn.execute(
                "SELECT cp.user_id, u.username, u.name, cp.last_read_at "
                "FROM conversation_participants cp "
                "LEFT JOIN users u ON u.id = cp.user_id "
                "WHERE cp.conversation_id = ?",
                (conv_id,),
            ).fetchall()
            result["participants"] = _rows(prows)
            # Last message
            last = conn.execute(
                "SELECT id, sender_id, body, created_at FROM messages "
                "WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1",
                (conv_id,),
            ).fetchone()
            result["last_message"] = _row(last)
            # Unread
            lr = conn.execute(
                "SELECT last_read_at FROM conversation_participants "
                "WHERE conversation_id = ? AND user_id = ?",
                (conv_id, user_id),
            ).fetchone()
            last_read = lr["last_read_at"] if lr and lr["last_read_at"] else "1970-01-01"
            unread = conn.execute(
                "SELECT COUNT(*) as cnt FROM messages "
                "WHERE conversation_id = ? AND created_at > ? AND sender_id != ?",
                (conv_id, last_read, user_id),
            ).fetchone()
            result["unread_count"] = unread["cnt"] if unread else 0
            results.append(result)
        return results
    finally:
        conn.close()


def is_participant(conv_id: str, user_id: int) -> bool:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT 1 FROM conversation_participants WHERE conversation_id = ? AND user_id = ?",
            (conv_id, user_id),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def mark_conversation_read(conv_id: str, user_id: int) -> None:
    conn = _connect()
    try:
        conn.execute(
            "UPDATE conversation_participants SET last_read_at = ? "
            "WHERE conversation_id = ? AND user_id = ?",
            (_now(), conv_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_total_unread(user_id: int) -> int:
    """Total unread message count across all of a user's conversations."""
    conn = _connect()
    try:
        convs = conn.execute(
            "SELECT conversation_id, last_read_at FROM conversation_participants WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        total = 0
        for cp in convs:
            last_read = cp["last_read_at"] or "1970-01-01"
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM messages "
                "WHERE conversation_id = ? AND created_at > ? AND sender_id != ?",
                (cp["conversation_id"], last_read, user_id),
            ).fetchone()
            total += row["cnt"] if row else 0
        return total
    finally:
        conn.close()


# ── MESSAGES ──────────────────────────────────────────────────────────────────

def send_direct_message(
    conv_id: str,
    sender_id: int,
    body: str,
    reply_to_id: str | None = None,
) -> dict[str, Any] | None:
    """Send a message in a conversation; bumps conversation updated_at."""
    if not body.strip():
        return None
    msg_id = _uuid()
    now = _now()
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO messages (id, conversation_id, sender_id, body, reply_to_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, conv_id, sender_id, body.strip(), reply_to_id, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conv_id),
        )
        # Mark sender as having read up to this moment
        conn.execute(
            "UPDATE conversation_participants SET last_read_at = ? "
            "WHERE conversation_id = ? AND user_id = ?",
            (now, conv_id, sender_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT m.*, u.username, u.name FROM messages m "
            "LEFT JOIN users u ON u.id = m.sender_id "
            "WHERE m.id = ?",
            (msg_id,),
        ).fetchone()
        return _row(row)
    finally:
        conn.close()


def list_messages_in_conversation(
    conv_id: str,
    before: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Fetch messages newest-first with cursor pagination."""
    conn = _connect()
    try:
        if before:
            rows = conn.execute(
                "SELECT m.*, u.username, u.name FROM messages m "
                "LEFT JOIN users u ON u.id = m.sender_id "
                "WHERE m.conversation_id = ? AND m.created_at < ? "
                "ORDER BY m.created_at DESC LIMIT ?",
                (conv_id, before, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT m.*, u.username, u.name FROM messages m "
                "LEFT JOIN users u ON u.id = m.sender_id "
                "WHERE m.conversation_id = ? "
                "ORDER BY m.created_at DESC LIMIT ?",
                (conv_id, limit),
            ).fetchall()
        return _rows(rows)
    finally:
        conn.close()


def list_new_messages_since(conv_id: str, since: str) -> list[dict[str, Any]]:
    """Poll: return messages newer than `since` ISO timestamp, oldest-first."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT m.*, u.username, u.name FROM messages m "
            "LEFT JOIN users u ON u.id = m.sender_id "
            "WHERE m.conversation_id = ? AND m.created_at > ? "
            "ORDER BY m.created_at ASC",
            (conv_id, since),
        ).fetchall()
        return _rows(rows)
    finally:
        conn.close()
