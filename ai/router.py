"""
AI API Router — Vendor Atlas
Mounted at /api/ai/* in server.py

All routes:
  - Check feature flags before doing anything
  - Return 403 with clear message if feature is disabled
  - Never touch core CRUD logic — they only call AI services
  - Accept JSON bodies, return JSON

Authentication: same session cookie as core routes (request.state.user).
If user is not authenticated, returns 401.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from features.flags import Feature, FeatureDisabledError, flags

logger = logging.getLogger("vendor-atlas.ai")

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _require_user(request: Request) -> dict:
    """Pull user from session — raises 401 if not logged in."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


def _feature_error(e: FeatureDisabledError) -> JSONResponse:
    return JSONResponse(
        {"ok": False, "error": str(e), "feature": e.feature.value},
        status_code=403,
    )


def _ai_error(e: Exception) -> JSONResponse:
    logger.exception("AI service error: %s", e)
    return JSONResponse(
        {"ok": False, "error": "AI service error. Check server logs."},
        status_code=502,
    )


# ------------------------------------------------------------------
# Feature flags status (public — no auth required)
# ------------------------------------------------------------------

@router.get("/status")
async def ai_status() -> JSONResponse:
    """Return which AI features are currently enabled."""
    return JSONResponse({"ok": True, "features": flags.all_flags()})


# ------------------------------------------------------------------
# Content Generation  (AI_CONTENT_ENABLED)
# ------------------------------------------------------------------

class VendorBioRequest(BaseModel):
    business_name: str
    category: str
    products: list[str] = Field(default_factory=list)
    location: str = ""
    tone: str = "friendly and professional"
    existing_bio: str = ""


@router.post("/content/vendor-bio")
async def generate_vendor_bio(request: Request, body: VendorBioRequest) -> JSONResponse:
    """Generate or rewrite a vendor bio using AI."""
    _require_user(request)
    try:
        flags.require(Feature.AI_CONTENT)
    except FeatureDisabledError as e:
        return _feature_error(e)
    try:
        from ai.services.content_generator import ContentGenerator
        result = ContentGenerator().generate_vendor_bio(
            business_name=body.business_name,
            category=body.category,
            products=body.products,
            location=body.location,
            tone=body.tone,
            existing_bio=body.existing_bio,
        )
        return JSONResponse({"ok": True, "bio": result.bio, "tagline": result.tagline, "keywords": result.keywords})
    except FeatureDisabledError as e:
        return _feature_error(e)
    except Exception as e:
        return _ai_error(e)


class ProductDescriptionRequest(BaseModel):
    product_name: str
    category: str
    price: float | None = None
    materials: list[str] = Field(default_factory=list)
    existing_description: str = ""


@router.post("/content/product-description")
async def generate_product_description(request: Request, body: ProductDescriptionRequest) -> JSONResponse:
    """Generate a product description using AI."""
    _require_user(request)
    try:
        flags.require(Feature.AI_CONTENT)
    except FeatureDisabledError as e:
        return _feature_error(e)
    try:
        from ai.services.content_generator import ContentGenerator
        result = ContentGenerator().generate_product_description(
            product_name=body.product_name,
            category=body.category,
            price=body.price,
            materials=body.materials,
            existing_description=body.existing_description,
        )
        return JSONResponse({
            "ok": True,
            "description": result.description,
            "short_description": result.short_description,
            "suggested_price_note": result.suggested_price_note,
        })
    except Exception as e:
        return _ai_error(e)


class EventDescriptionRequest(BaseModel):
    event_name: str
    event_type: str
    location: str
    date: str
    vendor_count: int | None = None
    categories: list[str] = Field(default_factory=list)


@router.post("/content/event-description")
async def generate_event_description(request: Request, body: EventDescriptionRequest) -> JSONResponse:
    """Generate an event description and vendor pitch using AI."""
    _require_user(request)
    try:
        flags.require(Feature.AI_CONTENT)
    except FeatureDisabledError as e:
        return _feature_error(e)
    try:
        from ai.services.content_generator import ContentGenerator
        result = ContentGenerator().generate_event_description(
            event_name=body.event_name,
            event_type=body.event_type,
            location=body.location,
            date=body.date,
            vendor_count=body.vendor_count,
            categories=body.categories,
        )
        return JSONResponse({"ok": True, "description": result.description, "vendor_pitch": result.vendor_pitch})
    except Exception as e:
        return _ai_error(e)


# ------------------------------------------------------------------
# Smart Matching  (AI_MATCHING_ENABLED)
# ------------------------------------------------------------------

class MatchVendorRequest(BaseModel):
    vendor: dict[str, Any]
    event: dict[str, Any]


@router.post("/match/vendor-event")
async def match_vendor_to_event(request: Request, body: MatchVendorRequest) -> JSONResponse:
    """AI analysis of vendor-event fit with natural language reasoning."""
    _require_user(request)
    try:
        flags.require(Feature.AI_MATCHING)
    except FeatureDisabledError as e:
        return _feature_error(e)
    try:
        from ai.services.smart_matcher import SmartMatcher
        result = SmartMatcher().match_vendor_to_event(
            vendor=body.vendor,
            event=body.event,
        )
        return JSONResponse({
            "ok": True,
            "score": result.score,
            "verdict": result.verdict,
            "reasons_for": result.reasons_for,
            "reasons_against": result.reasons_against,
            "recommendation": result.recommendation,
        })
    except Exception as e:
        return _ai_error(e)


