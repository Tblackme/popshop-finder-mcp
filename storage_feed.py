"""
Feed storage — video posts, likes, saves for the TikTok-style discovery feed.
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

def init_feed_db() -> None:
    conn = _connect()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS feed_posts (
                id              TEXT PRIMARY KEY,
                vendor_id       TEXT,
                vendor_username TEXT NOT NULL,
                vendor_name     TEXT NOT NULL DEFAULT '',
                vendor_verified INTEGER NOT NULL DEFAULT 0,
                caption         TEXT NOT NULL DEFAULT '',
                video_url       TEXT,
                thumbnail_url   TEXT,
                thumbnail_color TEXT DEFAULT '#0f766e',
                thumbnail_emoji TEXT DEFAULT '🎬',
                product_id      TEXT,
                product_name    TEXT,
                product_price   REAL,
                event_id        TEXT,
                event_name      TEXT,
                location        TEXT,
                tags            TEXT DEFAULT '[]',
                likes_count     INTEGER NOT NULL DEFAULT 0,
                saves_count     INTEGER NOT NULL DEFAULT 0,
                views_count     INTEGER NOT NULL DEFAULT 0,
                is_active       INTEGER NOT NULL DEFAULT 1,
                created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS feed_likes (
                post_id     TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (post_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS feed_saves (
                post_id     TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (post_id, user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_feed_posts_vendor
                ON feed_posts(vendor_username, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_feed_posts_active
                ON feed_posts(is_active, created_at DESC);
        """)
        conn.commit()
        _seed_feed(conn)
    finally:
        conn.close()


_DEMO_POSTS = [
    {
        "vendor_username": "crafty_maya",
        "vendor_name": "Crafty Maya Studio",
        "vendor_verified": True,
        "caption": "New collection just dropped! Hand-stamped copper rings made in my Austin studio 🔨✨ Come find me at the South Congress Night Market this Saturday!",
        "thumbnail_color": "#b45309",
        "thumbnail_emoji": "💍",
        "product_name": "Hand-Stamped Copper Ring",
        "product_price": 38.00,
        "event_name": "South Congress Night Market",
        "location": "Austin, TX",
        "tags": ["jewelry", "handmade", "copper", "rings"],
        "likes_count": 247,
        "saves_count": 89,
        "views_count": 1420,
    },
    {
        "vendor_username": "bloom_collective",
        "vendor_name": "Bloom Collective",
        "vendor_verified": True,
        "caption": "Pressed flower resin earrings — every pair is one-of-a-kind because no two flowers are ever the same 🌸 Limited stock at tomorrow's market!",
        "thumbnail_color": "#be185d",
        "thumbnail_emoji": "🌸",
        "product_name": "Pressed Flower Resin Earrings",
        "product_price": 24.00,
        "event_name": "Mueller Farmers Market",
        "location": "Austin, TX",
        "tags": ["earrings", "floral", "resin", "handmade"],
        "likes_count": 512,
        "saves_count": 203,
        "views_count": 3100,
    },
    {
        "vendor_username": "ember_ceramics",
        "vendor_name": "Ember Ceramics",
        "vendor_verified": True,
        "caption": "Behind the scenes: trimming the new mug collection before its first firing 🏺🔥 These will be at the Spring Artisan Bazaar — booth 14!",
        "thumbnail_color": "#92400e",
        "thumbnail_emoji": "🏺",
        "product_name": "Handthrown Stoneware Mug",
        "product_price": 45.00,
        "event_name": "Spring Artisan Bazaar",
        "location": "Dallas, TX",
        "tags": ["ceramics", "pottery", "mugs", "handmade"],
        "likes_count": 389,
        "saves_count": 156,
        "views_count": 2280,
    },
    {
        "vendor_username": "wax_and_wick",
        "vendor_name": "Wax & Wick Co.",
        "vendor_verified": False,
        "caption": "Slow-pour soy candles scented with Texas wildflowers 🕯️🌼 Making a fresh batch for the Houston Night Market next month. Pre-order link in bio!",
        "thumbnail_color": "#d97706",
        "thumbnail_emoji": "🕯️",
        "product_name": "Texas Wildflower Soy Candle",
        "product_price": 18.00,
        "event_name": "Houston Night Market",
        "location": "Houston, TX",
        "tags": ["candles", "soy", "scented", "texas"],
        "likes_count": 178,
        "saves_count": 67,
        "views_count": 980,
    },
    {
        "vendor_username": "stitch_and_sole",
        "vendor_name": "Stitch & Sole Leather",
        "vendor_verified": True,
        "caption": "Custom leather wallets hand-stitched in San Antonio 👜 Each one takes about 3 hours start to finish. Worth every minute. Booth C7 at the Riverwalk Art Fair!",
        "thumbnail_color": "#78350f",
        "thumbnail_emoji": "👜",
        "product_name": "Hand-Stitched Leather Bifold",
        "product_price": 65.00,
        "event_name": "Riverwalk Art Fair",
        "location": "San Antonio, TX",
        "tags": ["leather", "wallets", "handmade", "custom"],
        "likes_count": 634,
        "saves_count": 291,
        "views_count": 4200,
    },
    {
        "vendor_username": "fermented_flora",
        "vendor_name": "Fermented Flora",
        "vendor_verified": True,
        "caption": "Kimchi that actually tastes like it came from Seoul. Small-batch, traditional recipe passed down from my grandmother 🥬❤️ Find us at the Austin Farmers Market Sunday!",
        "thumbnail_color": "#dc2626",
        "thumbnail_emoji": "🥬",
        "product_name": "Traditional Napa Kimchi (32oz)",
        "product_price": 14.00,
        "event_name": "Austin Farmers Market",
        "location": "Austin, TX",
        "tags": ["food", "kimchi", "fermented", "korean"],
        "likes_count": 823,
        "saves_count": 344,
        "views_count": 5600,
    },
    {
        "vendor_username": "indigo_pressed",
        "vendor_name": "Indigo Pressed",
        "vendor_verified": False,
        "caption": "Risograph print zines about Texas wildlife 🦋 Each one is a limited run of 50. Only a few of the 'Monarch Migration' edition left before I reprint!",
        "thumbnail_color": "#3730a3",
        "thumbnail_emoji": "📚",
        "product_name": "Monarch Migration Riso Zine",
        "product_price": 12.00,
        "event_name": "East Austin Maker Fair",
        "location": "Austin, TX",
        "tags": ["zines", "print", "art", "risograph"],
        "likes_count": 267,
        "saves_count": 98,
        "views_count": 1650,
    },
    {
        "vendor_username": "highland_honey",
        "vendor_name": "Highland Honey Farm",
        "vendor_verified": True,
        "caption": "Raw wildflower honey straight from our Hill Country hives 🍯🐝 No heat treatment, no fillers — just pure Texas honey. We'll have 6 varieties at the Cedar Park Market!",
        "thumbnail_color": "#d97706",
        "thumbnail_emoji": "🍯",
        "product_name": "Raw Wildflower Honey (12oz)",
        "product_price": 16.00,
        "event_name": "Cedar Park Artisan Market",
        "location": "Cedar Park, TX",
        "tags": ["honey", "food", "farm", "texas"],
        "likes_count": 445,
        "saves_count": 187,
        "views_count": 2890,
    },
]


