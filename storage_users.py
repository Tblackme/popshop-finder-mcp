from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from db_runtime import connect, using_postgres

PBKDF2_ITERATIONS = 120_000


@dataclass
class UserRecord:
    id: int
    name: str
    email: str
    username: str
    password_hash: str
    role: str = "vendor"
    interests: str = ""
    bio: str = ""
    created_at: str = ""


@dataclass
class AvailabilityRecord:
    user_id: int
    weekdays: str = ""
    preferred_months: str = ""
    weekly_capacity: int = 2
    monthly_goal: int = 6
    notes: str = ""
    updated_at: str = ""


def _connect():
    return connect()


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}:{derived.hex()}"


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        salt_hex, expected_hex = password_hash.split(":", 1)
    except ValueError:
        return False

    actual = _hash_password(password, bytes.fromhex(salt_hex)).split(":", 1)[1]
    return secrets.compare_digest(actual, expected_hex)


def _user_from_row(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "username": row["username"],
        "role": row["role"] if "role" in row.keys() else "vendor",
        "interests": row["interests"] or "",
        "bio": row["bio"] or "",
        "created_at": row["created_at"] or "",
    }


def init_users_db() -> None:
    conn = _connect()
    try:
        if using_postgres():
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'vendor',
                    interests TEXT,
                    bio TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        else:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'vendor',
                    interests TEXT,
                    bio TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        columns = conn.table_columns("users")
        if "role" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'vendor'")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_markets (
                user_id INTEGER NOT NULL,
                event_id TEXT NOT NULL,
                saved_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, event_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shopper_rsvps (
                user_id INTEGER NOT NULL,
                event_id TEXT NOT NULL,
                rsvped_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, event_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_availability (
                user_id INTEGER PRIMARY KEY,
                weekdays TEXT,
                preferred_months TEXT,
                weekly_capacity INTEGER DEFAULT 2,
                monthly_goal INTEGER DEFAULT 6,
                notes TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_vendor_trackers (
                user_id INTEGER PRIMARY KEY,
                tracker_json TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vendor_followers (
                shopper_user_id INTEGER NOT NULL,
                vendor_user_id INTEGER NOT NULL,
                followed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (shopper_user_id, vendor_user_id),
                FOREIGN KEY (shopper_user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (vendor_user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vendor_event_visibility (
                vendor_user_id INTEGER NOT NULL,
                event_id TEXT NOT NULL,
                visible_to_followers INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (vendor_user_id, event_id),
                FOREIGN KEY (vendor_user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_notifications (
                id BIGSERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                related_user_id INTEGER,
                related_event_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                read_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vendor_profiles (
                user_id INTEGER PRIMARY KEY,
                business_name TEXT,
                category TEXT,
                subcategory TEXT,
                location TEXT,
                price_range TEXT,
                main_goal TEXT,
                preferred_env TEXT,
                experience_level TEXT,
                risk_tolerance TEXT,
                max_booth_price REAL,
                instagram_url TEXT,
                tiktok_url TEXT,
                website_url TEXT,
                banner_color TEXT DEFAULT '#0f766e',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vendor_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                price REAL,
                image_url TEXT,
                product_url TEXT,
                category TEXT,
                in_stock INTEGER NOT NULL DEFAULT 1,
                display_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        # ── vendor_verification_requests ─────────────────────────────────
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vendor_verification_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_user_id INTEGER NOT NULL,
                business_name TEXT,
                category TEXT,
                description TEXT,
                social_links TEXT,
                product_images TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                admin_notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT,
                FOREIGN KEY (vendor_user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        # Migrations: add columns added after initial schema
        for col, definition in [
            ("source", "TEXT DEFAULT 'manual'"),
            ("inventory_quantity", "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE vendor_products ADD COLUMN {col} {definition}")
            except Exception:
                pass  # column already exists
        # Migrations: vendor_profiles new columns
        for col, definition in [
            ("verification_status", "TEXT NOT NULL DEFAULT 'basic'"),
            ("sell_where", "TEXT"),
            ("etsy_url", "TEXT"),
        ]:
            try:
                conn.execute(f"ALTER TABLE vendor_profiles ADD COLUMN {col} {definition}")
            except Exception:
                pass  # column already exists
        conn.commit()
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    init_users_db()
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT id, name, email, username, role, interests, bio, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    return _user_from_row(row) if row else None


def get_user_by_email(email: str) -> dict[str, Any] | None:
    init_users_db()
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT id, name, email, username, role, interests, bio, created_at
            FROM users
            WHERE LOWER(email) = LOWER(?)
            """,
            (email.strip(),),
        ).fetchone()
    finally:
        conn.close()
    return _user_from_row(row) if row else None


def get_user_by_username(username: str) -> dict[str, Any] | None:
    init_users_db()
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT id, name, email, username, role, interests, bio, created_at
            FROM users
            WHERE LOWER(username) = LOWER(?)
            """,
            (username.strip(),),
        ).fetchone()
    finally:
        conn.close()
    return _user_from_row(row) if row else None


def list_public_users(role: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    init_users_db()
    normalized_role = (role or "").strip().lower()
    safe_limit = max(1, min(int(limit or 50), 200))
    conn = _connect()
    try:
        if normalized_role:
            rows = conn.execute(
                """
                SELECT id, name, email, username, role, interests, bio, created_at
                FROM users
                WHERE role = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (normalized_role, safe_limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, name, email, username, role, interests, bio, created_at
                FROM users
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
    finally:
        conn.close()

    return [
        {
            "id": row["id"],
            "name": row["name"],
            "username": row["username"],
            "role": row["role"] if "role" in row.keys() else "vendor",
            "interests": row["interests"] or "",
            "bio": row["bio"] or "",
            "created_at": row["created_at"] or "",
        }
        for row in rows
    ]


def is_username_available(username: str) -> bool:
    normalized = username.strip().lower()
    if not normalized:
        return False
    return get_user_by_username(normalized) is None


def create_user(
    name: str,
    email: str,
    username: str,
    password: str,
    role: str = "vendor",
    interests: str = "",
    bio: str = "",
) -> dict[str, Any]:
    init_users_db()
    normalized_email = email.strip().lower()
    normalized_username = username.strip().lower()

    conn = _connect()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?)",
            (normalized_email, normalized_username),
        ).fetchone()
        if existing:
            raise ValueError("An account with that email or username already exists.")

        conn.execute(
            """
            INSERT INTO users (name, email, username, password_hash, role, interests, bio)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name.strip(),
                normalized_email,
                normalized_username,
                _hash_password(password),
                role.strip().lower() or "vendor",
                interests.strip(),
                bio.strip(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    user = get_user_by_email(normalized_email)
    if not user:
        raise ValueError("Account created but could not be loaded.")
    return user


def authenticate_user(identifier: str, password: str) -> dict[str, Any] | None:
    init_users_db()
    normalized_identifier = identifier.strip().lower()
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT *
            FROM users
            WHERE LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?)
            """,
            (normalized_identifier, normalized_identifier),
        ).fetchone()
    finally:
        conn.close()

    if not row or not _verify_password(password, row["password_hash"]):
        return None
    return _user_from_row(row)


def update_user_profile(user_id: int, name: str, interests: str = "", bio: str = "") -> dict[str, Any]:
    init_users_db()
    conn = _connect()
    try:
        conn.execute(
            """
            UPDATE users
            SET name = ?, interests = ?, bio = ?
            WHERE id = ?
            """,
            (name.strip(), interests.strip(), bio.strip(), user_id),
        )
        conn.commit()
    finally:
        conn.close()

    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found.")
    return user


def save_market_for_user(user_id: int, event_id: str) -> None:
    init_users_db()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO saved_markets (user_id, event_id)
            VALUES (?, ?)
            ON CONFLICT(user_id, event_id) DO NOTHING
            """,
            (user_id, event_id),
        )
        conn.commit()
    finally:
        conn.close()


def remove_saved_market_for_user(user_id: int, event_id: str) -> None:
    init_users_db()
    conn = _connect()
    try:
        conn.execute(
            "DELETE FROM saved_markets WHERE user_id = ? AND event_id = ?",
            (user_id, event_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_saved_markets_for_user(user_id: int) -> list[dict[str, Any]]:
    init_users_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT
                e.*,
                sm.saved_at
            FROM saved_markets sm
            JOIN events e ON e.id = sm.event_id
            WHERE sm.user_id = ?
            ORDER BY sm.saved_at DESC, e.date ASC, e.name ASC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "id": row["id"],
            "name": row["name"],
            "city": row["city"],
            "state": row["state"],
            "date": row["date"],
            "vendor_count": row["vendor_count"],
            "estimated_traffic": row["estimated_traffic"],
            "booth_price": row["booth_price"],
            "application_link": row["application_link"],
            "organizer_contact": row["organizer_contact"],
            "popularity_score": row["popularity_score"],
            "source_url": row["source_url"],
            "vendor_category": row["vendor_category"],
            "event_size": row["event_size"],
            "saved_at": row["saved_at"],
        }
        for row in rows
    ]


def rsvp_event_for_user(user_id: int, event_id: str) -> None:
    init_users_db()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO shopper_rsvps (user_id, event_id)
            VALUES (?, ?)
            ON CONFLICT(user_id, event_id) DO NOTHING
            """,
            (user_id, event_id),
        )
        conn.commit()
    finally:
        conn.close()


def remove_rsvp_for_user(user_id: int, event_id: str) -> None:
    init_users_db()
    conn = _connect()
    try:
        conn.execute(
            "DELETE FROM shopper_rsvps WHERE user_id = ? AND event_id = ?",
            (user_id, event_id),
        )
        conn.commit()
    finally:
        conn.close()


def is_event_rsvped_by_user(user_id: int, event_id: str) -> bool:
    init_users_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT 1 FROM shopper_rsvps WHERE user_id = ? AND event_id = ?",
            (user_id, event_id),
        ).fetchone()
    finally:
        conn.close()
    return row is not None


def get_rsvped_events_for_user(user_id: int) -> list[dict[str, Any]]:
    init_users_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT
                e.*,
                sr.rsvped_at
            FROM shopper_rsvps sr
            JOIN events e ON e.id = sr.event_id
            WHERE sr.user_id = ?
            ORDER BY sr.rsvped_at DESC, e.date ASC, e.name ASC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "id": row["id"],
            "name": row["name"],
            "city": row["city"],
            "state": row["state"],
            "date": row["date"],
            "vendor_count": row["vendor_count"],
            "estimated_traffic": row["estimated_traffic"],
            "booth_price": row["booth_price"],
            "application_link": row["application_link"],
            "organizer_contact": row["organizer_contact"],
            "popularity_score": row["popularity_score"],
            "source_url": row["source_url"],
            "vendor_category": row["vendor_category"],
            "event_size": row["event_size"],
            "rsvped_at": row["rsvped_at"],
        }
        for row in rows
    ]


def get_rsvp_count(event_id: str) -> int:
    """Return total RSVP count for an event."""
    init_users_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM shopper_rsvps WHERE event_id = ?",
            (event_id,),
        ).fetchone()
        return int(row["c"]) if row else 0
    finally:
        conn.close()


def get_event_attendees(event_id: str, limit: int = 12) -> list[dict[str, Any]]:
    """Return a preview list of attendees for an event."""
    init_users_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT u.id, u.username, u.name
            FROM shopper_rsvps sr
            JOIN users u ON u.id = sr.user_id
            WHERE sr.event_id = ?
            ORDER BY sr.rsvped_at DESC
            LIMIT ?
            """,
            (event_id, limit),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "username": row["username"],
                "display_name": row["name"] or row["username"],
            }
            for row in rows
        ]
    finally:
        conn.close()


def _availability_from_row(row) -> dict[str, Any]:
    if not row:
        return {
            "weekdays": [],
            "preferred_months": [],
            "weekly_capacity": 2,
            "monthly_goal": 6,
            "notes": "",
        }

    return {
        "weekdays": [item for item in (row["weekdays"] or "").split(",") if item],
        "preferred_months": [item for item in (row["preferred_months"] or "").split(",") if item],
        "weekly_capacity": row["weekly_capacity"] or 2,
        "monthly_goal": row["monthly_goal"] or 6,
        "notes": row["notes"] or "",
    }


def get_availability_for_user(user_id: int) -> dict[str, Any]:
    init_users_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM user_availability WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    return _availability_from_row(row)


def upsert_availability_for_user(
    user_id: int,
    weekdays: list[str],
    preferred_months: list[str],
    weekly_capacity: int,
    monthly_goal: int,
    notes: str = "",
) -> dict[str, Any]:
    init_users_db()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO user_availability (
                user_id, weekdays, preferred_months, weekly_capacity, monthly_goal, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                weekdays=excluded.weekdays,
                preferred_months=excluded.preferred_months,
                weekly_capacity=excluded.weekly_capacity,
                monthly_goal=excluded.monthly_goal,
                notes=excluded.notes,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                user_id,
                ",".join(weekdays),
                ",".join(preferred_months),
                weekly_capacity,
                monthly_goal,
                notes.strip(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return get_availability_for_user(user_id)


def get_vendor_tracker_for_user(user_id: int) -> dict[str, Any] | None:
    init_users_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT tracker_json, updated_at FROM user_vendor_trackers WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    tracker = json.loads(row["tracker_json"])
    tracker["updated_at"] = row["updated_at"] or ""
    return tracker


def upsert_vendor_tracker_for_user(user_id: int, tracker: dict[str, Any]) -> dict[str, Any]:
    init_users_db()
    payload = json.dumps(tracker)
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO user_vendor_trackers (user_id, tracker_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                tracker_json = excluded.tracker_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, payload),
        )
        conn.commit()
    finally:
        conn.close()
    return get_vendor_tracker_for_user(user_id) or tracker


def follow_vendor(shopper_user_id: int, vendor_user_id: int) -> None:
    init_users_db()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO vendor_followers (shopper_user_id, vendor_user_id)
            VALUES (?, ?)
            ON CONFLICT(shopper_user_id, vendor_user_id) DO NOTHING
            """,
            (shopper_user_id, vendor_user_id),
        )
        conn.commit()
    finally:
        conn.close()


def unfollow_vendor(shopper_user_id: int, vendor_user_id: int) -> None:
    init_users_db()
    conn = _connect()
    try:
        conn.execute(
            "DELETE FROM vendor_followers WHERE shopper_user_id = ? AND vendor_user_id = ?",
            (shopper_user_id, vendor_user_id),
        )
        conn.commit()
    finally:
        conn.close()


def is_following_vendor(shopper_user_id: int, vendor_user_id: int) -> bool:
    init_users_db()
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT 1
            FROM vendor_followers
            WHERE shopper_user_id = ? AND vendor_user_id = ?
            """,
            (shopper_user_id, vendor_user_id),
        ).fetchone()
    finally:
        conn.close()
    return bool(row)


def get_followed_vendors_for_shopper(shopper_user_id: int) -> list[dict[str, Any]]:
    init_users_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT u.id, u.name, u.email, u.username, u.role, u.interests, u.bio, u.created_at, vf.followed_at
            FROM vendor_followers vf
            JOIN users u ON u.id = vf.vendor_user_id
            WHERE vf.shopper_user_id = ?
            ORDER BY vf.followed_at DESC, u.username ASC
            """,
            (shopper_user_id,),
        ).fetchall()
    finally:
        conn.close()
    vendors = []
    for row in rows:
        vendor = _user_from_row(row)
        vendor["followed_at"] = row["followed_at"] or ""
        vendors.append(vendor)
    return vendors


def get_follower_user_ids_for_vendor(vendor_user_id: int) -> list[int]:
    init_users_db()
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT shopper_user_id FROM vendor_followers WHERE vendor_user_id = ?",
            (vendor_user_id,),
        ).fetchall()
    finally:
        conn.close()
    return [int(row["shopper_user_id"]) for row in rows]


def set_vendor_event_visibility(vendor_user_id: int, event_id: str, visible_to_followers: bool) -> None:
    init_users_db()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO vendor_event_visibility (vendor_user_id, event_id, visible_to_followers, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(vendor_user_id, event_id) DO UPDATE SET
                visible_to_followers = excluded.visible_to_followers
            """,
            (vendor_user_id, event_id, 1 if visible_to_followers else 0),
        )
        conn.commit()
    finally:
        conn.close()


def get_vendor_visible_events(vendor_user_id: int, visible_only: bool = True) -> list[dict[str, Any]]:
    init_users_db()
    conn = _connect()
    try:
        sql = """
            SELECT e.*, ve.visible_to_followers, ve.created_at
            FROM vendor_event_visibility ve
            JOIN events e ON e.id = ve.event_id
            WHERE ve.vendor_user_id = ?
        """
        params: list[Any] = [vendor_user_id]
        if visible_only:
            sql += " AND ve.visible_to_followers = 1"
        sql += " ORDER BY e.date ASC, e.name ASC"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    return [
        {
            "id": row["id"],
            "name": row["name"],
            "city": row["city"],
            "state": row["state"],
            "date": row["date"],
            "vendor_count": row["vendor_count"],
            "estimated_traffic": row["estimated_traffic"],
            "booth_price": row["booth_price"],
            "application_link": row["application_link"],
            "organizer_contact": row["organizer_contact"],
            "popularity_score": row["popularity_score"],
            "source_url": row["source_url"],
            "vendor_category": row["vendor_category"],
            "event_size": row["event_size"],
            "visible_to_followers": bool(row["visible_to_followers"]),
            "shared_at": row["created_at"] or "",
        }
        for row in rows
    ]


def create_notification(
    user_id: int,
    kind: str,
    title: str,
    body: str,
    related_user_id: int | None = None,
    related_event_id: str | None = None,
) -> None:
    init_users_db()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO user_notifications (
                user_id, kind, title, body, related_user_id, related_event_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (user_id, kind, title, body, related_user_id, related_event_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_notifications_for_user(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    init_users_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM user_notifications
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": row["id"],
            "kind": row["kind"],
            "title": row["title"],
            "body": row["body"],
            "related_user_id": row["related_user_id"],
            "related_event_id": row["related_event_id"],
            "created_at": row["created_at"] or "",
            "read_at": row["read_at"] or "",
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Vendor extended profile
# ---------------------------------------------------------------------------

def get_vendor_profile(user_id: int) -> dict[str, Any]:
    """Return extended vendor profile, defaulting empty if not yet saved."""
    init_users_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM vendor_profiles WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    if row:
        return {key: row[key] for key in row.keys()}
    return {
        "user_id": user_id,
        "business_name": "",
        "category": "",
        "subcategory": "",
        "location": "",
        "price_range": "",
        "main_goal": "",
        "preferred_env": "",
        "experience_level": "",
        "risk_tolerance": "",
        "max_booth_price": None,
        "instagram_url": "",
        "tiktok_url": "",
        "website_url": "",
        "etsy_url": "",
        "sell_where": "",
        "banner_color": "#0f766e",
        "verification_status": "basic",
        "updated_at": "",
    }


def upsert_vendor_profile(user_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    init_users_db()
    allowed = {
        "business_name", "category", "subcategory", "location",
        "price_range", "main_goal", "preferred_env", "experience_level",
        "risk_tolerance", "max_booth_price", "instagram_url", "tiktok_url",
        "website_url", "etsy_url", "sell_where", "banner_color",
    }
    clean = {k: v for k, v in fields.items() if k in allowed}
    if not clean:
        return get_vendor_profile(user_id)
    conn = _connect()
    try:
        cols = ", ".join(clean.keys())
        placeholders = ", ".join("?" for _ in clean)
        update_clause = ", ".join(f"{k} = excluded.{k}" for k in clean)
        conn.execute(
            f"""
            INSERT INTO vendor_profiles (user_id, {cols}, updated_at)
            VALUES (?, {placeholders}, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                {update_clause},
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, *clean.values()),
        )
        conn.commit()
    finally:
        conn.close()
    return get_vendor_profile(user_id)


# ---------------------------------------------------------------------------
# Vendor verification
# ---------------------------------------------------------------------------

def get_verification_status(vendor_user_id: int) -> str:
    """Return verification_status for a vendor ('basic', 'pending', 'verified', 'trusted')."""
    profile = get_vendor_profile(vendor_user_id)
    return profile.get("verification_status", "basic")


def search_vendors_for_organizers(
    q: str = "",
    category: str = "",
    experience_level: str = "",
    verification_status: str = "",
    location: str = "",
    limit: int = 48,
) -> list[dict[str, Any]]:
    """Return vendors with profile data for organizer discovery.

    Joins users + vendor_profiles. Supports full-text search across
    business_name, name, username, category, location, and interests (tags).
    """
    init_users_db()
    safe_limit = max(1, min(int(limit or 48), 200))
    q_clean = (q or "").strip().lower()

    conditions: list[str] = ["u.role = 'vendor'"]
    params: list[Any] = []

    if q_clean:
        like = f"%{q_clean}%"
        conditions.append(
            "(LOWER(COALESCE(vp.business_name,'')) LIKE ?"
            " OR LOWER(u.name) LIKE ?"
            " OR LOWER(u.username) LIKE ?"
            " OR LOWER(COALESCE(vp.category,'')) LIKE ?"
            " OR LOWER(COALESCE(vp.location,'')) LIKE ?"
            " OR LOWER(COALESCE(u.interests,'')) LIKE ?"
            " OR LOWER(COALESCE(u.bio,'')) LIKE ?)"
        )
        params.extend([like, like, like, like, like, like, like])

    if category:
        conditions.append("LOWER(COALESCE(vp.category,'')) LIKE ?")
        params.append(f"%{category.strip().lower()}%")

    if experience_level:
        conditions.append("LOWER(COALESCE(vp.experience_level,'')) = ?")
        params.append(experience_level.strip().lower())

    if verification_status and verification_status != "all":
        conditions.append("LOWER(COALESCE(vp.verification_status,'basic')) = ?")
        params.append(verification_status.strip().lower())

    if location:
        conditions.append("LOWER(COALESCE(vp.location,'')) LIKE ?")
        params.append(f"%{location.strip().lower()}%")

    where = " AND ".join(conditions)
    params.append(safe_limit)

    conn = _connect()
    try:
        rows = conn.execute(
            f"""
            SELECT
                u.id,
                u.name,
                u.username,
                u.interests,
                u.bio,
                u.created_at,
                COALESCE(vp.business_name, u.name)    AS business_name,
                COALESCE(vp.category, '')              AS category,
                COALESCE(vp.subcategory, '')           AS subcategory,
                COALESCE(vp.location, '')              AS location,
                COALESCE(vp.experience_level, '')      AS experience_level,
                COALESCE(vp.verification_status,'basic') AS verification_status,
                COALESCE(vp.instagram_url, '')         AS instagram_url,
                COALESCE(vp.website_url, '')           AS website_url,
                COALESCE(vp.etsy_url, '')              AS etsy_url,
                COALESCE(vp.banner_color, '#0f766e')   AS banner_color
            FROM users u
            LEFT JOIN vendor_profiles vp ON vp.user_id = u.id
            WHERE {where}
            ORDER BY
                CASE WHEN COALESCE(vp.verification_status,'basic') = 'verified' THEN 0
                     WHEN COALESCE(vp.verification_status,'basic') = 'trusted'  THEN 1
                     ELSE 2 END,
                u.id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "id": row["id"],
            "name": row["name"],
            "username": row["username"],
            "business_name": row["business_name"] or row["name"],
            "category": row["category"],
            "subcategory": row["subcategory"],
            "location": row["location"],
            "experience_level": row["experience_level"],
            "verification_status": row["verification_status"],
            "instagram_url": row["instagram_url"],
            "website_url": row["website_url"],
            "etsy_url": row["etsy_url"],
            "banner_color": row["banner_color"] or "#0f766e",
            "bio": row["bio"] or "",
            "tags": [t.strip() for t in (row["interests"] or "").split(",") if t.strip()],
        }
        for row in rows
    ]


def set_verification_status(vendor_user_id: int, status: str) -> None:
    """Set verification_status on vendor_profiles (creates row if missing)."""
    allowed = {"basic", "pending", "verified", "trusted"}
    if status not in allowed:
        raise ValueError(f"Invalid status: {status}")
    init_users_db()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO vendor_profiles (user_id, verification_status)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                verification_status = excluded.verification_status,
                updated_at = CURRENT_TIMESTAMP
            """,
            (vendor_user_id, status),
        )
        conn.commit()
    finally:
        conn.close()


def submit_verification_request(
    vendor_user_id: int,
    business_name: str,
    category: str,
    description: str,
    social_links: dict | None = None,
    product_images: list | None = None,
) -> dict[str, Any]:
    """Create a new verification request (or re-open if previous was rejected)."""
    init_users_db()
    conn = _connect()
    try:
        # Only allow one active (pending) request at a time
        existing = conn.execute(
            "SELECT id, status FROM vendor_verification_requests WHERE vendor_user_id = ? ORDER BY created_at DESC LIMIT 1",
            (vendor_user_id,),
        ).fetchone()
        if existing and existing["status"] == "pending":
            raise ValueError("You already have a pending verification request.")

        conn.execute(
            """
            INSERT INTO vendor_verification_requests
                (vendor_user_id, business_name, category, description, social_links, product_images, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                vendor_user_id,
                (business_name or "").strip()[:200],
                (category or "").strip()[:100],
                (description or "").strip()[:2000],
                json.dumps(social_links or {}),
                json.dumps(product_images or []),
            ),
        )
        conn.commit()
        # Mark vendor profile as pending
        set_verification_status(vendor_user_id, "pending")
        row = conn.execute(
            "SELECT * FROM vendor_verification_requests WHERE vendor_user_id = ? ORDER BY id DESC LIMIT 1",
            (vendor_user_id,),
        ).fetchone()
    finally:
        conn.close()
    return _verification_request_from_row(row)


def list_verification_requests(status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """List verification requests for admin review."""
    init_users_db()
    conn = _connect()
    try:
        if status:
            rows = conn.execute(
                """
                SELECT vr.*, u.username, u.name AS vendor_name, u.email
                FROM vendor_verification_requests vr
                JOIN users u ON u.id = vr.vendor_user_id
                WHERE vr.status = ?
                ORDER BY vr.created_at DESC
                LIMIT ?
                """,
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT vr.*, u.username, u.name AS vendor_name, u.email
                FROM vendor_verification_requests vr
                JOIN users u ON u.id = vr.vendor_user_id
                ORDER BY vr.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return [_verification_request_from_row(r) for r in rows]


def review_verification_request(
    request_id: int,
    decision: str,
    admin_notes: str = "",
) -> dict[str, Any]:
    """Approve or reject a verification request. decision must be 'approved' or 'rejected'."""
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be 'approved' or 'rejected'")
    init_users_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM vendor_verification_requests WHERE id = ?",
            (request_id,),
        ).fetchone()
        if not row:
            raise ValueError("Verification request not found.")
        conn.execute(
            """
            UPDATE vendor_verification_requests
            SET status = ?, admin_notes = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (decision, (admin_notes or "").strip(), request_id),
        )
        conn.commit()
        vendor_user_id = row["vendor_user_id"]
    finally:
        conn.close()
    # Update vendor profile verification_status
    new_status = "verified" if decision == "approved" else "basic"
    set_verification_status(vendor_user_id, new_status)
    return {"ok": True, "request_id": request_id, "decision": decision}


def get_latest_verification_request(vendor_user_id: int) -> dict[str, Any] | None:
    """Return the most recent verification request for a vendor."""
    init_users_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM vendor_verification_requests WHERE vendor_user_id = ? ORDER BY created_at DESC LIMIT 1",
            (vendor_user_id,),
        ).fetchone()
    finally:
        conn.close()
    return _verification_request_from_row(row) if row else None


def _verification_request_from_row(row) -> dict[str, Any]:
    keys = row.keys()
    return {
        "id": row["id"],
        "vendor_user_id": row["vendor_user_id"],
        "business_name": row["business_name"] or "",
        "category": row["category"] or "",
        "description": row["description"] or "",
        "social_links": json.loads(row["social_links"] or "{}"),
        "product_images": json.loads(row["product_images"] or "[]"),
        "status": row["status"],
        "admin_notes": row["admin_notes"] or "",
        "created_at": row["created_at"] or "",
        "reviewed_at": row["reviewed_at"] or "",
        "username": row["username"] if "username" in keys else "",
        "vendor_name": row["vendor_name"] if "vendor_name" in keys else "",
        "email": row["email"] if "email" in keys else "",
    }


# ---------------------------------------------------------------------------
# Vendor manual products
# ---------------------------------------------------------------------------

def _product_from_row(row) -> dict[str, Any]:
    keys = row.keys()
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "name": row["name"],
        "description": row["description"] or "",
        "price": float(row["price"]) if row["price"] is not None else None,
        "image_url": row["image_url"] or "",
        "product_url": row["product_url"] or "",
        "category": row["category"] or "",
        "in_stock": bool(row["in_stock"]),
        "display_order": int(row["display_order"] or 0),
        "source": row["source"] if "source" in keys else "manual",
        "inventory_quantity": int(row["inventory_quantity"] or 0) if "inventory_quantity" in keys else 0,
        "created_at": row["created_at"] or "",
        "updated_at": row["updated_at"] or "",
    }


def list_vendor_products(user_id: int) -> list[dict[str, Any]]:
    init_users_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT * FROM vendor_products
            WHERE user_id = ?
            ORDER BY display_order ASC, created_at ASC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    return [_product_from_row(r) for r in rows]


def list_vendor_products_by_username(username: str) -> list[dict[str, Any]]:
    init_users_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT vp.* FROM vendor_products vp
            JOIN users u ON u.id = vp.user_id
            WHERE LOWER(u.username) = LOWER(?)
            ORDER BY vp.display_order ASC, vp.created_at ASC
            """,
            (username.strip(),),
        ).fetchall()
    finally:
        conn.close()
    return [_product_from_row(r) for r in rows]


def create_vendor_product(user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    init_users_db()
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("Product name is required.")
    conn = _connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO vendor_products
                (user_id, name, description, price, image_url, product_url, category, in_stock, display_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                name,
                str(payload.get("description", "")).strip(),
                float(payload["price"]) if payload.get("price") is not None else None,
                str(payload.get("image_url", "")).strip(),
                str(payload.get("product_url", "")).strip(),
                str(payload.get("category", "")).strip(),
                1 if payload.get("in_stock", True) else 0,
                int(payload.get("display_order", 0)),
            ),
        )
        product_id = cursor.lastrowid
        conn.commit()
        row = conn.execute("SELECT * FROM vendor_products WHERE id = ?", (product_id,)).fetchone()
    finally:
        conn.close()
    return _product_from_row(row)


def update_vendor_product(product_id: int, user_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    init_users_db()
    allowed = {"name", "description", "price", "image_url", "product_url", "category", "in_stock", "display_order"}
    clean: dict[str, Any] = {}
    for k, v in payload.items():
        if k not in allowed:
            continue
        if k == "in_stock":
            clean[k] = 1 if v else 0
        elif k == "price":
            clean[k] = float(v) if v is not None else None
        elif k == "display_order":
            clean[k] = int(v or 0)
        else:
            clean[k] = str(v).strip()
    conn = _connect()
    try:
        if clean:
            set_clause = ", ".join(f"{k} = ?" for k in clean)
            conn.execute(
                f"UPDATE vendor_products SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
                (*clean.values(), product_id, user_id),
            )
            conn.commit()
        row = conn.execute(
            "SELECT * FROM vendor_products WHERE id = ? AND user_id = ?", (product_id, user_id)
        ).fetchone()
    finally:
        conn.close()
    return _product_from_row(row) if row else None


def delete_vendor_product(product_id: int, user_id: int) -> bool:
    init_users_db()
    conn = _connect()
    try:
        result = conn.execute(
            "DELETE FROM vendor_products WHERE id = ? AND user_id = ?", (product_id, user_id)
        )
        deleted = result.rowcount > 0
        conn.commit()
    finally:
        conn.close()
    return deleted


def bulk_replace_csv_products(user_id: int, products: list[dict[str, Any]]) -> int:
    """Replace all CSV-sourced products for a user with a new set. Returns count inserted."""
    init_users_db()
    conn = _connect()
    try:
        conn.execute("DELETE FROM vendor_products WHERE user_id = ? AND source = 'csv'", (user_id,))
        for i, p in enumerate(products):
            name = str(p.get("name", "")).strip()
            if not name:
                continue
            conn.execute(
                """
                INSERT INTO vendor_products
                    (user_id, name, description, price, category, in_stock, inventory_quantity, source, display_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'csv', ?)
                """,
                (
                    user_id,
                    name[:500],
                    str(p.get("description", "")).strip()[:1000],
                    float(p["price"]) if p.get("price") is not None else None,
                    str(p.get("category", "")).strip()[:100],
                    1 if p.get("in_stock", True) else 0,
                    int(p.get("inventory_quantity", 0) or 0),
                    i,
                ),
            )
        conn.commit()
        return len(products)
    finally:
        conn.close()
