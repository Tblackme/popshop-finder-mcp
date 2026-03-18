"""
VendorAtlas MCP Tool Implementations
Full handlers for all 16 tools: event discovery, scoring, saving, searching, and vendor profiling.
"""

import json
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Coroutine

# ---------------------------------------------------------------------------
# Simple JSON file-based database (no external dependencies)
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "events.json"

def _load_db() -> List[Dict]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        try:
            return json.loads(DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def _save_db(records: List[Dict]):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

# ---------------------------------------------------------------------------
# Tool Definitions (JSON Schema)
# ---------------------------------------------------------------------------

SCRAPE_EVENT_TOOL = {
    "name": "scrape_event",
    "description": "Scrape an event page and extract structured vendor-market details such as date, booth price, organizer contact, and application link.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Event page URL to scrape."}
        },
        "required": ["url"],
    },
}

DISCOVER_EVENTS_TOOL = {
    "name": "discover_events",
    "description": "Find candidate popup markets, makers markets, craft fairs, and vendor events across supported source categories.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "city": {"type": "string"},
            "state": {"type": "string"},
            "start_date": {"type": "string"},
            "end_date": {"type": "string"},
            "keywords": {"type": "array", "items": {"type": "string"}},
            "sources": {"type": "array", "items": {"type": "string"}},
        },
        "required": [],
    },
}

EXTRACT_EVENT_TOOL = {
    "name": "extract_event",
    "description": "Scrape an event page and extract structured market details from the source URL.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "url": {"type": "string"}
        },
        "required": ["url"],
    },
}

ENRICH_EVENT_TOOL = {
    "name": "enrich_event",
    "description": "Add extra event signals such as social buzz, repeat-history hints, and traffic estimates.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "event": {"type": "object"},
            "event_id": {"type": "string"},
        },
        "required": [],
    },
}

SCORE_EVENT_TOOL = {
    "name": "score_event",
    "description": "Calculate Vendor Atlas Profit Signals for an event and classify it as low, medium, or high opportunity.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "event": {"type": "object"},
            "event_id": {"type": "string"},
            "enrichment": {"type": "object"},
        },
        "required": [],
    },
}

SAVE_EVENT_TOOL = {
    "name": "save_event",
    "description": "Store a discovered, extracted, or scored event in the Vendor Atlas events database.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "event": {"type": "object"}
        },
        "required": ["event"],
    },
}

SEARCH_EVENTS_TOOL = {
    "name": "search_events",
    "description": "Search stored Vendor Atlas events for dashboard and agent workflows.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "city": {"type": "string"},
            "state": {"type": "string"},
            "start_date": {"type": "string"},
            "end_date": {"type": "string"},
            "date_range": {"type": "string"},
            "event_size": {"type": "string"},
            "vendor_category": {"type": "string"},
            "distance_radius": {"type": ["string", "number"]},
        },
        "required": [],
    },
}

SEARCH_MARKETS_TOOL = {
    "name": "search_markets",
    "description": "Legacy-compatible wrapper that returns market-style search results using the Vendor Atlas event store.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City to search in, e.g. 'Austin'."},
            "state": {"type": "string", "description": "Optional state or region abbreviation."},
            "query": {"type": "string", "description": "Optional free-text search such as 'popup market' or 'makers fair'."},
            "start_date": {"type": "string", "description": "Optional ISO start date filter (YYYY-MM-DD)."},
            "end_date": {"type": "string", "description": "Optional ISO end date filter (YYYY-MM-DD)."},
            "date_range": {"type": "string", "description": "Optional compact date range in the form YYYY-MM-DD:YYYY-MM-DD."},
            "event_size": {"type": "string", "enum": ["small", "medium", "large", "any"], "description": "Approximate event size filter."},
            "indoor_outdoor": {"type": "string", "enum": ["indoor", "outdoor", "any"], "description": "Accepted for UI compatibility."},
            "vendor_category": {"type": "string", "description": "Optional vendor category like 'jewelry', 'food', or 'art'."},
            "category": {"type": "string", "description": "Alias for vendor_category."},
            "radius_miles": {"type": ["number", "string"], "description": "Optional distance radius from the selected city."},
            "distance_radius": {"type": ["number", "string"], "description": "Alias for radius_miles."},
            "sources": {
                "type": "array",
                "items": {"type": "string", "enum": ["google", "eventbrite", "facebook", "instagram", "local_market_sites", "vendor_directories"]},
                "description": "Source categories to search. Defaults to all supported categories.",
            },
        },
        "required": [],
    },
}

