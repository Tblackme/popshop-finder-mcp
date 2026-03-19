"""
server_ai.py — AI add-on routes for Vendor Atlas.

Registered conditionally in server.py only when AI_ENABLED=true.
None of these routes are required for the core platform to function.

Route groups:
  /api/ai/scores/*       Matching AI — event fit scoring
  /api/ai/content/*      Content AI — bio, descriptions, captions
  /api/ai/usage          Usage / rate limit info

Design rules enforced here:
  - AI never writes to core tables directly
  - All content routes return suggestions; the user must POST to a core
    route to actually save the output
  - Every route checks the appropriate sub-flag (ai_match_enabled, etc.)
    so individual features can be toggled without touching code
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers shared across routes
# ---------------------------------------------------------------------------

def _require_vendor(request: Request) -> dict[str, Any] | None:
    """Return current user if logged in as a vendor, else None."""
    user = request.session.get("user")
    if not user:
        return None
    role = str(user.get("role") or "vendor").strip().lower()
    return user if role == "vendor" else None


def _flags(request: Request) -> dict[str, bool]:
    """Read AI flags from app state (set by server.py on startup)."""
    return getattr(request.app.state, "ai_flags", {})


def _err(msg: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"ok": False, "error": msg}, status_code=status)


def _gate(request: Request, flag: str) -> JSONResponse | None:
    """Return an error response if the requested AI sub-feature is off."""
    if not _flags(request).get(flag):
        return _err(f"Feature '{flag}' is not enabled on this server.", status_code=403)
    return None


# ---------------------------------------------------------------------------
# Register all AI routes onto the app
# ---------------------------------------------------------------------------

def register_ai_routes(app: FastAPI) -> None:

    # ── MATCHING AI ──────────────────────────────────────────────────────────

    @app.post("/api/ai/scores/events")
    async def handle_score_events(request: Request) -> JSONResponse:
        """
        Score a list of events against the current vendor's profile.
        The caller POSTs a list of event objects; we return them with
        fit_score and fit_reason fields added, and persist to vendor_event_scores.

        Body: { "events": [...event objects...] }
        Returns: { "ok": true, "events": [...scored events...] }
        """
        blocked = _gate(request, "ai_match")
        if blocked:
            return blocked

        user = _require_vendor(request)
        if not user:
            return _err("Vendor login required.", status_code=401)

        try:
            body = await request.json()
        except Exception:
            return _err("Invalid JSON body.")

        events = body.get("events")
        if not isinstance(events, list):
            return _err("'events' must be an array.")
        if not events:
            return JSONResponse({"ok": True, "events": []})

        from storage_users import get_vendor_profile
        from storage_ai import score_and_store_events

        vendor_id = int(user["id"])
        vendor_profile = get_vendor_profile(vendor_id)
        scored = score_and_store_events(vendor_id, vendor_profile, events)
        return JSONResponse({"ok": True, "events": scored, "count": len(scored)})

    @app.get("/api/ai/scores/events")
    async def handle_get_event_scores(request: Request) -> JSONResponse:
        """
        Return all cached event scores for the current vendor.
        Optionally filter by ?event_ids=id1,id2,id3

        Returns: { "ok": true, "scores": { event_id: { score, reason, scored_at } } }
        """
        blocked = _gate(request, "ai_match")
        if blocked:
            return blocked

        user = _require_vendor(request)
        if not user:
            return _err("Vendor login required.", status_code=401)

        from storage_ai import get_bulk_event_scores

        vendor_id = int(user["id"])
        raw_ids = request.query_params.get("event_ids", "")
        event_ids = [e.strip() for e in raw_ids.split(",") if e.strip()] if raw_ids else []

        if not event_ids:
            return JSONResponse({"ok": True, "scores": {}})

        scores = get_bulk_event_scores(vendor_id, event_ids)
        # Slim the payload: only send what the frontend needs
        slim = {
            eid: {"score": row["score"], "reason": row["reason"], "scored_at": row["scored_at"]}
            for eid, row in scores.items()
        }
        return JSONResponse({"ok": True, "scores": slim})

    @app.post("/api/ai/scores/event/{event_id}")
    async def handle_score_single_event(request: Request, event_id: str) -> JSONResponse:
        """
        Score a single event against the vendor's profile on demand.
        Body: { "event": { ...event object... } }   (optional — will fetch from DB if omitted)
        Returns: { "ok": true, "score": int, "reason": str }
        """
        blocked = _gate(request, "ai_match")
        if blocked:
            return blocked

        user = _require_vendor(request)
        if not user:
            return _err("Vendor login required.", status_code=401)

        from storage_users import get_vendor_profile
        from storage_ai import upsert_event_score, _rule_based_score

        try:
            body = await request.json()
            event = body.get("event") or {}
        except Exception:
            event = {}

        if not event:
            # Try to fetch from DB
            try:
                from storage_events import get_event_by_id
                db_event = get_event_by_id(event_id)
                if db_event:
                    event = db_event.to_dict() if hasattr(db_event, "to_dict") else dict(db_event)
            except Exception:
                pass

        vendor_id = int(user["id"])
        vendor_profile = get_vendor_profile(vendor_id)
        event["id"] = event.get("id") or event_id
        score, reason = _rule_based_score(vendor_profile, event)
        upsert_event_score(vendor_id, event_id, score, reason)
        return JSONResponse({"ok": True, "score": score, "reason": reason, "event_id": event_id})

    # ── CONTENT AI ───────────────────────────────────────────────────────────

    @app.post("/api/ai/content/bio")
    async def handle_generate_bio(request: Request) -> JSONResponse:
        """
        Generate bio suggestions for the current vendor.
        Body: { "category": str, "location": str, "products": [str], "style": str }
        Returns: { "ok": true, "suggestions": [str, str, str] }

        Output is a SUGGESTION only — not saved until vendor POSTs to /api/vendor/shop-profile.
        """
        blocked = _gate(request, "ai_content")
        if blocked:
            return blocked

        user = _require_vendor(request)
        if not user:
            return _err("Vendor login required.", status_code=401)

        try:
            body = await request.json()
        except Exception:
            return _err("Invalid JSON body.")

        from storage_users import get_vendor_profile
        from storage_ai import get_ai_cache, set_ai_cache, log_ai_usage

        vendor_id = int(user["id"])
        profile = get_vendor_profile(vendor_id)

        category = str(body.get("category") or profile.get("category") or "")
        location = str(body.get("location") or profile.get("location") or "")
        products = body.get("products") or []
        style = str(body.get("style") or "friendly")

        cache_key = json.dumps({"category": category, "location": location, "products": products[:5], "style": style}, sort_keys=True)
        cached = get_ai_cache(vendor_id, "bio", cache_key)
        if cached:
            return JSONResponse({"ok": True, "suggestions": json.loads(cached), "cached": True})

        suggestions = await _call_content_ai(
            request=request,
            prompt=_bio_prompt(category, location, products, style),
            parse="suggestions",
        )
        if suggestions is None:
            return _err("Content AI is not available right now.", status_code=503)

        set_ai_cache(vendor_id, "bio", cache_key, json.dumps(suggestions))
        log_ai_usage(vendor_id, "bio")
        return JSONResponse({"ok": True, "suggestions": suggestions, "cached": False})

    @app.post("/api/ai/content/product-description")
    async def handle_generate_product_description(request: Request) -> JSONResponse:
        """
        Generate a product description suggestion.
        Body: { "name": str, "category": str, "price": float }
        Returns: { "ok": true, "description": str }
        """
        blocked = _gate(request, "ai_content")
        if blocked:
            return blocked

        user = _require_vendor(request)
        if not user:
            return _err("Vendor login required.", status_code=401)

        try:
            body = await request.json()
        except Exception:
            return _err("Invalid JSON body.")

        name = str(body.get("name") or "").strip()
        if not name:
            return _err("Product name is required.")

        from storage_ai import get_ai_cache, set_ai_cache, log_ai_usage

        vendor_id = int(user["id"])
        category = str(body.get("category") or "")
        price = body.get("price")

        cache_key = json.dumps({"name": name, "category": category, "price": price}, sort_keys=True)
        cached = get_ai_cache(vendor_id, "product_description", cache_key)
        if cached:
            return JSONResponse({"ok": True, "description": cached, "cached": True})

        result = await _call_content_ai(
            request=request,
            prompt=_product_desc_prompt(name, category, price),
            parse="text",
        )
        if result is None:
            return _err("Content AI is not available right now.", status_code=503)

        set_ai_cache(vendor_id, "product_description", cache_key, result)
        log_ai_usage(vendor_id, "product_description")
        return JSONResponse({"ok": True, "description": result, "cached": False})

    @app.post("/api/ai/content/caption")
    async def handle_generate_caption(request: Request) -> JSONResponse:
        """
        Generate an Instagram/TikTok caption for an upcoming event.
        Body: { "event_name": str, "event_date": str, "location": str, "products": [str] }
        Returns: { "ok": true, "caption": str, "hashtags": [str] }
        """
        blocked = _gate(request, "ai_content")
        if blocked:
            return blocked

        user = _require_vendor(request)
        if not user:
            return _err("Vendor login required.", status_code=401)

        try:
            body = await request.json()
        except Exception:
            return _err("Invalid JSON body.")

        event_name = str(body.get("event_name") or "").strip()
        if not event_name:
            return _err("event_name is required.")

        from storage_users import get_vendor_profile
        from storage_ai import get_ai_cache, set_ai_cache, log_ai_usage

        vendor_id = int(user["id"])
        profile = get_vendor_profile(vendor_id)
        products = body.get("products") or []
        event_date = str(body.get("event_date") or "")
        location = str(body.get("location") or profile.get("location") or "")
        category = str(profile.get("category") or "")

        cache_key = json.dumps({"event": event_name, "date": event_date, "loc": location, "products": products[:4], "cat": category}, sort_keys=True)
        cached = get_ai_cache(vendor_id, "caption", cache_key)
        if cached:
            data = json.loads(cached)
            return JSONResponse({"ok": True, **data, "cached": True})

        result = await _call_content_ai(
            request=request,
            prompt=_caption_prompt(event_name, event_date, location, products, category),
            parse="caption",
        )
        if result is None:
            return _err("Content AI is not available right now.", status_code=503)

        set_ai_cache(vendor_id, "caption", cache_key, json.dumps(result))
        log_ai_usage(vendor_id, "caption")
        return JSONResponse({"ok": True, **result, "cached": False})

    # ── USAGE ─────────────────────────────────────────────────────────────────

    @app.get("/api/ai/usage")
    async def handle_ai_usage(request: Request) -> JSONResponse:
        """Return AI usage summary for the current vendor (last 30 days)."""
        user = request.session.get("user")
        if not user:
            return _err("Login required.", status_code=401)
        from storage_ai import get_user_ai_usage
        usage = get_user_ai_usage(int(user["id"]))
        return JSONResponse({"ok": True, "usage": usage})


# ---------------------------------------------------------------------------
# Content AI engine
# ---------------------------------------------------------------------------

async def _call_content_ai(request: Request, prompt: str, parse: str) -> Any:
    """
    Call the Anthropic API for content generation.
    Returns parsed output or None if the API key is missing / call fails.

    parse = "text"        → returns plain string
    parse = "suggestions" → returns list of strings (expects numbered list)
    parse = "caption"     → returns {"caption": str, "hashtags": [str]}
    """
    cfg = getattr(request.app.state, "config", None)
    api_key = (cfg and cfg.anthropic_api_key) or ""
    if not api_key:
        logger.warning("Content AI called but ANTHROPIC_API_KEY is not set.")
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",  # fast + cheap for content gen
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
    except Exception as exc:
        logger.error("Anthropic API call failed: %s", exc)
        return None

    if parse == "text":
        return raw

    if parse == "suggestions":
        # Expect numbered list: "1. ...\n2. ...\n3. ..."
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        suggestions = []
        for line in lines:
            # Strip leading "1. " "- " "• " etc.
            cleaned = line.lstrip("0123456789.-•) ").strip()
            if cleaned:
                suggestions.append(cleaned)
        return suggestions[:3] or [raw]

    if parse == "caption":
        # Expect: first block = caption, then hashtags line starting with #
        parts = raw.split("\n\n")
        caption = parts[0].strip()
        hashtag_line = ""
        for part in parts[1:]:
            if "#" in part:
                hashtag_line = part.strip()
                break
        hashtags = [w.strip() for w in hashtag_line.split() if w.startswith("#")]
        return {"caption": caption, "hashtags": hashtags[:15]}

    return raw


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _bio_prompt(category: str, location: str, products: list, style: str) -> str:
    product_str = ", ".join(str(p) for p in products[:5]) if products else ""
    return f"""You are helping a small business vendor write a short shop bio for their public profile on a pop-up market platform.

