"""
Vendor Atlas — Google Calendar sync

Uses Google's OAuth 2.0 flow and the Calendar REST API via httpx.
No google-auth libraries needed — just standard HTTP calls.

Required env vars:
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    APP_BASE_URL     (e.g. https://popshop-finder-mcp.onrender.com)

Scopes requested:
    https://www.googleapis.com/auth/calendar
    https://www.googleapis.com/auth/calendar.events

Usage:
    from google_calendar_sync import (
        get_auth_url,
        exchange_code_for_tokens,
        refresh_access_token,
        create_google_event,
        update_google_event,
        delete_google_event,
        fetch_google_busy_times,
        parse_busy_windows,
    )
"""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger("vendor-atlas.gcal")

# ── Constants ─────────────────────────────────────────────────────────────────

_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
_CAL_BASE  = "https://www.googleapis.com/calendar/v3"
_SCOPES    = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]


# ── Config helpers ─────────────────────────────────────────────────────────────

def _client_id() -> str:
    v = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    if not v:
        raise RuntimeError("GOOGLE_CLIENT_ID env var is not set.")
    return v


def _client_secret() -> str:
    v = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    if not v:
        raise RuntimeError("GOOGLE_CLIENT_SECRET env var is not set.")
    return v


def _redirect_uri() -> str:
    base = os.environ.get("APP_BASE_URL", "http://localhost:3000").rstrip("/")
    return f"{base}/api/calendar/google/callback"


def is_configured() -> bool:
    """Return True if Google Calendar credentials are present in env."""
    return bool(
        os.environ.get("GOOGLE_CLIENT_ID", "").strip()
        and os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    )


# ── OAuth flow ────────────────────────────────────────────────────────────────

def get_auth_url(state: str = "") -> str:
    """
    Build the Google OAuth consent URL.
    `state` should be an opaque value (e.g. HMAC-signed vendor_id) that is
    validated in the callback to prevent CSRF.
    """
    params = {
        "client_id":     _client_id(),
        "redirect_uri":  _redirect_uri(),
        "response_type": "code",
        "scope":         " ".join(_SCOPES),
        "access_type":   "offline",   # request refresh_token
        "prompt":        "consent",   # force refresh_token on reconnect
        "include_granted_scopes": "true",
    }
    if state:
        params["state"] = state
    return _AUTH_URL + "?" + urllib.parse.urlencode(params)


