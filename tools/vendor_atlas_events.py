import hashlib
import json
import re
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from storage_events import Event, upsert_event

SCRAPE_EVENT_TOOL: dict[str, Any] = {
    "name": "scrape_event",
    "description": "Scrape an event page and extract structured vendor-market details such as date, booth price, organizer contact, and application link.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Event page URL to scrape.",
            },
        },
        "required": ["url"],
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "event": {
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
                },
                "required": ["id", "name", "city", "state", "date"],
            },
            "extracted_fields": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["url", "event", "extracted_fields"],
    },
}


class EventPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.meta: dict[str, str] = {}
        self.links: list[dict[str, str]] = []
        self.json_ld_blocks: list[str] = []
        self._capture_title = False
        self._capture_script = False
        self._script_type = ""
        self._script_parts: list[str] = []
        self._current_link: dict[str, str] | None = None
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): (value or "") for key, value in attrs}
        if tag == "title":
            self._capture_title = True
        elif tag == "meta":
            key = attr_map.get("property") or attr_map.get("name")
            value = attr_map.get("content")
            if key and value:
                self.meta[key.lower()] = value.strip()
        elif tag == "a":
            self._current_link = {"href": attr_map.get("href", "").strip(), "text": ""}
        elif tag == "script":
            self._capture_script = True
            self._script_type = attr_map.get("type", "").lower()
            self._script_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._capture_title = False
        elif tag == "a" and self._current_link:
            self.links.append(self._current_link)
            self._current_link = None
        elif tag == "script":
            if self._capture_script and "ld+json" in self._script_type:
                block = "".join(self._script_parts).strip()
                if block:
                    self.json_ld_blocks.append(block)
            self._capture_script = False
            self._script_type = ""
            self._script_parts = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if self._capture_title and text:
            self.title += text
        if self._current_link and text:
            self._current_link["text"] += (" " if self._current_link["text"] else "") + text
        if self._capture_script:
            self._script_parts.append(data)
        if text:
            self.text_parts.append(text)


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "event"


def _event_size(vendor_count: int | None) -> str:
    if vendor_count is None:
        return "unknown"
    if vendor_count < 50:
        return "small"
    if vendor_count < 100:
        return "medium"
    return "large"


def _extract_json_ld(parser: EventPageParser) -> dict[str, Any]:
    for raw_block in parser.json_ld_blocks:
        try:
            payload = json.loads(raw_block)
        except json.JSONDecodeError:
            continue

        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type")
            if item_type == "Event" or (isinstance(item_type, list) and "Event" in item_type):
                return item
            graph = item.get("@graph")
            if isinstance(graph, list):
                for graph_item in graph:
                    if isinstance(graph_item, dict):
                        graph_type = graph_item.get("@type")
                        if graph_type == "Event" or (
                            isinstance(graph_type, list) and "Event" in graph_type
                        ):
                            return graph_item
    return {}


def _normalize_date(value: Any) -> str:
    if not value:
        return ""
    text = str(value).strip()
    return text[:10] if len(text) >= 10 else text


