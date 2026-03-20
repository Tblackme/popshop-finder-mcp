"""
Community storage — groups, channels, messages, members, pins.
Supports the Discord-inspired community system for Vendor Atlas.
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


# ── SCHEMA ──────────────────────────────────────────────────────────────────

def init_community_db() -> None:
    conn = _connect()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS community_groups (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                type        TEXT NOT NULL CHECK (type IN ('event_room', 'vendor_circle', 'shopper_community')),
                description TEXT,
                icon        TEXT DEFAULT '🏘️',
                event_id    TEXT,
                created_by  TEXT,
                is_verified INTEGER NOT NULL DEFAULT 0,
                member_count INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS community_channels (
                id          TEXT PRIMARY KEY,
                group_id    TEXT NOT NULL,
                name        TEXT NOT NULL,
                description TEXT,
                is_default  INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES community_groups(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS community_messages (
                id          TEXT PRIMARY KEY,
                channel_id  TEXT NOT NULL,
                user_id     TEXT,
                username    TEXT NOT NULL DEFAULT 'Anonymous',
                display_name TEXT,
                content     TEXT NOT NULL,
                reply_to_id TEXT,
                media_url   TEXT,
                is_pinned   INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (channel_id) REFERENCES community_channels(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS community_members (
                id          TEXT PRIMARY KEY,
                group_id    TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'moderator', 'member')),
                joined_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(group_id, user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_community_messages_channel
                ON community_messages(channel_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_community_channels_group
                ON community_channels(group_id);
        """)
        conn.commit()
        _seed_community(conn)
    finally:
        conn.close()


