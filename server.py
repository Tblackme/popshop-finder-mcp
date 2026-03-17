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
import re
import sys
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
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
from middleware.session_manager import get_session_manager
from middleware.sync import get_sync_engine
from storage_events import init_events_db
from storage_markets import init_db
from storage_users import (
    authenticate_user,
    create_user,
    get_availability_for_user,
    get_saved_markets_for_user,
    get_user_by_id,
    init_users_db,
    remove_saved_market_for_user,
    save_market_for_user,
    update_user_profile,
    upsert_availability_for_user,
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
    "/features": "features.html",
    "/pricing": "pricing.html",
    "/about": "about.html",
    "/listings": "listings.html",
    "/find-my-next-market": "find-market.html",
    "/signin": "signin.html",
    "/signup": "signup.html",
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


def _current_user(request: Request) -> dict[str, Any] | None:
    user_id = _read_session_user_id(request)
    if not user_id:
        return None
    return get_user_by_id(int(user_id))


def _require_user(request: Request) -> dict[str, Any] | None:
    return _current_user(request)


def _validate_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))


def _validation_error(message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse({"ok": False, "error": message}, status_code=status_code)


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


def _recommend_markets_for_schedule(
    availability: dict[str, Any],
    saved_markets: list[dict[str, Any]],
    fallback_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    weekday_preferences = set(availability.get("weekdays", []))
    month_preferences = set(availability.get("preferred_months", []))
    pool = saved_markets or fallback_events
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

    return {
        "ok": True,
        "city": "Kansas City",
        "state": "MO",
        "current_events": current_events,
        "current_count": len(current_events),
        "more_events": discovered_events,
        "more_count": len(discovered_events),
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

    return {
        "ok": True,
        "filters": filters,
        "mcp_tools_used": ["search_events", "discover_events"],
        "search_results": search_events_result,
        "search_count": len(search_events_result),
        "discovered_results": discovered_events,
        "discover_count": len(discovered_events),
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
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
        if not _require_user(request):
            return RedirectResponse(url="/signin", status_code=302)
        return serve_page("dashboard.html")

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
            }
        )

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
        interests = str(body.get("interests", "")).strip()
        bio = str(body.get("bio", "")).strip()

        if not name or not email or not username or not password:
            return _validation_error("Name, email, username, and password are required.")
        if not _validate_email(email):
            return _validation_error("Enter a valid email address.")
        if len(username) < 3:
            return _validation_error("Username must be at least 3 characters.")
        if len(password) < 8:
            return _validation_error("Password must be at least 8 characters.")

        try:
            user = create_user(name, email, username, password, interests, bio)
        except ValueError as exc:
            return _validation_error(str(exc), status_code=409)

        response = JSONResponse({"ok": True, "user": user})
        _set_session_cookie(response, int(user["id"]))
        return response

    @app.post("/api/auth/signin")
    async def handle_auth_signin(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _validation_error("Invalid JSON body")

        email = str(body.get("email", "")).strip()
        password = str(body.get("password", ""))
        if not email or not password:
            return _validation_error("Email and password are required.")

        user = authenticate_user(email, password)
        if not user:
            return _validation_error("Incorrect email or password.", status_code=401)

        response = JSONResponse({"ok": True, "user": user})
        _set_session_cookie(response, int(user["id"]))
        return response

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
        saved_markets = get_saved_markets_for_user(int(user["id"]))
        availability = get_availability_for_user(int(user["id"]))
        fallback_events = run_search_events({"city": "", "state": "", "start_date": "", "end_date": ""}).get("events", [])
        return JSONResponse(
            {
                "ok": True,
                "user": user,
                "saved_markets": saved_markets,
                "saved_count": len(saved_markets),
                "availability": availability,
                "recommended_markets": _recommend_markets_for_schedule(availability, saved_markets, fallback_events),
            }
        )

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
        return JSONResponse(
            {
                "ok": True,
                "availability": availability,
                "recommended_markets": _recommend_markets_for_schedule(availability, saved_markets, fallback_events),
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