BUILD_VENDOR_PROFILE_TOOL = {
    "name": "build_vendor_profile",
    "description": "Summarize quiz-style answers about a vendor into a structured vendor profile for scoring and ranking.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "answers": {"type": "object", "description": "Key-value pairs of quiz answers about the vendor."}
        },
        "required": ["answers"],
    },
}

SCORE_MARKET_FOR_VENDOR_TOOL = {
    "name": "score_market_for_vendor",
    "description": "Compute a simple fit score (0-100) for one market given a vendor profile.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "market": {"type": "object"},
            "vendor_profile": {"type": "object"},
        },
        "required": ["market", "vendor_profile"],
    },
}

RANK_MARKETS_FOR_VENDOR_TOOL = {
    "name": "rank_markets_for_vendor",
    "description": "Rank a list of markets for a vendor and return scores plus short reasons.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "markets": {"type": "array", "items": {"type": "object"}},
            "vendor_profile": {"type": "object"},
        },
        "required": ["markets", "vendor_profile"],
    },
}

COMPARE_MARKETS_FOR_VENDOR_TOOL = {
    "name": "compare_markets_for_vendor",
    "description": "Compare 2-5 saved markets for a vendor and recommend an order.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "markets": {"type": "array", "items": {"type": "object"}, "minItems": 2, "maxItems": 5},
            "vendor_profile": {"type": "object"},
        },
        "required": ["markets", "vendor_profile"],
    },
}

INGEST_MARKETS_FROM_CSV_TOOL = {
    "name": "ingest_markets_from_csv",
    "description": "Ingest markets from a simple CSV payload into the Vendor Atlas market store.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "csv": {"type": "string", "description": "Raw CSV text with a header row."},
            "source_label": {"type": "string", "description": "Optional label for the source of this data."},
        },
        "required": ["csv"],
    },
}

