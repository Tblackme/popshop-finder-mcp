from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from db_runtime import connect

DEMO_DATA_PATH = Path(
    os.environ.get("VENDOR_ATLAS_DEMO_DATA_PATH", str(Path(__file__).resolve().parent / "data" / "demo_markets.json"))
).expanduser()


@dataclass
class Market:
    id: str
    name: str
    city: str
    state: str
    country: str = "US"
    start_date: str = ""
    end_date: str = ""
    vendor_count: int | None = None
    estimated_traffic: int | None = None
    booth_price: float | None = None
    application_deadline: str | None = None
    popularity_score: int | None = None
    indoor_outdoor: str = "unknown"
    categories: str = ""
    organizer_name: str | None = None
    organizer_contact: str | None = None
    apply_url: str | None = None
    source_type: str = "manual"
    source_ref: str | None = None
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # expose categories as list for tools while storing as comma string internally
        cats = [c.strip() for c in (self.categories or "").split(",") if c.strip()]
        data["categories"] = cats
        return data


def _connect():
    return connect()


def _upsert_market_conn(conn, market: Market) -> None:
    conn.execute(
        """
        INSERT INTO markets (
            id, name, city, state, country, start_date, end_date,
            vendor_count, estimated_traffic, booth_price,
            application_deadline, popularity_score, indoor_outdoor,
            categories, organizer_name, organizer_contact, apply_url,
            source_type, source_ref, last_updated
        ) VALUES (
            :id, :name, :city, :state, :country, :start_date, :end_date,
            :vendor_count, :estimated_traffic, :booth_price,
            :application_deadline, :popularity_score, :indoor_outdoor,
            :categories, :organizer_name, :organizer_contact, :apply_url,
            :source_type, :source_ref, :last_updated
        )
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            city=excluded.city,
            state=excluded.state,
            country=excluded.country,
            start_date=excluded.start_date,
            end_date=excluded.end_date,
            vendor_count=excluded.vendor_count,
            estimated_traffic=excluded.estimated_traffic,
            booth_price=excluded.booth_price,
            application_deadline=excluded.application_deadline,
            popularity_score=excluded.popularity_score,
            indoor_outdoor=excluded.indoor_outdoor,
            categories=excluded.categories,
            organizer_name=excluded.organizer_name,
            organizer_contact=excluded.organizer_contact,
            apply_url=excluded.apply_url,
            source_type=excluded.source_type,
            source_ref=excluded.source_ref,
            last_updated=excluded.last_updated
        """,
        {
            "id": market.id,
            "name": market.name,
            "city": market.city,
            "state": market.state,
            "country": market.country,
            "start_date": market.start_date,
            "end_date": market.end_date,
            "vendor_count": market.vendor_count,
            "estimated_traffic": market.estimated_traffic,
            "booth_price": market.booth_price,
            "application_deadline": market.application_deadline,
            "popularity_score": market.popularity_score,
            "indoor_outdoor": market.indoor_outdoor,
            "categories": market.categories,
            "organizer_name": market.organizer_name,
            "organizer_contact": market.organizer_contact,
            "apply_url": market.apply_url,
            "source_type": market.source_type,
            "source_ref": market.source_ref,
            "last_updated": market.last_updated,
        },
    )


