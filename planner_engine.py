"""
Vendor Atlas — Planner Engine

Smart scheduling logic for vendors:
  - suggest_work_times         — suggest production time blocks from availability
  - generate_production_plan   — recommend quantities to produce for an event
  - create_inventory_alerts    — warn when stock is too low for upcoming demand
  - recommend_events           — surface best-fit upcoming markets
"""

from __future__ import annotations

from datetime import date
from typing import Any

from storage_events import get_event_by_id, search_events
from storage_shopify import get_shopify_connection, get_shopify_products
from storage_users import get_user_by_id, get_vendor_profile, list_vendor_products

# Fraction of foot-traffic that buys from any one vendor (conservative).
_CONVERSION_RATE = 0.08

# Safety buffer multiplier added on top of expected event demand.
_PRODUCTION_BUFFER = 1.25

# Minimum on-hand units before we flag "low stock".
_LOW_STOCK_THRESHOLD = 5

# Maximum events returned by recommend_events.
_MAX_RECOMMENDED_EVENTS = 5

_WEEKDAY_ORDER = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]
_WEEKDAY_SET = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
_WEEKEND_SET = {"Saturday", "Sunday"}

# Default evening slot for weekdays; morning slot for weekends.
_DAY_SLOTS: dict[str, list[str]] = {
    "Monday":    ["6-8 PM", "8-10 AM"],
    "Tuesday":   ["6-8 PM", "8-10 AM"],
    "Wednesday": ["6-8 PM", "4-6 PM"],
    "Thursday":  ["6-8 PM", "4-6 PM"],
    "Friday":    ["4-6 PM", "6-8 PM"],
    "Saturday":  ["9-11 AM", "2-4 PM"],
    "Sunday":    ["10 AM-12 PM", "2-4 PM"],
}


def suggest_work_times(availability: dict[str, Any]) -> list[dict[str, str]]:
    """
    Given a user availability record (from get_availability_for_user),
    return a list of suggested production work-time blocks.

    Each suggestion has:
        day   — e.g. "Tuesday"
        time  — e.g. "6-8 PM"
        label — e.g. "Tuesday 6-8 PM"
        note  — optional context string
    """
    weekdays: list[str] = availability.get("weekdays") or []
    weekly_capacity: int = int(availability.get("weekly_capacity") or 2)

    # Keep only valid weekday names, preserving calendar order.
    available = [d for d in _WEEKDAY_ORDER if d in weekdays]
    if not available:
        # No preference saved — fall back to weekend mornings.
        available = ["Saturday", "Sunday"]

    suggestions: list[dict[str, str]] = []
    slot_index = 0  # Alternate between primary and secondary slot per day.

    for day in available:
        if len(suggestions) >= max(weekly_capacity, 1):
            break
        slots = _DAY_SLOTS.get(day, ["6-8 PM", "4-6 PM"])
        time = slots[slot_index % len(slots)]
        note = "After hours" if day in _WEEKDAY_SET else "Great for longer prep sessions"
        suggestions.append({"day": day, "time": time, "label": f"{day} {time}", "note": note})
        slot_index += 1

    # If capacity allows a second block and we only have one day, suggest another
    # slot on the same day rather than leaving the plan underloaded.
    if weekly_capacity >= 2 and len(suggestions) == 1:
        day = suggestions[0]["day"]
        slots = _DAY_SLOTS.get(day, ["6-8 PM", "4-6 PM"])
        alt_time = slots[1 % len(slots)]
        if alt_time != suggestions[0]["time"]:
            suggestions.append({
                "day": day,
                "time": alt_time,
                "label": f"{day} {alt_time}",
                "note": "Second block for this day",
            })

    return suggestions


# ── Helpers ───────────────────────────────────────────────────────────────────

def _estimate_sales_per_vendor(event: dict[str, Any]) -> float:
    """Estimate total unit sales for a single vendor at this event."""
    traffic = int(event.get("estimated_traffic") or 0)
    vendor_count = max(int(event.get("vendor_count") or 1), 1)
    return (traffic * _CONVERSION_RATE) / vendor_count


def _today_iso() -> str:
    return date.today().isoformat()


def _load_all_products(vendor_id: int) -> list[dict[str, Any]]:
    """Load platform products + Shopify products (deduplicated by name)."""
    products = list_vendor_products(vendor_id)
    shopify_conn = get_shopify_connection(vendor_id)
    if shopify_conn:
        existing_names = {p["name"] for p in products}
        for sp in get_shopify_products(vendor_id):
            if sp["name"] not in existing_names:
                products.append({
                    "name": sp["name"],
                    "price": sp.get("price"),
                    "inventory_quantity": sp.get("inventory_quantity", 0),
                    "source": "shopify",
                })
    return products


# ── Smart Planner functions ───────────────────────────────────────────────────