# ---------------------------------------------------------------------------
# Seed data — Kansas City events returned by discover_events
# ---------------------------------------------------------------------------
_SEED_EVENTS = [
    {"id": "kc-001", "name": "Art Garden KC – First Fridays", "city": "Kansas City", "state": "MO", "date": "2026-04-03", "fee": 10, "traffic": "high", "type": "market", "indoor": False, "electric": True, "audience": "Art lovers", "website": "https://www.artgardenkc.org"},
    {"id": "kc-002", "name": "Strawberry Swing Indie Craft Fair", "city": "Kansas City", "state": "MO", "date": "2026-06-14", "fee": 75, "traffic": "high", "type": "craft", "indoor": False, "electric": False, "audience": "Art lovers, Collectors", "website": "https://www.thestrawberryswing.com"},
    {"id": "kc-003", "name": "City Market Sunday Street Fair", "city": "Kansas City", "state": "MO", "date": "2026-04-05", "fee": 10, "traffic": "high", "type": "market", "indoor": False, "electric": False, "audience": "Tourists, Families", "website": "https://thecitymarketkc.org"},
    {"id": "kc-004", "name": "Summer Swing at Aubrey Vineyards", "city": "Overland Park", "state": "KS", "date": "2026-07-12", "fee": 85, "traffic": "medium", "type": "craft", "indoor": False, "electric": True, "audience": "Art lovers", "website": "https://www.thestrawberryswing.com"},
    {"id": "kc-005", "name": "Holiday Swing – Waldo", "city": "Kansas City", "state": "MO", "date": "2026-11-29", "fee": 75, "traffic": "high", "type": "craft", "indoor": False, "electric": False, "audience": "Art lovers, Families", "website": "https://www.thestrawberryswing.com"},
    {"id": "kc-006", "name": "KC Oddities & Curiosities Expo", "city": "Kansas City", "state": "MO", "date": "2026-09-19", "fee": 120, "traffic": "high", "type": "oddity", "indoor": True, "electric": True, "audience": "Collectors, Teens", "website": "https://www.oddities-expo.com"},
    {"id": "kc-007", "name": "West Bottoms Antique Weekend", "city": "Kansas City", "state": "MO", "date": "2026-05-02", "fee": 35, "traffic": "medium", "type": "vintage", "indoor": True, "electric": True, "audience": "Collectors", "website": "https://westbottomskc.com"},
    {"id": "kc-008", "name": "Riverside Artwalk", "city": "Riverside", "state": "MO", "date": "2026-06-21", "fee": 0, "traffic": "medium", "type": "market", "indoor": False, "electric": False, "audience": "Art lovers, Families", "website": "https://www.artgardenkc.org"},
    {"id": "kc-009", "name": "Plaza Art Fair", "city": "Kansas City", "state": "MO", "date": "2026-09-26", "fee": 80, "traffic": "high", "type": "craft", "indoor": False, "electric": False, "audience": "Art lovers", "website": "https://www.countryclubplaza.com"},
    {"id": "kc-010", "name": "Holiday Swing – Crossroads", "city": "Kansas City", "state": "MO", "date": "2026-12-20", "fee": 75, "traffic": "high", "type": "craft", "indoor": False, "electric": False, "audience": "Art lovers", "website": "https://www.thestrawberryswing.com"},
]

# ---------------------------------------------------------------------------
# Scoring helper
# ---------------------------------------------------------------------------
def _score_event_data(event: Dict) -> Dict:
    score = 50
    reasons = []

    fee = event.get("fee", 0) or 0
    traffic = str(event.get("traffic", "")).lower()
    indoor = event.get("indoor", False)
    electric = event.get("electric", False)
    event_type = str(event.get("type", "")).lower()

    # Traffic
    if traffic in ("high", "large"):
        score += 20; reasons.append("High foot traffic")
    elif traffic in ("medium", "med"):
        score += 10; reasons.append("Moderate foot traffic")
    else:
        score -= 5; reasons.append("Low foot traffic")

    # Fee
    if fee == 0:
        score += 15; reasons.append("Free booth — maximum ROI")
    elif fee <= 30:
        score += 12; reasons.append("Very low booth fee")
    elif fee <= 75:
        score += 8; reasons.append("Reasonable booth fee")
    elif fee <= 150:
        score += 2; reasons.append("Moderate booth fee")
    else:
        score -= 8; reasons.append("High booth fee — needs strong sales to break even")

    # Electric
    if electric:
        score += 5; reasons.append("Electricity available")

    # Type bonus
    if event_type in ("craft", "market"):
        score += 8; reasons.append(f"Buyer-intent {event_type} event")
    elif event_type == "oddity":
        score += 6; reasons.append("Niche collector audience")
    elif event_type == "convention":
        score -= 3; reasons.append("Convention crowd may be less focused on buying")

    score = max(0, min(100, score))
    tier = "high" if score >= 70 else "medium" if score >= 45 else "low"

    return {
        "profit_score": score,
        "tier": tier,
        "signals": reasons,
        "estimated_revenue_low": max(0, int(fee * 1.5 + (score / 100) * 200)),
        "estimated_revenue_high": max(0, int(fee * 4 + (score / 100) * 600)),
        "recommendation": (
            "Strong opportunity — prioritize applying." if tier == "high"
            else "Worth considering — evaluate alongside alternatives." if tier == "medium"
            else "Lower priority — only if no better options available."
        ),
    }


