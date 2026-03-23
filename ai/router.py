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

# lazy import helpers
def _get_events(limit: int = 100) -> list[dict]:
    """Pull events from storage for recommendation endpoints."""
    try:
        from storage_events import search_events
        return search_events({})[:limit]
    except Exception:
        return []

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


# ------------------------------------------------------------------
# Feature 1: Smart Event Recommendations  (AI_MATCHING or rule-based)
# ------------------------------------------------------------------

class RecommendEventsRequest(BaseModel):
    vendor: dict[str, Any] = Field(default_factory=dict)
    limit: int = 5
    city: str = ""
    vendor_category: str = ""


@router.post("/recommend-events")
async def recommend_events(request: Request, body: RecommendEventsRequest) -> JSONResponse:
    """Return personalized event recommendations for a vendor or shopper."""
    _require_user(request)
    try:
        events = _get_events(200)
        vendor = body.vendor

        # Filter by category/city if provided
        cat = (body.vendor_category or vendor.get("vendor_category") or "").lower()
        city = (body.city or vendor.get("city") or "").lower()
        if cat:
            events = [e for e in events if cat in (e.get("vendor_category") or "").lower() or not e.get("vendor_category")]
        if city:
            events = [e for e in events if city in (e.get("city") or "").lower()]

        # Try AI ranking if matching is enabled
        if flags.is_enabled(Feature.AI_MATCHING) and vendor and events:
            try:
                from ai.services.smart_matcher import SmartMatcher
                ranked = SmartMatcher().rank_events_for_vendor(vendor=vendor, events=events, top_n=body.limit)
                return JSONResponse({
                    "ok": True,
                    "source": "ai",
                    "recommendations": [
                        {
                            "event_id": r.event_id,
                            "event_title": r.event_title,
                            "score": r.match.score,
                            "verdict": r.match.verdict,
                            "recommendation": r.match.recommendation,
                        }
                        for r in ranked
                    ],
                })
            except Exception:
                pass  # fall through to rule-based

        # Rule-based: sort by popularity + date
        from storage_ai import _rule_based_score
        scored = []
        for ev in events:
            score = _rule_based_score(vendor, ev) if vendor else int(ev.get("popularity_score") or 0)
            scored.append({"event": ev, "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)

        return JSONResponse({
            "ok": True,
            "source": "rule-based",
            "recommendations": [
                {
                    "event_id": item["event"].get("id"),
                    "event_title": item["event"].get("name"),
                    "score": item["score"],
                    "verdict": "Strong match" if item["score"] >= 70 else "Worth considering" if item["score"] >= 45 else "Lower priority",
                    "recommendation": f"{item['event'].get('name')} in {item['event'].get('city', '')} — {item['event'].get('event_type') or item['event'].get('vendor_category') or 'Market'}.",
                }
                for item in scored[: body.limit]
            ],
        })
    except Exception as e:
        return _ai_error(e)


# ------------------------------------------------------------------
# Feature 2: Vendor Sales Insights  (AI_INSIGHTS)
# ------------------------------------------------------------------

class VendorInsightsRequest(BaseModel):
    vendor_id: int | None = None
    products: list[dict[str, Any]] = Field(default_factory=list)
    saved_events: list[dict[str, Any]] = Field(default_factory=list)
    vendor_category: str = ""


@router.post("/vendor-insights")
async def vendor_insights(request: Request, body: VendorInsightsRequest) -> JSONResponse:
    """Return AI-generated sales and business insights for a vendor dashboard."""
    _require_user(request)

    # Always return rule-based insights — AI enrichment when flag is on
    product_count = len(body.products)
    event_count = len(body.saved_events)
    cat = body.vendor_category or "general"

    rule_insights = []
    if product_count == 0:
        rule_insights.append({"icon": "🛍", "text": "Add your first product to start tracking what sells best at different events."})
    elif product_count < 5:
        rule_insights.append({"icon": "📦", "text": f"You have {product_count} product{'s' if product_count != 1 else ''}. Vendors with 8+ products typically see higher per-event revenue."})
    else:
        rule_insights.append({"icon": "✅", "text": f"Good product range with {product_count} items. Consider grouping into gift sets to increase average order value."})

    if event_count == 0:
        rule_insights.append({"icon": "📍", "text": "Save events on the Discover page to build your shortlist and track upcoming markets."})
    elif event_count < 3:
        rule_insights.append({"icon": "📅", "text": f"You have {event_count} saved event{'s' if event_count != 1 else ''}. Aim for 4–6 markets per season to maintain steady revenue."})
    else:
        rule_insights.append({"icon": "🗓", "text": f"Active event pipeline: {event_count} saved events. Use the Profit Planner to estimate ROI before committing."})

    cat_tips = {
        "craft": "Craft vendors do well at indoor winter markets — look for holiday and gift-themed events.",
        "vintage": "Vintage sellers perform best at flea markets and antique fairs with 500+ foot traffic.",
        "food": "Food vendors benefit most from evening events and festivals with live entertainment.",
        "art": "Art vendors thrive at curated gallery-style markets — look for events that vet their applicants.",
        "handmade": "Handmade goods sell well year-round. Outdoor summer markets drive the highest volume.",
    }
    for key, tip in cat_tips.items():
        if key in cat.lower():
            rule_insights.append({"icon": "💡", "text": tip})
            break

    if flags.is_enabled(Feature.AI_INSIGHTS) and (body.products or body.saved_events):
        try:
            import anthropic
            client = anthropic.Anthropic()
            product_names = [p.get("name", "") for p in body.products[:5]]
            event_names = [e.get("name", "") for e in body.saved_events[:5]]
            prompt = f"""You are a business coach for small vendors at pop-up markets.

Vendor category: {cat}
Products: {', '.join(product_names) or 'Not specified'}
Saved events: {', '.join(event_names) or 'None yet'}

Give exactly 2 brief, actionable business insights (1 sentence each). Be specific and practical.
Return JSON: {{"insights": ["insight 1", "insight 2"]}}"""
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip() if message.content else ""
            import json
            raw = raw.strip("```json\n").strip("```").strip()
            data = json.loads(raw)
            for text in (data.get("insights") or [])[:2]:
                rule_insights.append({"icon": "✦", "text": text, "ai": True})
        except Exception as exc:
            logger.debug("AI insights fallback: %s", exc)

    return JSONResponse({"ok": True, "insights": rule_insights})


# ------------------------------------------------------------------
# Feature 3: Caption Generator (already in server_ai.py; add here too)
# ------------------------------------------------------------------

class CaptionRequest(BaseModel):
    product_name: str = ""
    event_name: str = ""
    description: str = ""
    tone: str = "excited and authentic"


@router.post("/generate-caption")
async def generate_caption(request: Request, body: CaptionRequest) -> JSONResponse:
    """Generate a social media caption for a product or event post."""
    _require_user(request)
    try:
        flags.require(Feature.AI_CONTENT)
    except FeatureDisabledError as e:
        return _feature_error(e)
    try:
        import anthropic
        client = anthropic.Anthropic()
        parts = []
        if body.product_name:
            parts.append(f"Product: {body.product_name}")
        if body.event_name:
            parts.append(f"Event: {body.event_name}")
        if body.description:
            parts.append(f"Notes: {body.description}")
        prompt = f"""Write a social media caption for a vendor at a pop-up market.
Tone: {body.tone}
{chr(10).join(parts)}

Return JSON: {{"caption": "...", "hashtags": ["tag1", "tag2", "tag3"]}}"""
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        raw = (message.content[0].text if message.content else "").strip().strip("```json\n").strip("```").strip()
        data = json.loads(raw)
        return JSONResponse({"ok": True, "caption": data.get("caption", ""), "hashtags": data.get("hashtags", [])})
    except Exception as e:
        return _ai_error(e)


# ------------------------------------------------------------------
# Feature 4: Event Success Predictor  (rule-based + AI_INSIGHTS)
# ------------------------------------------------------------------

class EventPredictionRequest(BaseModel):
    event: dict[str, Any]
    vendor: dict[str, Any] = Field(default_factory=dict)


@router.post("/event-prediction")
async def event_prediction(request: Request, body: EventPredictionRequest) -> JSONResponse:
    """Predict event success: revenue range, traffic, risk level."""
    _require_user(request)
    try:
        from ai.services.event_predictor import EventPredictor
        use_ai = flags.is_enabled(Feature.AI_INSIGHTS)
        if use_ai:
            result = EventPredictor().predict(event=body.event, vendor=body.vendor or None)
        else:
            from ai.services.event_predictor import _rule_predict
            result = _rule_predict(event=body.event, vendor=body.vendor or None)
        return JSONResponse({
            "ok": True,
            "risk_level": result.risk_level,
            "risk_color": result.risk_color,
            "revenue_low": result.revenue_low,
            "revenue_high": result.revenue_high,
            "traffic_estimate": result.traffic_estimate,
            "competition_note": result.competition_note,
            "summary": result.summary,
            "confidence": result.confidence,
            "tips": result.tips,
        })
    except Exception as e:
        return _ai_error(e)


# ------------------------------------------------------------------
# Feature 5: AI Vendor Discovery  (rule-based always)
# ------------------------------------------------------------------

class VendorDiscoveryRequest(BaseModel):
    shopper_interests: list[str] = Field(default_factory=list)
    followed_categories: list[str] = Field(default_factory=list)
    limit: int = 6


@router.post("/vendor-discovery")
async def vendor_discovery(request: Request, body: VendorDiscoveryRequest) -> JSONResponse:
    """Return vendor recommendations for shoppers."""
    _require_user(request)
    try:
        from storage_users import list_public_users
        vendors = list_public_users(role="vendor", limit=50)
        interests = {i.lower() for i in body.shopper_interests + body.followed_categories}

        scored = []
        for v in vendors:
            score = 0
            vendor_cat = (v.get("vendor_category") or v.get("interests") or "").lower()
            for interest in interests:
                if interest in vendor_cat:
                    score += 10
            score += min(20, int(v.get("popularity_score") or 0) // 5)
            scored.append({"vendor": v, "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)
        recommendations = [
            {
                "vendor_id": item["vendor"].get("id"),
                "name": item["vendor"].get("name") or item["vendor"].get("username"),
                "category": item["vendor"].get("vendor_category") or item["vendor"].get("interests"),
                "bio": (item["vendor"].get("bio") or "")[:120],
                "score": item["score"],
            }
            for item in scored[: body.limit]
        ]
        return JSONResponse({"ok": True, "vendors": recommendations})
    except Exception as e:
        return _ai_error(e)


# ------------------------------------------------------------------
# Feature 6: AI Community Assistant  (AI_ASSISTANT)
# ------------------------------------------------------------------

class CommunityAskRequest(BaseModel):
    question: str
    context: str = ""


@router.post("/community/ask")
async def community_ask(request: Request, body: CommunityAskRequest) -> JSONResponse:
    """AI Q&A assistant for the community page."""
    _require_user(request)
    question = (body.question or "").strip()
    if not question:
        return JSONResponse({"ok": False, "error": "question is required"}, status_code=422)
    try:
        from ai.services.community_assistant import CommunityAssistant
        result = CommunityAssistant().ask(question=question, context=body.context)
        return JSONResponse({
            "ok": True,
            "answer": result.answer,
            "follow_up_prompts": result.follow_up_prompts,
        })
    except Exception as e:
        return _ai_error(e)


# ------------------------------------------------------------------
# Feature 7: Smart Product Tagging  (AI_CONTENT or rule-based)
# ------------------------------------------------------------------

class ProductTagRequest(BaseModel):
    product_name: str
    category: str = ""
    description: str = ""


# Category → common tags lookup for rule-based tier
_CATEGORY_TAGS: dict[str, list[str]] = {
    "candle": ["candle", "handmade", "home decor", "scented", "wax", "aromatherapy"],
    "soap": ["soap", "handmade", "natural", "skincare", "bath", "artisan"],
    "jewelry": ["jewelry", "handmade", "wearable art", "accessories", "gift"],
    "art": ["art", "original", "print", "illustration", "wall art", "handmade"],
    "vintage": ["vintage", "retro", "thrifted", "upcycled", "antique", "secondhand"],
    "food": ["food", "homemade", "artisan", "local", "small batch", "fresh"],
    "clothing": ["clothing", "handmade", "fashion", "wearable", "apparel"],
    "plant": ["plant", "garden", "green", "botanical", "nature", "eco"],
    "ceramic": ["ceramic", "pottery", "handmade", "clay", "artisan", "functional art"],
    "textile": ["textile", "fabric", "handmade", "fiber art", "woven"],
}


@router.post("/product-tags")
async def suggest_product_tags(request: Request, body: ProductTagRequest) -> JSONResponse:
    """Suggest tags and keywords for a product listing."""
    _require_user(request)

    name_lower = body.product_name.lower()
    cat_lower = (body.category or "").lower()

    # Rule-based: keyword matching
    rule_tags: list[str] = []
    for key, tags in _CATEGORY_TAGS.items():
        if key in name_lower or key in cat_lower:
            rule_tags.extend(tags[:4])
            break

    # Add name-derived tags
    words = [w.strip(",.!?") for w in body.product_name.lower().split() if len(w) > 3]
    rule_tags.extend(words[:3])
    rule_tags = list(dict.fromkeys(rule_tags))[:10]  # deduplicate

    if flags.is_enabled(Feature.AI_CONTENT):
        try:
            import json, anthropic
            client = anthropic.Anthropic()
            prompt = f"""Suggest 6-8 search tags for this product sold at pop-up markets and craft fairs.
Product: {body.product_name}
Category: {body.category or 'General'}
{('Description: ' + body.description) if body.description else ''}

Return JSON: {{"tags": ["tag1", "tag2", ...]}}"""
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = (message.content[0].text if message.content else "").strip().strip("```json\n").strip("```").strip()
            data = json.loads(raw)
            ai_tags = [t.lower().strip() for t in (data.get("tags") or [])]
            all_tags = list(dict.fromkeys(ai_tags + rule_tags))[:10]
            return JSONResponse({"ok": True, "tags": all_tags, "source": "ai"})
        except Exception as exc:
            logger.debug("Product tag AI fallback: %s", exc)

    return JSONResponse({"ok": True, "tags": rule_tags, "source": "rule-based"})


# ------------------------------------------------------------------
# Feature 8: Event Demand Insights for Organizers  (AI_INSIGHTS)
# ------------------------------------------------------------------

class OrganizerInsightsRequest(BaseModel):
    events: list[dict[str, Any]] = Field(default_factory=list)
    applications: list[dict[str, Any]] = Field(default_factory=list)
    organizer_name: str = ""


@router.post("/organizer-insights")
async def organizer_insights(request: Request, body: OrganizerInsightsRequest) -> JSONResponse:
    """Return demand insights and recommendations for event organizers."""
    _require_user(request)
    try:
        events = body.events
        apps = body.applications

        # Rule-based category analysis
        from collections import Counter
        cat_counter: Counter = Counter()
        status_counter: Counter = Counter()
        for app in apps:
            cat = (app.get("vendor_category") or app.get("category") or "General").title()
            cat_counter[cat] += 1
            status_counter[app.get("status", "Pending")] += 1

        insights = []
        if cat_counter:
            top_cat, top_n = cat_counter.most_common(1)[0]
            insights.append({"icon": "🔥", "text": f"{top_cat} vendors are your most common applicants ({top_n} applications). Consider reserving featured spots for this category."})
            if len(cat_counter) >= 3:
                underrep = cat_counter.most_common()[-1]
                insights.append({"icon": "📊", "text": f"{underrep[0]} vendors have the fewest applications — targeted outreach could improve category diversity."})

        accepted = status_counter.get("Accepted", 0)
        pending = status_counter.get("Pending", 0)
        if pending > accepted * 2:
            insights.append({"icon": "⚡", "text": f"{pending} applications still pending. Faster decisions reduce drop-off and help vendors plan their schedule."})

        if len(events) > 0 and len(apps) > 0:
            apps_per_event = len(apps) / len(events)
            if apps_per_event < 5:
                insights.append({"icon": "📢", "text": "Low application volume — share your event on the Feed and Community to attract more vendors."})
            elif apps_per_event >= 15:
                insights.append({"icon": "🎯", "text": f"Strong demand: ~{int(apps_per_event)} applications per event. You can be selective — prioritize vendors with complete profiles."})

        if flags.is_enabled(Feature.AI_INSIGHTS) and (events or apps):
            try:
                import json, anthropic
                client = anthropic.Anthropic()
                event_names = [e.get("name", "") for e in events[:5]]
                categories = list(cat_counter.keys())[:6]
                prompt = f"""You are advising a pop-up market organizer.

Events: {', '.join(event_names) or 'Not specified'}
Vendor categories applied: {', '.join(categories) or 'Various'}
Total applications: {len(apps)}
Accepted: {accepted}, Pending: {pending}

Give 1 specific, actionable tip to improve their next event. 1-2 sentences only.
Return JSON: {{"tip": "..."}}"""
                message = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=150,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = (message.content[0].text if message.content else "").strip().strip("```json\n").strip("```").strip()
                data = json.loads(raw)
                if data.get("tip"):
                    insights.append({"icon": "✦", "text": data["tip"], "ai": True})
            except Exception as exc:
                logger.debug("Organizer insights AI fallback: %s", exc)

        return JSONResponse({"ok": True, "insights": insights})
    except Exception as e:
        return _ai_error(e)
