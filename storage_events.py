from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from db_runtime import connect


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
    # Geo + display fields
    latitude: float | None = None
    longitude: float | None = None
    description: str | None = None
    location_name: str | None = None
    address: str | None = None
    event_type: str | None = None
    banner_image: str | None = None
    created_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_EVENT_SEED = (
    Event(
        id="seed-kc-strawberry-swing",
        name="The Strawberry Swing Indie Craft Fair",
        city="Kansas City",
        state="MO",
        date="2026-05-24",
        vendor_count=80,
        estimated_traffic=3000,
        booth_price=75.0,
        popularity_score=92,
        vendor_category="craft",
        event_size="medium",
        latitude=39.0997,
        longitude=-94.5786,
        event_type="Craft Fair",
        location_name="Loose Park",
        address="5200 Pennsylvania Ave, Kansas City, MO 64112",
    ),
    Event(
        id="seed-austin-night-market",
        name="Austin Night Market",
        city="Austin",
        state="TX",
        date="2026-06-13",
        vendor_count=95,
        estimated_traffic=2800,
        booth_price=120.0,
        popularity_score=88,
        vendor_category="art",
        event_size="medium",
        latitude=30.2672,
        longitude=-97.7431,
        event_type="Art Market",
        location_name="Rainey Street",
        address="Rainey St, Austin, TX 78701",
    ),
    Event(
        id="seed-chicago-makers-row",
        name="Chicago Makers Row",
        city="Chicago",
        state="IL",
        date="2026-07-11",
        vendor_count=110,
        estimated_traffic=4200,
        booth_price=160.0,
        popularity_score=90,
        vendor_category="handmade",
        event_size="large",
        latitude=41.8781,
        longitude=-87.6298,
        event_type="Makers Market",
        location_name="Millennium Park",
        address="201 E Randolph St, Chicago, IL 60602",
    ),
    Event(
        id="seed-nashville-vintage-fair",
        name="Nashville Vintage Fair",
        city="Nashville",
        state="TN",
        date="2026-08-09",
        vendor_count=65,
        estimated_traffic=2100,
        booth_price=95.0,
        popularity_score=79,
        vendor_category="vintage",
        event_size="medium",
        latitude=36.1627,
        longitude=-86.7816,
        event_type="Vintage Fair",
        location_name="The Fairgrounds Nashville",
        address="500 Wedgewood Ave, Nashville, TN 37203",
    ),
    Event(
        id="seed-denver-oddities-market",
        name="Denver Oddities Market",
        city="Denver",
        state="CO",
        date="2026-09-19",
        vendor_count=70,
        estimated_traffic=2600,
        booth_price=140.0,
        popularity_score=84,
        vendor_category="oddities",
        event_size="medium",
        latitude=39.7392,
        longitude=-104.9903,
        event_type="Oddities Market",
        location_name="Denver Merchandise Mart",
        address="451 E 58th Ave, Denver, CO 80216",
    ),
    Event(
        id="seed-atlanta-holiday-pop-up",
        name="Atlanta Holiday Pop-Up",
        city="Atlanta",
        state="GA",
        date="2026-11-21",
        vendor_count=120,
        estimated_traffic=4800,
        booth_price=185.0,
        popularity_score=91,
        vendor_category="gift",
        event_size="large",
        latitude=33.7490,
        longitude=-84.3880,
        event_type="Pop-Up Market",
        location_name="Ponce City Market",
        address="675 Ponce De Leon Ave NE, Atlanta, GA 30308",
    ),
)


def _connect():
    return connect()


def _normalize_event_size(vendor_count: int | None) -> str:
    if vendor_count is None:
        return "unknown"
    if vendor_count < 50:
        return "small"
    if vendor_count < 100:
        return "medium"
    return "large"


