from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "vendor_atlas.db"
DB_PATH = Path(os.environ.get("VENDOR_ATLAS_DB_PATH", str(DEFAULT_DB_PATH))).expanduser()

PBKDF2_ITERATIONS = 120_000


@dataclass
class UserRecord:
    id: int
    name: str
    email: str
    username: str
    password_hash: str
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


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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


def _user_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "username": row["username"],
        "interests": row["interests"] or "",
        "bio": row["bio"] or "",
        "created_at": row["created_at"] or "",
    }


def init_users_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                interests TEXT,
                bio TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
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
        conn.commit()
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    init_users_db()
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT id, name, email, username, interests, bio, created_at
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
            SELECT id, name, email, username, interests, bio, created_at
            FROM users
            WHERE LOWER(email) = LOWER(?)
            """,
            (email.strip(),),
        ).fetchone()
    finally:
        conn.close()
    return _user_from_row(row) if row else None


def create_user(
    name: str,
    email: str,
    username: str,
    password: str,
    interests: str = "",
    bio: str = "",
) -> dict[str, Any]:
    init_users_db()
    normalized_email = email.strip().lower()
    normalized_username = username.strip()

    conn = _connect()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?)",
            (normalized_email, normalized_username),
        ).fetchone()
        if existing:
            raise ValueError("An account with that email or username already exists.")

        cursor = conn.execute(
            """
            INSERT INTO users (name, email, username, password_hash, interests, bio)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name.strip(),
                normalized_email,
                normalized_username,
                _hash_password(password),
                interests.strip(),
                bio.strip(),
            ),
        )
        conn.commit()
        user_id = int(cursor.lastrowid)
    finally:
        conn.close()

    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("Account created but could not be loaded.")
    return user


def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    init_users_db()
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT *
            FROM users
            WHERE LOWER(email) = LOWER(?)
            """,
            (email.strip(),),
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
            INSERT OR IGNORE INTO saved_markets (user_id, event_id)
            VALUES (?, ?)
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


def _availability_from_row(row: sqlite3.Row | None) -> dict[str, Any]:
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
