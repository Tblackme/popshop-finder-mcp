from typing import Any

SCORE_MARKET_TOOL: dict[str, Any] = {
    "name": "score_market_for_vendor",
    "description": "Compute a simple fit score (0-100) for one market given a vendor profile.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "vendor_profile": {"type": "object"},
            "market": {"type": "object"},
        },
        "required": ["vendor_profile", "market"],
    },
}


RANK_MARKETS_TOOL: dict[str, Any] = {
    "name": "rank_markets_for_vendor",
    "description": "Rank a list of markets for a vendor and return scores plus short reasons.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "vendor_profile": {"type": "object"},
            "markets": {
                "type": "array",
                "items": {"type": "object"},
            },
        },
        "required": ["vendor_profile", "markets"],
    },
}


COMPARE_MARKETS_TOOL: dict[str, Any] = {
    "name": "compare_markets_for_vendor",
    "description": "Compare 2-5 saved markets for a vendor and recommend an order.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "vendor_profile": {"type": "object"},
            "markets": {
                "type": "array",
                "items": {"type": "object"},
                "minItems": 2,
                "maxItems": 5,
            },
        },
        "required": ["vendor_profile", "markets"],
    },
}


def _base_fit_for_market(vendor_profile: dict[str, Any], market: dict[str, Any]) -> dict[str, Any]:
    """Heuristic scoring based on budget, env, and basic popularity/traffic."""
    score = 50
    reasons_pos: list[str] = []
    reasons_risk: list[str] = []

    max_booth = vendor_profile.get("max_booth_price")
    booth_price = market.get("booth_price")
    if isinstance(booth_price, (int, float)) and booth_price > 0:
        if max_booth:
            if booth_price <= max_booth:
                score += 10
                reasons_pos.append("Booth price within your budget.")
            else:
                score -= 10
                reasons_risk.append("Booth price above your stated comfort zone.")
        else:
            score += 3

    preferred_env = vendor_profile.get("preferred_env")
    env = market.get("indoor_outdoor")
    if preferred_env in {"indoor", "outdoor"} and env:
        if preferred_env == env:
            score += 10
            reasons_pos.append(f"{env.capitalize()} event matches your preference.")
        elif env != "mixed":
            score -= 5
            reasons_risk.append(f"{env.capitalize()} event may not match your usual setup.")

    est_traffic = market.get("estimated_traffic") or 0
    if est_traffic >= 3000:
        score += 10
        reasons_pos.append("High estimated traffic.")
    elif est_traffic <= 500:
        score -= 5
        reasons_risk.append("Traffic may be on the lower side.")

    popularity = market.get("popularity_score") or 0
    if popularity >= 80:
        score += 5
    elif popularity <= 40:
        score -= 3

    risk_tolerance = vendor_profile.get("risk_tolerance", "medium")
    if risk_tolerance == "low" and booth_price and est_traffic and booth_price > 0:
        if booth_price > (max_booth or booth_price) and est_traffic < 1000:
            score -= 10
            reasons_risk.append("Higher risk for your low-risk comfort level.")

    score = max(0, min(100, score))
    if score >= 80:
        label = "Great fit"
    elif score >= 65:
        label = "Good fit"
    elif score >= 50:
        label = "Worth considering"
    else:
        label = "Lower priority"

    rec = "Solid option that aligns with your goals."
    if reasons_risk and score < 70:
        rec = "Consider this market if budget and logistics feel comfortable."
    elif score >= 80:
        rec = "Strong candidate for your next market."

    return {
        "fit_score": score,
        "fit_label": label,
        "positives": reasons_pos,
        "risks": reasons_risk,
        "recommendation": rec,
    }


async def handle_score_market_for_vendor(vendor_profile: dict[str, Any], market: dict[str, Any]) -> str:
    import json

    base = _base_fit_for_market(vendor_profile, market)
    result = {
        "market_id": market.get("id"),
        **base,
    }
    return json.dumps(result)


async def handle_rank_markets_for_vendor(vendor_profile: dict[str, Any], markets: list[dict[str, Any]]) -> str:
    import json

    scored = []
    for m in markets:
        base = _base_fit_for_market(vendor_profile, m)
        scored.append(
            {
                "market_id": m.get("id"),
                "fit_score": base["fit_score"],
                "fit_label": base["fit_label"],
                "short_reason": (base["positives"] or base["risks"] or [""])[0],
            }
        )
    scored.sort(key=lambda x: x["fit_score"], reverse=True)
    payload = {
        "ranked_markets": scored,
        "overall_advice": "Start with the top-ranked markets and review booth fees and logistics to confirm they fit your business.",
    }
    return json.dumps(payload)


async def handle_compare_markets_for_vendor(vendor_profile: dict[str, Any], markets: list[dict[str, Any]]) -> str:
    import json

    enriched = []
    for m in markets:
        base = _base_fit_for_market(vendor_profile, m)
        enriched.append(
            {
                "market_id": m.get("id"),
                "fit_score": base["fit_score"],
                "why": (base["positives"] or base["risks"] or [""])[0],
            }
        )
    enriched.sort(key=lambda x: x["fit_score"], reverse=True)

    summary = "Pick the top option if you want the best balance of fit and opportunity."
    strategy = [
        "Book the highest scoring market as your priority show.",
        "Use one lower-stakes event to practice your booth flow if you are newer to markets.",
    ]

    payload = {
        "recommendation_order": enriched,
        "summary": summary,
        "suggested_strategy": strategy,
    }
    return json.dumps(payload)


TOOLS: list[dict[str, Any]] = [
    SCORE_MARKET_TOOL,
    RANK_MARKETS_TOOL,
    COMPARE_MARKETS_TOOL,
]

HANDLERS: dict[str, Any] = {
    "score_market_for_vendor": handle_score_market_for_vendor,
    "rank_markets_for_vendor": handle_rank_markets_for_vendor,
    "compare_markets_for_vendor": handle_compare_markets_for_vendor,
}