def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """
    Exchange an authorization code for access + refresh tokens.

    Returns a dict with keys: access_token, refresh_token, expires_in,
    token_type, scope.
    Raises httpx.HTTPStatusError on failure.
    """
    resp = httpx.post(
        _TOKEN_URL,
        data={
            "code":          code,
            "client_id":     _client_id(),
            "client_secret": _client_secret(),
            "redirect_uri":  _redirect_uri(),
            "grant_type":    "authorization_code",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """
    Get a new access_token using a stored refresh_token.

    Returns dict with: access_token, expires_in, token_type, scope.
    """
    resp = httpx.post(
        _TOKEN_URL,
        data={
            "refresh_token": refresh_token,
            "client_id":     _client_id(),
            "client_secret": _client_secret(),
            "grant_type":    "refresh_token",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def revoke_token(token: str) -> None:
    """Revoke an access or refresh token (best-effort, ignores errors)."""
    try:
        httpx.post(_REVOKE_URL, params={"token": token}, timeout=10)
    except Exception as exc:
        logger.warning("Failed to revoke Google token: %s", exc)


# ── Token management helper ───────────────────────────────────────────────────

def _get_valid_token(integration: dict[str, Any]) -> str:
    """
    Return a valid access token for the given integration row.
    Auto-refreshes if expired and updates the DB.

    `integration` is the dict returned by get_calendar_integration().
    Raises RuntimeError if no valid token can be obtained.
    """
    from storage_calendar import update_integration_tokens

    access_token = integration.get("access_token", "")
    expires_at   = integration.get("expires_at", "")
    refresh_token = integration.get("refresh_token", "")

    if not access_token:
        raise RuntimeError("No Google Calendar access token stored.")

    # Check expiry with a 60-second buffer
    try:
        exp_dt = datetime.fromisoformat(expires_at) if expires_at else None
    except ValueError:
        exp_dt = None

    now = datetime.now(timezone.utc)
    if exp_dt and exp_dt.tzinfo is None:
        exp_dt = exp_dt.replace(tzinfo=timezone.utc)

    needs_refresh = (not exp_dt) or (exp_dt - now < timedelta(seconds=60))

    if needs_refresh and refresh_token:
        logger.info("Refreshing Google Calendar token for vendor_id=%s", integration.get("vendor_id"))
        data = refresh_access_token(refresh_token)
        new_access = data["access_token"]
        new_exp = now + timedelta(seconds=int(data.get("expires_in", 3600)))
        update_integration_tokens(
            int(integration["vendor_id"]),
            "google",
            access_token=new_access,
            expires_at=new_exp.isoformat(),
        )
        return new_access

    return access_token


# ── Calendar event helpers ────────────────────────────────────────────────────

def _event_body(event: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a Vendor Atlas event dict to a Google Calendar event payload.

    Accepted fields: name/title, date, start_time, end_time, description,
    location/city, state, event_url.
    """
    name  = str(event.get("name") or event.get("title") or "Vendor Atlas Event")
    date  = str(event.get("date") or "")
    start = str(event.get("start_time") or event.get("start") or "")
    end   = str(event.get("end_time")   or event.get("end")   or "")
    desc  = str(event.get("description") or event.get("notes") or "")
    city  = str(event.get("city") or "")
    state = str(event.get("state") or "")
    loc   = str(event.get("location") or f"{city}, {state}".strip(", "))

    # If we have time components, use dateTime; otherwise use all-day date
    if start and "T" in start:
        start_val = {"dateTime": start, "timeZone": "America/Chicago"}
        end_val   = {"dateTime": end or start, "timeZone": "America/Chicago"}
    elif start and date:
        start_val = {"dateTime": f"{date}T{start}:00", "timeZone": "America/Chicago"}
        end_val   = {"dateTime": f"{date}T{(end or start)}:00", "timeZone": "America/Chicago"}
    else:
        # All-day event
        start_val = {"date": date or datetime.now().strftime("%Y-%m-%d")}
        end_val   = start_val.copy()

    body: dict[str, Any] = {
        "summary":     name,
        "description": desc,
        "start":       start_val,
        "end":         end_val,
        "source":      {
            "title": "Vendor Atlas",
            "url":   os.environ.get("APP_BASE_URL", "https://vendoratlas.com"),
        },
    }
    if loc.strip(","):
        body["location"] = loc

    return body


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_google_event(
    integration: dict[str, Any],
    event: dict[str, Any],
    calendar_id: str = "primary",
) -> dict[str, Any]:
    """
    Push a new event to the vendor's Google Calendar.

    Returns the created Google Calendar event object (including .id).
    """
    token = _get_valid_token(integration)
    body  = _event_body(event)
    resp  = httpx.post(
        f"{_CAL_BASE}/calendars/{urllib.parse.quote(calendar_id)}/events",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        content=json.dumps(body),
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def update_google_event(
    integration: dict[str, Any],
    google_event_id: str,
    event: dict[str, Any],
    calendar_id: str = "primary",
) -> dict[str, Any]:
    """Update an existing event in Google Calendar (full replace)."""
    token = _get_valid_token(integration)
    body  = _event_body(event)
    resp  = httpx.put(
        f"{_CAL_BASE}/calendars/{urllib.parse.quote(calendar_id)}/events/{urllib.parse.quote(google_event_id)}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        content=json.dumps(body),
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def delete_google_event(
    integration: dict[str, Any],
    google_event_id: str,
    calendar_id: str = "primary",
) -> None:
    """Delete an event from Google Calendar. Silently ignores 404 (already gone)."""
    token = _get_valid_token(integration)
    resp  = httpx.delete(
        f"{_CAL_BASE}/calendars/{urllib.parse.quote(calendar_id)}/events/{urllib.parse.quote(google_event_id)}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    if resp.status_code == 404:
        return
    resp.raise_for_status()


def fetch_google_busy_times(
    integration: dict[str, Any],
    start: datetime,
    end: datetime,
    calendar_id: str = "primary",
) -> list[dict[str, str]]:
    """
    Return a list of busy windows from Google Calendar's FreeBusy API.

    Each item: {"start": "<ISO>", "end": "<ISO>"}
    """
    token = _get_valid_token(integration)
    payload = {
        "timeMin": start.astimezone(timezone.utc).isoformat(),
        "timeMax": end.astimezone(timezone.utc).isoformat(),
        "items":   [{"id": calendar_id}],
    }
    resp = httpx.post(
        f"{_CAL_BASE}/freeBusy",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        content=json.dumps(payload),
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    calendars = data.get("calendars", {})
    busy_list = calendars.get(calendar_id, {}).get("busy", [])
    return [{"start": b["start"], "end": b["end"]} for b in busy_list]


def sync_events_to_google(
    integration: dict[str, Any],
    events: list[dict[str, Any]],
    calendar_id: str = "primary",
) -> dict[str, Any]:
    """
    Sync a list of VA events to Google Calendar.

    Creates each event and returns a summary. Skips on individual errors
    rather than aborting the whole batch.
    """
    created  = 0
    skipped  = 0
    failures = []

    for event in events:
        try:
            create_google_event(integration, event, calendar_id)
            created += 1
        except Exception as exc:
            skipped += 1
            failures.append({"event": event.get("name") or event.get("title"), "error": str(exc)})
            logger.warning("Failed to sync event %r: %s", event.get("name"), exc)

    return {
        "ok":      True,
        "synced":  created,
        "skipped": skipped,
        "failures": failures,
    }


# ── Availability parser ────────────────────────────────────────────────────────

def parse_busy_windows(
    busy: list[dict[str, str]],
    day_start_hour: int = 8,
    day_end_hour: int = 22,
    min_free_minutes: int = 60,
) -> list[dict[str, Any]]:
    """
    Given a list of busy windows, return free production windows.

    Only looks within [day_start_hour, day_end_hour] each day.
    Windows shorter than `min_free_minutes` are excluded.

    Returns list of: {start, end, duration_minutes, label}
    """
    if not busy:
        return []

    # Parse all busy slots
    busy_slots: list[tuple[datetime, datetime]] = []
    for b in busy:
        try:
            s = datetime.fromisoformat(b["start"].replace("Z", "+00:00"))
            e = datetime.fromisoformat(b["end"].replace("Z", "+00:00"))
            busy_slots.append((s, e))
        except (ValueError, KeyError):
            continue

    if not busy_slots:
        return []

    busy_slots.sort(key=lambda x: x[0])

    # Determine date range
    first_day = busy_slots[0][0].date()
    last_day  = busy_slots[-1][1].date()

    free_windows: list[dict[str, Any]] = []
    current_date = first_day
    one_day = timedelta(days=1)

    while current_date <= last_day:
        tz = busy_slots[0][0].tzinfo or timezone.utc
        window_start = datetime(current_date.year, current_date.month, current_date.day,
                                day_start_hour, 0, tzinfo=tz)
        window_end   = datetime(current_date.year, current_date.month, current_date.day,
                                day_end_hour, 0, tzinfo=tz)

        # Collect busy slots that overlap this day's window
        day_busy: list[tuple[datetime, datetime]] = [
            (max(s, window_start), min(e, window_end))
            for s, e in busy_slots
            if s < window_end and e > window_start
        ]
        day_busy.sort(key=lambda x: x[0])

        # Find gaps
        cursor = window_start
        for busy_start, busy_end in day_busy:
            if busy_start > cursor:
                gap_minutes = int((busy_start - cursor).total_seconds() / 60)
                if gap_minutes >= min_free_minutes:
                    free_windows.append({
                        "start":            cursor.isoformat(),
                        "end":              busy_start.isoformat(),
                        "duration_minutes": gap_minutes,
                        "label":            _window_label(cursor, busy_start),
                    })
            cursor = max(cursor, busy_end)

        # Gap after last busy slot
        if cursor < window_end:
            gap_minutes = int((window_end - cursor).total_seconds() / 60)
            if gap_minutes >= min_free_minutes:
                free_windows.append({
                    "start":            cursor.isoformat(),
                    "end":              window_end.isoformat(),
                    "duration_minutes": gap_minutes,
                    "label":            _window_label(cursor, window_end),
                })

        current_date += one_day

    return free_windows


def _window_label(start: datetime, end: datetime) -> str:
    day = start.strftime("%A")
    s   = start.strftime("%-I:%M %p") if hasattr(start, "strftime") else str(start)
    e   = end.strftime("%-I:%M %p")   if hasattr(end, "strftime")   else str(end)
    return f"{day} {s} – {e}"
