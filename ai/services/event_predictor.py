"""
Event Success Predictor — Vendor Atlas AI Services

Estimates likely revenue, foot traffic, and vendor competition risk
for a given event. Works in two tiers:

  Tier 1 (always on): rule-based heuristics from event metadata
  Tier 2 (AI_INSIGHTS_ENABLED): Claude narrative + refined estimates
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("vendor-atlas.ai.event_predictor")


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class EventPrediction:
    risk_level: str           # "Low Risk" | "Medium Risk" | "High Opportunity"
    risk_color: str           # green | amber | teal
    revenue_low: int
    revenue_high: int
    traffic_estimate: str     # "Low" | "Medium" | "High"
    competition_note: str
    summary: str
    confidence: str           # "rule-based" | "ai-enhanced"
    tips: list[str]


# ─── Rule-based tier ──────────────────────────────────────────────────────────

def _rule_predict(event: dict[str, Any], vendor: dict[str, Any] | None) -> EventPrediction:
    """Deterministic prediction using event metadata only."""
    pop = int(event.get("popularity_score") or 0)
    traffic = int(event.get("estimated_traffic") or 0)
    vendor_count = int(event.get("vendor_count") or 0)
    booth_price = float(event.get("booth_price") or 0)
    event_size = (event.get("event_size") or "medium").lower()

    # Traffic estimate
    if traffic >= 3000 or event_size == "large":
        traffic_label = "High"
    elif traffic >= 1500 or event_size == "medium":
        traffic_label = "Medium"
    else:
        traffic_label = "Low"

    # Competition note
    if vendor_count >= 100:
        competition_note = "Large vendor pool — stand out with strong visual branding."
    elif vendor_count >= 60:
        competition_note = "Moderate competition — good category diversity expected."
    else:
        competition_note = "Smaller vendor group — less competition, more attention per booth."

    # Revenue estimate — based on avg transaction × expected buyers
    avg_txn = float(vendor.get("avg_price") or 35) if vendor else 35.0
    buyer_share = 0.03 if traffic_label == "Low" else 0.05 if traffic_label == "Medium" else 0.08
    expected_buyers = (traffic or 1500) * buyer_share
    rev_mid = int(expected_buyers * avg_txn)
    revenue_low = max(50, int(rev_mid * 0.6))
    revenue_high = int(rev_mid * 1.5)

    # Risk / opportunity level
    score = 0
    if pop >= 85: score += 3
    elif pop >= 65: score += 1
    if traffic_label == "High": score += 3
    elif traffic_label == "Medium": score += 1
    if booth_price > 0 and rev_mid / max(booth_price, 1) >= 4: score += 2
    if vendor_count < 60: score += 1

    if score >= 7:
        risk_level, risk_color = "High Opportunity", "teal"
    elif score >= 4:
        risk_level, risk_color = "Medium Risk", "amber"
    else:
        risk_level, risk_color = "Low Risk", "green"

    tips = []
    if booth_price > 0:
        tips.append(f"Break-even point: ~{max(1, int(booth_price / max(avg_txn, 1)))} sales to cover your booth fee.")
    if traffic_label == "High":
        tips.append("Bring extra inventory — high-traffic events often sell out.")
    if vendor_count >= 80:
        tips.append("Invest in eye-catching signage to stand out from the crowd.")

    summary = (
        f"Based on event data: {traffic_label.lower()} foot traffic, "
        f"{vendor_count or '?'} vendors, popularity score {pop}/100. "
        f"Estimated revenue range: ${revenue_low}–${revenue_high}."
    )

    return EventPrediction(
        risk_level=risk_level,
        risk_color=risk_color,
        revenue_low=revenue_low,
        revenue_high=revenue_high,
        traffic_estimate=traffic_label,
        competition_note=competition_note,
        summary=summary,
        confidence="rule-based",
        tips=tips,
    )


# ─── AI-enhanced tier ─────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


class EventPredictor:
    """Predicts event success — rule-based by default, AI-enhanced when enabled."""

    def predict(
        self,
        event: dict[str, Any],
        vendor: dict[str, Any] | None = None,
    ) -> EventPrediction:
        base = _rule_predict(event, vendor)

        try:
            import anthropic
            client = anthropic.Anthropic()
            prompt = self._build_prompt(event, vendor, base)
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text if message.content else ""
            data = _parse_json(raw)
            if data.get("summary"):
                base.summary = data["summary"]
                base.tips = data.get("tips", base.tips)
                base.confidence = "ai-enhanced"
        except Exception as exc:
            logger.debug("AI prediction fallback: %s", exc)

        return base

    def _build_prompt(
        self,
        event: dict[str, Any],
        vendor: dict[str, Any] | None,
        base: EventPrediction,
    ) -> str:
        vendor_ctx = ""
        if vendor:
            vendor_ctx = f"""
Vendor context:
- Category: {vendor.get('category') or vendor.get('vendor_category') or 'General'}
- Products: {', '.join(vendor.get('products', [])[:5]) or 'N/A'}
- Experience level: {vendor.get('experience') or 'unknown'}
"""
        return f"""You are helping a vendor decide whether to attend a market event.

Event details:
- Name: {event.get('name', 'Unknown Event')}
- City: {event.get('city', '')}, {event.get('state', '')}
- Date: {event.get('date', 'TBD')}
- Type: {event.get('event_type') or event.get('vendor_category') or 'Market'}
- Vendor count: {event.get('vendor_count', 'unknown')}
- Estimated traffic: {event.get('estimated_traffic', 'unknown')} visitors
- Booth price: ${event.get('booth_price', 0)}
- Popularity score: {event.get('popularity_score', 0)}/100
- Rule-based assessment: {base.risk_level}, revenue ${base.revenue_low}–${base.revenue_high}
{vendor_ctx}

Write a brief, honest 2-sentence summary of this event's potential, and 2-3 concise actionable tips.
Return JSON only:
{{
  "summary": "...",
  "tips": ["tip1", "tip2", "tip3"]
}}"""