class RankEventsRequest(BaseModel):
    vendor: dict[str, Any]
    events: list[dict[str, Any]]
    top_n: int = 5


@router.post("/match/rank-events")
async def rank_events_for_vendor(request: Request, body: RankEventsRequest) -> JSONResponse:
    """Rank a list of events for a vendor using AI-powered analysis."""
    _require_user(request)
    try:
        flags.require(Feature.AI_MATCHING)
    except FeatureDisabledError as e:
        return _feature_error(e)
    try:
        from ai.services.smart_matcher import SmartMatcher
        ranked = SmartMatcher().rank_events_for_vendor(
            vendor=body.vendor,
            events=body.events,
            top_n=body.top_n,
        )
        return JSONResponse({
            "ok": True,
            "ranked": [
                {
                    "event_id": r.event_id,
                    "event_title": r.event_title,
                    "score": r.match.score,
                    "verdict": r.match.verdict,
                    "reasons_for": r.match.reasons_for,
                    "reasons_against": r.match.reasons_against,
                    "recommendation": r.match.recommendation,
                }
                for r in ranked
            ],
        })
    except Exception as e:
        return _ai_error(e)


# ------------------------------------------------------------------
# Marketing Automation  (AI_MARKETING_ENABLED)
# ------------------------------------------------------------------

class SocialPostRequest(BaseModel):
    vendor_name: str
    event_name: str
    event_date: str
    event_location: str = ""
    products: list[str] = Field(default_factory=list)
    tone: str = "excited and authentic"


@router.post("/marketing/social-posts")
async def generate_social_posts(request: Request, body: SocialPostRequest) -> JSONResponse:
    """Generate Instagram, Facebook, and Twitter posts for an event."""
    _require_user(request)
    try:
        flags.require(Feature.AI_MARKETING)
    except FeatureDisabledError as e:
        return _feature_error(e)
    try:
        from ai.services.marketing_automation import MarketingAutomation
        result = MarketingAutomation().generate_social_posts(
            vendor_name=body.vendor_name,
            event_name=body.event_name,
            event_date=body.event_date,
            event_location=body.event_location,
            products=body.products,
            tone=body.tone,
        )
        return JSONResponse({
            "ok": True,
            "instagram": result.instagram,
            "facebook": result.facebook,
            "twitter": result.twitter,
            "hashtags": result.hashtags,
        })
    except Exception as e:
        return _ai_error(e)


class EmailCampaignRequest(BaseModel):
    sender_name: str
    campaign_type: str
    event_name: str = ""
    event_date: str = ""
    product_name: str = ""
    discount: str = ""
    audience: str = "past customers and followers"


@router.post("/marketing/email-campaign")
async def generate_email_campaign(request: Request, body: EmailCampaignRequest) -> JSONResponse:
    """Generate a complete email campaign."""
    _require_user(request)
    try:
        flags.require(Feature.AI_MARKETING)
    except FeatureDisabledError as e:
        return _feature_error(e)
    try:
        from ai.services.marketing_automation import MarketingAutomation
        result = MarketingAutomation().generate_email_campaign(
            sender_name=body.sender_name,
            campaign_type=body.campaign_type,
            event_name=body.event_name,
            event_date=body.event_date,
            product_name=body.product_name,
            discount=body.discount,
            audience=body.audience,
        )
        return JSONResponse({
            "ok": True,
            "subject_line": result.subject_line,
            "preview_text": result.preview_text,
            "body_html": result.body_html,
            "cta_text": result.cta_text,
            "cta_url_placeholder": result.cta_url_placeholder,
        })
    except Exception as e:
        return _ai_error(e)


class VendorAnnouncementRequest(BaseModel):
    organizer_name: str
    event_name: str
    event_date: str
    event_location: str
    vendor_slots: int | None = None
    application_deadline: str = ""
    fee: str = ""
    categories: list[str] = Field(default_factory=list)


@router.post("/marketing/vendor-announcement")
async def generate_vendor_announcement(request: Request, body: VendorAnnouncementRequest) -> JSONResponse:
    """Generate a vendor call-to-apply announcement for organizers."""
    _require_user(request)
    try:
        flags.require(Feature.AI_MARKETING)
    except FeatureDisabledError as e:
        return _feature_error(e)
    try:
        from ai.services.marketing_automation import MarketingAutomation
        result = MarketingAutomation().generate_vendor_announcement(
            organizer_name=body.organizer_name,
            event_name=body.event_name,
            event_date=body.event_date,
            event_location=body.event_location,
            vendor_slots=body.vendor_slots,
            application_deadline=body.application_deadline,
            fee=body.fee,
            categories=body.categories,
        )
        return JSONResponse({
            "ok": True,
            "headline": result.headline,
            "body": result.body,
            "call_to_action": result.call_to_action,
        })
    except Exception as e:
        return _ai_error(e)