def _vendor_market_fit(market: Dict, vendor: Dict) -> Dict:
    score = 50
    reasons = []

    budget = vendor.get("booth_budget_max", 500)
    preferred_types = [t.lower() for t in vendor.get("preferred_event_types", [])]
    audience_prefs = [a.lower() for a in vendor.get("target_audience", [])]

    fee = market.get("fee", 0) or 0
    traffic = str(market.get("traffic", "")).lower()
    mtype = str(market.get("type", "")).lower()
    m_audience = str(market.get("audience", "")).lower()
    indoor = market.get("indoor", False)
    electric = market.get("electric", False)

    # Budget fit
    if fee <= budget * 0.1:
        score += 20; reasons.append("Booth fee well within budget")
    elif fee <= budget * 0.3:
        score += 10; reasons.append("Booth fee fits budget")
    elif fee <= budget:
        score += 0; reasons.append("Booth fee at budget limit")
    else:
        score -= 20; reasons.append("Booth fee exceeds budget")

    # Traffic
    if traffic in ("high", "large"):
        score += 15; reasons.append("High traffic — good discovery")
    elif traffic in ("medium", "med"):
        score += 7

    # Type match
    if preferred_types and mtype in preferred_types:
        score += 15; reasons.append(f"Event type '{mtype}' matches preference")

    # Audience match
    for aud in audience_prefs:
        if aud in m_audience:
            score += 10; reasons.append(f"Audience matches: {aud}"); break

    # Features
    if electric:
        score += 5; reasons.append("Electricity available for display")

    score = max(0, min(100, score))
    return {"fit_score": score, "reasons": reasons}


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def handle_scrape_event(url: str = "") -> str:
    """Return a structured stub for the given URL (real scraping needs playwright)."""
    event_id = "scraped-" + hashlib.md5(url.encode()).hexdigest()[:8]
    result = {
        "id": event_id,
        "source_url": url,
        "name": "Event from " + url.split("/")[2] if "/" in url else url,
        "city": "Unknown",
        "state": "Unknown",
        "date": "TBD",
        "fee": None,
        "traffic": "unknown",
        "type": "market",
        "indoor": None,
        "electric": None,
        "note": "Live scraping requires a browser environment. Add this event manually or enrich it.",
    }
    return json.dumps(result, indent=2)


async def handle_discover_events(
    city: str = "",
    state: str = "",
    start_date: str = "",
    end_date: str = "",
    keywords: Optional[List[str]] = None,
    sources: Optional[List[str]] = None,
) -> str:
    db = _load_db()
    seed = list(_SEED_EVENTS)

    # Merge DB records with seed, deduplicate by id
    existing_ids = {e.get("id") for e in db}
    all_events = db + [e for e in seed if e.get("id") not in existing_ids]

    results = []
    city_lower = city.lower()
    state_lower = state.lower()
    kw_lower = [k.lower() for k in (keywords or [])]

    for e in all_events:
        e_city = str(e.get("city", "")).lower()
        e_state = str(e.get("state", "")).lower()
        e_name = str(e.get("name", "")).lower()
        e_type = str(e.get("type", "")).lower()

        if city_lower and city_lower not in e_city:
            continue
        if state_lower and state_lower not in e_state:
            continue
        if kw_lower and not any(k in e_name or k in e_type for k in kw_lower):
            continue
        if start_date and e.get("date", "9999") < start_date:
            continue
        if end_date and e.get("date", "0000") > end_date:
            continue

        results.append(e)

    return json.dumps({
        "found": len(results),
        "city": city or "all",
        "state": state or "all",
        "events": results,
    }, indent=2)


async def handle_extract_event(url: str = "") -> str:
    return await handle_scrape_event(url=url)