def _upsert_event_conn(conn, event: Event) -> None:
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
            event_size,
            latitude,
            longitude,
            description,
            location_name,
            address,
            event_type,
            banner_image,
            created_by
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
            :event_size,
            :latitude,
            :longitude,
            :description,
            :location_name,
            :address,
            :event_type,
            :banner_image,
            :created_by
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
            event_size=excluded.event_size,
            latitude=excluded.latitude,
            longitude=excluded.longitude,
            description=excluded.description,
            location_name=excluded.location_name,
            address=excluded.address,
            event_type=excluded.event_type,
            banner_image=excluded.banner_image,
            created_by=excluded.created_by
        """,
        event.to_dict(),
    )


def _event_from_row(row) -> Event:
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
        latitude=row["latitude"] if "latitude" in row.keys() else None,
        longitude=row["longitude"] if "longitude" in row.keys() else None,
        description=row["description"] if "description" in row.keys() else None,
        location_name=row["location_name"] if "location_name" in row.keys() else None,
        address=row["address"] if "address" in row.keys() else None,
        event_type=row["event_type"] if "event_type" in row.keys() else None,
        banner_image=row["banner_image"] if "banner_image" in row.keys() else None,
        created_by=row["created_by"] if "created_by" in row.keys() else None,
    )


def _migrate_events_db(conn) -> None:
    """Add new columns to the events table if they don't already exist."""
    new_columns = [
        ("latitude", "REAL"),
        ("longitude", "REAL"),
        ("description", "TEXT"),
        ("location_name", "TEXT"),
        ("address", "TEXT"),
        ("event_type", "TEXT"),
        ("banner_image", "TEXT"),
        ("created_by", "TEXT"),
    ]
    for col, col_type in new_columns:
        try:
            conn.execute(f"ALTER TABLE events ADD COLUMN {col} {col_type}")
        except Exception:
            pass  # Column already exists


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
                event_size TEXT,
                latitude REAL,
                longitude REAL,
                description TEXT,
                location_name TEXT,
                address TEXT,
                event_type TEXT,
                banner_image TEXT,
                created_by TEXT
            )
            """
        )
        _migrate_events_db(conn)
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


def ensure_seed_events() -> int:
    """Populate a small default event set when the events table is empty."""
    init_events_db()
    conn = _connect()
    try:
        existing = conn.execute("SELECT COUNT(*) AS count FROM events").fetchone()
        current_count = int(existing["count"]) if existing else 0
        if current_count > 0:
            return 0
        for event in DEFAULT_EVENT_SEED:
            seeded = Event(**event.to_dict())
            if not seeded.event_size:
                seeded.event_size = _normalize_event_size(seeded.vendor_count)
            _upsert_event_conn(conn, seeded)
        conn.commit()
        return len(DEFAULT_EVENT_SEED)
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


def get_events_for_map() -> list[dict[str, Any]]:
    """Return all events that have valid coordinates for map display."""
    init_events_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM events
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ORDER BY popularity_score DESC, date ASC
            LIMIT 500
            """
        ).fetchall()
    finally:
        conn.close()
    return [_event_from_row(row).to_dict() for row in rows]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in km between two lat/lng points."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_events_nearby(
    lat: float, lng: float, radius_km: float = 80.0
) -> list[dict[str, Any]]:
    """Return events within radius_km of the given coordinates, sorted by distance."""
    init_events_db()
    # Rough bounding box to reduce Python-side work
    deg_lat = radius_km / 111.0
    deg_lng = radius_km / (111.0 * math.cos(math.radians(lat)))
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT * FROM events
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
              AND latitude  BETWEEN :lat_min AND :lat_max
              AND longitude BETWEEN :lng_min AND :lng_max
            """,
            {
                "lat_min": lat - deg_lat,
                "lat_max": lat + deg_lat,
                "lng_min": lng - deg_lng,
                "lng_max": lng + deg_lng,
            },
        ).fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        event = _event_from_row(row).to_dict()
        dist = _haversine_km(lat, lng, event["latitude"], event["longitude"])
        if dist <= radius_km:
            event["distance_km"] = round(dist, 1)
            results.append(event)

    results.sort(key=lambda e: e["distance_km"])
    return results


def update_event_location(
    event_id: str,
    latitude: float,
    longitude: float,
    location_name: str | None = None,
    address: str | None = None,
) -> bool:
    """Update the geo fields on an existing event. Returns True if a row was updated."""
    init_events_db()
    conn = _connect()
    try:
        params: dict[str, Any] = {
            "id": event_id,
            "latitude": latitude,
            "longitude": longitude,
            "location_name": location_name,
            "address": address,
        }
        conn.execute(
            """
            UPDATE events
               SET latitude      = :latitude,
                   longitude     = :longitude,
                   location_name = COALESCE(:location_name, location_name),
                   address       = COALESCE(:address, address)
             WHERE id = :id
            """,
            params,
        )
        conn.commit()
        updated = conn.execute(
            "SELECT changes() AS n"
        ).fetchone()
        return bool(updated and updated["n"])
    finally:
        conn.close()


def update_event(event_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
    """Partial update of allowed event fields. Returns updated event or None."""
    allowed = {
        "name", "description", "date", "location_name", "address",
        "city", "state", "latitude", "longitude", "event_type",
        "banner_image", "vendor_count", "booth_price", "vendor_category",
        "application_link", "organizer_contact",
    }
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_event_by_id(event_id)

    init_events_db()
    conn = _connect()
    try:
        set_clause = ", ".join(f"{col} = :{col}" for col in updates)
        updates["id"] = event_id
        conn.execute(
            f"UPDATE events SET {set_clause} WHERE id = :id",
            updates,
        )
        conn.commit()
    finally:
        conn.close()
    return get_event_by_id(event_id)


_CITY_COORDS: dict[str, tuple[float, float]] = {
    "kansas city": (39.0997, -94.5786),
    "austin": (30.2672, -97.7431),
    "chicago": (41.8781, -87.6298),
    "nashville": (36.1627, -86.7816),
    "denver": (39.7392, -104.9903),
    "atlanta": (33.7490, -84.3880),
    "new york": (40.7128, -74.0060),
    "los angeles": (34.0522, -118.2437),
    "houston": (29.7604, -95.3698),
    "phoenix": (33.4484, -112.0740),
    "philadelphia": (39.9526, -75.1652),
    "san antonio": (29.4241, -98.4936),
    "san diego": (32.7157, -117.1611),
    "dallas": (32.7767, -96.7970),
    "san jose": (37.3382, -121.8863),
    "seattle": (47.6062, -122.3321),
    "portland": (45.5051, -122.6750),
    "miami": (25.7617, -80.1918),
    "minneapolis": (44.9778, -93.2650),
    "st. louis": (38.6270, -90.1994),
    "st louis": (38.6270, -90.1994),
    "baltimore": (39.2904, -76.6122),
    "charlotte": (35.2271, -80.8431),
    "raleigh": (35.7796, -78.6382),
    "pittsburgh": (40.4406, -79.9959),
    "sacramento": (38.5816, -121.4944),
    "salt lake city": (40.7608, -111.8910),
    "new orleans": (29.9511, -90.0715),
    "las vegas": (36.1699, -115.1398),
    "memphis": (35.1495, -90.0490),
    "louisville": (38.2527, -85.7585),
    "richmond": (37.5407, -77.4360),
    "oklahoma city": (35.4676, -97.5164),
    "tucson": (32.2217, -110.9265),
    "albuquerque": (35.0844, -106.6504),
    "omaha": (41.2565, -95.9345),
    "cleveland": (41.4993, -81.6944),
    "tampa": (27.9506, -82.4572),
    "orlando": (28.5383, -81.3792),
    "jacksonville": (30.3322, -81.6557),
    "columbus": (39.9612, -82.9988),
    "detroit": (42.3314, -83.0458),
    "indianapolis": (39.7684, -86.1581),
    "cincinnati": (39.1031, -84.5120),
    "boston": (42.3601, -71.0589),
    "washington": (38.9072, -77.0369),
    "washington dc": (38.9072, -77.0369),
    "san francisco": (37.7749, -122.4194),
    "buffalo": (42.8864, -78.8784),
    "rochester": (43.1566, -77.6088),
}


def backfill_seed_event_coords() -> int:
    """Backfill missing coordinates for all events using a city-name lookup."""
    init_events_db()
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, city FROM events WHERE latitude IS NULL OR longitude IS NULL"
        ).fetchall()
        updated = 0
        for row in rows:
            key = (row["city"] or "").strip().lower()
            if key not in _CITY_COORDS:
                continue
            lat, lng = _CITY_COORDS[key]
            conn.execute(
                "UPDATE events SET latitude = :lat, longitude = :lng WHERE id = :id",
                {"id": row["id"], "lat": lat, "lng": lng},
            )
            updated += 1

        # Also update seed events' supplemental fields (location_name, address, event_type)
        for event in DEFAULT_EVENT_SEED:
            conn.execute(
                """
                UPDATE events
                   SET latitude      = COALESCE(latitude, :latitude),
                       longitude     = COALESCE(longitude, :longitude),
                       location_name = COALESCE(location_name, :location_name),
                       address       = COALESCE(address, :address),
                       event_type    = COALESCE(event_type, :event_type)
                 WHERE id = :id
                """,
                {
                    "id": event.id,
                    "latitude": event.latitude,
                    "longitude": event.longitude,
                    "location_name": event.location_name,
                    "address": event.address,
                    "event_type": event.event_type,
                },
            )
        conn.commit()
    finally:
        conn.close()
    return updated


def clear_discovered_events() -> int:
    """Delete all pipeline-discovered events (id starts with 'discovered-'). Returns count deleted."""
    init_events_db()
    conn = _connect()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM events WHERE id LIKE 'discovered-%'"
        ).fetchone()[0]
        conn.execute("DELETE FROM events WHERE id LIKE 'discovered-%'")
        conn.commit()
    finally:
        conn.close()
    return count