def _seed_feed(conn) -> None:
    row = conn.execute("SELECT COUNT(*) as c FROM feed_posts").fetchone()
    if row and row["c"] > 0:
        return

    import json
    for post in _DEMO_POSTS:
        conn.execute(
            """INSERT INTO feed_posts
               (id, vendor_username, vendor_name, vendor_verified, caption,
                thumbnail_color, thumbnail_emoji, product_name, product_price,
                event_name, location, tags, likes_count, saves_count, views_count, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                _uuid(),
                post["vendor_username"],
                post["vendor_name"],
                int(post["vendor_verified"]),
                post["caption"],
                post.get("thumbnail_color", "#0f766e"),
                post.get("thumbnail_emoji", "🎬"),
                post.get("product_name"),
                post.get("product_price"),
                post.get("event_name"),
                post.get("location"),
                json.dumps(post.get("tags", [])),
                post.get("likes_count", 0),
                post.get("saves_count", 0),
                post.get("views_count", 0),
                _now(),
            )
        )
    conn.commit()


# ── POSTS ────────────────────────────────────────────────────────────────────

def list_feed_posts(limit: int = 20, offset: int = 0, location: str | None = None,
                    tag: str | None = None) -> list[dict[str, Any]]:
    import json
    conn = _connect()
    try:
        if location:
            rows = conn.execute(
                """SELECT * FROM feed_posts WHERE is_active = 1 AND location LIKE ?
                   ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                (f"%{location}%", limit, offset)
            ).fetchall()
        elif tag:
            rows = conn.execute(
                """SELECT * FROM feed_posts WHERE is_active = 1 AND tags LIKE ?
                   ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                (f'%"{tag}"%', limit, offset)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM feed_posts WHERE is_active = 1 ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
        result = _rows(rows)
        for post in result:
            try:
                post["tags"] = json.loads(post.get("tags") or "[]")
            except Exception:
                post["tags"] = []
        return result
    finally:
        conn.close()


def list_vendor_posts(vendor_username: str, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    import json
    conn = _connect()
    try:
        rows = conn.execute(
            """SELECT * FROM feed_posts WHERE is_active = 1 AND vendor_username = ?
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (vendor_username, limit, offset),
        ).fetchall()
        result = _rows(rows)
        for post in result:
            try:
                post["tags"] = json.loads(post.get("tags") or "[]")
            except Exception:
                post["tags"] = []
        return result
    finally:
        conn.close()