def _extract_city_state(text: str) -> tuple[str, str]:
    patterns = [
        r"\b([A-Z][a-zA-Z .'-]+),\s*([A-Z]{2})\b",
        r"\b([A-Z][a-zA-Z .'-]+),\s*([A-Z][a-z]+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip(), match.group(2).strip()
    return "", ""


def _extract_first_int(patterns: list[str], text: str) -> int | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def _extract_booth_price(text: str) -> float | None:
    patterns = [
        r"booth(?:\s+fee|\s+price)?[^$]{0,40}\$([0-9]+(?:\.[0-9]{2})?)",
        r"vendor\s+fee[^$]{0,40}\$([0-9]+(?:\.[0-9]{2})?)",
        r"application\s+fee[^$]{0,40}\$([0-9]+(?:\.[0-9]{2})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _extract_email(text: str) -> str:
    match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, flags=re.IGNORECASE)
    return match.group(0) if match else ""


def _extract_application_link(parser: EventPageParser, base_url: str) -> str:
    for link in parser.links:
        href = link.get("href", "")
        text = link.get("text", "")
        haystack = f"{text} {href}".lower()
        if any(keyword in haystack for keyword in ["apply", "vendor", "booth", "register"]):
            return urljoin(base_url, href)
    return ""


def _build_event_from_page(url: str, html: str) -> dict[str, Any]:
    parser = EventPageParser()
    parser.feed(html)
    full_text = unescape(" ".join(parser.text_parts))
    json_ld = _extract_json_ld(parser)

    name = (
        str(json_ld.get("name") or "").strip()
        or parser.meta.get("og:title", "").strip()
        or parser.meta.get("twitter:title", "").strip()
        or parser.title.strip()
    )

    location = json_ld.get("location", {}) if isinstance(json_ld, dict) else {}
    address = location.get("address", {}) if isinstance(location, dict) else {}
    city = str(address.get("addressLocality") or "").strip()
    state = str(address.get("addressRegion") or "").strip()
    if not city or not state:
        fallback_city, fallback_state = _extract_city_state(full_text)
        city = city or fallback_city
        state = state or fallback_state

    date = _normalize_date(json_ld.get("startDate"))
    vendor_count = _extract_first_int(
        [
            r"([0-9][0-9,]*)\s+vendors?\b",
            r"vendors?:\s*([0-9][0-9,]*)",
        ],
        full_text,
    )
    estimated_traffic = _extract_first_int(
        [
            r"([0-9][0-9,]*)\+?\s+(?:attendees|visitors|guests)\b",
            r"estimated\s+traffic[^0-9]{0,20}([0-9][0-9,]*)",
            r"traffic[^0-9]{0,20}([0-9][0-9,]*)",
        ],
        full_text,
    )
    booth_price = _extract_booth_price(full_text)
    organizer_contact = _extract_email(full_text)
    application_link = _extract_application_link(parser, url)
    popularity_score = _extract_first_int(
        [
            r"popularity[^0-9]{0,20}([0-9]{1,3})",
            r"score[^0-9]{0,20}([0-9]{1,3})",
        ],
        full_text,
    )

    event_id_source = name or url
    event_id = f"scraped-{_slugify(event_id_source)}-{hashlib.sha1(url.encode('utf-8')).hexdigest()[:8]}"

    event = {
        "id": event_id,
        "name": name or "Untitled Event",
        "city": city,
        "state": state,
        "date": date,
        "vendor_count": vendor_count,
        "estimated_traffic": estimated_traffic,
        "booth_price": booth_price,
        "application_link": application_link or None,
        "organizer_contact": organizer_contact or None,
        "popularity_score": popularity_score,
        "source_url": url,
        "vendor_category": None,
        "event_size": _event_size(vendor_count),
    }
    return event


async def _fetch_page(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme in {"", "file"}:
        path = parsed.path if parsed.scheme == "file" else url
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        response = await client.get(url, headers={"User-Agent": "VendorAtlasBot/0.1"})
        response.raise_for_status()
        return response.text


def _extracted_fields(event: dict[str, Any]) -> list[str]:
    return [key for key, value in event.items() if value not in (None, "", [])]


async def handle_scrape_event(url: str) -> str:
    html = await _fetch_page(url)
    event = _build_event_from_page(url, html)

    upsert_event(
        Event(
            id=event["id"],
            name=event["name"],
            city=event["city"],
            state=event["state"],
            date=event["date"],
            vendor_count=event["vendor_count"],
            estimated_traffic=event["estimated_traffic"],
            booth_price=event["booth_price"],
            application_link=event["application_link"],
            organizer_contact=event["organizer_contact"],
            popularity_score=event["popularity_score"],
            source_url=event["source_url"],
            vendor_category=event["vendor_category"],
            event_size=event["event_size"],
        )
    )

    payload = {
        "url": url,
        "event": event,
        "extracted_fields": _extracted_fields(event),
    }
    return json.dumps(payload)


TOOLS: list[dict[str, Any]] = [SCRAPE_EVENT_TOOL]

HANDLERS: dict[str, Any] = {
    "scrape_event": handle_scrape_event,
}
