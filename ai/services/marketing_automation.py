"""
AI Marketing Automation — Vendor Atlas

Generates social posts, email campaigns, and promotional copy for vendors
and event organizers. Fully independent of core functionality.

Enable with: AI_MARKETING_ENABLED=true + ANTHROPIC_API_KEY=sk-...
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class SocialPostResult:
    instagram: str
    facebook: str
    twitter: str          # ≤280 chars
    hashtags: list[str]


@dataclass
class EmailCampaignResult:
    subject_line: str
    preview_text: str
    body_html: str
    cta_text: str
    cta_url_placeholder: str


@dataclass
class VendorAnnouncementResult:
    headline: str
    body: str
    call_to_action: str


class MarketingAutomation:
    """
    AI-generated marketing content for vendors and organizers.

    All methods are synchronous and independently callable.
    None of them read from or write to the database.

    Usage:
        mkt = MarketingAutomation()
        posts = mkt.generate_social_posts(
            vendor_name="Strange Wares",
            event_name="Kansas City Night Market",
            event_date="Saturday, April 12",
            products=["taxidermy", "crystals"],
        )
        print(posts.instagram)
    """

    MODEL = "claude-haiku-4-5-20251001"

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as e:
                raise RuntimeError("Run: pip install anthropic") from e
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY is not set.")
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def _call(self, system: str, user: str) -> str:
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

    def generate_social_posts(
        self,
        *,
        vendor_name: str,
        event_name: str,
        event_date: str,
        event_location: str = "",
        products: list[str] | None = None,
        tone: str = "excited and authentic",
    ) -> SocialPostResult:
        """Generate platform-specific social posts announcing event attendance."""
        system = (
            "You are a social media manager for small creative businesses. "
            "Write authentic, engaging posts announcing a vendor's attendance at an event. "
            "Return ONLY valid JSON with keys: instagram (string), facebook (string), "
            "twitter (string, max 280 chars), hashtags (list of 8-10 strings without #)."
        )
        products_str = ", ".join(products) if products else "handmade goods"
        user = (
            f"Vendor: {vendor_name}\n"
            f"Event: {event_name}\n"
            f"Date: {event_date}\n"
            f"Location: {event_location or 'TBD'}\n"
            f"Products: {products_str}\n"
            f"Tone: {tone}"
        )
        raw = self._call(system, user)
        data = _parse_json(raw, {})
        return SocialPostResult(
            instagram=data.get("instagram", ""),
            facebook=data.get("facebook", ""),
            twitter=data.get("twitter", ""),
            hashtags=data.get("hashtags", []),
        )

    def generate_email_campaign(
        self,
        *,
        sender_name: str,
        campaign_type: str,  # "event_announcement" | "new_product" | "sale" | "follow_up"
        event_name: str = "",
        event_date: str = "",
        product_name: str = "",
        discount: str = "",
        audience: str = "past customers and followers",
    ) -> EmailCampaignResult:
        """Generate a complete email campaign for a vendor or organizer."""
        system = (
            "You are an email marketing specialist for small creative businesses. "
            "Write compelling email campaigns that feel personal, not corporate. "
            "Return ONLY valid JSON with keys: subject_line (string), preview_text (string, ~90 chars), "
            "body_html (full HTML email body, inline styles only), "
            "cta_text (string), cta_url_placeholder (string)."
        )
        user = (
            f"Sender: {sender_name}\n"
            f"Campaign type: {campaign_type}\n"
            f"Event: {event_name or 'N/A'}\n"
            f"Date: {event_date or 'N/A'}\n"
            f"Product: {product_name or 'N/A'}\n"
            f"Discount/offer: {discount or 'none'}\n"
            f"Audience: {audience}"
        )
        raw = self._call(system, user)
        data = _parse_json(raw, {})
        return EmailCampaignResult(
            subject_line=data.get("subject_line", ""),
            preview_text=data.get("preview_text", ""),
            body_html=data.get("body_html", ""),
            cta_text=data.get("cta_text", "Learn More"),
            cta_url_placeholder=data.get("cta_url_placeholder", "{{url}}"),
        )

    def generate_vendor_announcement(
        self,
        *,
        organizer_name: str,
        event_name: str,
        event_date: str,
        event_location: str,
        vendor_slots: int | None = None,
        application_deadline: str = "",
        fee: str = "",
        categories: list[str] | None = None,
    ) -> VendorAnnouncementResult:
        """Generate a vendor call-to-apply announcement for an organizer."""
        system = (
            "You are a marketing copywriter for pop-up market organizers. "
            "Write a compelling vendor recruitment announcement. "
            "Return ONLY valid JSON with keys: headline (string), "
            "body (2-3 paragraphs as plain text), call_to_action (string)."
        )
        cats = ", ".join(categories) if categories else "all categories"
        user = (
            f"Organizer: {organizer_name}\n"
            f"Event: {event_name}\n"
            f"Date: {event_date}\n"
            f"Location: {event_location}\n"
            f"Vendor slots: {vendor_slots or 'limited'}\n"
            f"Application deadline: {application_deadline or 'rolling'}\n"
            f"Booth fee: {fee or 'varies'}\n"
            f"Categories wanted: {cats}"
        )
        raw = self._call(system, user)
        data = _parse_json(raw, {})
        return VendorAnnouncementResult(
            headline=data.get("headline", ""),
            body=data.get("body", ""),
            call_to_action=data.get("call_to_action", "Apply Now"),
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _parse_json(raw: str, fallback: dict) -> dict:
    import json, re
    clean = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(clean)
    except Exception:
        return fallback