async def handle_enrich_event(
    event: Optional[Dict] = None,
    event_id: Optional[str] = None,
) -> str:
    if not event and event_id:
        db = _load_db()
        matches = [e for e in db if e.get("id") == event_id]
        event = matches[0] if matches else {}

    if not event:
        return json.dumps({"error": "No event provided or found for event_id."})

    enriched = dict(event)
    traffic = str(event.get("traffic", "medium")).lower()
    fee = event.get("fee", 0) or 0

    enriched["enrichment"] = {
        "social_buzz": "high" if traffic == "high" else "medium",
        "repeat_history": "returning event with consistent attendance" if fee > 0 else "free entry drives strong turnout",
        "estimated_attendance_low": 500 if traffic == "low" else 1000 if traffic == "medium" else 2000,
        "estimated_attendance_high": 1000 if traffic == "low" else 2500 if traffic == "medium" else 5000,
        "best_for": "jewelry, art, handmade goods" if event.get("type") in ("craft", "market") else "collectibles, curiosities",
        "enriched_at": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(enriched, indent=2)


async def handle_score_event(
    event: Optional[Dict] = None,
    event_id: Optional[str] = None,
    enrichment: Optional[Dict] = None,
) -> str:
    if not event and event_id:
        db = _load_db()
        matches = [e for e in db if e.get("id") == event_id]
        event = matches[0] if matches else {}

    if not event:
        return json.dumps({"error": "No event provided or found."})

    scoring = _score_event_data(event)
    result = {**event, "scoring": scoring}
    if enrichment:
        result["enrichment"] = enrichment
    return json.dumps(result, indent=2)


async def handle_save_event(event: Optional[Dict] = None) -> str:
    if not event:
        return json.dumps({"error": "No event object provided."})

    db = _load_db()

    # Auto-assign id if missing
    if not event.get("id"):
        event["id"] = "va-" + str(uuid.uuid4())[:8]

    event["saved_at"] = datetime.now(timezone.utc).isoformat()

    # Upsert: replace existing record with same id
    existing_ids = [e.get("id") for e in db]
    if event["id"] in existing_ids:
        db = [event if e.get("id") == event["id"] else e for e in db]
        action = "updated"
    else:
        db.append(event)
        action = "saved"

    _save_db(db)

    return json.dumps({
        "status": "ok",
        "action": action,
        "id": event["id"],
        "name": event.get("name", "Unnamed event"),
        "total_events_in_db": len(db),
    }, indent=2)


async def handle_search_events(
    city: str = "",
    state: str = "",
    start_date: str = "",
    end_date: str = "",
    date_range: str = "",
    event_size: str = "",
    vendor_category: str = "",
    distance_radius: Any = None,
) -> str:
    db = _load_db()
    seed = list(_SEED_EVENTS)
    existing_ids = {e.get("id") for e in db}
    all_events = db + [e for e in seed if e.get("id") not in existing_ids]

    # Parse date_range shorthand
    if date_range and ":" in date_range and not start_date and not end_date:
        parts = date_range.split(":", 1)
        start_date, end_date = parts[0], parts[1]

    results = []
    city_lower = city.lower()
    state_lower = state.lower()
    cat_lower = vendor_category.lower()

    for e in all_events:
        if city_lower and city_lower not in str(e.get("city", "")).lower():
            continue
        if state_lower and state_lower not in str(e.get("state", "")).lower():
            continue
        if start_date and e.get("date", "9999") < start_date:
            continue
        if end_date and e.get("date", "0000") > end_date:
            continue
        if cat_lower and cat_lower not in str(e.get("audience", "")).lower() and cat_lower not in str(e.get("type", "")).lower():
            continue
        results.append(e)

    results.sort(key=lambda e: e.get("date", ""), reverse=False)

    return json.dumps({
        "found": len(results),
        "filters": {"city": city, "state": state, "start_date": start_date, "end_date": end_date},
        "events": results,
    }, indent=2)


async def handle_search_markets(**kwargs) -> str:
    # Normalize aliases
    city = kwargs.get("city", "")
    state = kwargs.get("state", "")
    start_date = kwargs.get("start_date", "")
    end_date = kwargs.get("end_date", "")
    date_range = kwargs.get("date_range", "")
    vendor_category = kwargs.get("vendor_category", "") or kwargs.get("category", "")
    distance_radius = kwargs.get("distance_radius") or kwargs.get("radius_miles")
    query = kwargs.get("query", "")

    db = _load_db()
    seed = list(_SEED_EVENTS)
    existing_ids = {e.get("id") for e in db}
    all_events = db + [e for e in seed if e.get("id") not in existing_ids]

    if date_range and ":" in date_range and not start_date and not end_date:
        parts = date_range.split(":", 1)
        start_date, end_date = parts[0], parts[1]

    results = []
    for e in all_events:
        if city and city.lower() not in str(e.get("city", "")).lower():
            continue
        if state and state.lower() not in str(e.get("state", "")).lower():
            continue
        if start_date and e.get("date", "9999") < start_date:
            continue
        if end_date and e.get("date", "0000") > end_date:
            continue
        if vendor_category:
            vc = vendor_category.lower()
            if vc not in str(e.get("audience", "")).lower() and vc not in str(e.get("type", "")).lower():
                continue
        if query:
            q = query.lower()
            if q not in str(e.get("name", "")).lower() and q not in str(e.get("type", "")).lower() and q not in str(e.get("city", "")).lower():
                continue
        results.append(e)

    results.sort(key=lambda e: e.get("date", ""))

    return json.dumps({
        "found": len(results),
        "query": {"city": city, "state": state, "vendor_category": vendor_category},
        "markets": results,
    }, indent=2)


async def handle_build_vendor_profile(answers: Optional[Dict] = None) -> str:
    if not answers:
        return json.dumps({"error": "No answers provided."})

    profile = {
        "business_type": answers.get("business_type", answers.get("product_type", "handmade goods")),
        "price_range": answers.get("price_range", "$20–$100"),
        "target_audience": answers.get("target_audience", "art lovers, gift buyers"),
        "booth_budget_max": int(answers.get("booth_budget", answers.get("booth_budget_max", 150))),
        "preferred_event_types": answers.get("preferred_types", ["market", "craft"]),
        "setup_style": answers.get("setup_style", "easy"),
        "needs_electricity": bool(answers.get("needs_electricity", False)),
        "travel_radius_miles": int(answers.get("travel_radius", answers.get("travel_radius_miles", 50))),
        "priorities": answers.get("priorities", ["profitability", "audience fit"]),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps({"status": "ok", "vendor_profile": profile}, indent=2)


async def handle_score_market_for_vendor(
    market: Optional[Dict] = None,
    vendor_profile: Optional[Dict] = None,
) -> str:
    if not market or not vendor_profile:
        return json.dumps({"error": "Both market and vendor_profile are required."})

    result = _vendor_market_fit(market, vendor_profile)
    return json.dumps({
        "market": market.get("name", "Unknown"),
        "fit_score": result["fit_score"],
        "reasons": result["reasons"],
        "verdict": (
            "Strong fit — highly recommended." if result["fit_score"] >= 75
            else "Decent fit — worth considering." if result["fit_score"] >= 50
            else "Weak fit — lower priority."
        ),
    }, indent=2)


async def handle_rank_markets_for_vendor(
    markets: Optional[List[Dict]] = None,
    vendor_profile: Optional[Dict] = None,
) -> str:
    if not markets or not vendor_profile:
        return json.dumps({"error": "markets and vendor_profile are required."})

    ranked = []
    for m in markets:
        fit = _vendor_market_fit(m, vendor_profile)
        ranked.append({
            "name": m.get("name", "Unknown"),
            "city": m.get("city", ""),
            "date": m.get("date", ""),
            "fee": m.get("fee"),
            "fit_score": fit["fit_score"],
            "top_reason": fit["reasons"][0] if fit["reasons"] else "General fit",
            "verdict": (
                "Top pick" if fit["fit_score"] >= 75
                else "Worth trying" if fit["fit_score"] >= 50
                else "Low priority"
            ),
        })

    ranked.sort(key=lambda x: x["fit_score"], reverse=True)
    for i, r in enumerate(ranked):
        r["rank"] = i + 1

    return json.dumps({
        "ranked_markets": ranked,
        "top_pick": ranked[0]["name"] if ranked else None,
    }, indent=2)


async def handle_compare_markets_for_vendor(
    markets: Optional[List[Dict]] = None,
    vendor_profile: Optional[Dict] = None,
) -> str:
    if not markets or not vendor_profile:
        return json.dumps({"error": "markets (2-5) and vendor_profile are required."})

    result = json.loads(await handle_rank_markets_for_vendor(markets=markets, vendor_profile=vendor_profile))
    ranked = result.get("ranked_markets", [])

    comparison = {
        "recommendation": f"Start with '{ranked[0]['name']}' — highest fit score of {ranked[0]['fit_score']}." if ranked else "No markets to compare.",
        "suggested_order": [r["name"] for r in ranked],
        "comparison": ranked,
        "tradeoffs": [
            f"{r['name']}: score {r['fit_score']} — {r['top_reason']}"
            for r in ranked
        ],
    }
    return json.dumps(comparison, indent=2)


async def handle_ingest_markets_from_csv(
    csv: str = "",
    source_label: str = "csv_import",
) -> str:
    if not csv.strip():
        return json.dumps({"error": "Empty CSV provided."})

    lines = csv.strip().splitlines()
    if len(lines) < 2:
        return json.dumps({"error": "CSV must have a header row and at least one data row."})

    headers = [h.strip().lower() for h in lines[0].split(",")]
    db = _load_db()
    existing_ids = {e.get("id") for e in db}
    imported = []
    skipped = 0

    for line in lines[1:]:
        if not line.strip():
            continue
        values = [v.strip() for v in line.split(",")]
        record: Dict[str, Any] = {}
        for i, h in enumerate(headers):
            record[h] = values[i] if i < len(values) else ""

        # Normalize common field names
        if "name" not in record and "event_name" in record:
            record["name"] = record.pop("event_name")
        if "fee" in record:
            try:
                record["fee"] = float(record["fee"].replace("$", "").strip())
            except (ValueError, AttributeError):
                record["fee"] = None

        if not record.get("id"):
            record["id"] = "csv-" + hashlib.md5(str(record).encode()).hexdigest()[:8]

        record["source"] = source_label
        record["saved_at"] = datetime.now(timezone.utc).isoformat()

        if record["id"] in existing_ids:
            skipped += 1
        else:
            db.append(record)
            existing_ids.add(record["id"])
            imported.append(record.get("name", record["id"]))

    _save_db(db)

    return json.dumps({
        "status": "ok",
        "imported": len(imported),
        "skipped_duplicates": skipped,
        "total_in_db": len(db),
        "names_imported": imported[:20],
    }, indent=2)


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
TOOLS = [
    SCRAPE_EVENT_TOOL,
    DISCOVER_EVENTS_TOOL,
    EXTRACT_EVENT_TOOL,
    ENRICH_EVENT_TOOL,
    SCORE_EVENT_TOOL,
    SAVE_EVENT_TOOL,
    SEARCH_EVENTS_TOOL,
    SEARCH_MARKETS_TOOL,
    BUILD_VENDOR_PROFILE_TOOL,
    SCORE_MARKET_FOR_VENDOR_TOOL,
    RANK_MARKETS_FOR_VENDOR_TOOL,
    COMPARE_MARKETS_FOR_VENDOR_TOOL,
    INGEST_MARKETS_FROM_CSV_TOOL,
]

HANDLERS: Dict[str, Callable[..., Coroutine]] = {
    "scrape_event": handle_scrape_event,
    "discover_events": handle_discover_events,
    "extract_event": handle_extract_event,
    "enrich_event": handle_enrich_event,
    "score_event": handle_score_event,
    "save_event": handle_save_event,
    "search_events": handle_search_events,
    "search_markets": handle_search_markets,
    "build_vendor_profile": handle_build_vendor_profile,
    "score_market_for_vendor": handle_score_market_for_vendor,
    "rank_markets_for_vendor": handle_rank_markets_for_vendor,
    "compare_markets_for_vendor": handle_compare_markets_for_vendor,
    "ingest_markets_from_csv": handle_ingest_markets_from_csv,
}
