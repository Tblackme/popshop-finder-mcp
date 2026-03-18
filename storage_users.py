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
