"""
Vendor Atlas MCP Server (Protocol 2024-11-05)

FastAPI-based MCP server with:
    - SSE transport for remote MCP clients
    - stdio transport for local MCP usage
    - browser-friendly consumer routes
    - static site serving for the Vendor Atlas frontend
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sys
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles

from billing import BillingConfig, UsageTracker, create_billing_middleware
from config import get_config
from db_runtime import backend_summary
from middleware.session_manager import get_session_manager
from middleware.sync import get_sync_engine
from storage_events import Event as StoredEvent, get_event_by_id, init_events_db, search_events as stored_search_events, upsert_event
from storage_markets import init_db
from storage_marketplace import (
    create_application as create_marketplace_application,
    create_event as create_marketplace_event,
    create_vendor as create_marketplace_vendor,
    ensure_vendor_marketplace_profile,
    get_first_marketplace_user,
    get_first_vendor,
    get_event as get_marketplace_event,
    get_marketplace_user_by_username,
    get_vendor as get_marketplace_vendor,
    get_vendor_by_username,
    get_vendor_stats as get_marketplace_vendor_stats,
    get_organizer_analytics as get_marketplace_organizer_analytics,
    get_shopper_analytics as get_marketplace_shopper_analytics,
    init_marketplace_db,
    list_applications as list_marketplace_applications,
    list_events as list_marketplace_events,
    list_saved_events as list_marketplace_saved_events,
    save_event_for_user as save_marketplace_event_for_user,
)
from storage_shopify import (
    disconnect_shopify,
    get_shopify_access_token,
    get_shopify_connection,
    get_shopify_products,
    get_shopify_storefront_access_token,
    set_shopify_connection,
    set_shopify_storefront_connection,
    upsert_shopify_products,
)
from storage_users import (
    authenticate_user,
    create_notification,
    create_user,
    follow_vendor,
    get_availability_for_user,
    get_followed_vendors_for_shopper,
    get_follower_user_ids_for_vendor,
    get_notifications_for_user,
    get_rsvped_events_for_user,
    get_saved_markets_for_user,
    get_user_by_id,
    get_user_by_username,
    list_public_users,
    get_vendor_tracker_for_user,
    is_username_available,
    is_following_vendor,
    is_event_rsvped_by_user,
    init_users_db,
    get_vendor_visible_events,
    remove_rsvp_for_user,
    remove_saved_market_for_user,
    rsvp_event_for_user,
    save_market_for_user,
    set_vendor_event_visibility,
    unfollow_vendor,
    update_user_profile,
    upsert_availability_for_user,
    upsert_vendor_tracker_for_user,
)
from shopify_oauth import (
    build_authorize_url,
    exchange_code_for_token,
    fetch_storefront_products,
    products_with_inventory,
    verify_hmac,
)
from tools import ALL_HANDLERS, ALL_TOOLS
from tools.vendor_atlas_pipeline import build_search_event_filters, run_search_events

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("vendor-atlas")

SERVER_INFO = {
    "name": "Vendor Atlas",
    "version": "0.1.0",
}
PROTOCOL_VERSION = "2024-11-05"

billing_config = BillingConfig()
usage_tracker = UsageTracker(billing_config)
billing_middleware = create_billing_middleware(usage_tracker)
SESSION_COOKIE_NAME = "vendor_atlas_session"

PUBLIC_PAGE_ROUTES = {
    "/": "index.html",
    "/discover": "discover.html",
    "/features": "features.html",
    "/pricing": "pricing.html",
    "/about": "about.html",
    "/listings": "listings.html",
    "/find-my-next-market": "find-market.html",
    "/business": "business.html",
    "/profile": "profile.html",
    "/final-plan": "final-plan.html",
    "/shopper-plan": "shopper-plan.html",
    "/history": "history.html",
    "/integrations": "integrations.html",
    "/signin": "signin.html",
    "/signup": "signup.html",
}

MONTH_NAME_PATTERN = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b",
    re.IGNORECASE,
)
RECURRING_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("weekly", "Weekly"),
    ("every week", "Weekly"),
    ("biweekly", "Biweekly"),
    ("every other week", "Biweekly"),
    ("monthly", "Monthly"),
    ("every month", "Monthly"),
    ("night market", "Recurring series"),
    ("market series", "Recurring series"),
    ("popup series", "Recurring series"),
    ("recurring", "Recurring series"),
    ("annual", "Annual"),
    ("yearly", "Annual"),
    ("every year", "Annual"),
    ("spring", "Seasonal"),
    ("summer", "Seasonal"),
    ("fall", "Seasonal"),
    ("autumn", "Seasonal"),
    ("winter", "Seasonal"),
    ("holiday", "Seasonal"),
)
TRACKER_MONTHS = ("April", "May", "June", "July", "August", "September", "October", "November", "December")
TRACKER_SELECTION_CRITERIA = {
    "booth_price_guide": [
        "Under $125: usually a strong low-risk test if traffic and fit are credible.",
        "$125-$250: workable for proven markets when expected traffic and buyer fit are above average.",
        "$250+: only worth it when traffic, conversion confidence, and organizer quality are all strong.",
    ],
    "traffic_benchmarks": [
        "2,500+ visitors: strong traffic signal for most product businesses.",
        "1,000-2,499 visitors: viable if the audience is highly aligned and booth fee stays reasonable.",
        "Under 1,000 visitors: treat as a test market unless the event is niche and well targeted.",
    ],
    "warning_signs": [
        "No clear application page, organizer contact, or setup details.",
        "High booth fee without traffic history or vendor proof.",
        "Vague audience description, weak photos, or inconsistent event dates.",
    ],
}


def _event_to_market_payload(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": event.get("id"),
        "name": event.get("name"),
        "city": event.get("city"),
        "state": event.get("state"),
        "start_date": event.get("date"),
        "end_date": event.get("date"),
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
        "source_ref": event.get("source_url"),
    }


def _parse_event_date(date_text: str | None) -> datetime | None:
    if not date_text:
        return None

    normalized = str(date_text).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    return None


def _normalize_event_name(name: str) -> str:
    normalized = name.lower()
    normalized = MONTH_NAME_PATTERN.sub(" ", normalized)
    normalized = re.sub(r"\b(20\d{2}|19\d{2})\b", " ", normalized)
    normalized = re.sub(r"\b(first|second|third|fourth|annual|monthly|weekly|seasonal|series)\b", " ", normalized)
    normalized = re.sub(r"[^a-z]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _infer_recurrence_details(event: dict[str, Any], peer_events: list[dict[str, Any]]) -> dict[str, Any]:
    name = str(event.get("name") or event.get("title") or "").strip()
    haystack = f"{name} {event.get('source_url', '')} {event.get('url', '')}".lower()
    explicit_label = next((label for keyword, label in RECURRING_KEYWORDS if keyword in haystack), "")

    normalized_name = _normalize_event_name(name)
    matching_dates: list[datetime] = []
    for peer in peer_events:
        peer_name = str(peer.get("name") or peer.get("title") or "").strip()
        if not peer_name:
            continue
        if _normalize_event_name(peer_name) != normalized_name:
            continue
        parsed = _parse_event_date(peer.get("date"))
        if parsed:
            matching_dates.append(parsed)

    matching_dates = sorted({item.strftime("%Y-%m-%d"): item for item in matching_dates}.values(), key=lambda item: item)
    repeat_count = len(matching_dates)

    cadence = explicit_label
    if repeat_count >= 2:
        day_gaps = [
            (matching_dates[index] - matching_dates[index - 1]).days
            for index in range(1, len(matching_dates))
        ]
        avg_gap = sum(day_gaps) / len(day_gaps)
        if avg_gap <= 10:
            cadence = cadence or "Weekly"
        elif avg_gap <= 24:
            cadence = cadence or "Biweekly"
        elif avg_gap <= 50:
            cadence = cadence or "Monthly"
        elif avg_gap <= 140:
            cadence = cadence or "Seasonal"
        else:
            cadence = cadence or "Annual"

    is_recurring = bool(cadence)
    confidence = "high" if repeat_count >= 3 else "medium" if repeat_count >= 2 or explicit_label else "low"
    return {
        "is_recurring": is_recurring,
        "label": cadence or "One-off",
        "repeat_count": repeat_count,
        "confidence": confidence if is_recurring else "low",
    }


def _apply_recurrence_signals(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not events:
        return []

    enriched: list[dict[str, Any]] = []
    for event in events:
        recurrence = _infer_recurrence_details(event, events)
        enriched.append({**event, "recurrence": recurrence})
    return enriched


def _build_recurrence_summary(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for event in events:
        recurrence = event.get("recurrence") or {}
        if not recurrence.get("is_recurring"):
            continue

        key = _normalize_event_name(str(event.get("name") or event.get("title") or ""))
        if not key:
            continue

        entry = grouped.setdefault(
            key,
            {
                "name": event.get("name") or event.get("title"),
                "city": event.get("city"),
                "state": event.get("state"),
                "label": recurrence.get("label"),
                "repeat_count": 0,
                "next_date": event.get("date") or "",
            },
        )
        entry["repeat_count"] = max(entry["repeat_count"], int(recurrence.get("repeat_count") or 0))
        candidate_date = str(event.get("date") or "")
        if candidate_date and (not entry["next_date"] or candidate_date < entry["next_date"]):
            entry["next_date"] = candidate_date

    return sorted(grouped.values(), key=lambda item: (item.get("next_date") or "", item.get("name") or ""))[:6]


def _current_user(request: Request) -> dict[str, Any] | None:
    user_id = _read_session_user_id(request)
    if not user_id:
        return None
    return get_user_by_id(int(user_id))


def _normalized_role(user: dict[str, Any] | None) -> str:
    if not user:
        return "vendor"
    role = str(user.get("role") or "vendor").strip().lower()
    if role not in {"vendor", "market", "shopper"}:
        return "vendor"
    return role


def _dashboard_path_for_role(role: str) -> str:
    normalized = str(role or "vendor").strip().lower()
    if normalized == "market":
        return "/market-dashboard"
    if normalized == "shopper":
        return "/shopper-dashboard"
    return "/dashboard"


def _role_entry_path(role: str) -> str:
    normalized = str(role or "vendor").strip().lower()
    if normalized not in {"vendor", "market", "shopper"}:
        normalized = "vendor"
    return f"/signup?role={normalized}"


def _dev_login_enabled(request: Request) -> bool:
    env_value = os.environ.get("VENDOR_ATLAS_ENABLE_DEV_LOGIN", "").strip().lower()
    if env_value in {"0", "false", "no", "off"}:
        return False
    if env_value in {"1", "true", "yes", "on"}:
        return True
    host = (request.url.hostname or "").strip().lower()
    if host in {"127.0.0.1", "localhost", "testserver"}:
        return True
    # Default to enabled for local MVP/dev testing unless explicitly turned off.
    return True


def _serialize_vendor_profile(vendor: dict[str, Any], viewer: dict[str, Any] | None = None) -> dict[str, Any]:
    vendor_id = int(vendor["id"])
    upcoming_events = _apply_recurrence_signals(get_vendor_visible_events(vendor_id, visible_only=True))
    payload = {
        "id": vendor_id,
        "name": vendor.get("name", ""),
        "username": vendor.get("username", ""),
        "bio": vendor.get("bio", ""),
        "interests": vendor.get("interests", ""),
        "upcoming_events": upcoming_events,
        "profile_url": f"/u/{vendor.get('username', '')}",
        "followers_visible_events_count": len(upcoming_events),
    }
    if viewer and _normalized_role(viewer) == "shopper":
        payload["is_following"] = is_following_vendor(int(viewer["id"]), vendor_id)
    return payload


def _require_user(request: Request) -> dict[str, Any] | None:
    return _current_user(request)


def _validate_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))


def _validation_error(message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse({"ok": False, "error": message}, status_code=status_code)


def _normalize_shopify_domain(raw_shop: str) -> str:
    value = str(raw_shop or "").strip().lower()
    if not value:
        return ""
    value = re.sub(r"^https?://", "", value)
    value = value.split("/", 1)[0].strip()
    if value.startswith("www."):
        value = value[4:]
    if "." not in value:
        value = f"{value}.myshopify.com"
    return value


def _sign_session_value(user_id: int, secret: str) -> str:
    raw = str(user_id).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(raw + b"." + signature.encode("utf-8")).decode("utf-8")
    return token


def _unsign_session_value(token: str, secret: str) -> int | None:
    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        user_id_text, signature = decoded.split(".", 1)
    except Exception:
        return None

    expected = hmac.new(secret.encode("utf-8"), user_id_text.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None

    try:
        return int(user_id_text)
    except ValueError:
        return None


def _read_session_user_id(request: Request) -> int | None:
    config = get_config()
    token = request.cookies.get(SESSION_COOKIE_NAME, "")
    if not token:
        return None
    return _unsign_session_value(token, config.session_secret)


def _set_session_cookie(response: Response, user_id: int) -> None:
    config = get_config()
    response.set_cookie(
        SESSION_COOKIE_NAME,
        _sign_session_value(user_id, config.session_secret),
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
        max_age=60 * 60 * 24 * 14,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


def _shopify_state_encode(user_id: int, secret: str) -> str:
    raw = f"{user_id}:{secrets.token_hex(16)}"
    sig = hmac.new(secret.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{raw}.{sig}".encode("utf-8")).decode("utf-8")


def _shopify_state_decode(state: str, secret: str) -> int | None:
    try:
        decoded = base64.urlsafe_b64decode(state.encode("utf-8")).decode("utf-8")
        rest, sig = decoded.rsplit(".", 1)
        user_id_str, _nonce = rest.split(":", 1)
        expected = hmac.new(secret.encode("utf-8"), rest.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        return int(user_id_str)
    except Exception:
        return None


def _recommend_markets_for_schedule(
    availability: dict[str, Any],
    saved_markets: list[dict[str, Any]],
    fallback_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    weekday_preferences = set(availability.get("weekdays", []))
    month_preferences = set(availability.get("preferred_months", []))
    pool = _apply_recurrence_signals(saved_markets or fallback_events)
    recommendations: list[dict[str, Any]] = []

    for event in pool:
        score = 50
        reasons: list[str] = []
        date_text = str(event.get("date") or "")
        event_dt = None
        if date_text:
            try:
                event_dt = datetime.strptime(date_text, "%Y-%m-%d")
            except ValueError:
                event_dt = None

        if event_dt:
            weekday = event_dt.strftime("%A")
            month_name = event_dt.strftime("%B")
            if weekday_preferences and weekday in weekday_preferences:
                score += 18
                reasons.append(f"Matches your {weekday.lower()} availability.")
            if month_preferences and month_name in month_preferences:
                score += 14
                reasons.append(f"Falls in a preferred month: {month_name}.")

        if event.get("booth_price") and float(event["booth_price"]) <= 150:
            score += 8
            reasons.append("Lower booth cost makes it easier to fit into a regular schedule.")
        if event.get("popularity_score") and int(event["popularity_score"]) >= 80:
            score += 8
            reasons.append("Popularity score suggests stronger turnout.")
        if event.get("estimated_traffic") and int(event["estimated_traffic"]) >= 2500:
            score += 8
            reasons.append("Traffic potential looks healthy.")
        recurrence = event.get("recurrence") or {}
        if recurrence.get("is_recurring"):
            score += 6
            reasons.append(f"{recurrence.get('label')} pattern makes repeat planning easier.")

        recommendations.append(
            {
                **event,
                "schedule_fit_score": min(score, 100),
                "schedule_reasons": reasons or ["Add more availability preferences to improve recommendations."],
            }
        )

    recommendations.sort(key=lambda item: (-item["schedule_fit_score"], item.get("date") or "", item.get("name") or ""))
    return recommendations[:5]


def _score_listing(event: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    avg_sale_price = float(inputs.get("avg_sale_price") or 0)
    avg_sales_per_event = float(inputs.get("avg_sales_per_event") or 0)
    typical_cogs = float(inputs.get("typical_cogs") or 0)
    travel_cost = float(inputs.get("travel_cost") or 0)
    booth_budget = float(inputs.get("booth_budget") or 0)
    preferred_min_profit = float(inputs.get("preferred_min_profit") or 0)

    booth_price = float(event.get("booth_price") or 0)
    vendor_count = float(event.get("vendor_count") or 0)
    estimated_traffic = float(event.get("estimated_traffic") or 0)
    popularity_score = float(event.get("popularity_score") or 0)

    estimated_revenue = avg_sale_price * avg_sales_per_event
    estimated_cost = typical_cogs + travel_cost + booth_price
    estimated_profit = estimated_revenue - estimated_cost

    profit_ratio = 0 if preferred_min_profit <= 0 else estimated_profit / max(preferred_min_profit, 1)
    profit_potential = max(1, min(10, round(5 + profit_ratio * 3)))
    traffic_quality = max(1, min(10, round((estimated_traffic / 600) + (popularity_score / 25))))
    booth_cost_fairness = max(1, min(10, round(10 - max(0, booth_price - booth_budget) / 25))) if booth_budget else max(1, min(10, round(10 - booth_price / 35)))
    competition_level = max(1, min(10, round(10 - vendor_count / 18))) if vendor_count else 6
    break_even_confidence = max(1, min(10, round((estimated_revenue / max(estimated_cost, 1)) * 3)))

    overall = round(
        (
            profit_potential * 0.35
            + traffic_quality * 0.2
            + booth_cost_fairness * 0.2
            + competition_level * 0.1
            + break_even_confidence * 0.15
        ),
        1,
    )

    if overall >= 8:
        recommendation = "Strong Yes"
    elif overall >= 5:
        recommendation = "Maybe"
    else:
        recommendation = "Not Worth It"

    explanation_parts = []
    if estimated_profit >= preferred_min_profit:
        explanation_parts.append("Estimated profit clears your preferred minimum.")
    elif estimated_profit > 0:
        explanation_parts.append("Estimated profit is positive, but below your preferred target.")
    else:
        explanation_parts.append("Current inputs suggest the event may not be profitable.")

    if booth_price and booth_budget and booth_price > booth_budget:
        explanation_parts.append("Booth cost is above your stated budget.")
    elif booth_price:
        explanation_parts.append("Booth cost stays within a manageable range.")

    if estimated_traffic >= 2500 or popularity_score >= 80:
        explanation_parts.append("Traffic signals look promising.")
    elif estimated_traffic:
        explanation_parts.append("Traffic looks moderate, so conversion matters more.")

    return {
        **event,
        "analysis": {
            "estimated_revenue": round(estimated_revenue, 2),
            "estimated_cost": round(estimated_cost, 2),
            "estimated_profit": round(estimated_profit, 2),
            "ratings": {
                "profit_potential": int(profit_potential),
                "traffic_quality": int(traffic_quality),
                "booth_cost_fairness": int(booth_cost_fairness),
                "competition_level": int(competition_level),
                "break_even_confidence": int(break_even_confidence),
                "overall_worth_it": overall,
            },
            "recommendation": recommendation,
            "explanation": " ".join(explanation_parts),
        },
    }


def _event_date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None


def _vendor_learning_profile(user: dict[str, Any] | None) -> dict[str, Any]:
    if not user or _normalized_role(user) != "vendor":
        return {
            "has_history": False,
            "preferred_months": [],
            "comfortable_fee_cap": 175.0,
            "average_profit": 0.0,
        }

    vendor = get_vendor_by_username(str(user.get("username") or "").strip().lower())
    if not vendor:
        return {
            "has_history": False,
            "preferred_months": [],
            "comfortable_fee_cap": 175.0,
            "average_profit": 0.0,
        }

    payload = get_marketplace_vendor_stats(vendor["id"])
    stats = payload.get("events", [])
    profitable = [item for item in stats if float(item.get("profit") or 0) > 0]
    month_counts: dict[int, int] = {}
    for item in profitable:
        month = int(str(item.get("start_date") or "")[5:7] or 0)
        if month:
            month_counts[month] = month_counts.get(month, 0) + 1

    preferred_months = [
        month
        for month, _count in sorted(month_counts.items(), key=lambda pair: (-pair[1], pair[0]))[:3]
    ]
    profitable_fees = [float(item.get("vendor_fee") or 0) for item in profitable if float(item.get("vendor_fee") or 0) > 0]
    comfortable_fee_cap = round((sum(profitable_fees) / len(profitable_fees)) + 40, 2) if profitable_fees else 175.0
    average_profit = float(payload.get("summary", {}).get("average_profit_per_event") or 0)
    return {
        "has_history": bool(stats),
        "preferred_months": preferred_months,
        "comfortable_fee_cap": comfortable_fee_cap,
        "average_profit": average_profit,
    }


def _generic_event_rank(event: dict[str, Any], user: dict[str, Any] | None = None) -> dict[str, Any]:
    booth_price = float(event.get("booth_price") or event.get("vendor_fee") or 0)
    popularity_score = float(event.get("popularity_score") or 0)
    estimated_traffic = float(event.get("estimated_traffic") or 0)
    vendor_count = float(event.get("vendor_count") or 0)
    learning = _vendor_learning_profile(user)

    score = 48.0
    reasons: list[str] = []
    breakdown = {
        "fee": 0,
        "demand": 0,
        "timing": 0,
        "competition": 0,
        "learning": 0,
    }

    if booth_price <= 125:
        score += 12
        breakdown["fee"] += 12
        reasons.append("Booth cost stays in an easier-to-profit range.")
    elif booth_price <= 220:
        score += 6
        breakdown["fee"] += 6
        reasons.append("Booth cost is still manageable.")
    elif booth_price > 0:
        score -= 8
        breakdown["fee"] -= 8
        reasons.append("Booth cost needs stronger sales to pay off.")

    if estimated_traffic >= 2500 or popularity_score >= 80:
        score += 14
        breakdown["demand"] += 14
        reasons.append("Traffic signals look strong.")
    elif estimated_traffic >= 1200 or popularity_score >= 60:
        score += 8
        breakdown["demand"] += 8
        reasons.append("Traffic looks promising.")
    else:
        score -= 2
        breakdown["demand"] -= 2
        reasons.append("Turnout looks less certain, so conversion matters more.")

    if vendor_count:
        if vendor_count <= 60:
            score += 6
            breakdown["competition"] += 6
            reasons.append("Competition looks lighter than average.")
        elif vendor_count >= 130:
            score -= 5
            breakdown["competition"] -= 5
            reasons.append("A crowded vendor mix could make sales harder.")

    event_dt = _event_date(event.get("date"))
    if event_dt:
        days_until = (event_dt.date() - datetime.now(timezone.utc).date()).days
        if days_until >= 0 and days_until <= 90:
            score += 8
            breakdown["timing"] += 8
            reasons.append("The date is close enough to act on now.")
        elif days_until > 180:
            score -= 3
            breakdown["timing"] -= 3
            reasons.append("This one is farther out, so it is less urgent right now.")

        if learning["has_history"] and event_dt.month in set(learning["preferred_months"]):
            score += 8
            breakdown["learning"] += 8
            reasons.append("Your stronger past results line up with this time of year.")

    if learning["has_history"]:
        if booth_price and booth_price <= float(learning["comfortable_fee_cap"] or 0):
            score += 7
            breakdown["learning"] += 7
            reasons.append("The fee lines up with events that have worked for you before.")
        elif booth_price and booth_price > float(learning["comfortable_fee_cap"] or 0) + 40:
            score -= 6
            breakdown["learning"] -= 6
            reasons.append("The fee is higher than your more reliable past events.")
        if float(learning["average_profit"] or 0) > 0 and booth_price <= max(float(learning["comfortable_fee_cap"] or 0), 200):
            score += 4
            breakdown["learning"] += 4

    fit_score = max(1, min(99, round(score)))
    if fit_score >= 75:
        bucket = "Best Matches"
        label = "Strong fit"
    elif fit_score >= 55:
        bucket = "Worth Trying"
        label = "Worth trying"
    else:
        bucket = "Watch List"
        label = "Needs a closer look"

    return {
        **event,
        "fit_score": fit_score,
        "worth_it_score": fit_score,
        "fit_reason": " ".join(reasons[:2]) if reasons else "A balanced mix of fee, turnout, and timing signals.",
        "score_label": label,
        "bucket": bucket,
        "score_reasons": reasons[:4],
        "score_breakdown": breakdown,
    }


def _rank_events_for_user(events: list[dict[str, Any]], user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    ranked = [_generic_event_rank(event, user) for event in events]
    ranked.sort(
        key=lambda item: (
            -float(item.get("fit_score") or 0),
            str(item.get("date") or ""),
            str(item.get("name") or item.get("title") or ""),
        )
    )
    return ranked


def _tracker_float(value: Any) -> float:
    try:
        if value in ("", None):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _tracker_int(value: Any) -> int:
    try:
        if value in ("", None):
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _tracker_budget_metrics(row: dict[str, Any]) -> dict[str, Any]:
    booth_fee = _tracker_float(row.get("booth_fee"))
    additional_costs = _tracker_float(row.get("additional_costs"))
    projected_revenue = _tracker_float(row.get("projected_revenue"))
    actual_revenue = _tracker_float(row.get("actual_revenue"))
    revenue_basis = actual_revenue if actual_revenue > 0 else projected_revenue
    total_cost = booth_fee + additional_costs
    net_profit = revenue_basis - total_cost
    roi = round((net_profit / total_cost) * 100, 1) if total_cost > 0 else 0.0
    return {
        "net_profit": round(net_profit, 2),
        "roi": roi,
    }


def _tracker_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_booth_fees = round(sum(_tracker_float(row.get("booth_fee")) for row in rows), 2)
    total_additional_costs = round(sum(_tracker_float(row.get("additional_costs")) for row in rows), 2)
    total_projected_revenue = round(sum(_tracker_float(row.get("projected_revenue")) for row in rows), 2)
    total_actual_revenue = round(sum(_tracker_float(row.get("actual_revenue")) for row in rows), 2)
    calculated_rows = [{**row, **_tracker_budget_metrics(row)} for row in rows]
    total_net_profit = round(sum(_tracker_float(row.get("net_profit")) for row in calculated_rows), 2)
    rows_with_costs = [row for row in calculated_rows if (_tracker_float(row.get("booth_fee")) + _tracker_float(row.get("additional_costs"))) > 0]
    average_roi = round(sum(_tracker_float(row.get("roi")) for row in rows_with_costs) / len(rows_with_costs), 1) if rows_with_costs else 0.0
    return {
        "total_booth_fees": total_booth_fees,
        "total_additional_costs": total_additional_costs,
        "total_projected_revenue": total_projected_revenue,
        "total_actual_revenue": total_actual_revenue,
        "total_net_profit": total_net_profit,
        "average_roi": average_roi,
    }


def _application_status_for_event(event: dict[str, Any]) -> str:
    if event.get("application_link"):
        return "Apply Now"
    if event.get("booth_price") or event.get("estimated_traffic"):
        return "Watch"
    return "Research"


def _priority_stars(index: int) -> int:
    return max(1, 5 - index)


def _event_sort_key(event: dict[str, Any]) -> tuple[float, float, float, str]:
    return (
        -float(event.get("popularity_score") or 0),
        -float(event.get("estimated_traffic") or 0),
        float(event.get("booth_price") or 999999),
        str(event.get("date") or ""),
    )


def _build_tracker_application_calendar(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(events, key=_event_sort_key)[:5]
    items: list[dict[str, Any]] = []
    for index, event in enumerate(ranked):
        items.append(
            {
                "event_id": event.get("id") or f"event-{index + 1}",
                "name": event.get("name") or event.get("title") or "Untitled Market",
                "city": event.get("city") or "",
                "state": event.get("state") or "",
                "date": event.get("date") or "",
                "status": _application_status_for_event(event),
                "booth_fee": _tracker_float(event.get("booth_price")),
                "traffic": _tracker_int(event.get("estimated_traffic")),
                "vendor_count": _tracker_int(event.get("vendor_count")),
                "priority_stars": _priority_stars(index),
                "notes": "",
                "apply_url": event.get("application_link") or event.get("url") or event.get("source_url") or "",
            }
        )
    return items


def _build_tracker_budget_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tracker_events = [
        event
        for event in sorted(events, key=lambda item: (str(item.get("date") or ""), str(item.get("name") or "")))
        if str(event.get("date") or "").startswith("2026-")
    ]

    rows: list[dict[str, Any]] = []
    for event in tracker_events[:17]:
        parsed = _parse_event_date(str(event.get("date") or ""))
        month_name = parsed.strftime("%B") if parsed else ""
        rows.append(
            {
                "event_id": event.get("id") or "",
                "month": month_name,
                "date": event.get("date") or "",
                "event_name": event.get("name") or event.get("title") or "Untitled Event",
                "booth_fee": _tracker_float(event.get("booth_price")),
                "additional_costs": 0.0,
                "projected_revenue": 0.0,
                "actual_revenue": 0.0,
                "units_sold": 0,
            }
        )

    month_index = 0
    while len(rows) < 17:
        rows.append(
            {
                "event_id": "",
                "month": TRACKER_MONTHS[month_index % len(TRACKER_MONTHS)],
                "date": "",
                "event_name": "",
                "booth_fee": 0.0,
                "additional_costs": 0.0,
                "projected_revenue": 0.0,
                "actual_revenue": 0.0,
                "units_sold": 0,
            }
        )
        month_index += 1

    return rows


def _default_vendor_tracker(saved_markets: list[dict[str, Any]], fallback_events: list[dict[str, Any]]) -> dict[str, Any]:
    source_events = saved_markets or fallback_events
    budget_rows = _build_tracker_budget_rows(source_events)
    return {
        "application_calendar": _build_tracker_application_calendar(source_events),
        "booth_budget": [{**row, **_tracker_budget_metrics(row)} for row in budget_rows],
        "selection_criteria": {
            **TRACKER_SELECTION_CRITERIA,
            "notes": "",
        },
        "summary": _tracker_summary(budget_rows),
    }


def _normalize_tracker_payload(payload: dict[str, Any], fallback_tracker: dict[str, Any]) -> dict[str, Any]:
    application_calendar_raw = payload.get("application_calendar", fallback_tracker.get("application_calendar", []))
    normalized_calendar: list[dict[str, Any]] = []
    for item in application_calendar_raw[:5]:
        normalized_calendar.append(
            {
                "event_id": str(item.get("event_id", "")),
                "name": str(item.get("name", "")).strip(),
                "city": str(item.get("city", "")).strip(),
                "state": str(item.get("state", "")).strip(),
                "date": str(item.get("date", "")).strip(),
                "status": str(item.get("status", "Research")).strip() or "Research",
                "booth_fee": round(_tracker_float(item.get("booth_fee")), 2),
                "traffic": _tracker_int(item.get("traffic")),
                "vendor_count": _tracker_int(item.get("vendor_count")),
                "priority_stars": max(1, min(5, _tracker_int(item.get("priority_stars")) or 1)),
                "notes": str(item.get("notes", "")).strip(),
                "apply_url": str(item.get("apply_url", "")).strip(),
            }
        )

    budget_raw = payload.get("booth_budget", fallback_tracker.get("booth_budget", []))
    normalized_budget: list[dict[str, Any]] = []
    for item in budget_raw[:17]:
        row = {
            "event_id": str(item.get("event_id", "")).strip(),
            "month": str(item.get("month", "")).strip(),
            "date": str(item.get("date", "")).strip(),
            "event_name": str(item.get("event_name", "")).strip(),
            "booth_fee": round(_tracker_float(item.get("booth_fee")), 2),
            "additional_costs": round(_tracker_float(item.get("additional_costs")), 2),
            "projected_revenue": round(_tracker_float(item.get("projected_revenue")), 2),
            "actual_revenue": round(_tracker_float(item.get("actual_revenue")), 2),
            "units_sold": max(0, _tracker_int(item.get("units_sold"))),
        }
        normalized_budget.append({**row, **_tracker_budget_metrics(row)})

    criteria_raw = payload.get("selection_criteria", fallback_tracker.get("selection_criteria", {}))
    selection_criteria = {
        "booth_price_guide": [str(item).strip() for item in criteria_raw.get("booth_price_guide", TRACKER_SELECTION_CRITERIA["booth_price_guide"])[:6]],
        "traffic_benchmarks": [str(item).strip() for item in criteria_raw.get("traffic_benchmarks", TRACKER_SELECTION_CRITERIA["traffic_benchmarks"])[:6]],
        "warning_signs": [str(item).strip() for item in criteria_raw.get("warning_signs", TRACKER_SELECTION_CRITERIA["warning_signs"])[:6]],
        "notes": str(criteria_raw.get("notes", "")).strip(),
    }

    while len(normalized_budget) < 17:
        month_name = TRACKER_MONTHS[len(normalized_budget) % len(TRACKER_MONTHS)]
        row = {
            "event_id": "",
            "month": month_name,
            "date": "",
            "event_name": "",
            "booth_fee": 0.0,
            "additional_costs": 0.0,
            "projected_revenue": 0.0,
            "actual_revenue": 0.0,
            "units_sold": 0,
        }
        normalized_budget.append({**row, **_tracker_budget_metrics(row)})

    return {
        "application_calendar": normalized_calendar,
        "booth_budget": normalized_budget,
        "selection_criteria": selection_criteria,
        "summary": _tracker_summary(normalized_budget),
    }


async def _load_kansas_city_listings() -> dict[str, Any]:
    current_payload = run_search_events(
        build_search_event_filters(city="Kansas City", state="MO")
    )
    current_events = current_payload.get("events", [])

    discovered_events: list[dict[str, Any]] = []
    discover_handler = ALL_HANDLERS.get("discover_events")
    if discover_handler:
        try:
            discovered_raw = await discover_handler(
                city="Kansas City",
                state="MO",
                keywords=["popup market", "makers market", "craft fair", "flea market"],
                sources=["google", "eventbrite", "public_event_listings", "social_media"],
            )
            discovered_payload = json.loads(discovered_raw) if isinstance(discovered_raw, str) else discovered_raw
            discovered_events = discovered_payload.get("events", [])
        except Exception as exc:
            logger.warning("Kansas City discovery failed: %s", exc)

    all_events = _apply_recurrence_signals([*current_events, *discovered_events])
    current_ids = {event.get("id") for event in current_events}
    current_events = [event for event in all_events if event.get("id") in current_ids]
    discovered_with_recurrence = [event for event in all_events if event.get("id") not in current_ids]

    return {
        "ok": True,
        "city": "Kansas City",
        "state": "MO",
        "current_events": current_events,
        "current_count": len(current_events),
        "more_events": discovered_with_recurrence,
        "more_count": len(discovered_with_recurrence),
        "recurring_series": _build_recurrence_summary(all_events),
    }


async def _load_finder_results(
    city: str,
    state: str,
    vendor_category: str,
    event_size: str,
    distance_radius: str,
) -> dict[str, Any]:
    filters = build_search_event_filters(
        city=city,
        state=state,
        vendor_category=vendor_category,
        event_size=event_size,
        distance_radius=distance_radius,
    )
    search_payload = run_search_events(filters)
    search_events_result = search_payload.get("events", [])

    discover_handler = ALL_HANDLERS.get("discover_events")
    discovered_events: list[dict[str, Any]] = []
    if discover_handler:
        try:
            discovered_raw = await discover_handler(
                city=city,
                state=state,
                keywords=[vendor_category or "popup market", "makers market", "craft fair", "flea market"],
                sources=["google", "eventbrite", "public_event_listings", "social_media"],
            )
            discovered_payload = json.loads(discovered_raw) if isinstance(discovered_raw, str) else discovered_raw
            discovered_events = discovered_payload.get("events", [])
        except Exception as exc:
            logger.warning("Finder discovery failed: %s", exc)

    all_events = _apply_recurrence_signals([*search_events_result, *discovered_events])
    search_ids = {event.get("id") for event in search_events_result}
    search_events_result = [event for event in all_events if event.get("id") in search_ids]
    discovered_events = [event for event in all_events if event.get("id") not in search_ids]

    return {
        "ok": True,
        "filters": filters,
        "mcp_tools_used": ["search_events", "discover_events"],
        "search_results": search_events_result,
        "search_count": len(search_events_result),
        "discovered_results": discovered_events,
        "discover_count": len(discovered_events),
        "recurring_series": _build_recurrence_summary(all_events),
    }


class SSETransport:
    """Minimal in-process SSE transport for MCP clients."""

    def __init__(self) -> None:
        self._clients: dict[str, asyncio.Queue[str]] = {}

    async def connect(self) -> tuple[str, asyncio.Queue[str]]:
        import uuid

        session_id = str(uuid.uuid4())
        queue: asyncio.Queue[str] = asyncio.Queue()
        await queue.put(f"event: endpoint\ndata: /message?sessionId={session_id}\n\n")
        self._clients[session_id] = queue
        logger.info("SSE client connected: %s", session_id)
        return session_id, queue

    async def disconnect(self, session_id: str) -> None:
        self._clients.pop(session_id, None)
        logger.info("SSE client disconnected: %s", session_id)

    async def send(self, session_id: str, payload: dict[str, Any]) -> None:
        queue = self._clients.get(session_id)
        if not queue:
            return
        data = json.dumps(payload)
        await queue.put(f"event: message\ndata: {data}\n\n")

    def has_session(self, session_id: str) -> bool:
        return session_id in self._clients

    @property
    def connected_clients(self) -> int:
        return len(self._clients)


sse_transport = SSETransport()


async def handle_jsonrpc(
    message: dict[str, Any],
    api_key: str = "",
    session_id: str = "",
) -> dict[str, Any] | None:
    """Process a single MCP JSON-RPC message."""
    method = message.get("method", "")
    msg_id = message.get("id")
    params = message.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                },
                "serverInfo": SERVER_INFO,
            },
        }

    if method.startswith("notifications/"):
        return None

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": ALL_TOOLS},
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {}) or {}

        handler = ALL_HANDLERS.get(tool_name)
        if not handler:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}",
                },
            }

        sync_engine = get_sync_engine()
        await sync_engine.get_context(tool_name, str(arguments))

        session_mgr = get_session_manager()
        session_mgr.get_or_create_session(session_id, user_id=api_key or "anonymous")

        import time as _time

        started = _time.monotonic()
        result = await billing_middleware(tool_name, arguments, api_key, handler)
        duration_ms = (_time.monotonic() - started) * 1000
        success = "error" not in result

        asyncio.create_task(
            sync_engine.capture_and_sync(
                tool_name=tool_name,
                arguments=arguments,
                user_id=api_key or "anonymous",
                session_id=session_id,
                result=result,
                duration_ms=duration_ms,
                success=success,
            )
        )
        session_mgr.update_session(session_id, tool_name)

        if "error" in result:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": result["error"],
            }

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result,
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}",
        },
    }


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(title="Vendor Atlas MCP Server", version=SERVER_INFO["version"])
    site_dir = Path(__file__).resolve().parent / "site"
    init_db()
    init_events_db()
    init_users_db()
    init_marketplace_db()
    from storage_shopify import init_shopify_db
    init_shopify_db()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def _background_seed_events() -> None:
        async def _run() -> None:
            await asyncio.sleep(5)  # let server finish starting
            discover_handler = ALL_HANDLERS.get("discover_events")
            if not discover_handler:
                return
            keyword_sets = [
                ["popup market", "makers market", "craft fair", "vendor fair", "flea market"],
                ["oddity market", "curiosities market", "dark market", "oddities and curiosities", "horror convention"],
                ["rave", "electronic music festival", "underground event", "DJ event vendor"],
                ["tattoo convention", "tattoo expo", "tattoo festival"],
                ["anime convention", "comic con", "cosplay convention", "fan expo"],
                ["small concert vendor", "music festival vendor", "festival vendor application"],
                ["night market", "art market", "vintage market", "antique market", "holiday market"],
                ["street fair vendor", "vendor expo", "outdoor vendor event"],
            ]
            for keywords in keyword_sets:
                try:
                    raw = await discover_handler(
                        city="Kansas City",
                        state="MO",
                        keywords=keywords,
                        sources=["google", "eventbrite", "facebook_events", "public_event_listings"],
                    )
                    payload = json.loads(raw) if isinstance(raw, str) else raw
                    for event in payload.get("events", []):
                        try:
                            from storage_events import Event, upsert_event
                            upsert_event(Event(
                                id=event.get("id") or event.get("event_id") or "",
                                name=event.get("name") or event.get("title") or "",
                                city=event.get("city") or "Kansas City",
                                state=event.get("state") or "MO",
                                date=event.get("date") or event.get("start_date") or "",
                                vendor_count=event.get("vendor_count"),
                                estimated_traffic=event.get("estimated_traffic"),
                                booth_price=event.get("booth_price") or event.get("vendor_fee"),
                                application_link=event.get("application_link") or event.get("url") or event.get("source_url") or "",
                                source_url=event.get("source_url") or event.get("url") or "",
                                vendor_category=event.get("vendor_category") or event.get("event_type") or "",
                                event_size=event.get("event_size") or "",
                            ))
                        except Exception:
                            pass
                    await asyncio.sleep(2)
                except Exception as exc:
                    logger.warning("Startup discovery failed for %s: %s", keywords[0], exc)
        asyncio.create_task(_run())

    @app.exception_handler(404)
    async def custom_not_found(request: Request, _exc: Any) -> JSONResponse:
        return JSONResponse(
            {
                "ok": False,
                "error": "Not found",
                "path": request.url.path,
                "suggested": [
                    "/",
                    "/discover",
                    "/final-plan",
                    "/find-my-next-market",
                    "/signin",
                    "/signup",
                    "/dashboard",
                    "/health",
                ],
            },
            status_code=404,
        )

    if site_dir.exists():
        app.mount("/site", StaticFiles(directory=site_dir), name="site")
        assets_dir = site_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    def serve_page(filename: str) -> Response:
        page_path = site_dir / filename
        if page_path.exists():
            return FileResponse(page_path)
        return JSONResponse(
            {
                "service": SERVER_INFO["name"],
                "status": "ok",
                "message": f"Page not found: {filename}",
            },
            status_code=404,
        )

    for route_path, filename in PUBLIC_PAGE_ROUTES.items():
        async def _page_handler(filename: str = filename) -> Response:
            return serve_page(filename)

        app.add_api_route(route_path, _page_handler, methods=["GET"], response_class=FileResponse)

    @app.get("/dashboard", response_class=FileResponse)
    async def handle_dashboard_page(request: Request) -> Response:
        user = _require_user(request)
        if not user:
            return RedirectResponse(url="/signin", status_code=302)
        if _normalized_role(user) != "vendor":
            return RedirectResponse(url=_dashboard_path_for_role(_normalized_role(user)), status_code=302)
        return serve_page("dashboard.html")

    @app.get("/market-dashboard", response_class=FileResponse)
    async def handle_market_dashboard_page(request: Request) -> Response:
        user = _require_user(request)
        if not user:
            return RedirectResponse(url="/signin", status_code=302)
        if _normalized_role(user) != "market":
            return RedirectResponse(url=_dashboard_path_for_role(_normalized_role(user)), status_code=302)
        return serve_page("market-dashboard.html")

    @app.get("/shopper-dashboard", response_class=FileResponse)
    async def handle_shopper_dashboard_page(request: Request) -> Response:
        user = _require_user(request)
        if not user:
            return RedirectResponse(url="/signin", status_code=302)
        if _normalized_role(user) != "shopper":
            return RedirectResponse(url=_dashboard_path_for_role(_normalized_role(user)), status_code=302)
        return serve_page("shopper-dashboard.html")

    @app.get("/shop/{username}")
    async def handle_vendor_shop_page(username: str) -> Response:
        return serve_page("vendor-shop.html")

    @app.get("/api/users/{username}")
    async def handle_public_user_profile(username: str) -> JSONResponse:
        user = get_user_by_username(username)
        if not user or _normalized_role(user) != "vendor":
            return JSONResponse({"error": "Vendor not found."}, status_code=404)
        return JSONResponse({
            "id": user["id"],
            "username": user["username"],
            "display_name": user.get("display_name") or user["username"],
            "bio": user.get("bio") or "",
            "role": _normalized_role(user),
        })

    @app.get("/enter/{role_name}")
    async def handle_role_entry(request: Request, role_name: str) -> Response:
        normalized = str(role_name or "").strip().lower()
        if normalized not in {"vendor", "market", "shopper"}:
            return RedirectResponse(url="/", status_code=302)
        user = _current_user(request)
        if user and _normalized_role(user) == normalized:
            return RedirectResponse(url=_dashboard_path_for_role(normalized), status_code=302)
        return RedirectResponse(url=_role_entry_path(normalized), status_code=302)

    @app.get("/public-comparison.json")
    async def handle_public_comparison() -> Response:
        comparison = site_dir / "public-comparison.json"
        if comparison.exists():
            return FileResponse(comparison)
        return JSONResponse(
            {
                "summary": "Run strategy/competitor_analysis.py to generate public-comparison.json.",
                "items": [],
            }
        )

    @app.get("/health")
    async def handle_health() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "server": SERVER_INFO["name"],
                "version": SERVER_INFO["version"],
                "protocol": PROTOCOL_VERSION,
                "tools": len(ALL_TOOLS),
                "connected_clients": sse_transport.connected_clients,
                "database": backend_summary(),
                "event_count": len(stored_search_events({})),
            }
        )

    @app.post("/api/admin/refresh-events")
    async def handle_refresh_events() -> JSONResponse:
        """Trigger live MCP discovery for Kansas City and save results. Returns what was found."""
        discover_handler = ALL_HANDLERS.get("discover_events")
        if not discover_handler:
            return JSONResponse({"ok": False, "error": "discover_events handler not found"}, status_code=500)

        keyword_sets = [
            ["popup market", "makers market", "craft fair", "vendor fair", "flea market"],
            ["oddity market", "curiosities market", "oddities and curiosities", "horror convention"],
            ["rave", "electronic music festival", "underground event vendor"],
            ["tattoo convention", "tattoo expo", "tattoo festival"],
            ["anime convention", "comic con", "cosplay convention"],
            ["music festival vendor", "festival vendor application", "concert vendor"],
            ["night market", "art market", "vintage market", "holiday market"],
            ["street fair vendor", "outdoor vendor event", "vendor expo"],
        ]

        saved = 0
        found: list[dict[str, Any]] = []
        errors: list[str] = []

        for keywords in keyword_sets:
            try:
                raw = await discover_handler(
                    city="Kansas City",
                    state="MO",
                    keywords=keywords,
                    sources=["google", "eventbrite", "facebook_events", "public_event_listings"],
                )
                payload = json.loads(raw) if isinstance(raw, str) else raw
                events = payload.get("events", [])
                for event in events:
                    try:
                        from storage_events import Event, upsert_event
                        upsert_event(Event(
                            id=event.get("id") or event.get("event_id") or "",
                            name=event.get("name") or event.get("title") or "",
                            city=event.get("city") or "Kansas City",
                            state=event.get("state") or "MO",
                            date=event.get("date") or event.get("start_date") or "",
                            vendor_count=event.get("vendor_count"),
                            estimated_traffic=event.get("estimated_traffic"),
                            booth_price=event.get("booth_price") or event.get("vendor_fee"),
                            application_link=event.get("application_link") or event.get("url") or event.get("source_url") or "",
                            source_url=event.get("source_url") or event.get("url") or "",
                            vendor_category=event.get("vendor_category") or event.get("event_type") or "",
                            event_size=event.get("event_size") or "",
                        ))
                        saved += 1
                        found.append({"name": event.get("name") or event.get("title"), "url": event.get("url") or event.get("source_url"), "keywords": keywords[0]})
                    except Exception as exc:
                        errors.append(str(exc))
            except Exception as exc:
                errors.append(f"{keywords[0]}: {exc}")

        total_in_db = len(stored_search_events({}))
        return JSONResponse({"ok": True, "saved": saved, "total_in_db": total_in_db, "found": found, "errors": errors})

    @app.get("/api/auth/me")
    async def handle_auth_me(request: Request) -> JSONResponse:
        user = _current_user(request)
        return JSONResponse({"ok": True, "authenticated": bool(user), "user": user})

    @app.post("/api/auth/signup")
    async def handle_auth_signup(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _validation_error("Invalid JSON body")

        name = str(body.get("name", "")).strip()
        email = str(body.get("email", "")).strip()
        username = str(body.get("username", "")).strip()
        password = str(body.get("password", ""))
        role = str(body.get("role", "vendor")).strip().lower()
        interests = str(body.get("interests", "")).strip()
        bio = str(body.get("bio", "")).strip()

        if not name or not email or not username or not password:
            return _validation_error("Name, email, username, and password are required.")
        if role not in {"vendor", "market", "shopper"}:
            return _validation_error("Choose whether you're a vendor, event organizer, or shopper.")
        if not _validate_email(email):
            return _validation_error("Enter a valid email address.")
        if not re.fullmatch(r"[a-z0-9_]{3,32}", username.lower()):
            return _validation_error("Username must be 3-32 characters and use only letters, numbers, or underscores.")
        if len(username) < 3:
            return _validation_error("Username must be at least 3 characters.")
        if len(password) < 8:
            return _validation_error("Password must be at least 8 characters.")

        try:
            user = create_user(name, email, username, password, role, interests, bio)
        except ValueError as exc:
            return _validation_error(str(exc), status_code=409)

        response = JSONResponse({"ok": True, "user": user})
        _set_session_cookie(response, int(user["id"]))
        return response

    @app.get("/api/auth/username-availability")
    async def handle_username_availability(username: str = "") -> JSONResponse:
        normalized = username.strip().lower()
        if not normalized:
            return JSONResponse({"ok": True, "available": False, "message": "Enter a username to check availability."})
        if not re.fullmatch(r"[a-z0-9_]{3,32}", normalized):
            return JSONResponse(
                {
                    "ok": True,
                    "available": False,
                    "message": "Use 3-32 lowercase letters, numbers, or underscores.",
                }
            )
        available = is_username_available(normalized)
        return JSONResponse(
            {
                "ok": True,
                "available": available,
                "normalized": normalized,
                "message": "Username is available." if available else "That username is already taken.",
            }
        )

    @app.post("/api/auth/signin")
    async def handle_auth_signin(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _validation_error("Invalid JSON body")

        identifier = str(body.get("identifier", body.get("email", ""))).strip()
        password = str(body.get("password", ""))
        if not identifier or not password:
            return _validation_error("Username or email and password are required.")

        user = authenticate_user(identifier, password)
        if not user:
            return _validation_error("Incorrect username, email, or password.", status_code=401)

        response = JSONResponse({"ok": True, "user": user})
        _set_session_cookie(response, int(user["id"]))
        return response

    @app.post("/api/auth/dev-login")
    async def handle_auth_dev_login(request: Request) -> JSONResponse:
        if not _dev_login_enabled(request):
            return _validation_error("Temporary test access is only available in local development.", status_code=403)

        try:
            body = await request.json()
        except json.JSONDecodeError:
            body = {}

        role = str(body.get("role", "vendor")).strip().lower() or "vendor"
        if role not in {"vendor", "market", "shopper"}:
            return _validation_error("Choose vendor, organizer, or shopper test access.")

        username = f"temp_{role}"
        user = get_user_by_username(username)
        if not user:
            role_copy = "Organizer" if role == "market" else role.capitalize()
            user = create_user(
                f"Temp {role_copy}",
                f"{username}@vendoratlas.test",
                username,
                "tempaccess123",
                role,
                "temporary testing account",
                "Temporary local testing account.",
            )

        if role == "vendor":
            ensure_vendor_marketplace_profile(
                username=username,
                email=f"{username}@vendoratlas.test",
                business_name="Temp Vendor Studio",
                description="Temporary local testing vendor profile with seeded analytics.",
                category="Accessories",
                location="Austin, TX",
            )

        response = JSONResponse({"ok": True, "user": user, "temporary": True})
        _set_session_cookie(response, int(user["id"]))
        return response

    @app.get("/u/{username}", response_class=FileResponse)
    async def handle_public_profile(username: str) -> Response:
        user = get_user_by_username(username)
        if not user:
            raise HTTPException(status_code=404, detail="Profile not found.")
        return serve_page("profile.html")

    @app.get("/event-details/{event_id}", response_class=FileResponse)
    async def handle_event_detail_page(event_id: str) -> Response:
        event = get_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found.")
        return serve_page("event.html")

    @app.get("/api/vendors/{username}")
    async def handle_vendor_profile(request: Request, username: str) -> JSONResponse:
        vendor = get_user_by_username(username)
        if not vendor or _normalized_role(vendor) != "vendor":
            return _validation_error("Vendor not found.", status_code=404)
        viewer = _current_user(request)
        return JSONResponse({"ok": True, "vendor": _serialize_vendor_profile(vendor, viewer)})

    @app.get("/api/vendors/{username}/products")
    async def handle_vendor_products(username: str) -> JSONResponse:
        vendor = get_user_by_username(username)
        if not vendor or _normalized_role(vendor) != "vendor":
            return _validation_error("Vendor not found.", status_code=404)

        conn = get_shopify_connection(int(vendor["id"]))
        storefront_token = get_shopify_storefront_access_token(int(vendor["id"]))
        if not conn or not storefront_token:
            return JSONResponse(
                {
                    "ok": True,
                    "connected": False,
                    "shop": "",
                    "products": [],
                    "message": "This vendor has not connected Shopify products yet.",
                }
            )

        shop_domain = conn.get("storefront_domain") or conn.get("shop_domain") or ""
        if not shop_domain:
            return JSONResponse(
                {
                    "ok": True,
                    "connected": False,
                    "shop": "",
                    "products": [],
                    "message": "This vendor has not connected Shopify products yet.",
                }
            )
        try:
            products = fetch_storefront_products(shop_domain, storefront_token, limit=10)
        except Exception as exc:
            logger.warning("Shopify storefront fetch failed for @%s: %s", vendor.get("username"), exc)
            return JSONResponse(
                {
                    "ok": False,
                    "connected": True,
                    "shop": shop_domain,
                    "products": [],
                    "message": "Try again soon while this vendor's Shopify products refresh.",
                    "error": "Products are temporarily unavailable right now.",
                },
                status_code=502,
            )
        return JSONResponse(
            {
                "ok": True,
                "connected": True,
                "shop": shop_domain,
                "products": products,
                "message": "Products are ready to browse." if products else "This vendor's storefront is connected, but no products are published yet.",
            }
        )

    @app.post("/api/vendors/{vendor_id}/follow")
    async def handle_follow_vendor(request: Request, vendor_id: int) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        if _normalized_role(user) not in {"shopper", "market"}:
            return _validation_error("Only shoppers and organizers can follow vendors.", status_code=403)
        vendor = get_user_by_id(vendor_id)
        if not vendor or _normalized_role(vendor) != "vendor":
            return _validation_error("Vendor not found.", status_code=404)
        follow_vendor(int(user["id"]), vendor_id)
        create_notification(
            vendor_id,
            "new_follower",
            "You have a new follower",
            f"@{user.get('username', '')} is now following your vendor profile.",
            related_user_id=int(user["id"]),
        )
        return JSONResponse({"ok": True, "following": True})

    @app.delete("/api/vendors/{vendor_id}/follow")
    async def handle_unfollow_vendor(request: Request, vendor_id: int) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        if _normalized_role(user) not in {"shopper", "market"}:
            return _validation_error("Only shoppers and organizers can unfollow vendors.", status_code=403)
        unfollow_vendor(int(user["id"]), vendor_id)
        return JSONResponse({"ok": True, "following": False})

    @app.get("/api/role-home")
    async def handle_role_home(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        role = _normalized_role(user)
        return JSONResponse({"ok": True, "role": role, "dashboard_path": _dashboard_path_for_role(role)})

    @app.post("/api/auth/logout")
    async def handle_auth_logout(request: Request) -> JSONResponse:
        response = JSONResponse({"ok": True})
        _clear_session_cookie(response)
        return response

    @app.get("/api/dashboard")
    async def handle_dashboard_data(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        role = _normalized_role(user)
        if role != "vendor":
            return JSONResponse(
                {
                    "ok": True,
                    "role": role,
                    "user": user,
                    "dashboard_path": _dashboard_path_for_role(role),
                }
            )
        saved_markets = get_saved_markets_for_user(int(user["id"]))
        availability = get_availability_for_user(int(user["id"]))
        fallback_events = run_search_events({"city": "", "state": "", "start_date": "", "end_date": ""}).get("events", [])
        saved_with_recurrence = _apply_recurrence_signals(saved_markets)
        fallback_with_recurrence = _apply_recurrence_signals(fallback_events)
        return JSONResponse(
            {
                "ok": True,
                "role": role,
                "user": user,
                "saved_markets": saved_with_recurrence,
                "saved_count": len(saved_with_recurrence),
                "availability": availability,
                "recommended_markets": _recommend_markets_for_schedule(
                    availability,
                    saved_with_recurrence,
                    fallback_with_recurrence,
                ),
                "recurring_series": _build_recurrence_summary(saved_with_recurrence or fallback_with_recurrence),
            }
        )

    @app.get("/api/vendor/follower-events")
    async def handle_vendor_follower_events(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        if _normalized_role(user) != "vendor":
            return _validation_error("Vendor access required.", status_code=403)

        saved_markets = _apply_recurrence_signals(get_saved_markets_for_user(int(user["id"])))
        shared_events = get_vendor_visible_events(int(user["id"]), visible_only=False)
        shared_ids = {str(event["id"]): event for event in shared_events}
        rows = []
        for event in saved_markets:
            entry = {
                **event,
                "visible_to_followers": bool(shared_ids.get(str(event["id"]), {}).get("visible_to_followers", False)),
            }
            rows.append(entry)
        return JSONResponse({"ok": True, "events": rows})

    @app.post("/api/vendor/follower-events")
    async def handle_vendor_follower_event_update(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        if _normalized_role(user) != "vendor":
            return _validation_error("Vendor access required.", status_code=403)

        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _validation_error("Invalid JSON body")

        event_id = str(body.get("event_id", "")).strip()
        visible = bool(body.get("visible_to_followers", True))
        if not event_id:
            return _validation_error("event_id is required.")

        set_vendor_event_visibility(int(user["id"]), event_id, visible)
        event = next((item for item in get_saved_markets_for_user(int(user["id"])) if str(item["id"]) == event_id), None)
        if visible and event:
            for follower_id in get_follower_user_ids_for_vendor(int(user["id"])):
                create_notification(
                    follower_id,
                    "vendor_event_added",
                    f"{user.get('name', 'A vendor')} added an event",
                    f"{user.get('name', 'A vendor')} will be at {event.get('name', 'an event')} in {event.get('city', '')}.",
                    related_user_id=int(user["id"]),
                    related_event_id=event_id,
                )
        return JSONResponse({"ok": True, "event_id": event_id, "visible_to_followers": visible})

    @app.get("/api/market-dashboard")
    async def handle_market_dashboard_data(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        if _normalized_role(user) != "market":
            return _validation_error("Market organizer access required.", status_code=403)

        organizer_events = [
            event
            for event in stored_search_events({})
            if str(event.get("source_url") or "") == f"organizer://{int(user['id'])}"
        ]
        if not organizer_events:
            organizer_events = run_search_events({"city": "", "state": "", "start_date": "", "end_date": ""}).get("events", [])[:4]
        event_names = {str(event.get("name") or "").strip().lower() for event in organizer_events if event.get("name")}
        applications = [
            {
                "id": item.get("id"),
                "vendor_name": item.get("vendor_name") or "Vendor",
                "category": item.get("vendor_category") or "Vendor",
                "status": str(item.get("status") or "Applied").replace("accepted", "Accepted").replace("rejected", "Rejected").replace("waitlisted", "Waitlisted").replace("applied", "Applied"),
                "notes": item.get("event_title") or "Application received.",
                "message": item.get("message") or "",
            }
            for item in list_marketplace_applications()
            if str(item.get("event_title") or "").strip().lower() in event_names
        ]
        analytics = {
            "active_events": len(organizer_events),
            "applications": len(applications),
            "accepted_vendors": sum(1 for item in applications if item.get("status") == "Accepted"),
            "views": 0,
        }
        return JSONResponse(
            {
                "ok": True,
                "role": "market",
                "user": user,
                "analytics": analytics,
                "events": organizer_events,
                "applications": applications,
            }
        )

    @app.get("/api/market/events")
    async def handle_market_events(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        if _normalized_role(user) != "market":
            return _validation_error("Market organizer access required.", status_code=403)

        events = [
            event
            for event in stored_search_events({})
            if str(event.get("source_url") or "") == f"organizer://{int(user['id'])}"
        ]
        return JSONResponse({"ok": True, "events": events})

    @app.post("/api/market/events")
    async def handle_market_event_create(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        if _normalized_role(user) != "market":
            return _validation_error("Market organizer access required.", status_code=403)

        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _validation_error("Invalid JSON body")

        name = str(body.get("name", "")).strip()
        city = str(body.get("city", "")).strip()
        state = str(body.get("state", "")).strip()
        date = str(body.get("date", "")).strip()
        if not all([name, city, state, date]):
            return _validation_error("Name, city, state, and date are required.")

        event_id = f"org-{int(user['id'])}-{secrets.token_hex(6)}"
        event = StoredEvent(
            id=event_id,
            name=name,
            city=city,
            state=state,
            date=date,
            vendor_count=int(body.get("vendor_count") or 0) or None,
            estimated_traffic=int(body.get("estimated_traffic") or 0) or None,
            booth_price=float(body.get("booth_price") or 0) or None,
            application_link=str(body.get("application_link", "")).strip() or None,
            organizer_contact=str(body.get("organizer_contact", "")).strip() or user.get("email"),
            popularity_score=int(body.get("popularity_score") or 70) or 70,
            source_url=f"organizer://{int(user['id'])}",
            vendor_category=str(body.get("vendor_category", "")).strip() or None,
            event_size=str(body.get("event_size", "")).strip() or None,
        )
        upsert_event(event)
        return JSONResponse({"ok": True, "event": event.to_dict()})

    @app.put("/api/market/events/{event_id}")
    async def handle_market_event_update(request: Request, event_id: str) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        if _normalized_role(user) != "market":
            return _validation_error("Market organizer access required.", status_code=403)

        existing = get_event_by_id(event_id)
        if not existing:
            return _validation_error("Event not found.", status_code=404)
        if str(existing.get("source_url") or "") != f"organizer://{int(user['id'])}":
            return _validation_error("You can only edit your own events.", status_code=403)

        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _validation_error("Invalid JSON body")

        name = str(body.get("name", existing.get("name", ""))).strip()
        city = str(body.get("city", existing.get("city", ""))).strip()
        state = str(body.get("state", existing.get("state", ""))).strip()
        date = str(body.get("date", existing.get("date", ""))).strip()
        if not all([name, city, state, date]):
            return _validation_error("Name, city, state, and date are required.")

        event = StoredEvent(
            id=event_id,
            name=name,
            city=city,
            state=state,
            date=date,
            vendor_count=int(body.get("vendor_count") or existing.get("vendor_count") or 0) or None,
            estimated_traffic=int(body.get("estimated_traffic") or existing.get("estimated_traffic") or 0) or None,
            booth_price=float(body.get("booth_price") or existing.get("booth_price") or 0) or None,
            application_link=str(body.get("application_link", existing.get("application_link", ""))).strip() or None,
            organizer_contact=str(body.get("organizer_contact", existing.get("organizer_contact", ""))).strip() or user.get("email"),
            popularity_score=int(body.get("popularity_score") or existing.get("popularity_score") or 70) or 70,
            source_url=f"organizer://{int(user['id'])}",
            vendor_category=str(body.get("vendor_category", existing.get("vendor_category", ""))).strip() or None,
            event_size=str(body.get("event_size", existing.get("event_size", ""))).strip() or None,
        )
        upsert_event(event)
        return JSONResponse({"ok": True, "event": event.to_dict()})

    @app.get("/api/shopper-dashboard")
    async def handle_shopper_dashboard_data(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        if _normalized_role(user) != "shopper":
            return _validation_error("Shopper access required.", status_code=403)

        events = run_search_events({"city": "", "state": "", "start_date": "", "end_date": ""}).get("events", [])[:8]
        featured_vendor_candidates = list_public_users(role="vendor", limit=6)
        featured_vendors = [
            _serialize_vendor_profile(candidate, user) | {"category": candidate.get("interests") or candidate.get("bio") or "Vendor", "note": candidate.get("bio") or ""}
            for candidate in featured_vendor_candidates
            if candidate and _normalized_role(candidate) == "vendor"
        ][:4]
        return JSONResponse(
            {
                "ok": True,
                "role": "shopper",
                "user": user,
                "events": _apply_recurrence_signals(events),
                "featured_vendors": featured_vendors,
                "rsvped_events": _apply_recurrence_signals(get_rsvped_events_for_user(int(user["id"]))),
            }
        )

    @app.get("/api/shopper/following")
    async def handle_shopper_following_feed(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        if _normalized_role(user) not in {"shopper", "market"}:
            return _validation_error("Shopper or organizer access required.", status_code=403)

        followed_vendors = get_followed_vendors_for_shopper(int(user["id"]))
        vendor_cards = [_serialize_vendor_profile(vendor, user) for vendor in followed_vendors]
        feed_events: list[dict[str, Any]] = []
        notifications = get_notifications_for_user(int(user["id"]))

        today = datetime.now().date()
        for vendor in vendor_cards:
            for event in vendor.get("upcoming_events", []):
                feed_events.append({**event, "vendor": {"id": vendor["id"], "name": vendor["name"], "username": vendor["username"]}})
                try:
                    event_date = datetime.strptime(str(event.get("date") or ""), "%Y-%m-%d").date()
                except ValueError:
                    event_date = None
                if event_date and 0 <= (event_date - today).days <= 14:
                    notifications.append(
                        {
                            "id": f"near-{vendor['id']}-{event['id']}",
                            "kind": "upcoming_event_near",
                            "title": "A followed vendor has an event coming up",
                            "body": f"{vendor['name']} will be at {event.get('name', 'an event')} on {event.get('date', '')}.",
                            "related_user_id": vendor["id"],
                            "related_event_id": event["id"],
                            "created_at": str(today),
                            "read_at": "",
                        }
                    )

        return JSONResponse(
            {
                "ok": True,
                "vendors": vendor_cards,
                "events": sorted(feed_events, key=lambda item: (item.get("date") or "", item.get("name") or "")),
                "notifications": notifications[:20],
            }
        )

    @app.get("/api/events/{event_id}/followed-vendors")
    async def handle_followed_vendors_for_event(request: Request, event_id: str) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        if _normalized_role(user) not in {"shopper", "market"}:
            return _validation_error("Shopper or organizer access required.", status_code=403)

        vendors = []
        for vendor in get_followed_vendors_for_shopper(int(user["id"])):
            shared_events = get_vendor_visible_events(int(vendor["id"]), visible_only=True)
            if any(str(event["id"]) == str(event_id) for event in shared_events):
                vendors.append(_serialize_vendor_profile(vendor, user))
        return JSONResponse({"ok": True, "vendors": vendors})

    @app.get("/api/events/{event_id}")
    async def handle_event_detail(request: Request, event_id: str) -> JSONResponse:
        event = get_event_by_id(event_id)
        if not event:
            return _validation_error("Event not found.", status_code=404)
        user = _current_user(request)
        ranked_event = _generic_event_rank(event, user)
        is_saved = False
        is_rsvped = False
        if user:
            is_saved = any(str(item.get("id")) == str(event_id) for item in get_saved_markets_for_user(int(user["id"])))
            if _normalized_role(user) == "shopper":
                is_rsvped = is_event_rsvped_by_user(int(user["id"]), event_id)
        related = _rank_events_for_user([
            item
            for item in stored_search_events(
                {
                    "city": event.get("city", ""),
                    "vendor_category": event.get("vendor_category", ""),
                }
            )
            if str(item.get("id")) != str(event_id)
        ], user)[:3]
        return JSONResponse({"ok": True, "event": ranked_event, "is_saved": is_saved, "is_rsvped": is_rsvped, "related_events": related})

    @app.post("/api/events/{event_id}/rsvp")
    async def handle_event_rsvp(request: Request, event_id: str) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        if _normalized_role(user) != "shopper":
            return _validation_error("Shopper access required.", status_code=403)
        event = get_event_by_id(event_id)
        if not event:
            return _validation_error("Event not found.", status_code=404)
        rsvp_event_for_user(int(user["id"]), event_id)
        return JSONResponse({"ok": True, "event_id": event_id, "rsvped": True})

    @app.delete("/api/events/{event_id}/rsvp")
    async def handle_event_rsvp_delete(request: Request, event_id: str) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        if _normalized_role(user) != "shopper":
            return _validation_error("Shopper access required.", status_code=403)
        remove_rsvp_for_user(int(user["id"]), event_id)
        return JSONResponse({"ok": True, "event_id": event_id, "rsvped": False})

    @app.get("/api/events")
    async def handle_events_index(request: Request, limit: int = 25) -> JSONResponse:
        user = _current_user(request)
        cap = max(1, min(int(limit or 25), 100))
        events = _rank_events_for_user(
            _apply_recurrence_signals(stored_search_events({})[:cap]),
            user,
        )
        return JSONResponse({"ok": True, "count": len(events), "events": events})

    @app.get("/api/users")
    async def handle_users_index(request: Request, role: str = "", limit: int = 25) -> JSONResponse:
        users = list_public_users(role=role, limit=limit)
        return JSONResponse(
            {
                "ok": True,
                "count": len(users),
                "users": users,
                "authenticated": bool(_current_user(request)),
                "current_user": _current_user(request),
            }
        )

    @app.get("/events")
    async def handle_marketplace_events(
        category: str = "",
        location: str = "",
        vendor_fee: float | None = None,
    ) -> JSONResponse:
        events = list_marketplace_events(category=category, location=location, max_vendor_fee=vendor_fee)
        return JSONResponse({"ok": True, "events": events, "count": len(events)})

    @app.get("/events/{event_id}")
    async def handle_marketplace_event_detail(event_id: str) -> JSONResponse:
        event = get_marketplace_event(event_id)
        if not event:
            return _validation_error("Event not found.", status_code=404)
        return JSONResponse({"ok": True, "event": event})

    @app.post("/events")
    async def handle_marketplace_event_create(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _validation_error("Invalid JSON body")

        required = ("organizer_id", "title", "location", "start_date", "end_date")
        if not all(str(body.get(field, "")).strip() for field in required):
            return _validation_error("organizer_id, title, location, start_date, and end_date are required.")
        event = create_marketplace_event(body)
        return JSONResponse({"ok": True, "event": event}, status_code=201)

    @app.get("/vendors/{vendor_id}")
    async def handle_marketplace_vendor_detail(vendor_id: str) -> JSONResponse:
        vendor = get_marketplace_vendor(vendor_id)
        if not vendor:
            return _validation_error("Vendor not found.", status_code=404)
        return JSONResponse({"ok": True, "vendor": vendor})

    @app.post("/vendors")
    async def handle_marketplace_vendor_create(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _validation_error("Invalid JSON body")

        required = ("email", "username", "business_name")
        if not all(str(body.get(field, "")).strip() for field in required):
            return _validation_error("email, username, and business_name are required.")
        vendor = create_marketplace_vendor(body)
        return JSONResponse({"ok": True, "vendor": vendor}, status_code=201)

    @app.post("/applications")
    async def handle_marketplace_application_create(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _validation_error("Invalid JSON body")

        required = ("event_id", "vendor_id")
        if not all(str(body.get(field, "")).strip() for field in required):
            return _validation_error("event_id and vendor_id are required.")
        status = str(body.get("status", "applied")).strip().lower() or "applied"
        if status not in {"applied", "accepted", "rejected", "waitlisted"}:
            return _validation_error("status must be applied, accepted, rejected, or waitlisted.")
        application = create_marketplace_application({**body, "status": status})
        return JSONResponse({"ok": True, "application": application}, status_code=201)

    @app.get("/applications")
    async def handle_marketplace_applications(vendor_id: str = "") -> JSONResponse:
        applications = list_marketplace_applications(vendor_id=vendor_id)
        return JSONResponse({"ok": True, "applications": applications, "count": len(applications)})

    @app.post("/saved-events")
    async def handle_marketplace_saved_event_create(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _validation_error("Invalid JSON body")

        user_id = str(body.get("user_id", "")).strip()
        event_id = str(body.get("event_id", "")).strip()
        if not user_id or not event_id:
            return _validation_error("user_id and event_id are required.")
        saved = save_marketplace_event_for_user(user_id, event_id)
        return JSONResponse(saved, status_code=201)

    @app.get("/saved-events")
    async def handle_marketplace_saved_events(user_id: str = "") -> JSONResponse:
        if not user_id:
            return _validation_error("user_id is required.")
        events = list_marketplace_saved_events(user_id)
        return JSONResponse({"ok": True, "saved_events": events, "count": len(events)})

    @app.get("/vendor-stats")
    async def handle_vendor_stats(vendor_id: str = "") -> JSONResponse:
        if not vendor_id:
            return _validation_error("vendor_id is required.")
        stats = get_marketplace_vendor_stats(vendor_id)
        return JSONResponse({"ok": True, **stats})

    @app.get("/api/analytics")
    async def handle_role_analytics(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)

        role = _normalized_role(user)
        username = str(user.get("username") or "").strip()

        if role == "vendor":
            vendor = get_vendor_by_username(username) or get_first_vendor()
            if not vendor:
                return JSONResponse({"ok": True, "role": role, "summary": {}, "events": [], "vendor": None})
            payload = get_marketplace_vendor_stats(str(vendor["id"]))
            return JSONResponse({"ok": True, "role": role, "vendor": vendor, **payload})

        if role == "market":
            organizer = get_marketplace_user_by_username(username) or get_first_marketplace_user("organizer")
            if not organizer:
                return JSONResponse({"ok": True, "role": role, "summary": {}, "events": [], "organizer": None})
            payload = get_marketplace_organizer_analytics(str(organizer["id"]))
            return JSONResponse({"ok": True, "role": role, "organizer": organizer, **payload})

        shopper = get_marketplace_user_by_username(username) or get_first_marketplace_user("shopper")
        if not shopper:
            return JSONResponse(
                {"ok": True, "role": role, "summary": {"events_saved": 0, "followed_vendors": 0, "upcoming_events": 0}, "saved_events": [], "followed_vendors": []}
            )
        payload = get_marketplace_shopper_analytics(str(shopper["id"]))
        return JSONResponse({"ok": True, "role": role, "shopper": shopper, **payload})

    @app.get("/api/vendor-tracker")
    async def handle_vendor_tracker(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)

        saved_markets = get_saved_markets_for_user(int(user["id"]))
        fallback_events = run_search_events({"city": "", "state": "", "start_date": "", "end_date": ""}).get("events", [])
        fallback_tracker = _default_vendor_tracker(saved_markets, fallback_events)
        stored = get_vendor_tracker_for_user(int(user["id"]))
        tracker = _normalize_tracker_payload(stored or fallback_tracker, fallback_tracker)
        if not stored:
            tracker = upsert_vendor_tracker_for_user(int(user["id"]), tracker)
        return JSONResponse({"ok": True, "tracker": tracker})

    @app.api_route("/vendor-tracker", methods=["GET", "POST"])
    async def handle_vendor_tracker_alias() -> RedirectResponse:
        return RedirectResponse(url="/api/vendor-tracker", status_code=307)

    @app.post("/api/vendor-tracker")
    async def handle_vendor_tracker_update(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)

        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _validation_error("Invalid JSON body")

        if not isinstance(body, dict):
            return _validation_error("Tracker payload must be an object.")

        saved_markets = get_saved_markets_for_user(int(user["id"]))
        fallback_events = run_search_events({"city": "", "state": "", "start_date": "", "end_date": ""}).get("events", [])
        fallback_tracker = _default_vendor_tracker(saved_markets, fallback_events)
        tracker = _normalize_tracker_payload(body, fallback_tracker)
        stored = upsert_vendor_tracker_for_user(int(user["id"]), tracker)
        return JSONResponse({"ok": True, "tracker": stored})

    @app.post("/api/profile")
    async def handle_profile_update(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)

        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _validation_error("Invalid JSON body")

        name = str(body.get("name", "")).strip()
        interests = str(body.get("interests", "")).strip()
        bio = str(body.get("bio", "")).strip()
        if not name:
            return _validation_error("Name is required.")

        updated = update_user_profile(int(user["id"]), name, interests, bio)
        return JSONResponse({"ok": True, "user": updated})

    @app.get("/api/saved-markets")
    async def handle_saved_markets(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        saved_markets = get_saved_markets_for_user(int(user["id"]))
        return JSONResponse({"ok": True, "saved_markets": saved_markets})

    @app.get("/api/availability")
    async def handle_availability(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        availability = get_availability_for_user(int(user["id"]))
        return JSONResponse({"ok": True, "availability": availability})

    @app.post("/api/availability")
    async def handle_availability_update(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)

        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _validation_error("Invalid JSON body")

        weekdays = body.get("weekdays", [])
        preferred_months = body.get("preferred_months", [])
        weekly_capacity = int(body.get("weekly_capacity", 2) or 2)
        monthly_goal = int(body.get("monthly_goal", 6) or 6)
        notes = str(body.get("notes", ""))

        if not isinstance(weekdays, list) or not isinstance(preferred_months, list):
            return _validation_error("weekdays and preferred_months must be arrays.")

        availability = upsert_availability_for_user(
            int(user["id"]),
            [str(item) for item in weekdays],
            [str(item) for item in preferred_months],
            max(1, weekly_capacity),
            max(1, monthly_goal),
            notes,
        )
        saved_markets = get_saved_markets_for_user(int(user["id"]))
        fallback_events = run_search_events({"city": "", "state": "", "start_date": "", "end_date": ""}).get("events", [])
        saved_with_recurrence = _apply_recurrence_signals(saved_markets)
        fallback_with_recurrence = _apply_recurrence_signals(fallback_events)
        return JSONResponse(
            {
                "ok": True,
                "availability": availability,
                "recommended_markets": _recommend_markets_for_schedule(
                    availability,
                    saved_with_recurrence,
                    fallback_with_recurrence,
                ),
                "recurring_series": _build_recurrence_summary(saved_with_recurrence or fallback_with_recurrence),
            }
        )

    @app.post("/api/saved-markets")
    async def handle_save_market(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)

        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _validation_error("Invalid JSON body")

        event_id = str(body.get("event_id", "")).strip()
        if not event_id:
            return _validation_error("event_id is required.")

        save_market_for_user(int(user["id"]), event_id)
        saved_markets = get_saved_markets_for_user(int(user["id"]))
        return JSONResponse({"ok": True, "saved_markets": saved_markets})

    @app.delete("/api/saved-markets/{event_id}")
    async def handle_remove_saved_market(event_id: str, request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)

        remove_saved_market_for_user(int(user["id"]), event_id)
        saved_markets = get_saved_markets_for_user(int(user["id"]))
        return JSONResponse({"ok": True, "saved_markets": saved_markets})

    # --- Shopify ---
    @app.get("/api/shopify/connect")
    async def handle_shopify_connect(request: Request, shop: str = "") -> Response:
        user = _require_user(request)
        if not user:
            from urllib.parse import quote
            next_path = quote("/api/shopify/connect" + ("?shop=" + shop if shop else ""), safe="")
            return RedirectResponse(url=f"/signin?next={next_path}", status_code=302)
        config = get_config()
        if not config.shopify_api_key:
            return JSONResponse({"ok": False, "error": "Shopify is not configured."}, status_code=503)
        shop = (shop or "").strip().lower()
        if not shop:
            return _validation_error("Missing shop parameter. Example: ?shop=yourstore")
        if not shop.endswith(".myshopify.com"):
            shop = f"{shop}.myshopify.com"
        redirect_uri = f"{config.app_base_url}/api/shopify/callback"
        state = _shopify_state_encode(int(user["id"]), config.session_secret)
        url = build_authorize_url(
            shop,
            config.shopify_api_key,
            redirect_uri,
            scopes=config.shopify_scopes,
            state=state,
        )
        return RedirectResponse(url=url, status_code=302)

    @app.get("/api/shopify/callback")
    async def handle_shopify_callback(
        request: Request,
        code: str = "",
        shop: str = "",
        state: str = "",
    ) -> Response:
        config = get_config()
        user_id = _shopify_state_decode(state, config.session_secret)
        if not user_id or not code or not shop:
            return RedirectResponse(url="/final-plan?shopify=error", status_code=302)
        query = dict(request.query_params)
        if not verify_hmac(query, config.shopify_api_secret):
            return RedirectResponse(url="/final-plan?shopify=error", status_code=302)
        try:
            token_data = exchange_code_for_token(
                shop,
                code,
                config.shopify_api_key,
                config.shopify_api_secret,
            )
        except Exception as e:
            logger.exception("Shopify token exchange failed: %s", e)
            return RedirectResponse(url="/final-plan?shopify=error", status_code=302)
        access_token = token_data.get("access_token")
        if not access_token:
            return RedirectResponse(url="/final-plan?shopify=error", status_code=302)
        set_shopify_connection(user_id, shop, access_token)
        try:
            products = products_with_inventory(shop, access_token, limit=250)
            upsert_shopify_products(user_id, products)
        except Exception as e:
            logger.warning("Shopify initial product sync failed: %s", e)
        return RedirectResponse(url="/final-plan?shopify=connected", status_code=302)

    @app.get("/api/shopify/me")
    async def handle_shopify_me(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return JSONResponse({"ok": True, "connected": False, "storefront_connected": False})
        conn = get_shopify_connection(int(user["id"]))
        if not conn:
            return JSONResponse({"ok": True, "connected": False, "storefront_connected": False})
        return JSONResponse(
            {
                "ok": True,
                "connected": bool(get_shopify_access_token(int(user["id"]))),
                "shop": conn["shop_domain"],
                "storefront_connected": bool(conn.get("storefront_connected")),
                "storefront_shop": conn.get("storefront_domain", "") or conn["shop_domain"],
                "updated_at": conn.get("updated_at", ""),
            }
        )

    @app.post("/api/shopify/storefront")
    async def handle_shopify_storefront_save(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        if _normalized_role(user) != "vendor":
            return _validation_error("Vendor access required.", status_code=403)
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _validation_error("Invalid JSON body")

        shop_domain = _normalize_shopify_domain(body.get("shop_domain", ""))
        storefront_token = str(body.get("storefront_token", "")).strip()
        if not shop_domain:
            return _validation_error("Enter your Shopify shop domain.")
        if len(storefront_token) < 10:
            return _validation_error("Enter a valid Storefront access token.")

        set_shopify_storefront_connection(int(user["id"]), shop_domain, storefront_token)
        return JSONResponse(
            {
                "ok": True,
                "shop": shop_domain,
                "storefront_connected": True,
            }
        )

    @app.get("/api/shopify/products")
    async def handle_shopify_products(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        products = get_shopify_products(int(user["id"]))
        return JSONResponse({"ok": True, "products": products})

    @app.post("/api/shopify/sync")
    async def handle_shopify_sync(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        conn = get_shopify_connection(int(user["id"]))
        if not conn:
            return _validation_error("Store not connected.", status_code=400)
        token = get_shopify_access_token(int(user["id"]))
        if not token:
            return _validation_error("Store not connected.", status_code=400)
        try:
            products = products_with_inventory(conn["shop_domain"], token, limit=250)
            upsert_shopify_products(int(user["id"]), products)
        except Exception as e:
            logger.exception("Shopify sync failed: %s", e)
            return JSONResponse({"ok": False, "error": str(e)}, status_code=502)
        return JSONResponse({"ok": True, "synced": len(products)})

    @app.post("/api/shopify/disconnect")
    async def handle_shopify_disconnect(request: Request) -> JSONResponse:
        user = _require_user(request)
        if not user:
            return _validation_error("Authentication required.", status_code=401)
        disconnect_shopify(int(user["id"]))
        return JSONResponse({"ok": True})

    @app.get("/consumer/tools")
    async def handle_consumer_tools() -> JSONResponse:
        tools = [
            {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "inputSchema": tool.get("inputSchema", {}),
            }
            for tool in ALL_TOOLS
        ]
        return JSONResponse({"tools": tools, "count": len(tools)})

    @app.get("/config.json")
    async def handle_runtime_config(request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "api_base_url": str(request.base_url).rstrip("/"),
                "database": backend_summary(),
                "product": {
                    "name": SERVER_INFO["name"],
                    "pro_status": "coming_soon",
                },
                "features": {
                    "dashboard_search": True,
                    "saved_markets": True,
                    "pro_pricing_live": False,
                },
            }
        )

    @app.get("/markets/search")
    async def handle_market_search(
        city: str = "",
        state: str = "",
        date_range: str = "",
        event_size: str = "",
        vendor_category: str = "",
        distance_radius: str = "",
        start_date: str = "",
        end_date: str = "",
    ) -> JSONResponse:
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
        payload = run_search_events(filters)
        payload["markets"] = [_event_to_market_payload(event) for event in payload.get("events", [])]
        payload["result"] = json.dumps({"markets": payload["markets"]})
        payload["ok"] = True
        return JSONResponse(payload)

    @app.get("/api/find-market")
    async def handle_find_market(
        city: str = "",
        state: str = "",
        vendor_category: str = "",
        event_size: str = "",
        distance_radius: str = "",
    ) -> JSONResponse:
        payload = await _load_finder_results(
            city=city,
            state=state,
            vendor_category=vendor_category,
            event_size=event_size,
            distance_radius=distance_radius,
        )
        return JSONResponse(payload)

    @app.get("/api/listings/kansas-city")
    async def handle_kansas_city_listings() -> JSONResponse:
        payload = await _load_kansas_city_listings()
        return JSONResponse(payload)

    @app.post("/api/listings/kansas-city/evaluate")
    async def handle_kansas_city_listing_evaluation(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _validation_error("Invalid JSON body")

        payload = await _load_kansas_city_listings()
        inputs = {
            "avg_sale_price": body.get("avg_sale_price", 45),
            "avg_sales_per_event": body.get("avg_sales_per_event", 18),
            "typical_cogs": body.get("typical_cogs", 180),
            "travel_cost": body.get("travel_cost", 45),
            "booth_budget": body.get("booth_budget", 150),
            "preferred_min_profit": body.get("preferred_min_profit", 250),
            "vendor_type": body.get("vendor_type", ""),
        }

        return JSONResponse(
            {
                **payload,
                "business_inputs": inputs,
                "current_events": [_score_listing(event, inputs) for event in payload.get("current_events", [])],
                "more_events": [_score_listing(event, inputs) for event in payload.get("more_events", [])],
            }
        )

    @app.post("/consumer/run")
    async def handle_consumer_run(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({"ok": False, "error": "Invalid JSON body"}, status_code=400)

        tool_name = body.get("tool", "")
        arguments = body.get("arguments", {}) or {}
        if not tool_name:
            return JSONResponse({"ok": False, "error": "tool is required"}, status_code=400)

        handler = ALL_HANDLERS.get(tool_name)
        if not handler:
            return JSONResponse({"ok": False, "error": f"Unknown tool: {tool_name}"}, status_code=404)

        api_key = body.get("api_key", "")
        if not api_key:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                api_key = auth_header[7:]
            else:
                api_key = request.headers.get("X-API-Key", "")

        result = await billing_middleware(tool_name, arguments, api_key, handler)
        if "error" in result:
            err = result["error"]
            msg = (
                err
                if isinstance(err, str)
                else err.get("message", "Unknown error")
                if isinstance(err, dict)
                else "Unknown error"
            )
            return JSONResponse({"ok": False, "error": msg}, status_code=400)

        text = result.get("content", [{}])[0].get("text", "")
        return JSONResponse({"ok": True, "tool": tool_name, "result": text})

    @app.get("/sse")
    async def handle_sse() -> StreamingResponse:
        session_id, queue = await sse_transport.connect()

        async def event_stream() -> AsyncIterator[str]:
            try:
                while True:
                    try:
                        payload = await asyncio.wait_for(queue.get(), timeout=30)
                    except TimeoutError:
                        yield ": heartbeat\n\n"
                        continue
                    yield payload
            finally:
                await sse_transport.disconnect(session_id)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            },
        )

    @app.post("/message")
    @app.post("/messages")
    async def handle_message(request: Request) -> Response:
        session_id = request.query_params.get("sessionId", "")
        if session_id and not sse_transport.has_session(session_id):
            return JSONResponse({"error": "Unknown session"}, status_code=404)

        try:
            message = await request.json()
        except json.JSONDecodeError:
            return JSONResponse(
                {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}},
                status_code=400,
            )

        api_key = request.headers.get("X-API-Key", request.headers.get("Authorization", ""))
        if api_key.startswith("Bearer "):
            api_key = api_key[7:]

        result = await handle_jsonrpc(message, api_key, session_id)
        if result is None:
            return Response(status_code=204)

        if session_id:
            await sse_transport.send(session_id, result)

        return JSONResponse(result)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def catch_all_not_found(request: Request, full_path: str) -> JSONResponse:
        path = "/" + full_path if full_path else "/"
        return JSONResponse(
            {
                "ok": False,
                "error": "Not found",
                "path": path,
                "suggested": [
                    "/",
                    "/discover",
                    "/final-plan",
                    "/find-my-next-market",
                    "/signin",
                    "/signup",
                    "/dashboard",
                    "/health",
                ],
            },
            status_code=404,
        )

    return app


async def run_stdio() -> None:
    """Run MCP over stdin/stdout."""
    logger.info("Starting stdio transport...")
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line = await reader.readline()
        if not line:
            break

        line = line.decode("utf-8").strip()
        if not line:
            continue

        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None,
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()
            continue

        result = await handle_jsonrpc(message, api_key="stdio-local")
        if result is not None:
            sys.stdout.write(json.dumps(result) + "\n")
            sys.stdout.flush()


async def run_both(host: str, port: int) -> None:
    """Run FastAPI HTTP server and stdio transport together."""
    config = uvicorn.Config(create_app(), host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    http_task = asyncio.create_task(server.serve())
    stdio_task = asyncio.create_task(run_stdio())

    done, pending = await asyncio.wait(
        {http_task, stdio_task},
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
    for task in done:
        task.result()


def main() -> None:
    parser = argparse.ArgumentParser(description="Vendor Atlas MCP Server")
    parser.add_argument("--stdio", action="store_true", help="Run in stdio mode (for local MCP clients)")
    parser.add_argument("--both", action="store_true", help="Run both SSE and stdio transports")
    parser.add_argument("--port", type=int, default=None, help="HTTP server port (default: 3000)")
    parser.add_argument("--host", type=str, default=None, help="HTTP server host (default: 0.0.0.0)")
    args = parser.parse_args()

    config = get_config()
    port = args.port or config.port
    host = args.host or config.host

    logger.info("Starting %s v%s", SERVER_INFO["name"], SERVER_INFO["version"])
    logger.info("Registered tools: %s", [t["name"] for t in ALL_TOOLS])
    logger.info("Billing enabled: %s", billing_config.enabled)

    if args.stdio:
        asyncio.run(run_stdio())
    elif args.both:
        asyncio.run(run_both(host, port))
    else:
        uvicorn.run(create_app(), host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
