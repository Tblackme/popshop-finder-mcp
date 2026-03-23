from __future__ import annotations

import os
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from db_runtime import connect

def _connect():
    conn = connect()
    if getattr(conn, "kind", "") == "sqlite":
        conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _uuid() -> str:
    return str(uuid.uuid4())


def _row_to_dict(row) -> dict[str, Any] | None:
    if not row:
        return None
    return {key: row[key] for key in row.keys()}


def _rows_to_dicts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: row[key] for key in row.keys()} for row in rows]


def init_marketplace_db() -> None:
    conn = _connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS marketplace_users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                username TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('vendor', 'organizer', 'shopper')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS marketplace_vendors (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                business_name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                location TEXT,
                instagram_url TEXT,
                website_url TEXT,
                shopify_url TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES marketplace_users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS marketplace_events (
                id TEXT PRIMARY KEY,
                organizer_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT,
                location TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                vendor_fee REAL,
                application_url TEXT,
                is_claimed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizer_id) REFERENCES marketplace_users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS marketplace_event_applications (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                vendor_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('applied', 'accepted', 'rejected', 'waitlisted')),
                message TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES marketplace_events(id) ON DELETE CASCADE,
                FOREIGN KEY (vendor_id) REFERENCES marketplace_vendors(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS marketplace_saved_events (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES marketplace_users(id) ON DELETE CASCADE,
                FOREIGN KEY (event_id) REFERENCES marketplace_events(id) ON DELETE CASCADE,
                UNIQUE(user_id, event_id)
            );

            CREATE TABLE IF NOT EXISTS marketplace_followed_vendors (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                vendor_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES marketplace_users(id) ON DELETE CASCADE,
                FOREIGN KEY (vendor_id) REFERENCES marketplace_vendors(id) ON DELETE CASCADE,
                UNIQUE(user_id, vendor_id)
            );

            CREATE TABLE IF NOT EXISTS marketplace_vendor_event_stats (
                id TEXT PRIMARY KEY,
                vendor_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                revenue REAL DEFAULT 0,
                expenses REAL DEFAULT 0,
                vendor_fee REAL DEFAULT 0,
                profit REAL DEFAULT 0,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vendor_id) REFERENCES marketplace_vendors(id) ON DELETE CASCADE,
                FOREIGN KEY (event_id) REFERENCES marketplace_events(id) ON DELETE CASCADE,
                UNIQUE(vendor_id, event_id)
            );

            CREATE TABLE IF NOT EXISTS marketplace_products (
                id TEXT PRIMARY KEY,
                vendor_id TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT,
                price REAL DEFAULT 0,
                FOREIGN KEY (vendor_id) REFERENCES marketplace_vendors(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS marketplace_sales (
                id TEXT PRIMARY KEY,
                vendor_id TEXT NOT NULL,
                product_id TEXT,
                event_id TEXT,
                price REAL DEFAULT 0,
                quantity INTEGER DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vendor_id) REFERENCES marketplace_vendors(id) ON DELETE CASCADE
            );
            """
        )
        _seed_marketplace(conn)
        _seed_profit_data(conn)
        conn.commit()
    finally:
        conn.close()


def _seed_marketplace(conn) -> None:
    existing = conn.execute("SELECT COUNT(*) AS count FROM marketplace_events").fetchone()["count"]
    if existing:
        return

    organizer_id = _uuid()
    shopper_id = _uuid()
    vendor_users = [
        (_uuid(), "sunlitclay@example.com", "sunlitclay", "vendor"),
        (_uuid(), "wildflowerthreads@example.com", "wildflowerthreads", "vendor"),
        (_uuid(), "midnightprints@example.com", "midnightprints", "vendor"),
        (_uuid(), "junipergoods@example.com", "junipergoods", "vendor"),
        (_uuid(), "goldenhourjewelry@example.com", "goldenhourjewelry", "vendor"),
    ]

    base_users = [
        (organizer_id, "organizer@vendoratlas.test", "austinmakerhost", "organizer"),
        (shopper_id, "shopper@vendoratlas.test", "weekendwanderer", "shopper"),
        *vendor_users,
    ]
    conn.executemany(
        "INSERT INTO marketplace_users (id, email, username, role) VALUES (?, ?, ?, ?)",
        base_users,
    )

    vendor_rows = [
        (_uuid(), vendor_users[0][0], "Sunlit Clay Studio", "Hand-thrown ceramics and tableware.", "Ceramics", "Austin, TX", "https://instagram.com/sunlitclay", "https://sunlitclay.example.com", ""),
        (_uuid(), vendor_users[1][0], "Wildflower Threads", "Soft apparel and embroidered goods.", "Apparel", "Austin, TX", "https://instagram.com/wildflowerthreads", "https://wildflowerthreads.example.com", ""),
        (_uuid(), vendor_users[2][0], "Midnight Prints", "Limited-run art prints and zines.", "Art", "Dallas, TX", "https://instagram.com/midnightprints", "https://midnightprints.example.com", ""),
        (_uuid(), vendor_users[3][0], "Juniper Home Goods", "Warm home accents and candles.", "Home", "Houston, TX", "https://instagram.com/junipergoods", "https://junipergoods.example.com", ""),
        (_uuid(), vendor_users[4][0], "Golden Hour Jewelry", "Layered jewelry for gift shoppers.", "Jewelry", "San Antonio, TX", "https://instagram.com/goldenhourjewelry", "https://goldenhourjewelry.example.com", ""),
    ]
    conn.executemany(
        """
        INSERT INTO marketplace_vendors (
            id, user_id, business_name, description, category, location, instagram_url, website_url, shopify_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        vendor_rows,
    )

    events = [
        (_uuid(), organizer_id, "Austin Spring Makers Market", "A curated handmade market for spring shoppers.", "Craft", "Austin, TX", "2026-04-12", "2026-04-12", 125, "https://example.com/events/austin-spring-makers/apply", 1),
        (_uuid(), organizer_id, "South Congress Night Market", "Evening pop-up with music and food trucks.", "Night Market", "Austin, TX", "2026-04-26", "2026-04-26", 175, "https://example.com/events/soco-night/apply", 1),
        (_uuid(), organizer_id, "Hill Country Vintage Fair", "Vintage-focused market with home and style vendors.", "Vintage", "Round Rock, TX", "2026-05-03", "2026-05-03", 140, "https://example.com/events/hill-country-vintage/apply", 0),
        (_uuid(), organizer_id, "Makers on Main Street", "Small-batch makers and local artists downtown.", "Art", "Dallas, TX", "2026-05-10", "2026-05-10", 110, "https://example.com/events/makers-main/apply", 0),
        (_uuid(), organizer_id, "Summer Pop-Up Social", "Lifestyle brands, food, and music for weekend foot traffic.", "Lifestyle", "Houston, TX", "2026-05-17", "2026-05-17", 160, "https://example.com/events/summer-popup-social/apply", 1),
        (_uuid(), organizer_id, "Riverside Handmade Market", "Handmade-only event with family-friendly shoppers.", "Handmade", "Austin, TX", "2026-05-24", "2026-05-24", 95, "https://example.com/events/riverside-handmade/apply", 0),
        (_uuid(), organizer_id, "West End Art Walk", "Outdoor art walk with live demos and music.", "Art", "Dallas, TX", "2026-06-07", "2026-06-07", 130, "https://example.com/events/west-end-art-walk/apply", 0),
        (_uuid(), organizer_id, "Lakeside Summer Bazaar", "Seasonal shopping event with strong family traffic.", "Seasonal", "Houston, TX", "2026-06-14", "2026-06-14", 150, "https://example.com/events/lakeside-bazaar/apply", 0),
        (_uuid(), organizer_id, "Sunset Food + Makers Market", "Food-forward market with room for gift and home vendors.", "Food + Makers", "Austin, TX", "2026-06-21", "2026-06-21", 145, "https://example.com/events/sunset-food-makers/apply", 1),
        (_uuid(), organizer_id, "San Antonio Weekend Market", "Regional weekend market with tourist traffic.", "General", "San Antonio, TX", "2026-06-28", "2026-06-28", 115, "https://example.com/events/san-antonio-weekend/apply", 0),
    ]
    conn.executemany(
        """
        INSERT INTO marketplace_events (
            id, organizer_id, title, description, category, location, start_date, end_date, vendor_fee, application_url, is_claimed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        events,
    )

    event_map = {title: event_id for (event_id, _org, title, *_rest) in events}
    vendor_map = {business_name: vendor_id for (vendor_id, _user_id, business_name, *_rest) in vendor_rows}
    stat_rows = [
        ("Sunlit Clay Studio", "Austin Spring Makers Market", 2400, 520, 125, "Strong pottery sell-through and repeat customers."),
        ("Sunlit Clay Studio", "Riverside Handmade Market", 1350, 310, 95, "Smaller crowd but healthy conversion."),
        ("Wildflower Threads", "South Congress Night Market", 3100, 880, 175, "Excellent apparel sales during evening rush."),
        ("Wildflower Threads", "Summer Pop-Up Social", 1850, 740, 160, "Good traffic, but inventory mix was too broad."),
        ("Midnight Prints", "Makers on Main Street", 980, 410, 110, "More browsing than buying this time."),
        ("Golden Hour Jewelry", "San Antonio Weekend Market", 2750, 690, 115, "Best average order value of the month."),
    ]
    conn.executemany(
        """
        INSERT INTO marketplace_vendor_event_stats (
            id, vendor_id, event_id, revenue, expenses, vendor_fee, profit, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                _uuid(),
                vendor_map[vendor_name],
                event_map[event_title],
                revenue,
                expenses,
                vendor_fee,
                revenue - expenses - vendor_fee,
                notes,
            )
            for vendor_name, event_title, revenue, expenses, vendor_fee, notes in stat_rows
        ],
    )

    application_rows = [
        (vendor_map["Sunlit Clay Studio"], event_map["Austin Spring Makers Market"], "accepted", "Ceramics are a strong fit."),
        (vendor_map["Wildflower Threads"], event_map["South Congress Night Market"], "accepted", "Great category match."),
        (vendor_map["Midnight Prints"], event_map["Makers on Main Street"], "waitlisted", "Art category nearly full."),
        (vendor_map["Golden Hour Jewelry"], event_map["San Antonio Weekend Market"], "applied", "Would love to join this event."),
        (vendor_map["Juniper Home Goods"], event_map["Summer Pop-Up Social"], "rejected", "Home category was over capacity."),
    ]
    conn.executemany(
        """
        INSERT INTO marketplace_event_applications (id, event_id, vendor_id, status, message)
        VALUES (?, ?, ?, ?, ?)
        """,
        [(_uuid(), event_id, vendor_id, status, message) for vendor_id, event_id, status, message in application_rows],
    )

    conn.executemany(
        """
        INSERT INTO marketplace_saved_events (id, user_id, event_id)
        VALUES (?, ?, ?)
        """,
        [
            (_uuid(), shopper_id, event_map["Austin Spring Makers Market"]),
            (_uuid(), shopper_id, event_map["South Congress Night Market"]),
            (_uuid(), shopper_id, event_map["San Antonio Weekend Market"]),
        ],
    )

    conn.executemany(
        """
        INSERT INTO marketplace_followed_vendors (id, user_id, vendor_id)
        VALUES (?, ?, ?)
        """,
        [
            (_uuid(), shopper_id, vendor_map["Sunlit Clay Studio"]),
            (_uuid(), shopper_id, vendor_map["Golden Hour Jewelry"]),
        ],
    )


def list_events(category: str = "", location: str = "", max_vendor_fee: float | None = None) -> list[dict[str, Any]]:
    init_marketplace_db()
    clauses = []
    params: list[Any] = []
    if category:
        clauses.append("LOWER(COALESCE(category, '')) LIKE LOWER(?)")
        params.append(f"%{category.strip()}%")
    if location:
        clauses.append("LOWER(COALESCE(location, '')) LIKE LOWER(?)")
        params.append(f"%{location.strip()}%")
    if max_vendor_fee is not None:
        clauses.append("COALESCE(vendor_fee, 0) <= ?")
        params.append(float(max_vendor_fee))

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    conn = _connect()
    try:
        rows = conn.execute(
            f"""
            SELECT *
            FROM marketplace_events
            {where_sql}
            ORDER BY date(start_date) ASC, title ASC
            """,
            params,
        ).fetchall()
    finally:
        conn.close()
    return _rows_to_dicts(rows)


def get_event(event_id: str) -> dict[str, Any] | None:
    init_marketplace_db()
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM marketplace_events WHERE id = ?", (event_id,)).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row)


def create_event(payload: dict[str, Any]) -> dict[str, Any]:
    init_marketplace_db()
    event_id = _uuid()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO marketplace_events (
                id, organizer_id, title, description, category, location, start_date, end_date, vendor_fee, application_url, is_claimed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                payload["organizer_id"],
                payload["title"],
                payload.get("description", ""),
                payload.get("category", ""),
                payload.get("location", ""),
                payload["start_date"],
                payload["end_date"],
                payload.get("vendor_fee"),
                payload.get("application_url", ""),
                1 if payload.get("is_claimed") else 0,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return get_event(event_id)


def get_vendor(vendor_id: str) -> dict[str, Any] | None:
    init_marketplace_db()
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT v.*, u.username, u.email, u.role
            FROM marketplace_vendors v
            JOIN marketplace_users u ON u.id = v.user_id
            WHERE v.id = ?
            """,
            (vendor_id,),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row)


def create_vendor(payload: dict[str, Any]) -> dict[str, Any]:
    init_marketplace_db()
    conn = _connect()
    try:
        user_id = payload.get("user_id") or _uuid()
        existing_user = conn.execute("SELECT id FROM marketplace_users WHERE id = ?", (user_id,)).fetchone()
        if not existing_user:
            conn.execute(
                "INSERT INTO marketplace_users (id, email, username, role) VALUES (?, ?, ?, 'vendor')",
                (
                    user_id,
                    payload["email"],
                    payload["username"],
                ),
            )

        vendor_id = _uuid()
        conn.execute(
            """
            INSERT INTO marketplace_vendors (
                id, user_id, business_name, description, category, location, instagram_url, website_url, shopify_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                vendor_id,
                user_id,
                payload["business_name"],
                payload.get("description", ""),
                payload.get("category", ""),
                payload.get("location", ""),
                payload.get("instagram_url", ""),
                payload.get("website_url", ""),
                payload.get("shopify_url", ""),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return get_vendor(vendor_id)


def create_application(payload: dict[str, Any]) -> dict[str, Any]:
    init_marketplace_db()
    application_id = _uuid()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO marketplace_event_applications (id, event_id, vendor_id, status, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                application_id,
                payload["event_id"],
                payload["vendor_id"],
                payload.get("status", "applied"),
                payload.get("message", ""),
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM marketplace_event_applications WHERE id = ?",
            (application_id,),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row)


def list_applications(vendor_id: str = "") -> list[dict[str, Any]]:
    init_marketplace_db()
    conn = _connect()
    try:
        if vendor_id:
            rows = conn.execute(
                """
                SELECT a.*, e.title AS event_title, v.business_name AS vendor_name, v.category AS vendor_category
                FROM marketplace_event_applications a
                JOIN marketplace_events e ON e.id = a.event_id
                JOIN marketplace_vendors v ON v.id = a.vendor_id
                WHERE a.vendor_id = ?
                ORDER BY a.created_at DESC
                """,
                (vendor_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT a.*, e.title AS event_title, v.business_name AS vendor_name, v.category AS vendor_category
                FROM marketplace_event_applications a
                JOIN marketplace_events e ON e.id = a.event_id
                JOIN marketplace_vendors v ON v.id = a.vendor_id
                ORDER BY a.created_at DESC
                """
            ).fetchall()
    finally:
        conn.close()
    return _rows_to_dicts(rows)


def save_event_for_user(user_id: str, event_id: str) -> dict[str, Any]:
    init_marketplace_db()
    saved_id = _uuid()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO marketplace_saved_events (id, user_id, event_id)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, event_id) DO NOTHING
            """,
            (saved_id, user_id, event_id),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True, "user_id": user_id, "event_id": event_id}


def list_saved_events(user_id: str) -> list[dict[str, Any]]:
    init_marketplace_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT s.id, s.user_id, s.event_id, s.created_at, e.title, e.location, e.start_date, e.end_date, e.vendor_fee, e.application_url, e.category
            FROM marketplace_saved_events s
            JOIN marketplace_events e ON e.id = s.event_id
            WHERE s.user_id = ?
            ORDER BY s.created_at DESC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    return _rows_to_dicts(rows)


def list_vendors() -> list[dict[str, Any]]:
    init_marketplace_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT v.*, u.username, u.email
            FROM marketplace_vendors v
            JOIN marketplace_users u ON u.id = v.user_id
            ORDER BY v.business_name ASC
            """
        ).fetchall()
    finally:
        conn.close()
    return _rows_to_dicts(rows)


def get_vendor_by_username(username: str) -> dict[str, Any] | None:
    init_marketplace_db()
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT v.*, u.username, u.email
            FROM marketplace_vendors v
            JOIN marketplace_users u ON u.id = v.user_id
            WHERE LOWER(u.username) = LOWER(?)
            """,
            (username.strip(),),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row)


def get_marketplace_user_by_username(username: str) -> dict[str, Any] | None:
    init_marketplace_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM marketplace_users WHERE LOWER(username) = LOWER(?)",
            (username.strip(),),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row)


def get_first_marketplace_user(role: str) -> dict[str, Any] | None:
    init_marketplace_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM marketplace_users WHERE role = ? ORDER BY created_at ASC LIMIT 1",
            (role,),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row)


def get_first_vendor() -> dict[str, Any] | None:
    vendors = list_vendors()
    return vendors[0] if vendors else None


def ensure_vendor_marketplace_profile(
    *,
    username: str,
    email: str,
    business_name: str,
    description: str = "",
    category: str = "General",
    location: str = "",
) -> dict[str, Any]:
    init_marketplace_db()
    conn = _connect()
    try:
        user_row = conn.execute(
            "SELECT * FROM marketplace_users WHERE LOWER(username) = LOWER(?)",
            (username.strip(),),
        ).fetchone()
        if user_row:
            user_id = str(user_row["id"])
        else:
            user_id = _uuid()
            conn.execute(
                "INSERT INTO marketplace_users (id, email, username, role) VALUES (?, ?, ?, 'vendor')",
                (user_id, email.strip().lower(), username.strip().lower()),
            )

        vendor_row = conn.execute(
            "SELECT * FROM marketplace_vendors WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if vendor_row:
            vendor_id = str(vendor_row["id"])
            conn.execute(
                """
                UPDATE marketplace_vendors
                SET business_name = ?, description = ?, category = ?, location = ?
                WHERE id = ?
                """,
                (business_name, description, category, location, vendor_id),
            )
        else:
            vendor_id = _uuid()
            conn.execute(
                """
                INSERT INTO marketplace_vendors (
                    id, user_id, business_name, description, category, location, instagram_url, website_url, shopify_url
                ) VALUES (?, ?, ?, ?, ?, ?, '', '', '')
                """,
                (vendor_id, user_id, business_name, description, category, location),
            )

        stat_count = conn.execute(
            "SELECT COUNT(*) AS count FROM marketplace_vendor_event_stats WHERE vendor_id = ?",
            (vendor_id,),
        ).fetchone()["count"]

        if not stat_count:
            event_rows = conn.execute(
                """
                SELECT id, title, vendor_fee
                FROM marketplace_events
                ORDER BY date(start_date) ASC, title ASC
                LIMIT 3
                """
            ).fetchall()
            seeded_stats = [
                (2550.0, 680.0, "Strong sales mix and repeat buyers."),
                (1725.0, 540.0, "Solid turnout with moderate setup costs."),
                (1180.0, 460.0, "Smaller crowd, but profitable overall."),
            ]
            for index, row in enumerate(event_rows):
                revenue, expenses, notes = seeded_stats[min(index, len(seeded_stats) - 1)]
                vendor_fee = float(row["vendor_fee"] or 0)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO marketplace_vendor_event_stats (
                        id, vendor_id, event_id, revenue, expenses, vendor_fee, profit, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        _uuid(),
                        vendor_id,
                        str(row["id"]),
                        revenue,
                        expenses,
                        vendor_fee,
                        revenue - expenses - vendor_fee,
                        notes,
                    ),
                )

        conn.commit()
    finally:
        conn.close()

    vendor = get_vendor_by_username(username)
    if not vendor:
        raise RuntimeError(f"Failed to ensure marketplace vendor profile for {username}")
    return vendor


def list_vendor_event_stats(vendor_id: str) -> list[dict[str, Any]]:
    init_marketplace_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT s.*, e.title AS event_title, e.location AS event_location, e.start_date, e.end_date
            FROM marketplace_vendor_event_stats s
            JOIN marketplace_events e ON e.id = s.event_id
            WHERE s.vendor_id = ?
            ORDER BY date(e.start_date) DESC, e.title ASC
            """,
            (vendor_id,),
        ).fetchall()
    finally:
        conn.close()
    stats = _rows_to_dicts(rows)
    for item in stats:
        revenue = float(item.get("revenue") or 0)
        expenses = float(item.get("expenses") or 0)
        vendor_fee = float(item.get("vendor_fee") or 0)
        item["profit"] = round(revenue - expenses - vendor_fee, 2)
        total_cost = expenses + vendor_fee
        item["roi"] = round((item["profit"] / total_cost) * 100, 1) if total_cost > 0 else 0.0
    return stats


def get_vendor_stats(vendor_id: str) -> dict[str, Any]:
    stats = list_vendor_event_stats(vendor_id)
    total_revenue = round(sum(float(item.get("revenue") or 0) for item in stats), 2)
    total_expenses = round(sum(float(item.get("expenses") or 0) for item in stats), 2)
    total_vendor_fee = round(sum(float(item.get("vendor_fee") or 0) for item in stats), 2)
    total_profit = round(total_revenue - total_expenses - total_vendor_fee, 2)
    average_profit = round(total_profit / len(stats), 2) if stats else 0.0
    best = max(stats, key=lambda item: float(item.get("profit") or 0), default=None)
    worst = min(stats, key=lambda item: float(item.get("profit") or 0), default=None)
    return {
        "vendor_id": vendor_id,
        "events": stats,
        "summary": {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "total_vendor_fee": total_vendor_fee,
            "total_profit": total_profit,
            "average_profit_per_event": average_profit,
            "best_event": best,
            "worst_event": worst,
            "event_count": len(stats),
        },
    }


def get_organizer_analytics(organizer_id: str) -> dict[str, Any]:
    init_marketplace_db()
    conn = _connect()
    try:
        event_rows = conn.execute(
            """
            SELECT e.*,
                   COUNT(a.id) AS applicant_count,
                   COUNT(CASE WHEN a.status = 'accepted' THEN 1 END) AS accepted_count
            FROM marketplace_events e
            LEFT JOIN marketplace_event_applications a ON a.event_id = e.id
            WHERE e.organizer_id = ?
            GROUP BY e.id
            ORDER BY date(e.start_date) ASC, e.title ASC
            """,
            (organizer_id,),
        ).fetchall()
    finally:
        conn.close()
    events = _rows_to_dicts(event_rows)
    for item in events:
        applicant_count = int(item.get("applicant_count") or 0)
        vendor_fee = float(item.get("vendor_fee") or 0)
        item["estimated_revenue"] = round(vendor_fee * applicant_count, 2)
    total_events = len(events)
    total_applications = sum(int(item.get("applicant_count") or 0) for item in events)
    avg_vendors = round(total_applications / total_events, 1) if total_events else 0.0
    estimated_revenue = round(sum(float(item.get("estimated_revenue") or 0) for item in events), 2)
    return {
        "events": events,
        "summary": {
            "total_events_hosted": total_events,
            "total_applications_received": total_applications,
            "avg_vendors_per_event": avg_vendors,
            "estimated_vendor_fee_revenue": estimated_revenue,
        },
    }


def get_shopper_analytics(user_id: str) -> dict[str, Any]:
    init_marketplace_db()
    conn = _connect()
    try:
        saved_rows = conn.execute(
            """
            SELECT s.id, s.event_id, s.created_at, e.title, e.location, e.start_date, e.end_date, e.category
            FROM marketplace_saved_events s
            JOIN marketplace_events e ON e.id = s.event_id
            WHERE s.user_id = ?
            ORDER BY date(e.start_date) ASC, e.title ASC
            """,
            (user_id,),
        ).fetchall()
        followed_rows = conn.execute(
            """
            SELECT f.id, f.created_at, v.id AS vendor_id, v.business_name, v.category, v.location
            FROM marketplace_followed_vendors f
            JOIN marketplace_vendors v ON v.id = f.vendor_id
            WHERE f.user_id = ?
            ORDER BY v.business_name ASC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    saved_events = _rows_to_dicts(saved_rows)
    followed_vendors = _rows_to_dicts(followed_rows)
    return {
        "saved_events": saved_events,
        "followed_vendors": followed_vendors,
        "summary": {
            "events_saved": len(saved_events),
            "followed_vendors": len(followed_vendors),
            "upcoming_events": len(saved_events),
        },
    }


# ---------------------------------------------------------------------------
# Profit dashboard seed and query helpers
# ---------------------------------------------------------------------------

def _seed_profit_data(conn) -> None:
    """Seed products, past events, and sales for the profit dashboard demo. Safe to call on existing DBs."""
    existing = conn.execute("SELECT COUNT(*) AS count FROM marketplace_products").fetchone()["count"]
    if existing:
        return

    organizer_row = conn.execute(
        "SELECT id FROM marketplace_users WHERE role = 'organizer' LIMIT 1"
    ).fetchone()
    if not organizer_row:
        return
    organizer_id = organizer_row["id"]

    vendor_rows = conn.execute(
        "SELECT id, business_name FROM marketplace_vendors LIMIT 5"
    ).fetchall()
    if not vendor_rows:
        return
    vendor_map: dict[str, str] = {row["business_name"]: row["id"] for row in vendor_rows}

    # Past events (Jan-Mar 2026) for chart time-series data
    past_events: list[tuple] = [
        (_uuid(), organizer_id, "Winter Bazaar Austin", "Year-end handmade market.", "Craft", "Austin, TX", "2026-01-18", "2026-01-18", 110.0, "", 1),
        (_uuid(), organizer_id, "February Flea Market", "Monthly flea with vintage and handmade.", "Flea", "Austin, TX", "2026-02-08", "2026-02-08", 95.0, "", 1),
        (_uuid(), organizer_id, "Spring Preview Market", "Early spring market with fresh inventory.", "Craft", "Austin, TX", "2026-02-22", "2026-02-22", 130.0, "", 1),
        (_uuid(), organizer_id, "March Makers Fair", "Local makers and artisans showcase.", "Art", "Austin, TX", "2026-03-08", "2026-03-08", 120.0, "", 1),
    ]
    conn.executemany(
        """INSERT OR IGNORE INTO marketplace_events
           (id, organizer_id, title, description, category, location, start_date, end_date, vendor_fee, application_url, is_claimed)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        past_events,
    )
    past_event_map: dict[str, str] = {title: eid for (eid, _, title, *_rest) in past_events}

    sunlit = vendor_map.get("Sunlit Clay Studio")
    wildflower = vendor_map.get("Wildflower Threads")
    golden = vendor_map.get("Golden Hour Jewelry")
    midnight = vendor_map.get("Midnight Prints")
    juniper = vendor_map.get("Juniper Home Goods")

    cat_lookup: dict[str | None, str] = {
        sunlit: "Ceramics", wildflower: "Apparel", golden: "Jewelry",
        midnight: "Art", juniper: "Home",
    }
    vendor_products: dict[str | None, list[tuple[str, float]]] = {
        sunlit: [("Ceramic Mug", 18.0), ("Pottery Bowl", 35.0), ("Plant Pot", 28.0), ("Clay Vase", 45.0)],
        wildflower: [("Embroidered Tote", 38.0), ("Linen Shirt", 65.0), ("Knit Cardigan", 85.0)],
        golden: [("Gold Stack Ring", 42.0), ("Layered Necklace", 68.0), ("Statement Earrings", 55.0)],
        midnight: [("Art Print 8x10", 22.0), ("Mini Zine", 12.0), ("Poster Roll", 35.0)],
        juniper: [("Soy Candle", 24.0), ("Linen Pillow Cover", 42.0), ("Woven Basket", 58.0)],
    }
    products: list[tuple] = []
    product_map: dict[tuple, str] = {}
    for vid, items in vendor_products.items():
        if not vid:
            continue
        cat = cat_lookup.get(vid, "General")
        for name, price in items:
            pid = _uuid()
            products.append((pid, vid, name, cat, price))
            product_map[(vid, name)] = pid
    conn.executemany(
        "INSERT OR IGNORE INTO marketplace_products (id, vendor_id, name, category, price) VALUES (?, ?, ?, ?, ?)",
        products,
    )

    # Vendor event stats for past events
    if sunlit:
        past_stats = [
            (sunlit, past_event_map["Winter Bazaar Austin"], 1240.0, 280.0, 110.0, "Good winter traffic, mugs sold well."),
            (sunlit, past_event_map["February Flea Market"], 980.0, 220.0, 95.0, "Smaller crowd, steady pottery sales."),
            (sunlit, past_event_map["Spring Preview Market"], 1680.0, 360.0, 130.0, "Strong spring opener, vases popular."),
            (sunlit, past_event_map["March Makers Fair"], 1520.0, 310.0, 120.0, "Busy day with high conversion."),
        ]
        conn.executemany(
            """INSERT OR IGNORE INTO marketplace_vendor_event_stats
               (id, vendor_id, event_id, revenue, expenses, vendor_fee, profit, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [(_uuid(), vid, eid, rev, exp, fee, rev - exp - fee, notes)
             for vid, eid, rev, exp, fee, notes in past_stats],
        )

    # Applications for past events (organizer fill-rate data)
    all_vids = [v for v in [sunlit, wildflower, golden, midnight, juniper] if v]
    app_data: list[tuple[str, list[tuple[str, str]]]] = [
        ("Winter Bazaar Austin", [(v, "accepted") for v in all_vids[:4]] + ([(all_vids[4], "waitlisted")] if len(all_vids) > 4 else [])),
        ("February Flea Market", [(all_vids[0], "accepted"), (all_vids[1], "accepted"), (all_vids[2], "applied")] if len(all_vids) >= 3 else []),
        ("Spring Preview Market", [(v, "accepted") for v in all_vids[:4]]),
        ("March Makers Fair", [(all_vids[0], "accepted"), (all_vids[1], "waitlisted"), (all_vids[2], "accepted")] if len(all_vids) >= 3 else []),
    ]
    app_rows: list[tuple] = []
    for event_title, vendor_statuses in app_data:
        eid = past_event_map.get(event_title)
        if not eid:
            continue
        for vid, status in vendor_statuses:
            app_rows.append((_uuid(), eid, vid, status, ""))
    if app_rows:
        conn.executemany(
            "INSERT OR IGNORE INTO marketplace_event_applications (id, event_id, vendor_id, status, message) VALUES (?, ?, ?, ?, ?)",
            app_rows,
        )

    # Sales records with timestamps for time-series charts
    sales: list[tuple] = []
    if sunlit:
        mug = product_map.get((sunlit, "Ceramic Mug"))
        bowl = product_map.get((sunlit, "Pottery Bowl"))
        pot = product_map.get((sunlit, "Plant Pot"))
        vase = product_map.get((sunlit, "Clay Vase"))
        for event_title, sale_date, items in [
            ("Winter Bazaar Austin", "2026-01-18", [(mug, 18.0, 12), (bowl, 35.0, 6), (pot, 28.0, 4)]),
            ("February Flea Market", "2026-02-08", [(mug, 18.0, 15), (bowl, 35.0, 8)]),
            ("Spring Preview Market", "2026-02-22", [(mug, 18.0, 20), (pot, 28.0, 7), (vase, 45.0, 5)]),
            ("March Makers Fair", "2026-03-08", [(mug, 18.0, 18), (bowl, 35.0, 10), (vase, 45.0, 3)]),
        ]:
            eid = past_event_map.get(event_title)
            for pid, price, qty in items:
                if pid:
                    sales.append((_uuid(), sunlit, pid, eid, price, qty, f"{sale_date} 10:00:00"))
    if sales:
        conn.executemany(
            "INSERT OR IGNORE INTO marketplace_sales (id, vendor_id, product_id, event_id, price, quantity, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            sales,
        )


def _period_cutoff(period: str) -> str:
    today = date.today()
    if period == "7d":
        return (today - timedelta(days=7)).isoformat()
    if period == "30d":
        return (today - timedelta(days=30)).isoformat()
    if period == "90d":
        return (today - timedelta(days=90)).isoformat()
    return date(today.year, 1, 1).isoformat()


def get_vendor_profit_summary(vendor_id: str, period: str = "30d") -> dict[str, Any]:
    init_marketplace_db()
    cutoff = _period_cutoff(period)
    conn = _connect()
    try:
        all_stats = conn.execute(
            """
            SELECT s.revenue, s.expenses, s.vendor_fee, s.profit, e.start_date, e.title AS event_title
            FROM marketplace_vendor_event_stats s
            JOIN marketplace_events e ON e.id = s.event_id
            WHERE s.vendor_id = ?
            ORDER BY date(e.start_date) ASC
            """,
            (vendor_id,),
        ).fetchall()
        all_sales = conn.execute(
            "SELECT price, quantity FROM marketplace_sales WHERE vendor_id = ?",
            (vendor_id,),
        ).fetchall()
    finally:
        conn.close()
    total_revenue = round(sum(float(r["revenue"] or 0) for r in all_stats), 2)
    period_stats = [r for r in all_stats if str(r["start_date"] or "") >= cutoff]
    period_revenue = round(sum(float(r["revenue"] or 0) for r in period_stats), 2)
    markets = len(all_stats)
    total_orders = sum(int(r["quantity"] or 1) for r in all_sales)
    sales_revenue = sum(float(r["price"] or 0) * int(r["quantity"] or 1) for r in all_sales)
    avg_order = round(sales_revenue / total_orders, 2) if total_orders else 0.0
    chart = [
        {"date": str(r["start_date"] or ""), "label": str(r["event_title"] or ""), "revenue": round(float(r["revenue"] or 0), 2)}
        for r in period_stats
    ]
    return {
        "summary": {
            "total_revenue": total_revenue,
            "monthly_revenue": period_revenue,
            "total_orders": total_orders,
            "avg_order_value": avg_order,
            "markets_attended": markets,
        },
        "chart": chart,
        "period": period,
    }


def get_vendor_product_performance(vendor_id: str) -> list[dict[str, Any]]:
    init_marketplace_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT p.name, p.price,
                   COALESCE(SUM(s.quantity), 0) AS units_sold,
                   COALESCE(SUM(s.price * s.quantity), 0) AS revenue
            FROM marketplace_products p
            LEFT JOIN marketplace_sales s ON s.product_id = p.id
            WHERE p.vendor_id = ?
            GROUP BY p.id, p.name, p.price
            ORDER BY COALESCE(SUM(s.price * s.quantity), 0) DESC
            """,
            (vendor_id,),
        ).fetchall()
    finally:
        conn.close()
    result = []
    for row in rows:
        units = int(row["units_sold"] or 0)
        revenue = round(float(row["revenue"] or 0), 2)
        est_views = max(units * 3, 1)
        conv = round(units / est_views, 2)
        result.append({"name": row["name"], "units_sold": units, "revenue": revenue, "conversion_rate": conv})
    return result


def get_organizer_profit_summary(organizer_id: str, period: str = "year") -> dict[str, Any]:
    init_marketplace_db()
    cutoff = _period_cutoff(period)
    conn = _connect()
    try:
        event_rows = conn.execute(
            """
            SELECT e.*,
                   COUNT(a.id) AS applicant_count,
                   COUNT(CASE WHEN a.status = 'accepted' THEN 1 END) AS accepted_count
            FROM marketplace_events e
            LEFT JOIN marketplace_event_applications a ON a.event_id = e.id
            WHERE e.organizer_id = ?
            GROUP BY e.id
            ORDER BY date(e.start_date) ASC
            """,
            (organizer_id,),
        ).fetchall()
    finally:
        conn.close()
    events = _rows_to_dicts(event_rows)
    for item in events:
        accepted = int(item.get("accepted_count") or 0)
        fee = float(item.get("vendor_fee") or 0)
        item["booth_fees_collected"] = round(fee * accepted, 2)
    all_revenue = round(sum(float(e.get("booth_fees_collected") or 0) for e in events), 2)
    total_vendors = sum(int(e.get("accepted_count") or 0) for e in events)
    fees = [float(e.get("vendor_fee") or 0) for e in events if float(e.get("vendor_fee") or 0) > 0]
    avg_fee = round(sum(fees) / len(fees), 2) if fees else 0.0
    period_events = [e for e in events if str(e.get("start_date") or "") >= cutoff]
    chart = [
        {"label": str(e.get("title") or "Event"), "date": str(e.get("start_date") or ""), "revenue": float(e.get("booth_fees_collected") or 0)}
        for e in period_events
    ]
    return {
        "summary": {
            "total_revenue": all_revenue,
            "events_hosted": len(events),
            "vendors_registered": total_vendors,
            "avg_booth_fee": avg_fee,
        },
        "chart": chart,
        "period": period,
    }


def get_organizer_event_breakdown(organizer_id: str) -> list[dict[str, Any]]:
    init_marketplace_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT e.id, e.title, e.start_date, e.location, e.vendor_fee,
                   COUNT(a.id) AS applicant_count,
                   COUNT(CASE WHEN a.status = 'accepted' THEN 1 END) AS vendor_count
            FROM marketplace_events e
            LEFT JOIN marketplace_event_applications a ON a.event_id = e.id
            WHERE e.organizer_id = ?
            GROUP BY e.id
            ORDER BY date(e.start_date) DESC
            """,
            (organizer_id,),
        ).fetchall()
    finally:
        conn.close()
    result = []
    for row in rows:
        vendor_count = int(row["vendor_count"] or 0)
        fee = float(row["vendor_fee"] or 0)
        booth_fees = round(fee * vendor_count, 2)
        result.append({
            "name": str(row["title"]),
            "date": str(row["start_date"] or ""),
            "location": str(row["location"] or ""),
            "vendor_count": vendor_count,
            "applicant_count": int(row["applicant_count"] or 0),
            "booth_fee": fee,
            "booth_fees_collected": booth_fees,
            "ticket_revenue": 0.0,
            "profit": booth_fees,
        })
    return result


def get_organizer_vendor_demand(organizer_id: str) -> dict[str, Any]:
    init_marketplace_db()
    conn = _connect()
    try:
        cat_rows = conn.execute(
            """
            SELECT v.category, COUNT(a.id) AS count
            FROM marketplace_event_applications a
            JOIN marketplace_vendors v ON v.id = a.vendor_id
            JOIN marketplace_events e ON e.id = a.event_id
            WHERE e.organizer_id = ?
            GROUP BY v.category
            ORDER BY count DESC
            """,
            (organizer_id,),
        ).fetchall()
        fill_rows = conn.execute(
            """
            SELECT e.id, e.title, e.start_date,
                   COUNT(a.id) AS applicant_count,
                   COUNT(CASE WHEN a.status = 'accepted' THEN 1 END) AS accepted_count
            FROM marketplace_events e
            LEFT JOIN marketplace_event_applications a ON a.event_id = e.id
            WHERE e.organizer_id = ?
            GROUP BY e.id
            ORDER BY applicant_count DESC
            """,
            (organizer_id,),
        ).fetchall()
    finally:
        conn.close()
    top_categories = [
        {"category": str(r["category"] or "Uncategorized"), "count": int(r["count"] or 0)}
        for r in cat_rows[:5]
    ]
    fill_dicts = _rows_to_dicts(fill_rows)
    with_apps = [r for r in fill_dicts if int(r.get("applicant_count") or 0) > 0]
    avg_fill = round(
        sum(int(r.get("accepted_count") or 0) / max(int(r.get("applicant_count") or 1), 1) for r in with_apps) / len(with_apps),
        2,
    ) if with_apps else 0.0
    fastest = fill_dicts[:3]
    return {
        "top_categories": top_categories,
        "avg_fill_rate": avg_fill,
        "fastest_selling_events": [
            {"name": str(r.get("title") or "Event"), "applicants": int(r.get("applicant_count") or 0), "date": str(r.get("start_date") or "")}
            for r in fastest
        ],
    }
