import csv
from datetime import UTC, datetime
from typing import Any

from storage_markets import Market, upsert_market

INGEST_CSV_TOOL: dict[str, Any] = {
    "name": "ingest_markets_from_csv",
    "description": "Ingest markets from a simple CSV payload into the Vendor Atlas market store.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "csv_text": {
                "type": "string",
                "description": "CSV text with headers id,name,city,state,country,start_date,end_date,vendor_count,estimated_traffic,booth_price,application_deadline,popularity_score,indoor_outdoor,categories,organizer_name,organizer_contact,apply_url,source_type,source_ref",
            },
        },
        "required": ["csv_text"],
    },
}


async def handle_ingest_markets_from_csv(csv_text: str) -> str:
    """
    Basic CSV ingestion helper for internal use via MCP.
    """
    import io
    reader = csv.DictReader(io.StringIO(csv_text))
    count = 0
    now = datetime.now(UTC).isoformat()
    for row in reader:
        if not (row.get("id") and row.get("name") and row.get("city") and row.get("state")):
            continue
        try:
            vendor_count = int(row["vendor_count"]) if row.get("vendor_count") else None
        except ValueError:
            vendor_count = None
        try:
            estimated_traffic = int(row["estimated_traffic"]) if row.get("estimated_traffic") else None
        except ValueError:
            estimated_traffic = None
        try:
            booth_price = float(row["booth_price"]) if row.get("booth_price") else None
        except ValueError:
            booth_price = None
        try:
            popularity_score = int(row["popularity_score"]) if row.get("popularity_score") else None
        except ValueError:
            popularity_score = None

        m = Market(
            id=row["id"],
            name=row["name"],
            city=row["city"],
            state=row["state"],
            country=row.get("country") or "US",
            start_date=row.get("start_date") or "",
            end_date=row.get("end_date") or "",
            vendor_count=vendor_count,
            estimated_traffic=estimated_traffic,
            booth_price=booth_price,
            application_deadline=row.get("application_deadline") or None,
            popularity_score=popularity_score,
            indoor_outdoor=row.get("indoor_outdoor") or "unknown",
            categories=row.get("categories") or "",
            organizer_name=row.get("organizer_name") or None,
            organizer_contact=row.get("organizer_contact") or None,
            apply_url=row.get("apply_url") or None,
            source_type=row.get("source_type") or "csv",
            source_ref=row.get("source_ref") or None,
            last_updated=now,
        )
        upsert_market(m)
        count += 1

    return f"Ingested {count} markets from CSV."


TOOLS: list[dict[str, Any]] = [INGEST_CSV_TOOL]

HANDLERS: dict[str, Any] = {
    "ingest_markets_from_csv": handle_ingest_markets_from_csv,
}

