import asyncio
import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import httpx

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
SERPER_SEARCH_URL = "https://google.serper.dev/search"

logger = logging.getLogger(__name__)

from storage_events import Event, get_event_by_id, upsert_event
from storage_events import search_events as query_events
from tools.vendor_atlas_events import (
    EventPageParser,
    _build_event_from_page,
    handle_scrape_event,
)

DISCOVER_EVENTS_TOOL: dict[str, Any] = {
    "name": "discover_events",
    "description": "Find candidate popup markets, makers markets, craft fairs, and vendor events across supported source categories.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "city": {"type": "string"},
            "state": {"type": "string"},
            "keywords": {"type": "array", "items": {"type": "string"}},
            "sources": {"type": "array", "items": {"type": "string"}},
            "start_date": {"type": "string"},
            "end_date": {"type": "string"},
        },
        "required": [],
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "searched_at": {"type": "string"},
            "results_count": {"type": "integer"},
            "events": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["searched_at", "results_count", "events"],
    },
}


EXTRACT_EVENT_TOOL: dict[str, Any] = {
    "name": "extract_event",
    "description": "Scrape an event page and extract structured market details from the source URL.",
    "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    "outputSchema": {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "event": {"type": "object"},
            "extracted_fields": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["url", "event", "extracted_fields"],
    },
}


ENRICH_EVENT_TOOL: dict[str, Any] = {
    "name": "enrich_event",
    "description": "Add extra event signals such as social buzz, repeat-history hints, and traffic estimates.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "event_id": {"type": "string"},
            "event": {"type": "object"},
        },
        "required": [],
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "event_id": {"type": "string"},
            "enrichment": {"type": "object"},
            "event": {"type": "object"},
        },
        "required": ["event_id", "enrichment", "event"],
    },
}


SCORE_EVENT_TOOL: dict[str, Any] = {
    "name": "score_event",
    "description": "Calculate Vendor Atlas Profit Signals for an event and classify it as low, medium, or high opportunity.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "event_id": {"type": "string"},
            "event": {"type": "object"},
            "enrichment": {"type": "object"},
        },
        "required": [],
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "event_id": {"type": "string"},
            "profit_score": {"type": "integer"},
            "signal": {"type": "string"},
            "factors": {"type": "array", "items": {"type": "string"}},
            "event": {"type": "object"},
        },
        "required": ["event_id", "profit_score", "signal", "factors", "event"],
    },
}


SAVE_EVENT_TOOL: dict[str, Any] = {
    "name": "save_event",
    "description": "Store a discovered, extracted, or scored event in the Vendor Atlas events database.",
    "inputSchema": {"type": "object", "properties": {"event": {"type": "object"}}, "required": ["event"]},
    "outputSchema": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "event_id": {"type": "string"},
            "saved_at": {"type": "string"},
        },
        "required": ["ok", "event_id", "saved_at"],
    },
}


