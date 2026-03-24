"""
Vendor Atlas — Calendar Integrations

Helpers for exporting events to standard calendar formats and
syncing with external calendar providers.

Google Calendar and Apple Calendar (via .ics) are supported.
Google Calendar sync is currently a placeholder — full OAuth
integration will be added when the AI infrastructure phase lands.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# ICS export (works for both Google Calendar and Apple Calendar import)
# ---------------------------------------------------------------------------

def export_event_to_ics(event: dict[str, Any]) -> str:
    """
    Convert a single event dict to a valid iCalendar (.ics) string.

    Accepts the event shape used by storage_events and storage_marketplace:
        id, name/title, date, description, location/city, apply_url
    """
    now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    uid = f"{event.get('id') or now_stamp}@vendoratlas"
    summary = _ics_text(str(event.get("name") or event.get("title") or "Event"))
    description_parts = []
    if event.get("description"):
        description_parts.append(str(event["description"]))
    if event.get("apply_url"):
        description_parts.append(f"Apply: {event['apply_url']}")
    description = _ics_text("\n".join(description_parts))
    location = _ics_text(str(event.get("location") or event.get("city") or ""))

    raw_date = str(event.get("date") or "")
    dtstart = _parse_date_ics(raw_date)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Vendor Atlas//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now_stamp}",
    ]

    if dtstart:
        lines.append(f"DTSTART;VALUE=DATE:{dtstart}")
        lines.append(f"DTEND;VALUE=DATE:{dtstart}")
    else:
        lines.append(f"DTSTART;VALUE=DATE:{now_stamp[:8]}")
        lines.append(f"DTEND;VALUE=DATE:{now_stamp[:8]}")

    lines.append(f"SUMMARY:{summary}")
    if description:
        lines.append(f"DESCRIPTION:{description}")
    if location:
        lines.append(f"LOCATION:{location}")
    lines += ["END:VEVENT", "END:VCALENDAR"]

    return "\r\n".join(lines)


def export_events_to_ics(events: list[dict[str, Any]], calendar_name: str = "Vendor Atlas Events") -> str:
    """
    Export multiple events into a single .ics calendar file.
    """
    now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    vevent_blocks: list[str] = []

    for event in events:
        uid = f"{event.get('id') or now_stamp}@vendoratlas"
        summary = _ics_text(str(event.get("name") or event.get("title") or "Event"))
        description_parts = []
        if event.get("description"):
            description_parts.append(str(event["description"]))
        if event.get("apply_url"):
            description_parts.append(f"Apply: {event['apply_url']}")
        description = _ics_text("\n".join(description_parts))
        location = _ics_text(str(event.get("location") or event.get("city") or ""))
        dtstart = _parse_date_ics(str(event.get("date") or "")) or now_stamp[:8]

        block_lines = [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART;VALUE=DATE:{dtstart}",
            f"DTEND;VALUE=DATE:{dtstart}",
            f"SUMMARY:{summary}",
        ]
        if description:
            block_lines.append(f"DESCRIPTION:{description}")
        if location:
            block_lines.append(f"LOCATION:{location}")
        block_lines.append("END:VEVENT")
        vevent_blocks.append("\r\n".join(block_lines))

    header = "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Vendor Atlas//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_ics_text(calendar_name)}",
    ])
    footer = "END:VCALENDAR"
    return header + "\r\n" + "\r\n".join(vevent_blocks) + "\r\n" + footer


# ---------------------------------------------------------------------------
# Google Calendar sync (placeholder)
# ---------------------------------------------------------------------------

def sync_google_calendar(user_id: int, events: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Placeholder for Google Calendar OAuth sync.

    Full implementation requires:
    1. OAuth2 flow (google-auth-oauthlib)
    2. Storing refresh tokens per user
    3. Calling the Google Calendar API events.insert endpoint

    For now, export .ics and let users import manually.
    """
    return {
        "ok": True,
        "synced": 0,
        "provider": "google",
        "message": (
            "Google Calendar sync is coming soon. "
            "In the meantime, export your events as .ics and import them into Google Calendar."
        ),
    }


def sync_apple_calendar(user_id: int, events: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Placeholder for Apple Calendar sync.

    Apple Calendar uses the same .ics standard — export the file and
    double-click it to import into Calendar.app on Mac or iPhone.
    """
    return {
        "ok": True,
        "synced": 0,
        "provider": "apple",
        "message": (
            "Export your events as .ics and open the file on your Mac or iPhone "
            "to add them to Apple Calendar."
        ),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ics_text(value: str) -> str:
    """Escape special characters for ICS text fields."""
    return (
        value
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _parse_date_ics(date_str: str) -> str | None:
    """Parse a date string into YYYYMMDD format for ICS DTSTART."""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y%m%d")
        except (ValueError, AttributeError):
            continue
    return None