def get_feed_post(post_id: str) -> dict[str, Any] | None:
    import json
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM feed_posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            return None
        post = _row(row)
        try:
            post["tags"] = json.loads(post.get("tags") or "[]")
        except Exception:
            post["tags"] = []
        return post
    finally:
        conn.close()


def create_feed_post(vendor_username: str, vendor_name: str, caption: str,
                     vendor_id: str | None = None, vendor_verified: bool = False,
                     video_url: str | None = None, thumbnail_url: str | None = None,
                     thumbnail_color: str = "#0f766e", thumbnail_emoji: str = "🎬",
                     product_name: str | None = None, product_price: float | None = None,
                     event_name: str | None = None, location: str | None = None,
                     tags: list[str] | None = None) -> dict[str, Any]:
    import json
    pid = _uuid()
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO feed_posts
               (id, vendor_id, vendor_username, vendor_name, vendor_verified, caption,
                video_url, thumbnail_url, thumbnail_color, thumbnail_emoji,
                product_name, product_price, event_name, location, tags, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid, vendor_id, vendor_username, vendor_name, int(vendor_verified), caption,
             video_url, thumbnail_url, thumbnail_color, thumbnail_emoji,
             product_name, product_price, event_name, location,
             json.dumps(tags or []), _now())
        )
        conn.commit()
        return get_feed_post(pid)
    finally:
        conn.close()


def like_post(post_id: str, user_id: str) -> dict[str, Any]:
    conn = _connect()
    try:
        existing = conn.execute(
            "SELECT 1 FROM feed_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id)
        ).fetchone()
        if existing:
            conn.execute("DELETE FROM feed_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
            conn.execute("UPDATE feed_posts SET likes_count = MAX(0, likes_count - 1) WHERE id = ?", (post_id,))
            liked = False
        else:
            conn.execute(
                "INSERT INTO feed_likes (post_id, user_id, created_at) VALUES (?,?,?)",
                (post_id, user_id, _now())
            )
            conn.execute("UPDATE feed_posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
            liked = True
        conn.commit()
        row = conn.execute("SELECT likes_count FROM feed_posts WHERE id = ?", (post_id,)).fetchone()
        return {"liked": liked, "likes_count": row["likes_count"] if row else 0}
    finally:
        conn.close()


def save_post(post_id: str, user_id: str) -> dict[str, Any]:
    conn = _connect()
    try:
        existing = conn.execute(
            "SELECT 1 FROM feed_saves WHERE post_id = ? AND user_id = ?", (post_id, user_id)
        ).fetchone()
        if existing:
            conn.execute("DELETE FROM feed_saves WHERE post_id = ? AND user_id = ?", (post_id, user_id))
            conn.execute("UPDATE feed_posts SET saves_count = MAX(0, saves_count - 1) WHERE id = ?", (post_id,))
            saved = False
        else:
            conn.execute(
                "INSERT INTO feed_saves (post_id, user_id, created_at) VALUES (?,?,?)",
                (post_id, user_id, _now())
            )
            conn.execute("UPDATE feed_posts SET saves_count = saves_count + 1 WHERE id = ?", (post_id,))
            saved = True
        conn.commit()
        row = conn.execute("SELECT saves_count FROM feed_posts WHERE id = ?", (post_id,)).fetchone()
        return {"saved": saved, "saves_count": row["saves_count"] if row else 0}
    finally:
        conn.close()


def record_view(post_id: str) -> None:
    conn = _connect()
    try:
        conn.execute("UPDATE feed_posts SET views_count = views_count + 1 WHERE id = ?", (post_id,))
        conn.commit()
    finally:
        conn.close()


def get_user_liked_posts(user_id: str) -> list[str]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT post_id FROM feed_likes WHERE user_id = ?", (user_id,)).fetchall()
        return [r["post_id"] for r in rows]
    finally:
        conn.close()


def get_user_saved_posts(user_id: str) -> list[str]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT post_id FROM feed_saves WHERE user_id = ?", (user_id,)).fetchall()
        return [r["post_id"] for r in rows]
    finally:
        conn.close()