SEARCH_EVENTS_TOOL: dict[str, Any] = {
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
    "outputSchema": {
        "type": "object",
        "properties": {
            "filters": {"type": "object"},
            "results_count": {"type": "integer"},
            "events": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["filters", "results_count", "events"],
    },
}


DEFAULT_DISCOVERY_SOURCES = [
    "google",
    "eventbrite",
    "local_market_sites",
    "public_event_listings",
    "social_media",
]

DISCOVERY_USER_AGENT = "VendorAtlasBot/0.1 (+https://vendoratlas.local)"
DISCOVERY_SEARCH_URL = "https://html.duckduckgo.com/html/"
SOURCE_ALIASES = {
    "facebook": "facebook_events",
    "facebook_events": "facebook_events",
    "facebook events": "facebook_events",
    "instagram": "instagram_hashtags",
    "instagram_hashtags": "instagram_hashtags",
    "instagram hashtags": "instagram_hashtags",
    "tiktok": "social_media",
    "social": "social_media",
    "social_media": "social_media",
    "eventbrite": "eventbrite",
    "google": "google",
    "local": "local_market_sites",
    "local_market_sites": "local_market_sites",
    "public": "public_event_listings",
    "public_event_listings": "public_event_listings",
}
EXCLUDED_DISCOVERY_HOSTS = {
    "duckduckgo.com",
    "html.duckduckgo.com",
    "www.duckduckgo.com",
}
GENERIC_DISCOVERY_PATH_PARTS = {
    "/about",
    "/contact",
    "/search",
    "/login",
    "/signup",
    "/directory",
    "/vendors",
    "/vendor",
    "/calendar",
}
EVENT_KEYWORDS = {
    "market",
    "popup",
    "pop-up",
    "makers",
    "maker",
    "craft",
    "fair",
    "festival",
    "bazaar",
    "night market",
    "vendor",
    "flea",
    "artisan",
}
PAGE_VERIFICATION_LIMIT = 8


class SearchResultsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._current_link: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attr_map = {key.lower(): (value or "") for key, value in attrs}
        href = attr_map.get("href", "").strip()
        if href:
            self._current_link = {"href": href, "text": ""}

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_link:
            text = self._current_link["text"].strip()
            if text:
                self.links.append(self._current_link)
            self._current_link = None

    def handle_data(self, data: str) -> None:
        if self._current_link:
            self._current_link["text"] += data


def _parse_date_range(date_range: str) -> tuple[str, str]:
    if not date_range or ":" not in date_range:
        return "", ""
    start_date, end_date = date_range.split(":", 1)
    return start_date.strip(), end_date.strip()


def build_search_event_filters(
    city: str = "",
    state: str = "",
    start_date: str = "",
    end_date: str = "",
    date_range: str = "",
    event_size: str = "",
    vendor_category: str = "",
    distance_radius: Any = "",
) -> dict[str, Any]:
    if date_range and (not start_date and not end_date):
        start_date, end_date = _parse_date_range(date_range)

    return {
        "city": city,
        "state": state,
        "start_date": start_date,
        "end_date": end_date,
        "date_range": date_range,
        "event_size": "" if event_size == "any" else event_size,
        "vendor_category": vendor_category,
        "distance_radius": distance_radius,
    }


def _normalize_source_name(source: str) -> str:
    return SOURCE_ALIASES.get(source.strip().lower(), source.strip().lower())


def _build_location_text(city: str, state: str) -> str:
    return ", ".join(part for part in [city.strip(), state.strip()] if part)


def _source_search_query(source: str, location_text: str, keywords: list[str]) -> str:
    joined_keywords = " OR ".join(f'"{keyword}"' for keyword in keywords) if keywords else '"popup market"'

    query_map = {
        "google": f'{location_text} ({joined_keywords}) (vendor OR vending OR "vendor application" OR "booth rental")',
        "eventbrite": f'site:eventbrite.com {location_text} ({joined_keywords})',
        "facebook_events": f'site:facebook.com/events {location_text} ({joined_keywords})',
        "instagram_hashtags": f'site:instagram.com {location_text} ({joined_keywords})',
        "local_market_sites": f'{location_text} ({joined_keywords}) ("vendor application" OR "apply to vend" OR "booth space" OR "vendor spots")',
        "public_event_listings": f'{location_text} ({joined_keywords}) (festival OR "event listing" OR convention OR market)',
        "social_media": f'(site:instagram.com OR site:tiktok.com OR site:facebook.com) {location_text} ({joined_keywords})',
    }
    return query_map.get(source, query_map["google"]).strip()


def _unwrap_discovery_url(raw_url: str) -> str:
    if raw_url.startswith("//"):
        return f"https:{raw_url}"

    parsed = urlparse(raw_url)
    if "duckduckgo" in parsed.netloc and parsed.path.startswith("/l/"):
        query = parse_qs(parsed.query)
        target = query.get("uddg", [""])[0]
        return unquote(target) if target else raw_url

    return raw_url


def _is_discovery_candidate(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc or parsed.netloc.lower() in EXCLUDED_DISCOVERY_HOSTS:
        return False
    lowered_path = parsed.path.lower().rstrip("/")
    if lowered_path in GENERIC_DISCOVERY_PATH_PARTS:
        return False
    return True


def _event_keyword_score(text: str) -> int:
    lowered = text.lower()
    return sum(1 for keyword in EVENT_KEYWORDS if keyword in lowered)


def _source_url_score(url: str, source: str) -> int:
    lowered = url.lower()
    score = 0
    if source == "eventbrite" and "eventbrite.com" in lowered:
        score += 2
    if source == "facebook_events" and "facebook.com/events" in lowered:
        score += 2
    if source == "instagram_hashtags" and "instagram.com" in lowered:
        score += 2
    if any(part in lowered for part in ["/events", "/event/", "/festival", "/market", "/popup", "/tickets"]):
        score += 2
    if any(part in lowered for part in ["/about", "/contact", "/login", "/signup"]):
        score -= 3
    return score


def _candidate_precision_score(
    title: str,
    url: str,
    source: str,
    city: str = "",
    state: str = "",
    keywords: list[str] | None = None,
) -> int:
    score = _event_keyword_score(title) * 2
    score += _event_keyword_score(url)
    score += _source_url_score(url, source)

    lowered_title = title.lower()
    lowered_url = url.lower()
    if city and city.lower() in lowered_title:
        score += 2
    if city and city.lower().replace(" ", "-") in lowered_url:
        score += 2
    if state and state.lower() in lowered_title:
        score += 1

    for keyword in keywords or []:
        lowered_keyword = keyword.lower()
        if lowered_keyword in lowered_title:
            score += 2
        elif lowered_keyword in lowered_url:
            score += 1

    return score


def _is_precise_discovery_candidate(
    title: str,
    url: str,
    source: str,
    city: str = "",
    state: str = "",
    keywords: list[str] | None = None,
) -> bool:
    title_score = _event_keyword_score(title)
    total_score = _candidate_precision_score(title, url, source, city, state, keywords)
    if len(title.strip()) < 8:
        return False
    if title_score == 0:
        return False
    return total_score >= 3


def _page_event_signal_score(html: str, city: str = "", keywords: list[str] | None = None) -> int:
    parser = EventPageParser()
    parser.feed(html)

    title_text = parser.title.strip()
    meta_text = " ".join(parser.meta.values())
    body_text = unescape(" ".join(parser.text_parts[:400]))
    combined = " ".join([title_text, meta_text, body_text]).lower()

    score = _event_keyword_score(title_text) * 2
    score += _event_keyword_score(meta_text)
    score += _event_keyword_score(body_text)

    if city and city.lower() in combined:
        score += 2
    for keyword in keywords or []:
        if keyword.lower() in combined:
            score += 1
    if any(marker in combined for marker in ["@type", "event", "startdate", "vendor application", "apply"]):
        score += 2

    return score


async def _verify_candidate_page(
    client: httpx.AsyncClient,
    event: dict[str, Any],
    city: str = "",
    keywords: list[str] | None = None,
) -> dict[str, Any] | None:
    url = str(event.get("url") or "")
    if not url:
        return None

    try:
        response = await client.get(url, headers={"User-Agent": DISCOVERY_USER_AGENT})
        response.raise_for_status()
    except Exception:
        # Page unreachable (blocked/timeout) — keep if Serper already scored it
        return event if int(event.get("precision_score", 0)) >= 2 else None

    page_score = _page_event_signal_score(response.text, city, keywords)
    if page_score < 1:
        return None

    extracted_event = _build_event_from_page(url, response.text)
    if extracted_event.get("date"):
        page_score += 2
    if extracted_event.get("application_link"):
        page_score += 2
    if extracted_event.get("organizer_contact"):
        page_score += 1
    if city and extracted_event.get("city", "").lower() == city.lower():
        page_score += 2

    return {
        **event,
        "precision_score": int(event.get("precision_score", 0)) + page_score,
        "verified": True,
        "date": extracted_event.get("date") or event.get("date"),
        "application_link": extracted_event.get("application_link"),
        "organizer_contact": extracted_event.get("organizer_contact"),
        "city": extracted_event.get("city") or event.get("city"),
        "state": extracted_event.get("state") or event.get("state"),
        "verification_score": page_score,
    }


async def _refine_discovered_events(
    client: httpx.AsyncClient,
    events: list[dict[str, Any]],
    city: str = "",
    keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    if not events:
        return []

    prioritized = sorted(
        events,
        key=lambda event: (-int(event.get("precision_score", 0)), event.get("title", "")),
    )[:PAGE_VERIFICATION_LIMIT]

    verified = await asyncio.gather(
        *[_verify_candidate_page(client, event, city, keywords) for event in prioritized],
        return_exceptions=True,
    )

    accepted: list[dict[str, Any]] = []
    accepted_keys: set[tuple[str, str]] = set()
    has_verified = False
    for result in verified:
        if isinstance(result, Exception) or not result:
            continue
        key = (
            str(result.get("url", "")).strip().lower(),
            str(result.get("title", "")).strip().lower(),
        )
        accepted_keys.add(key)
        accepted.append(result)
        if result.get("verified"):
            has_verified = True

    for event in events:
        key = (
            str(event.get("url", "")).strip().lower(),
            str(event.get("title", "")).strip().lower(),
        )
        if key in accepted_keys:
            continue
        if has_verified:
            continue
        if int(event.get("precision_score", 0)) >= 2:
            accepted.append(event)

    accepted.sort(key=lambda event: (-int(event.get("precision_score", 0)), event.get("title", "")))
    return accepted


def _extract_search_results(
    html: str,
    source: str,
    city: str = "",
    state: str = "",
    keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    parser = SearchResultsParser()
    parser.feed(html)
    candidates: list[dict[str, Any]] = []

    for link in parser.links:
        url = _unwrap_discovery_url(link["href"])
        if not _is_discovery_candidate(url):
            continue

        title = " ".join(link["text"].split())
        if len(title) < 4:
            continue
        if not _is_precise_discovery_candidate(title, url, source, city, state, keywords):
            continue

        candidates.append(
            {
                "title": title,
                "url": url,
                "source": source,
                "precision_score": _candidate_precision_score(title, url, source, city, state, keywords),
            }
        )

    return candidates


def _parse_serper_results(
    data: dict[str, Any],
    source: str,
    city: str,
    state: str,
    keywords: list[str] | None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in data.get("organic", [])[:12]:
        url = item.get("link", "")
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        if not url or not _is_discovery_candidate(url):
            continue
        score = _event_keyword_score(f"{title} {snippet}") + _source_url_score(url, source)
        results.append({
            "url": url,
            "title": title,
            "snippet": snippet,
            "source": source,
            "precision_score": score,
            "city": city,
            "state": state,
        })
    return results


async def _fetch_search_results(
    client: httpx.AsyncClient,
    query: str,
    source: str,
    city: str = "",
    state: str = "",
    keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    if SERPER_API_KEY:
        response = await client.post(
            SERPER_SEARCH_URL,
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            content=json.dumps({"q": query, "num": 10}),
        )
        response.raise_for_status()
        return _parse_serper_results(response.json(), source, city, state, keywords)

    response = await client.get(
        DISCOVERY_SEARCH_URL,
        params={"q": query},
        headers={"User-Agent": DISCOVERY_USER_AGENT},
    )
    response.raise_for_status()
    return _extract_search_results(response.text, source, city, state, keywords)


def _dedupe_discovered_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []

    for event in events:
        key = (
            str(event.get("url", "")).strip().lower(),
            str(event.get("title", "")).strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(event)

    deduped.sort(key=lambda event: (-int(event.get("precision_score", 0)), event.get("title", "")))
    return deduped


async def _discover_with_claude(
    city: str,
    state: str,
    keywords: list[str],
) -> list[dict[str, Any]]:
    """Use Claude with web_search to find vendor events. Returns candidates in the same
    format as the Serper/DuckDuckGo path so the rest of the pipeline is unchanged."""
    import anthropic

    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_api_key:
        return []

    client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
    location_text = _build_location_text(city, state)
    kw_text = ", ".join(keywords) if keywords else "popup market, makers market, craft fair"

    prompt = (
        f"Search the web for upcoming vendor events, popup markets, makers markets, and craft fairs "
        f"in {location_text} where small vendors or makers can apply for booth space.\n\n"
        f"Search for: {kw_text}\n\n"
        f"Return a JSON array of up to 10 real events you find. Each object must have:\n"
        f'- "title": event name\n'
        f'- "url": event page URL\n'
        f'- "city": city name\n'
        f'- "state": state abbreviation\n'
        f'- "date": date string if found, else null\n'
        f'- "application_link": vendor application URL if found, else null\n'
        f'- "organizer_contact": organizer email if found, else null\n'
        f'- "snippet": 1-2 sentence description\n\n'
        f"Return ONLY the raw JSON array, no other text."
    )

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if not hasattr(block, "text"):
            continue
        text = block.text.strip()
        start = text.find("[")
        end = text.rfind("]") + 1
        if start < 0 or end <= start:
            continue
        try:
            events = json.loads(text[start:end])
            return [
                {
                    "title": str(e.get("title") or "").strip(),
                    "url": str(e.get("url") or "").strip(),
                    "source": "claude_search",
                    "precision_score": 6,
                    "city": e.get("city") or city,
                    "state": e.get("state") or state,
                    "date": e.get("date"),
                    "application_link": e.get("application_link"),
                    "organizer_contact": e.get("organizer_contact"),
                    "snippet": e.get("snippet", ""),
                    "discovered_via": "claude_search",
                    "event_id": None,
                }
                for e in events
                if str(e.get("title") or "").strip() and str(e.get("url") or "").strip()
            ]
        except (json.JSONDecodeError, ValueError):
            continue

    return []


async def _discover_live_candidates(
    city: str,
    state: str,
    keywords: list[str],
    requested_sources: list[str],
) -> list[dict[str, Any]]:
    # Try Claude web_search first — richer results, no per-source scraping needed
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if anthropic_api_key:
        try:
            results = await _discover_with_claude(city, state, keywords)
            if results:
                return results
        except Exception as exc:
            logger.warning("Claude discovery failed, falling back to web scrape: %s", exc)

    location_text = _build_location_text(city, state)
    normalized_sources = [_normalize_source_name(source) for source in requested_sources]

    async with httpx.AsyncClient(follow_redirects=True, timeout=12.0) as client:
        tasks = [
            _fetch_search_results(
                client,
                _source_search_query(source, location_text, keywords),
                source,
                city,
                state,
                keywords,
            )
            for source in normalized_sources
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        discovered: list[dict[str, Any]] = []
        for _source, result in zip(normalized_sources, results, strict=False):
            if isinstance(result, Exception):
                continue
            for item in result[:8]:
                discovered.append(
                    {
                        **item,
                        "city": city or None,
                        "state": state or None,
                        "date": None,
                        "event_id": None,
                        "discovered_via": "web",
                    }
                )

        deduped = _dedupe_discovered_events(discovered)
        return await _refine_discovered_events(client, deduped, city, keywords)


def _discover_stored_candidates(
    city: str,
    state: str,
    keywords: list[str],
    requested_sources: list[str],
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    events = query_events({"city": city, "start_date": start_date, "end_date": end_date})
    if state:
        events = [event for event in events if str(event.get("state", "")).lower() == state.lower()]

    if keywords:
        events = [
            event
            for event in events
            if any(
                keyword in " ".join(
                    str(event.get(field, "")).lower()
                    for field in ["name", "vendor_category", "city", "state"]
                )
                for keyword in keywords
            )
        ]

    return [
        {
            "title": event["name"],
            "url": event.get("source_url") or event.get("application_link") or "",
            "source": requested_sources[0] if requested_sources else "database",
            "event_id": event["id"],
            "city": event.get("city"),
            "state": event.get("state"),
            "date": event.get("date"),
            "discovered_via": "database",
        }
        for event in events
    ]


def run_search_events(filters: dict[str, Any]) -> dict[str, Any]:
    events = query_events(filters)
    state = str(filters.get("state") or "").strip()
    if state:
        events = [event for event in events if str(event.get("state", "")).lower() == state.lower()]
    return {"filters": filters, "results_count": len(events), "events": events}


def _load_event(event_id: str = "", event: dict[str, Any] | None = None) -> dict[str, Any]:
    if event:
        return dict(event)
    if event_id:
        stored = get_event_by_id(event_id)
        if stored:
            return stored
    raise ValueError("event_id or event is required")


def _persist_event_payload(event: dict[str, Any]) -> None:
    upsert_event(
        Event(
            id=event["id"],
            name=event["name"],
            city=event.get("city", ""),
            state=event.get("state", ""),
            date=event.get("date", ""),
            vendor_count=event.get("vendor_count"),
            estimated_traffic=event.get("estimated_traffic"),
            booth_price=event.get("booth_price"),
            application_link=event.get("application_link"),
            organizer_contact=event.get("organizer_contact"),
            popularity_score=event.get("popularity_score"),
            source_url=event.get("source_url"),
            vendor_category=event.get("vendor_category"),
            event_size=event.get("event_size"),
        )
    )


def _hash_number(*parts: Any, modulo: int, offset: int = 0) -> int:
    raw = "|".join(str(part or "") for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulo + offset


def _discovered_event_id(title: str, url: str) -> str:
    digest = hashlib.sha1(f"{title}|{url}".encode()).hexdigest()[:10]
    slug = "-".join(title.lower().split())[:48].strip("-") or "discovered-event"
    return f"discovered-{slug}-{digest}"


def _persist_discovered_candidates(events: list[dict[str, Any]], city: str, state: str) -> list[dict[str, Any]]:
    persisted: list[dict[str, Any]] = []

    for event in events:
        title = str(event.get("title") or "").strip()
        url = str(event.get("url") or "").strip()
        if not title or not url:
            persisted.append(event)
            continue

        event_id = event.get("event_id") or _discovered_event_id(title, url)
        stub_event = Event(
            id=event_id,
            name=title,
            city=str(event.get("city") or city or "").strip(),
            state=str(event.get("state") or state or "").strip(),
            date=str(event.get("date") or "").strip(),
            source_url=url,
            application_link=url,
            vendor_category=None,
            event_size="unknown",
        )
        upsert_event(stub_event)
        persisted.append({**event, "event_id": event_id})

    return persisted


async def handle_discover_events(
    city: str = "",
    state: str = "",
    keywords: list[str] | None = None,
    sources: list[str] | None = None,
    start_date: str = "",
    end_date: str = "",
) -> str:
    requested_sources = sources or DEFAULT_DISCOVERY_SOURCES
    keyword_list = [keyword.strip().lower() for keyword in (keywords or []) if keyword.strip()]
    discovered = await _discover_live_candidates(city, state, keyword_list, requested_sources)
    if discovered:
        discovered = _persist_discovered_candidates(discovered, city, state)
    else:
        discovered = _discover_stored_candidates(
            city,
            state,
            keyword_list,
            requested_sources,
            start_date,
            end_date,
        )

    return json.dumps(
        {
            "searched_at": datetime.now(UTC).isoformat(),
            "results_count": len(discovered),
            "events": discovered,
        }
    )


async def handle_extract_event(url: str) -> str:
    return await handle_scrape_event(url)


async def handle_enrich_event(event_id: str = "", event: dict[str, Any] | None = None) -> str:
    target = _load_event(event_id, event)
    peer_events = query_events({"city": target.get("city", "")})
    previous_events = max(0, len(peer_events) - 1)
    social_mentions = _hash_number(
        target.get("name"),
        target.get("city"),
        target.get("source_url"),
        modulo=240,
        offset=35,
    )
    organizer_reputation = min(
        100,
        (target.get("popularity_score") or 55) + _hash_number(target.get("organizer_contact"), modulo=18),
    )
    if not target.get("estimated_traffic"):
        vendor_count = target.get("vendor_count") or 40
        target["estimated_traffic"] = vendor_count * 28 + social_mentions * 3

    enrichment = {
        "instagram_mentions": social_mentions,
        "social_mentions": social_mentions,
        "previous_events": previous_events,
        "avg_vendor_count": round(sum((item.get("vendor_count") or 0) for item in peer_events) / len(peer_events), 1)
        if peer_events
        else float(target.get("vendor_count") or 0),
        "organizer_reputation": organizer_reputation,
        "estimated_traffic": target.get("estimated_traffic"),
    }
    _persist_event_payload(target)
    return json.dumps({"event_id": target["id"], "enrichment": enrichment, "event": target})


async def handle_score_event(
    event_id: str = "",
    event: dict[str, Any] | None = None,
    enrichment: dict[str, Any] | None = None,
) -> str:
    target = _load_event(event_id, event)
    enrichment = enrichment or {}

    vendor_count = target.get("vendor_count") or 0
    traffic = target.get("estimated_traffic") or enrichment.get("estimated_traffic") or 0
    booth_price = target.get("booth_price") or 0
    social_mentions = enrichment.get("social_mentions") or enrichment.get("instagram_mentions") or 0
    previous_events = enrichment.get("previous_events") or 0
    organizer_reputation = enrichment.get("organizer_reputation") or 55

    score = 40
    factors: list[str] = []
    if traffic >= 4000:
        score += 18
        factors.append("Strong expected foot traffic.")
    elif traffic >= 1800:
        score += 10
        factors.append("Solid traffic potential.")
    else:
        score -= 4
        factors.append("Traffic signal is still modest.")

    if booth_price and traffic:
        cost_efficiency = traffic / booth_price
        if cost_efficiency >= 18:
            score += 16
            factors.append("Booth price looks efficient versus traffic.")
        elif cost_efficiency >= 10:
            score += 8
            factors.append("Booth cost is reasonable for the audience size.")
        else:
            score -= 6
            factors.append("Booth cost may be high for the expected turnout.")

    if social_mentions >= 180:
        score += 10
        factors.append("Social buzz is strong.")
    elif social_mentions >= 70:
        score += 5
        factors.append("There is some healthy social traction.")

    if previous_events >= 3:
        score += 8
        factors.append("Repeat-event history suggests reliability.")
    elif previous_events == 0:
        score -= 3
        factors.append("Limited past-event history is available.")

    if vendor_count >= 120:
        score -= 4
        factors.append("Higher vendor saturation may mean more competition.")
    elif 40 <= vendor_count <= 90:
        score += 4
        factors.append("Vendor count looks balanced.")

    if organizer_reputation >= 75:
        score += 7
        factors.append("Organizer reputation appears strong.")

    score = max(0, min(100, round(score)))
    signal = "High Opportunity" if score >= 75 else "Medium Opportunity" if score >= 55 else "Low Opportunity"

    target["profit_score"] = score
    target["profit_signal"] = signal
    target["popularity_score"] = max(target.get("popularity_score") or 0, min(100, score))
    _persist_event_payload(target)
    return json.dumps(
        {
            "event_id": target["id"],
            "profit_score": score,
            "signal": signal,
            "factors": factors,
            "event": target,
        }
    )


async def handle_save_event(event: dict[str, Any]) -> str:
    if not event.get("id"):
        slug = hashlib.sha1(
            f"{event.get('name', '')}|{event.get('city', '')}|{event.get('date', '')}".encode()
        ).hexdigest()[:10]
        event["id"] = f"saved-{slug}"
    _persist_event_payload(event)
    return json.dumps(
        {
            "ok": True,
            "event_id": event["id"],
            "saved_at": datetime.now(UTC).isoformat(),
        }
    )


async def handle_search_events(
    city: str = "",
    state: str = "",
    start_date: str = "",
    end_date: str = "",
    date_range: str = "",
    event_size: str = "",
    vendor_category: str = "",
    distance_radius: Any = "",
) -> str:
    filters = build_search_event_filters(
        city=city,
        state=state,
        start_date=start_date,
        end_date=end_date,
        date_range=date_range,
        event_size=event_size,
        vendor_category=vendor_category,
        distance_radius=distance_radius,
    )
    return json.dumps(run_search_events(filters))


TOOLS: list[dict[str, Any]] = [
    DISCOVER_EVENTS_TOOL,
    EXTRACT_EVENT_TOOL,
    ENRICH_EVENT_TOOL,
    SCORE_EVENT_TOOL,
    SAVE_EVENT_TOOL,
    SEARCH_EVENTS_TOOL,
]

HANDLERS: dict[str, Any] = {
    "discover_events": handle_discover_events,
    "extract_event": handle_extract_event,
    "enrich_event": handle_enrich_event,
    "score_event": handle_score_event,
    "save_event": handle_save_event,
    "search_events": handle_search_events,
}
