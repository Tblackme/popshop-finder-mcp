"""
AI Content Generator — Vendor Atlas

Generates vendor bios, product descriptions, and event copy using Claude.
This service is completely independent of core CRUD logic.

Enable with: AI_CONTENT_ENABLED=true + ANTHROPIC_API_KEY=sk-...
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class VendorBioResult:
    bio: str
    tagline: str
    keywords: list[str]


@dataclass
class ProductDescriptionResult:
    description: str
    short_description: str
    suggested_price_note: str | None


@dataclass
class EventDescriptionResult:
    description: str
    vendor_pitch: str  # text to show vendors considering applying


class ContentGenerator:
    """
    Generates marketing-quality content using Claude.

    Usage:
        gen = ContentGenerator()
        result = await gen.generate_vendor_bio(
            business_name="Strange Wares",
            category="oddities",
            products=["taxidermy", "crystals", "vintage oddities"],
            tone="mysterious but approachable",
        )
        print(result.bio)
    """

    MODEL = "claude-haiku-4-5-20251001"  # fast + cheap for content tasks

    def __init__(self) -> None:
        self._client = None  # lazy-loaded

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as e:
                raise RuntimeError(
                    "anthropic package not installed. Run: pip install anthropic"
                ) from e
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set.")
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def _call(self, system: str, user: str) -> str:
        import anthropic
        client = self._get_client()
        msg = client.messages.create(
            model=self.MODEL,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text.strip()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def generate_vendor_bio(
        self,
        *,
        business_name: str,
        category: str,
        products: list[str],
        location: str = "",
        tone: str = "friendly and professional",
        existing_bio: str = "",
    ) -> VendorBioResult:
        system = (
            "You are a brand copywriter specializing in small creative businesses. "
            "Write concise, compelling vendor bios for craft market / pop-up shop vendors. "
            "Return ONLY valid JSON with keys: bio (2-3 sentences), tagline (1 line), keywords (list of 5 strings)."
        )
        product_list = ", ".join(products) if products else "handmade goods"
        existing = f"\nExisting bio to improve: {existing_bio}" if existing_bio else ""
        user = (
            f"Business: {business_name}\n"
            f"Category: {category}\n"
            f"Products: {product_list}\n"
            f"Location: {location or 'not specified'}\n"
            f"Tone: {tone}"
            f"{existing}"
        )
        raw = self._call(system, user)
        data = _parse_json(raw, {"bio": "", "tagline": "", "keywords": []})
        return VendorBioResult(
            bio=data.get("bio", ""),
            tagline=data.get("tagline", ""),
            keywords=data.get("keywords", []),
        )

    def generate_product_description(
        self,
        *,
        product_name: str,
        category: str,
        price: float | None = None,
        materials: list[str] | None = None,
        existing_description: str = "",
    ) -> ProductDescriptionResult:
        system = (
            "You are a product copywriter for Etsy-style artisan goods. "
            "Write compelling product descriptions that drive sales. "
            "Return ONLY valid JSON with keys: "
            "description (3-4 sentences), short_description (1 sentence), suggested_price_note (optional tip or null)."
        )
        mat_str = ", ".join(materials) if materials else "not specified"
        existing = f"\nExisting description: {existing_description}" if existing_description else ""
        user = (
            f"Product: {product_name}\n"
            f"Category: {category}\n"
            f"Price: {f'${price:.2f}' if price else 'not set'}\n"
            f"Materials: {mat_str}"
            f"{existing}"
        )
        raw = self._call(system, user)
        data = _parse_json(raw, {"description": "", "short_description": "", "suggested_price_note": None})
        return ProductDescriptionResult(
            description=data.get("description", ""),
            short_description=data.get("short_description", ""),
            suggested_price_note=data.get("suggested_price_note"),
        )

    def generate_event_description(
        self,
        *,
        event_name: str,
        event_type: str,
        location: str,
        date: str,
        vendor_count: int | None = None,
        categories: list[str] | None = None,
    ) -> EventDescriptionResult:
        system = (
            "You are an event marketing copywriter. Write descriptions for pop-up markets and craft fairs. "
            "Return ONLY valid JSON with keys: "
            "description (public-facing, 3-4 sentences), vendor_pitch (why vendors should apply, 2-3 sentences)."
        )
        cats = ", ".join(categories) if categories else "various"
        user = (
            f"Event: {event_name}\n"
            f"Type: {event_type}\n"
            f"Location: {location}\n"
            f"Date: {date}\n"
            f"Vendor spots: {vendor_count or 'TBD'}\n"
            f"Categories: {cats}"
        )
        raw = self._call(system, user)
        data = _parse_json(raw, {"description": "", "vendor_pitch": ""})
        return EventDescriptionResult(
            description=data.get("description", ""),
            vendor_pitch=data.get("vendor_pitch", ""),
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _parse_json(raw: str, fallback: dict) -> dict:
    import json, re
    # strip markdown code fences if present
    clean = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(clean)
    except Exception:
        return fallback
