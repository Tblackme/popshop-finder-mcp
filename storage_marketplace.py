from __future__ import annotations

import os
import uuid
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
            """
        )
        _seed_marketplace(conn)
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