Vendor details:
- Category: {category or "handmade goods"}
- Location: {location or "local markets"}
- Products: {product_str or "various handmade items"}
- Tone: {style}

Write 3 different short bio options (1-2 sentences each). Each should feel authentic, specific, and human — not generic marketing copy.

Format your response as a numbered list:
1. [first bio]
2. [second bio]
3. [third bio]"""


def _product_desc_prompt(name: str, category: str, price: Any) -> str:
    price_str = f"${price:.2f}" if price else ""
    return f"""Write a short, appealing product description for a vendor's online shop listing.

Product: {name}
Category: {category or "handmade"}
Price: {price_str or "not specified"}

Write 2-3 sentences max. Be specific and sensory. No filler phrases like "perfect gift" or "made with love". Just describe what it is and why someone would want it.

Return only the description, no labels."""


def _caption_prompt(event_name: str, event_date: str, location: str, products: list, category: str) -> str:
    product_str = ", ".join(str(p) for p in products[:4]) if products else "my latest work"
    return f"""Write an Instagram/TikTok caption for a vendor announcing they'll be at an upcoming pop-up market.

Event: {event_name}
Date: {event_date or "this weekend"}
Location: {location or "local"}
What I sell: {product_str}
Category: {category or "handmade"}

Keep it casual, friendly, and under 150 words. Add a call to action to come find them.
Then on a new line, add 8-12 relevant hashtags.

Format:
[caption text]

[hashtags]"""
