from datetime import UTC, datetime
from typing import Any

BUILD_VENDOR_PROFILE_TOOL: dict[str, Any] = {
    "name": "build_vendor_profile",
    "description": "Summarize quiz-style answers about a vendor into a structured vendor profile for Vendor Atlas.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "answers": {
                "type": "object",
                "description": "Raw answers from the vendor quiz.",
                "properties": {
                    "what_you_sell": {"type": "string"},
                    "style": {"type": "string"},
                    "price_range": {"type": "string"},
                    "main_goal": {"type": "string"},
                    "event_preferences": {"type": "string"},
                    "max_booth_price": {"type": ["number", "null"]},
                    "logistics": {"type": "string"},
                    "experience_level": {"type": "string"},
                },
                "required": ["what_you_sell"],
            }
        },
        "required": ["answers"],
    },
}


def _infer_category(text: str) -> str:
    t = text.lower()
    if "jewel" in t or "earring" in t or "necklace" in t:
        return "Handmade Jewelry"
    if "vintage" in t or "thrift" in t:
        return "Vintage & Thrift"
    if "art" in t or "print" in t or "painting" in t:
        return "Art & Prints"
    if "bake" in t or "cookie" in t or "cake" in t or "food" in t:
        return "Food & Treats"
    if "candle" in t or "soap" in t or "body" in t:
        return "Home & Body"
    return "Handmade Goods"


def _infer_price_range(text: str) -> str:
    t = text.lower()
    if any(word in t for word in ["under $20", "under 20", "cheap", "low"]):
        return "low"
    if any(word in t for word in ["over $200", "over 200", "premium", "luxury"]):
        return "high"
    return "mid"


def _infer_goal(text: str) -> str:
    t = text.lower()
    if "sell out" in t or "money" in t or "profit" in t:
        return "sell_out"
    if "audience" in t or "followers" in t or "email" in t:
        return "grow_audience"
    if "test" in t or "experiment" in t or "try" in t:
        return "test_ideas"
    return "community"


def _infer_env(text: str) -> str:
    t = text.lower()
    if "indoor" in t:
        return "indoor"
    if "outdoor" in t:
        return "outdoor"
    return "either"


def _infer_risk(text: str) -> str:
    t = text.lower()
    if "safe" in t or "low risk" in t or "not risky" in t:
        return "low"
    if "risk" in t or "experiment" in t or "try big" in t:
        return "high"
    return "medium"


async def handle_build_vendor_profile(answers: dict[str, Any]) -> str:
    """
    Heuristically structure quiz answers into a vendor profile JSON string.
    The calling AI can treat this as the authoritative profile shape.
    """
    import json

    what = (answers.get("what_you_sell") or "").strip()
    style = (answers.get("style") or "").strip()
    price_text = (answers.get("price_range") or "").strip()
    goal_text = (answers.get("main_goal") or "").strip()
    prefs = (answers.get("event_preferences") or "").strip()
    experience_text = (answers.get("experience_level") or "").strip()

    category = _infer_category(what)
    price_range = _infer_price_range(price_text)
    goal = _infer_goal(goal_text)
    preferred_env = _infer_env(prefs)
    risk_tolerance = _infer_risk(goal_text + " " + experience_text)

    max_booth_price = answers.get("max_booth_price")
    try:
        if isinstance(max_booth_price, str):
            cleaned = max_booth_price.replace("$", "").strip()
            max_booth_price = float(cleaned) if cleaned else None
    except ValueError:
        max_booth_price = None

    summary_parts: list[str] = []
    if category:
        summary_parts.append(category)
    if "jewel" in what.lower():
        summary_parts.append("jewelry")
    if style:
        summary_parts.append(style)
    summary = " ".join(summary_parts) or "Independent vendor"

    profile = {
        "id": f"profile-{int(datetime.now(UTC).timestamp())}",
        "summary": summary,
        "category": category,
        "subcategories": [],
        "price_range": price_range,
        "goal": goal,
        "preferred_env": preferred_env,
        "preferred_times": [],
        "max_booth_price": max_booth_price,
        "risk_tolerance": risk_tolerance,
        "logistics_needs": [],
        "experience_level": "early_stage" if "first" in experience_text.lower() or "new" in experience_text.lower() else "experienced",
        "ideal_audience": [],
        "tags": [],
    }

    return json.dumps({"profile": profile})


TOOLS: list[dict[str, Any]] = [BUILD_VENDOR_PROFILE_TOOL]

HANDLERS: dict[str, Any] = {
    "build_vendor_profile": handle_build_vendor_profile,
}