def _seed_demo_markets_if_empty(conn) -> None:
    count = conn.execute("SELECT COUNT(*) AS count FROM markets").fetchone()["count"]
    if count or not DEMO_DATA_PATH.exists():
        return

    raw_markets = json.loads(DEMO_DATA_PATH.read_text(encoding="utf-8"))
    for item in raw_markets:
        market = Market(
            id=item["id"],
            name=item["name"],
            city=item["city"],
            state=item["state"],
            country=item.get("country", "US"),
            start_date=item.get("start_date", ""),
            end_date=item.get("end_date", ""),
            vendor_count=item.get("vendor_count"),
            estimated_traffic=item.get("estimated_traffic"),
            booth_price=item.get("booth_price"),
            application_deadline=item.get("application_deadline"),
            popularity_score=item.get("popularity_score"),
            indoor_outdoor=item.get("indoor_outdoor", "unknown"),
            categories=",".join(item.get("categories", [])),
            organizer_name=item.get("organizer_name"),
            organizer_contact=item.get("organizer_contact"),
            apply_url=item.get("apply_url"),
            source_type=item.get("source_type", "demo"),
            source_ref=item.get("source_ref"),
            last_updated=item.get("last_updated", ""),
        )
        _upsert_market_conn(conn, market)


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS markets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                country TEXT,
                start_date TEXT,
                end_date TEXT,
                vendor_count INTEGER,
                estimated_traffic INTEGER,
                booth_price REAL,
                application_deadline TEXT,
                popularity_score INTEGER,
                indoor_outdoor TEXT,
                categories TEXT,
                organizer_name TEXT,
                organizer_contact TEXT,
                apply_url TEXT,
                source_type TEXT,
                source_ref TEXT,
                last_updated TEXT
            )
            """
        )
        _seed_demo_markets_if_empty(conn)
        conn.commit()
    finally:
        conn.close()


def upsert_market(market: Market) -> None:
    init_db()
    conn = _connect()
    try:
        _upsert_market_conn(conn, market)
        conn.commit()
    finally:
        conn.close()


def get_markets(filters: dict[str, Any]) -> list[dict[str, Any]]:
    init_db()
    clauses = []
    params: dict[str, Any] = {}

    city = (filters.get("city") or "").strip()
    if city:
        clauses.append("LOWER(city) = LOWER(:city)")
        params["city"] = city

    state = (filters.get("state") or "").strip()
    if state:
        clauses.append("LOWER(state) = LOWER(:state)")
        params["state"] = state

    indoor_outdoor = filters.get("indoor_outdoor")
    if indoor_outdoor and indoor_outdoor in {"indoor", "outdoor"}:
        clauses.append("indoor_outdoor = :indoor_outdoor")
        params["indoor_outdoor"] = indoor_outdoor

    start_date = (filters.get("start_date") or "").strip()
    if start_date:
        clauses.append("date(end_date) >= date(:start_date)")
        params["start_date"] = start_date

    end_date = (filters.get("end_date") or "").strip()
    if end_date:
        clauses.append("date(start_date) <= date(:end_date)")
        params["end_date"] = end_date

    category = (filters.get("category") or "").strip()
    if category:
        clauses.append("LOWER(categories) LIKE LOWER(:category_like)")
        params["category_like"] = f"%{category}%"

    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    sql = f"""
        SELECT *
        FROM markets
        {where_sql}
        ORDER BY start_date ASC, popularity_score DESC
        LIMIT 200
    """

    conn = _connect()
    try:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
    finally:
        conn.close()

    markets: list[dict[str, Any]] = []
    for row in rows:
        m = Market(
            id=row["id"],
            name=row["name"],
            city=row["city"],
            state=row["state"],
            country=row["country"],
            start_date=row["start_date"] or "",
            end_date=row["end_date"] or "",
            vendor_count=row["vendor_count"],
            estimated_traffic=row["estimated_traffic"],
            booth_price=row["booth_price"],
            application_deadline=row["application_deadline"],
            popularity_score=row["popularity_score"],
            indoor_outdoor=row["indoor_outdoor"] or "unknown",
            categories=row["categories"] or "",
            organizer_name=row["organizer_name"],
            organizer_contact=row["organizer_contact"],
            apply_url=row["apply_url"],
            source_type=row["source_type"] or "manual",
            source_ref=row["source_ref"],
            last_updated=row["last_updated"] or "",
        )
        markets.append(m.to_dict())
    return markets


def get_market_by_id(market_id: str) -> dict[str, Any] | None:
    init_db()
    conn = _connect()
    try:
        cur = conn.execute("SELECT * FROM markets WHERE id = ?", (market_id,))
        row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    m = Market(
        id=row["id"],
        name=row["name"],
        city=row["city"],
        state=row["state"],
        country=row["country"],
        start_date=row["start_date"] or "",
        end_date=row["end_date"] or "",
        vendor_count=row["vendor_count"],
        estimated_traffic=row["estimated_traffic"],
        booth_price=row["booth_price"],
        application_deadline=row["application_deadline"],
        popularity_score=row["popularity_score"],
        indoor_outdoor=row["indoor_outdoor"] or "unknown",
        categories=row["categories"] or "",
        organizer_name=row["organizer_name"],
        organizer_contact=row["organizer_contact"],
        apply_url=row["apply_url"],
        source_type=row["source_type"] or "manual",
        source_ref=row["source_ref"],
        last_updated=row["last_updated"] or "",
    )
    return m.to_dict()

