from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "vendor_atlas.db"
DB_PATH = Path(os.environ.get("VENDOR_ATLAS_DB_PATH", str(DEFAULT_DB_PATH))).expanduser()
DEMO_DATA_PATH = Path(
    os.environ.get("VENDOR_ATLAS_DEMO_DATA_PATH", str(Path(__file__).resolve().parent / "data" / "demo_markets.json"))
).expanduser()


@dataclass
class Event:
    id: str
    name: str
    city: str
    state: str
    date: str
    vendor_count: int | None = None
    estimated_traffic: int | None = None
    booth_price: float | None = None
    application_link: str | None = None
    organizer_contact: str | None = None
    popularity_score: int | None = None
    source_url: str | None = None
    vendor_category: str | None = None
    event_size: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _normalize_event_size(vendor_count: int | None) -> str:
    if vendor_count is None:
        return "unknown"
    if vendor_count < 50:
        return "small"
    if vendor_count < 100:
        return "medium"
    return "large"


def _upsert_event_conn(conn: sqlite3.Connection, event: Event) -> None:
    conn.execute(
        """
        INSERT INTO events (
            id,
            name,
            city,
            state,
            date,
            vendor_count,
            estimated_traffic,
            booth_price,
            application_link,
            organizer_contact,
            popularity_score,
            source_url,
            vendor_category,
            event_size
        ) VALUES (
            :id,
            :name,
            :city,
            :state,
            :date,
            :vendor_count,
            :estimated_traffic,
            :booth_price,
            :application_link,
            :organizer_contact,
            :popularity_score,
            :source_url,
            :vendor_category,
            :event_size
        )
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            city=excluded.city,
            state=excluded.state,
            date=excluded.date,
            vendor_count=excluded.vendor_count,
            estimated_traffic=excluded.estimated_traffic,
            booth_price=excluded.booth_price,
            application_link=excluded.application_link,
            organizer_contact=excluded.organizer_contact,
            popularity_score=excluded.popularity_score,
            source_url=excluded.source_url,
            vendor_category=excluded.vendor_category,
            event_size=excluded.event_size
        """,
        event.to_dict(),
    )


def _event_from_row(row: sqlite3.Row) -> Event:
    return Event(
        id=row["id"],
        name=row["name"],
        city=row["city"],
        state=row["state"],
        date=row["date"],
        vendor_count=row["vendor_count"],
        estimated_traffic=row["estimated_traffic"],
        booth_price=row["booth_price"],
        application_link=row["application_link"],
        organizer_contact=row["organizer_contact"],
        popularity_score=row["popularity_score"],
        source_url=row["source_url"],
        vendor_category=row["vendor_category"],
        event_size=row["event_size"],
    )


def _seed_demo_events_if_empty(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) AS count FROM events").fetchone()["count"]
    if count or not DEMO_DATA_PATH.exists():
        return

    raw_markets = json.loads(DEMO_DATA_PATH.read_text(encoding="utf-8"))
    for item in raw_markets:
        categories = item.get("categories", [])
        event = Event(
            id=item["id"],
            name=item["name"],
            city=item["city"],
            state=item["state"],
            date=item.get("start_date", ""),
            vendor_count=item.get("vendor_count"),
            estimated_traffic=item.get("estimated_traffic"),
            booth_price=item.get("booth_price"),
            application_link=item.get("apply_url"),
            organizer_contact=item.get("organizer_contact"),
            popularity_score=item.get("popularity_score"),
            source_url=item.get("source_ref") or item.get("apply_url"),
            vendor_category=categories[0] if categories else None,
            event_size=_normalize_event_size(item.get("vendor_count")),
        )
        _upsert_event_conn(conn, event)


def init_events_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                date TEXT NOT NULL,
                vendor_count INTEGER,
                estimated_traffic INTEGER,
                booth_price REAL,
                application_link TEXT,
                organizer_contact TEXT,
                popularity_score INTEGER,
                source_url TEXT,
                vendor_category TEXT,
                event_size TEXT
            )
            """
        )
        _seed_demo_events_if_empty(conn)
        conn.commit()
    finally:
        conn.close()


def upsert_event(event: Event) -> None:
    init_events_db()
    conn = _connect()
    try:
        if not event.event_size:
            event.event_size = _normalize_event_size(event.vendor_count)
        _upsert_event_conn(conn, event)
        conn.commit()
    finally:
        conn.close()


def get_event_by_id(event_id: str) -> dict[str, Any] | None:
    init_events_db()
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return _event_from_row(row).to_dict()


def search_events(filters: dict[str, Any]) -> list[dict[str, Any]]:
    init_events_db()
    clauses: list[str] = []
    params: dict[str, Any] = {}

    city = (filters.get("city") or "").strip()
    if city:
        clauses.append("LOWER(city) = LOWER(:city)")
        params["city"] = city

    event_size = (filters.get("event_size") or "").strip().lower()
    if event_size:
        clauses.append("LOWER(event_size) = :event_size")
        params["event_size"] = event_size

    vendor_category = (filters.get("vendor_category") or "").strip()
    if vendor_category:
        clauses.append("LOWER(COALESCE(vendor_category, '')) LIKE LOWER(:vendor_category)")
        params["vendor_category"] = f"%{vendor_category}%"

    start_date = (filters.get("start_date") or "").strip()
    if start_date:
        clauses.append("date(date) >= date(:start_date)")
        params["start_date"] = start_date

    end_date = (filters.get("end_date") or "").strip()
    if end_date:
        clauses.append("date(date) <= date(:end_date)")
        params["end_date"] = end_date

    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    sql = f"""
        SELECT *
        FROM events
        {where_sql}
        ORDER BY date ASC, popularity_score DESC, name ASC
        LIMIT 200
    """

    conn = _connect()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    return [_event_from_row(row).to_dict() for row in rows]
