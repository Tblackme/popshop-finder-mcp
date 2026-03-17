from datetime import UTC, datetime
from typing import Any

from storage_events import search_events

SEARCH_MARKETS_TOOL: dict[str, Any] = {
    "name": "search_markets",
    "description": "Legacy-compatible wrapper that returns market-style search results using the Vendor Atlas event store.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Optional free-text search such as 'popup market' or 'makers fair'.",
            },
            "city": {
                "type": "string",
                "description": "City to search in, e.g. 'Austin'.",
            },
            "state": {
                "type": "string",
                "description": "Optional state or region abbreviation.",
            },
            "start_date": {
                "type": "string",
                "description": "Optional ISO start date filter (YYYY-MM-DD).",
            },
            "end_date": {
                "type": "string",
                "description": "Optional ISO end date filter (YYYY-MM-DD).",
            },
            "date_range": {
                "type": "string",
                "description": "Optional compact date range in the form YYYY-MM-DD:YYYY-MM-DD.",
            },
            "event_size": {
                "type": "string",
                "enum": ["small", "medium", "large", "any"],
                "description": "Approximate event size filter.",
            },
            "vendor_category": {
                "type": "string",
                "description": "Optional vendor category like 'jewelry', 'food', or 'art'.",
            },
            "category": {
                "type": "string",
                "description": "Alias for vendor_category.",
            },
            "indoor_outdoor": {
                "type": "string",
                "enum": ["indoor", "outdoor", "any"],
                "description": "Accepted for UI compatibility.",
            },
            "radius_miles": {
                "type": ["number", "string"],
                "description": "Optional distance radius from the selected city. Accepted and echoed back for dashboard filtering.",
            },
            "distance_radius": {
                "type": ["number", "string"],
                "description": "Alias for radius_miles.",
            },
            "sources": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "google",
                        "eventbrite",
                        "facebook",
                        "instagram",
                        "local_market_sites",
                        "vendor_directories",
                    ],
                },
                "description": "Source categories to search. Defaults to all supported categories.",
            },
        },
        "required": [],
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "searched_at": {"type": "string"},
            "query": {"type": "string"},
            "filters": {"type": "object"},
            "sources_requested": {
                "type": "array",
                "items": {"type": "string"},
            },
            "results_count": {"type": "integer"},
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string"},
                        "date": {"type": "string"},
                        "vendor_count": {"type": ["integer", "null"]},
                        "estimated_traffic": {"type": ["integer", "null"]},
                        "booth_price": {"type": ["number", "null"]},
                        "application_link": {"type": ["string", "null"]},
                        "organizer_contact": {"type": ["string", "null"]},
                        "popularity_score": {"type": ["integer", "null"]},
                        "source_url": {"type": ["string", "null"]},
                        "vendor_category": {"type": ["string", "null"]},
                        "event_size": {"type": ["string", "null"]},
                        "discovered_sources": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "markets": {
                "type": "array",
                "items": {"type": "object"},
            },
        },
        "required": ["searched_at", "filters", "results_count", "events", "markets"],
    },
}


SOURCE_LABELS = {
    "google": "Google search",
    "eventbrite": "Eventbrite",
    "facebook": "Facebook events",
    "instagram": "Instagram hashtags",
    "local_market_sites": "Local market websites",
    "vendor_directories": "Vendor directories",
}


def _parse_date_range(date_range: str) -> tuple[str, str]:
    if not date_range or ":" not in date_range:
        return "", ""
    start_date, end_date = date_range.split(":", 1)
    return start_date.strip(), end_date.strip()


def _normalize_sources(sources: Any) -> list[str]:
    if not isinstance(sources, list) or not sources:
        return list(SOURCE_LABELS.keys())
    normalized = [str(source).strip() for source in sources if str(source).strip() in SOURCE_LABELS]
    return normalized or list(SOURCE_LABELS.keys())


def _event_to_market_card(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": event["id"],
        "name": event["name"],
        "city": event["city"],
        "state": event["state"],
        "start_date": event["date"],
        "end_date": event["date"],
        "vendor_count": event.get("vendor_count"),
        "estimated_traffic": event.get("estimated_traffic"),
        "booth_price": event.get("booth_price"),
        "application_deadline": None,
        "popularity_score": event.get("popularity_score"),
        "indoor_outdoor": "unknown",
        "categories": [event["vendor_category"]] if event.get("vendor_category") else [],
        "organizer_name": None,
        "organizer_contact": event.get("organizer_contact"),
        "apply_url": event.get("application_link"),
        "source_type": "event_search",
        "source_ref": event.get("source_url"),
        "last_updated": "",
    }


def _decorate_event(event: dict[str, Any], requested_sources: list[str]) -> dict[str, Any]:
    discovered_sources = [SOURCE_LABELS[source] for source in requested_sources]
    return {
        **event,
        "discovered_sources": discovered_sources,
    }


async def handle_search_markets(
    query: str = "",
    city: str = "",
    state: str = "",
    start_date: str = "",
    end_date: str = "",
    date_range: str = "",
    event_size: str = "any",
    vendor_category: str = "",
    category: str = "",
    indoor_outdoor: str = "any",
    radius_miles: Any = "",
    distance_radius: Any = "",
    sources: Any = None,
) -> str:
    """
    Compatibility wrapper over the event store for older market-style consumers.
    The forward search path is search_events plus GET /markets/search.
    """
    import json

    if date_range and (not start_date and not end_date):
        start_date, end_date = _parse_date_range(date_range)

    if event_size == "any":
        event_size = ""

    effective_radius = distance_radius or radius_miles
    effective_category = vendor_category or category
    requested_sources = _normalize_sources(sources)

    filters: dict[str, Any] = {
        "query": query,
        "city": city,
        "state": state,
        "start_date": start_date,
        "end_date": end_date,
        "event_size": event_size,
        "vendor_category": effective_category,
        "radius_miles": effective_radius,
        "distance_radius": effective_radius,
        "date_range": date_range,
        "sources": requested_sources,
    }
    if state:
        filters["state"] = state
    if indoor_outdoor in {"indoor", "outdoor"}:
        filters["indoor_outdoor"] = indoor_outdoor

    events = search_events(
        {
            "city": city,
            "start_date": start_date,
            "end_date": end_date,
            "event_size": event_size,
            "vendor_category": effective_category,
        }
    )
    if state:
        events = [event for event in events if str(event.get("state", "")).lower() == state.lower()]

    decorated_events = [_decorate_event(event, requested_sources) for event in events]
    markets = [_event_to_market_card(event) for event in decorated_events]

    payload: dict[str, Any] = {
        "searched_at": datetime.now(UTC).isoformat(),
        "query": query,
        "filters": filters,
        "sources_requested": requested_sources,
        "results_count": len(markets),
        "events": decorated_events,
        "markets": markets,
    }
    return json.dumps(payload)


TOOLS: list[dict[str, Any]] = [SEARCH_MARKETS_TOOL]

HANDLERS: dict[str, Any] = {
    "search_markets": handle_search_markets,
}