def generate_production_plan(
    vendor_id: int,
    event_id: str,
) -> dict[str, Any]:
    """
    Generate a recommended production plan for a vendor attending a specific event.

    Returns recommended quantities per product based on expected foot-traffic,
    vendor count, and current inventory levels.
    """
    event = get_event_by_id(event_id)
    if not event:
        return {"error": f"Event '{event_id}' not found."}

    products = _load_all_products(vendor_id)
    expected_per_vendor = _estimate_sales_per_vendor(event)
    n_products = max(len(products), 1)
    expected_per_product = expected_per_vendor / n_products

    breakdown: list[dict[str, Any]] = []
    for p in products:
        current_stock = int(p.get("inventory_quantity") or 0)
        target = max(int(expected_per_product * _PRODUCTION_BUFFER), 1)
        to_produce = max(target - current_stock, 0)
        breakdown.append({
            "product": p["name"],
            "current_inventory": current_stock,
            "expected_demand": round(expected_per_product, 1),
            "target_stock": target,
            "quantity_to_produce": to_produce,
        })

    breakdown.sort(key=lambda x: x["quantity_to_produce"], reverse=True)

    return {
        "event": event.get("name", event_id),
        "event_id": event_id,
        "event_date": event.get("date"),
        "estimated_traffic": event.get("estimated_traffic"),
        "vendor_count": event.get("vendor_count"),
        "expected_sales_per_vendor": round(expected_per_vendor, 1),
        "recommended_production": [
            {"product": r["product"], "quantity": r["quantity_to_produce"]}
            for r in breakdown
            if r["quantity_to_produce"] > 0
        ],
        "full_breakdown": breakdown,
    }


def create_inventory_alerts(vendor_id: int) -> list[dict[str, Any]]:
    """
    Compare current inventory against aggregate demand from upcoming events.

    Returns a list of low-stock warnings sorted by severity.
    """
    products = _load_all_products(vendor_id)
    if not products:
        return []

    upcoming = search_events({"start_date": _today_iso()})[:10]
    n_products = max(len(products), 1)

    # Accumulate expected demand per product across all upcoming events.
    total_demand: dict[str, float] = {p["name"]: 0.0 for p in products}
    demand_sources: dict[str, list[str]] = {p["name"]: [] for p in products}
    for event in upcoming:
        per_product = _estimate_sales_per_vendor(event) / n_products
        for p in products:
            total_demand[p["name"]] += per_product
            demand_sources[p["name"]].append(event.get("name") or event.get("id", ""))

    alerts: list[dict[str, Any]] = []
    for p in products:
        current = int(p.get("inventory_quantity") or 0)
        demand = total_demand[p["name"]]
        if current < _LOW_STOCK_THRESHOLD or current < demand:
            shortfall = max(round(demand - current, 1), 0.0)
            if current == 0:
                severity = "critical"
            elif shortfall > 5:
                severity = "high"
            else:
                severity = "low"
            rec = (
                f"Produce at least {int(shortfall) + _LOW_STOCK_THRESHOLD} more units."
                if shortfall > 0
                else f"Stock is low ({current} units). Consider restocking."
            )
            alerts.append({
                "product": p["name"],
                "current_inventory": current,
                "expected_demand": round(demand, 1),
                "shortfall": shortfall,
                "severity": severity,
                "events": demand_sources[p["name"]][:3],
                "recommendation": rec,
            })

    # Sort: critical → high → low
    severity_rank = {"critical": 0, "high": 1, "low": 2}
    alerts.sort(key=lambda a: severity_rank.get(a["severity"], 9))
    return alerts


def recommend_events(vendor_id: int) -> list[dict[str, Any]]:
    """
    Return upcoming events ranked by fit for this vendor.

    Considers vendor category, city, date proximity, and popularity score.
    """
    profile = get_vendor_profile(vendor_id)
    user = get_user_by_id(vendor_id)

    category = (profile or {}).get("category") or (user or {}).get("interests") or ""
    city = (profile or {}).get("location") or ""

    filters: dict[str, Any] = {"start_date": _today_iso()}
    if category:
        filters["vendor_category"] = category.split(",")[0].strip()

    events = search_events(filters)

    def _score(ev: dict[str, Any]) -> float:
        base = float(ev.get("popularity_score") or 50)
        if city and city.lower() in (ev.get("city") or "").lower():
            base += 20
        ev_date = ev.get("date") or ""
        if ev_date:
            try:
                days_away = (date.fromisoformat(ev_date) - date.today()).days
                if 0 <= days_away <= 30:
                    base += 10
                elif days_away <= 60:
                    base += 5
            except ValueError:
                pass
        return base

    ranked = sorted(events, key=_score, reverse=True)[:_MAX_RECOMMENDED_EVENTS]

    return [
        {
            "id": ev.get("id"),
            "name": ev.get("name"),
            "city": ev.get("city"),
            "state": ev.get("state"),
            "date": ev.get("date"),
            "estimated_traffic": ev.get("estimated_traffic"),
            "booth_price": ev.get("booth_price"),
            "popularity_score": ev.get("popularity_score"),
            "event_type": ev.get("event_type"),
            "vendor_category": ev.get("vendor_category"),
            "match_score": round(_score(ev), 1),
        }
        for ev in ranked
    ]