def _seed_community(conn) -> None:
    """Seed demo groups, channels, and messages if empty."""
    row = conn.execute("SELECT COUNT(*) as c FROM community_groups").fetchone()
    if row and row["c"] > 0:
        return

    groups = [
        (_uuid(), "Austin Night Market Crew", "event_room", "Live chat for vendors & shoppers at the Austin Night Market this weekend.", "🌙", "evt-001", True, 42),
        (_uuid(), "Handmade Jewelry Makers", "vendor_circle", "A circle for indie jewelry vendors — tips, trends, and event sharing.", "💍", None, True, 128),
        (_uuid(), "Vintage & Thrift Collective", "vendor_circle", "Vintage vendors connecting over markets, sourcing, and storytelling.", "🧥", None, False, 67),
        (_uuid(), "Ceramics & Pottery Guild", "vendor_circle", "Ceramics vendors sharing techniques, events, and studio life.", "🏺", None, False, 53),
        (_uuid(), "ATX Popup Shoppers", "shopper_community", "Austin shoppers following the best local vendors and popup events.", "🛍️", None, False, 312),
        (_uuid(), "Dallas Makers Scene", "shopper_community", "DFW shoppers discovering handmade goods and local markets.", "⭐", None, False, 189),
        (_uuid(), "Spring Artisan Bazaar", "event_room", "Official room for vendors accepted to the Spring Artisan Bazaar.", "🌸", "evt-002", True, 28),
    ]

    for g in groups:
        gid, name, gtype, desc, icon, event_id, verified, members = g
        conn.execute(
            """INSERT INTO community_groups (id, name, type, description, icon, event_id, created_by, is_verified, member_count, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (gid, name, gtype, desc, icon, event_id, "system", int(verified), members, _now())
        )

        # Default channels per group
        channels = [
            (_uuid(), gid, "general", "General discussion", 1),
            (_uuid(), gid, "announcements", "Official updates", 0),
            (_uuid(), gid, "events", "Event talk and planning", 0),
        ]
        if gtype == "vendor_circle":
            channels.append((_uuid(), gid, "tips-and-tricks", "Vendor best practices", 0))
            channels.append((_uuid(), gid, "show-your-booth", "Share booth setups and photos", 0))
        elif gtype == "event_room":
            channels.append((_uuid(), gid, "vendor-chat", "Vendor-only discussion", 0))
            channels.append((_uuid(), gid, "live-updates", "Real-time event updates", 0))
        elif gtype == "shopper_community":
            channels.append((_uuid(), gid, "finds", "Cool things spotted at markets", 0))
            channels.append((_uuid(), gid, "recommendations", "Vendor shoutouts", 0))

        for ch in channels:
            conn.execute(
                "INSERT INTO community_channels (id, group_id, name, description, is_default, created_at) VALUES (?,?,?,?,?,?)",
                (ch[0], ch[1], ch[2], ch[3], ch[4], _now())
            )

            # Seed a few messages in general channel
            if ch[2] == "general":
                seed_msgs = [
                    ("seed_u1", "crafty_maya", "Maya Chen", f"Welcome to {name}! 👋 This is the place to connect."),
                    ("seed_u2", "vendor_jose", "Jose Reyes", "So glad this community exists. Already found two new events to apply to!"),
                    ("seed_u3", "market_sarah", "Sarah Kim", "Has anyone done the Barton Creek Farmers Market? Looking for reviews."),
                    ("seed_u1", "crafty_maya", "Maya Chen", "Yes! Great foot traffic on weekends. Booth fees are reasonable too."),
                ]
                for i, (uid, uname, dname, content) in enumerate(seed_msgs):
                    conn.execute(
                        """INSERT INTO community_messages (id, channel_id, user_id, username, display_name, content, created_at)
                           VALUES (?,?,?,?,?,?,?)""",
                        (_uuid(), ch[0], uid, uname, dname, content, _now())
                    )

    conn.commit()


# ── GROUPS ───────────────────────────────────────────────────────────────────

def list_groups(group_type: str | None = None) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        if group_type:
            rows = conn.execute(
                "SELECT * FROM community_groups WHERE type = ? ORDER BY member_count DESC, created_at DESC",
                (group_type,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM community_groups ORDER BY member_count DESC, created_at DESC"
            ).fetchall()
        return _rows(rows)
    finally:
        conn.close()


def get_group(group_id: str) -> dict[str, Any] | None:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM community_groups WHERE id = ?", (group_id,)).fetchone()
        return _row(row)
    finally:
        conn.close()


def create_group(name: str, group_type: str, description: str = "", icon: str = "🏘️",
                 event_id: str | None = None, created_by: str | None = None) -> dict[str, Any]:
    gid = _uuid()
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO community_groups (id, name, type, description, icon, event_id, created_by, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (gid, name, group_type, description, icon, event_id, created_by, _now())
        )
        # Create default channels
        for ch_name, is_default in [("general", 1), ("announcements", 0)]:
            conn.execute(
                "INSERT INTO community_channels (id, group_id, name, is_default, created_at) VALUES (?,?,?,?,?)",
                (_uuid(), gid, ch_name, is_default, _now())
            )
        conn.commit()
        row = conn.execute("SELECT * FROM community_groups WHERE id = ?", (gid,)).fetchone()
        return _row(row)
    finally:
        conn.close()


# ── CHANNELS ─────────────────────────────────────────────────────────────────

def list_channels(group_id: str) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM community_channels WHERE group_id = ? ORDER BY is_default DESC, name ASC",
            (group_id,)
        ).fetchall()
        return _rows(rows)
    finally:
        conn.close()


def get_channel(channel_id: str) -> dict[str, Any] | None:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM community_channels WHERE id = ?", (channel_id,)).fetchone()
        return _row(row)
    finally:
        conn.close()


def create_channel(group_id: str, name: str, description: str = "") -> dict[str, Any]:
    cid = _uuid()
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO community_channels (id, group_id, name, description, created_at) VALUES (?,?,?,?,?)",
            (cid, group_id, name, description, _now())
        )
        conn.commit()
        row = conn.execute("SELECT * FROM community_channels WHERE id = ?", (cid,)).fetchone()
        return _row(row)
    finally:
        conn.close()


# ── MESSAGES ─────────────────────────────────────────────────────────────────

def list_messages(channel_id: str, limit: int = 50, before: str | None = None) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        if before:
            rows = conn.execute(
                """SELECT * FROM community_messages
                   WHERE channel_id = ? AND created_at < ?
                   ORDER BY created_at DESC LIMIT ?""",
                (channel_id, before, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM community_messages
                   WHERE channel_id = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (channel_id, limit)
            ).fetchall()
        return list(reversed(_rows(rows)))
    finally:
        conn.close()


def list_messages_since(channel_id: str, since: str) -> list[dict[str, Any]]:
    """Poll for new messages after a timestamp (for real-time updates)."""
    conn = _connect()
    try:
        rows = conn.execute(
            """SELECT * FROM community_messages
               WHERE channel_id = ? AND created_at > ?
               ORDER BY created_at ASC LIMIT 100""",
            (channel_id, since)
        ).fetchall()
        return _rows(rows)
    finally:
        conn.close()


def send_message(channel_id: str, content: str, user_id: str | None = None,
                 username: str = "Anonymous", display_name: str | None = None,
                 reply_to_id: str | None = None, media_url: str | None = None) -> dict[str, Any]:
    mid = _uuid()
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO community_messages
               (id, channel_id, user_id, username, display_name, content, reply_to_id, media_url, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (mid, channel_id, user_id, username, display_name or username, content, reply_to_id, media_url, _now())
        )
        conn.commit()
        row = conn.execute("SELECT * FROM community_messages WHERE id = ?", (mid,)).fetchone()
        return _row(row)
    finally:
        conn.close()


def pin_message(message_id: str) -> bool:
    conn = _connect()
    try:
        conn.execute("UPDATE community_messages SET is_pinned = 1 WHERE id = ?", (message_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def unpin_message(message_id: str) -> bool:
    conn = _connect()
    try:
        conn.execute("UPDATE community_messages SET is_pinned = 0 WHERE id = ?", (message_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def list_pinned_messages(channel_id: str) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM community_messages WHERE channel_id = ? AND is_pinned = 1 ORDER BY created_at DESC",
            (channel_id,)
        ).fetchall()
        return _rows(rows)
    finally:
        conn.close()


# ── MEMBERSHIP ────────────────────────────────────────────────────────────────

def join_group(group_id: str, user_id: str) -> bool:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO community_members (id, group_id, user_id, joined_at) VALUES (?,?,?,?)",
            (_uuid(), group_id, user_id, _now())
        )
        conn.execute(
            "UPDATE community_groups SET member_count = member_count + 1 WHERE id = ? AND NOT EXISTS (SELECT 1 FROM community_members WHERE group_id=? AND user_id=?)",
            (group_id, group_id, user_id)
        )
        conn.commit()
        return True
    finally:
        conn.close()


def leave_group(group_id: str, user_id: str) -> bool:
    conn = _connect()
    try:
        conn.execute("DELETE FROM community_members WHERE group_id = ? AND user_id = ?", (group_id, user_id))
        conn.execute("UPDATE community_groups SET member_count = MAX(0, member_count - 1) WHERE id = ?", (group_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def is_member(group_id: str, user_id: str) -> bool:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT 1 FROM community_members WHERE group_id = ? AND user_id = ?", (group_id, user_id)
        ).fetchone()
        return bool(row)
    finally:
        conn.close()


def list_user_groups(user_id: str) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            """SELECT g.* FROM community_groups g
               JOIN community_members m ON m.group_id = g.id
               WHERE m.user_id = ?
               ORDER BY g.member_count DESC""",
            (user_id,)
        ).fetchall()
        return _rows(rows)
    finally:
        conn.close()
