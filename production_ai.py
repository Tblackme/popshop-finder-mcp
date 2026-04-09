"""
Vendor Atlas — AI Production Planner

Connects material inventory, product recipes, upcoming events, and the vendor
calendar to automatically plan production.

Functions
---------
calculate_material_requirements(vendor_id, product_name, quantity)
    → how much of each material is needed to make N units of a product

check_material_inventory(vendor_id, requirements)
    → which materials have enough stock vs. what needs to be ordered

calculate_shipping_time(vendor_id, requirements)
    → latest order date per material given supplier shipping times

generate_production_schedule(vendor_id, event_id)
    → full schedule: order dates, production blocks, calendar suggestions

generate_material_alerts(vendor_id)
    → alerts for materials that will run out before upcoming events
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from storage_events import search_events
from storage_materials import (
    get_low_stock_materials,
    get_product_recipe,
    get_recipes_for_vendor,
    list_materials,
)
from storage_users import list_vendor_products


# ── Constants ─────────────────────────────────────────────────────────────────

# How many days before the event to finish all production
_PRODUCTION_LEAD_DAYS = 2

# Extra buffer factor on top of expected demand
_PRODUCTION_BUFFER = 1.25

# Estimated sales conversion rate per vendor
_CONVERSION_RATE = 0.08


# ── Helpers ───────────────────────────────────────────────────────────────────

def _today() -> date:
    return date.today()


def _parse_date(d: str | None) -> date | None:
    if not d:
        return None
    try:
        return date.fromisoformat(str(d)[:10])
    except ValueError:
        return None


def _estimate_demand(event: dict[str, Any], n_products: int) -> float:
    """Estimate unit demand for a single product at an event."""
    traffic = int(event.get("estimated_traffic") or 0)
    vendor_count = max(int(event.get("vendor_count") or 1), 1)
    n_products = max(n_products, 1)
    per_vendor = (traffic * _CONVERSION_RATE) / vendor_count
    return (per_vendor / n_products) * _PRODUCTION_BUFFER


# ── Core Functions ────────────────────────────────────────────────────────────

def calculate_material_requirements(
    vendor_id: int,
    product_id: int,
    quantity: int,
) -> list[dict[str, Any]]:
    """
    Return how much of each raw material is needed to make `quantity` units
    of a given product (looked up via product recipe).

    Each entry:
        material_id, material_name, unit,
        per_unit, total_needed, stock_on_hand,
        shortfall (negative means we have surplus),
        needs_order (bool)
    """
    recipe = get_product_recipe(product_id)
    if not recipe:
        return []

    result = []
    for r in recipe:
        per_unit = float(r["quantity_required"])
        total_needed = per_unit * int(quantity)
        stock = float(r.get("stock", 0))
        shortfall = total_needed - stock
        result.append({
            "material_id": r["material_id"],
            "material_name": r["material_name"],
            "unit": r["unit"],
            "per_unit": per_unit,
            "total_needed": round(total_needed, 3),
            "stock_on_hand": round(stock, 3),
            "shortfall": round(max(shortfall, 0), 3),
            "needs_order": shortfall > 0,
        })

    return sorted(result, key=lambda x: x["needs_order"], reverse=True)


def check_material_inventory(
    vendor_id: int,
    requirements: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Given a requirements list (from calculate_material_requirements),
    split into:
        sufficient  — materials with enough stock
        short       — materials that must be ordered
    Also returns a summary boolean `all_clear`.
    """
    sufficient = [r for r in requirements if not r["needs_order"]]
    short = [r for r in requirements if r["needs_order"]]
    return {
        "all_clear": len(short) == 0,
        "sufficient": sufficient,
        "short": short,
        "summary": (
            "All materials in stock — ready to produce."
            if not short
            else f"{len(short)} material(s) need to be ordered before production can begin."
        ),
    }


def calculate_shipping_time(
    vendor_id: int,
    requirements: list[dict[str, Any]],
    event_date: str | None = None,
) -> list[dict[str, Any]]:
    """
    For each material that needs to be ordered, compute:
        order_by_date — latest date vendor must place the order
        days_until_event — how many days remain
        on_time — whether there is still time to order and receive

    If event_date is None, returns shipping info without deadline checks.
    """
    materials = {m["id"]: m for m in list_materials(vendor_id)}
    ev_date = _parse_date(event_date)
    today = _today()

    result = []
    for req in requirements:
        if not req.get("needs_order"):
            continue
        mat = materials.get(req["material_id"], {})
        shipping_days = int(mat.get("shipping_days") or req.get("shipping_days", 0) or 0)
        supplier_url = mat.get("supplier_url") or ""
        last_price = float(mat.get("last_price") or 0)

        entry: dict[str, Any] = {
            "material_id": req["material_id"],
            "material_name": req["material_name"],
            "shortfall": req["shortfall"],
            "unit": req["unit"],
            "shipping_days": shipping_days,
            "supplier_url": supplier_url,
            "last_price": last_price,
            "order_by_date": None,
            "days_until_deadline": None,
            "on_time": True,
        }

        if ev_date:
            production_end = ev_date - timedelta(days=_PRODUCTION_LEAD_DAYS)
            order_by = production_end - timedelta(days=shipping_days)
            days_left = (order_by - today).days
            entry["order_by_date"] = order_by.isoformat()
            entry["days_until_deadline"] = days_left
            entry["on_time"] = days_left >= 0

        result.append(entry)

    return sorted(result, key=lambda x: (x["on_time"], x.get("days_until_deadline") or 999))


def generate_production_schedule(
    vendor_id: int,
    event_id: str,
) -> dict[str, Any]:
    """
    Full AI production schedule for a vendor attending a specific event.

    Steps:
    1. Look up event + vendor products
    2. Estimate demand per product
    3. For each product, calculate material requirements
    4. Check stock, identify what to order
    5. Compute order deadlines by material shipping time
    6. Suggest production calendar blocks

    Returns a rich schedule object with all sections filled.
    """
    from storage_events import get_event_by_id

    event = get_event_by_id(event_id)
    if not event:
        return {"error": f"Event '{event_id}' not found."}

    products = list_vendor_products(vendor_id)
    if not products:
        return {"error": "No products found for this vendor."}

    event_date_str: str = event.get("date") or ""
    ev_date = _parse_date(event_date_str)
    today = _today()
    days_to_event = (ev_date - today).days if ev_date else None

    n_products = len(products)
    demand_per_product = _estimate_demand(event, n_products)

    production_blocks: list[dict[str, Any]] = []
    order_actions: list[dict[str, Any]] = []
    all_requirements: list[dict[str, Any]] = []

    for product in products:
        product_id = int(product.get("id") or 0)
        product_name = product.get("name") or product.get("product_name") or ""
        quantity = max(int(demand_per_product), 1)

        reqs = calculate_material_requirements(vendor_id, product_id, quantity)
        if not reqs:
            # No recipe defined — still suggest a production block
            production_blocks.append({
                "product": product_name,
                "quantity": quantity,
                "note": "No material recipe set. Add ingredients in Materials.",
            })
            continue

        check = check_material_inventory(vendor_id, reqs)
        shipping = calculate_shipping_time(vendor_id, reqs, event_date_str)

        for s in shipping:
            # Avoid duplicate order actions for same material across products
            existing_ids = [a["material_id"] for a in order_actions]
            if s["material_id"] not in existing_ids:
                order_actions.append(s)

        all_requirements.extend(reqs)

        # Suggest production block date
        if ev_date and days_to_event is not None:
            # Aim to finish _PRODUCTION_LEAD_DAYS before event
            # If materials need ordering, schedule production after they arrive
            max_shipping = max(
                (int(r.get("shipping_days", 0) or 0) for r in reqs if r.get("needs_order")),
                default=0,
            )
            earliest_start = today + timedelta(days=max_shipping + 1)
            production_end = ev_date - timedelta(days=_PRODUCTION_LEAD_DAYS)
            if earliest_start <= production_end:
                block_start = production_end - timedelta(days=1)
                block_date = block_start.isoformat()
            else:
                block_date = today.isoformat()
        else:
            block_date = today.isoformat()

        production_blocks.append({
            "product": product_name,
            "quantity": quantity,
            "suggested_date": block_date,
            "materials_ready": check["all_clear"],
            "note": check["summary"],
        })

    # Deduplicate order actions
    seen: set[int] = set()
    deduped_orders: list[dict[str, Any]] = []
    for a in order_actions:
        if a["material_id"] not in seen:
            seen.add(a["material_id"])
            deduped_orders.append(a)

    urgent_orders = [o for o in deduped_orders if not o.get("on_time", True)]
    upcoming_orders = [o for o in deduped_orders if o.get("on_time", True)]

    return {
        "event": event.get("name", event_id),
        "event_id": event_id,
        "event_date": event_date_str,
        "days_to_event": days_to_event,
        "production_blocks": production_blocks,
        "order_actions": {
            "urgent": urgent_orders,
            "upcoming": upcoming_orders,
        },
        "calendar_suggestions": _build_calendar_suggestions(production_blocks, ev_date),
        "summary": _build_summary(production_blocks, deduped_orders, urgent_orders),
    }


def _build_calendar_suggestions(
    blocks: list[dict[str, Any]],
    ev_date: date | None,
) -> list[dict[str, Any]]:
    """Convert production blocks into accept/decline calendar suggestions."""
    suggestions = []
    for b in blocks:
        if not b.get("suggested_date"):
            continue
        product = b["product"]
        qty = b["quantity"]
        suggested_date = b["suggested_date"]
        suggestions.append({
            "title": f"Make {qty} × {product}",
            "date": suggested_date,
            "start_time": f"{suggested_date}T18:00:00",
            "end_time": f"{suggested_date}T20:00:00",
            "type": "production",
            "notes": b.get("note", ""),
            "status": "suggested",  # vendor can accept or decline
        })
    return suggestions


def _build_summary(
    blocks: list[dict[str, Any]],
    order_actions: list[dict[str, Any]],
    urgent_orders: list[dict[str, Any]],
) -> str:
    parts = []
    total_products = len(blocks)
    total_orders = len(order_actions)
    urgent = len(urgent_orders)

    if total_products:
        parts.append(f"Plan covers {total_products} product(s).")
    if total_orders:
        parts.append(f"{total_orders} material(s) need to be ordered.")
    if urgent:
        mat_names = ", ".join(o["material_name"] for o in urgent_orders[:3])
        parts.append(f"URGENT: order {mat_names} immediately — shipping deadline has passed or is today.")
    elif total_orders:
        earliest = min(
            (o["order_by_date"] for o in order_actions if o.get("order_by_date")),
            default=None,
        )
        if earliest:
            parts.append(f"Order by {earliest} to receive materials in time.")

    return " ".join(parts) if parts else "Production schedule generated."


# ── Material Alerts ───────────────────────────────────────────────────────────

def generate_material_alerts(vendor_id: int) -> list[dict[str, Any]]:
    """
    Generate plain-language alerts for materials that will run out
    before upcoming events.

    Format:
        {
            material_name, current_stock, unit,
            shortfall, severity (critical/high/low),
            events_affected (list of event names),
            message (human-readable alert),
            order_by_date (if calculable),
            supplier_url
        }
    """
    materials = list_materials(vendor_id)
    if not materials:
        return []

    upcoming = search_events({"start_date": _today().isoformat()})[:8]
    products = list_vendor_products(vendor_id)
    n_products = max(len(products), 1)

    # Build a map of material_id → total demand across upcoming events
    demand_map: dict[int, float] = {m["id"]: 0.0 for m in materials}
    events_map: dict[int, list[str]] = {m["id"]: [] for m in materials}

    for event in upcoming:
        demand_per_product = _estimate_demand(event, n_products)
        event_name = event.get("name") or str(event.get("id", ""))
        event_date_str = event.get("date") or ""

        for product in products:
            product_id = int(product.get("id") or 0)
            recipe = get_product_recipe(product_id)
            qty = max(int(demand_per_product), 1)
            for r in recipe:
                mat_id = r["material_id"]
                if mat_id in demand_map:
                    demand_map[mat_id] += r["quantity_required"] * qty
                    if event_name not in events_map[mat_id]:
                        events_map[mat_id].append(event_name)

    # Also catch low-stock materials even without recipe demand
    low_stock = {m["id"] for m in get_low_stock_materials(vendor_id)}

    alerts = []
    today = _today()

    for mat in materials:
        mat_id = mat["id"]
        stock = float(mat["quantity"])
        demand = demand_map.get(mat_id, 0.0)
        threshold = float(mat.get("low_stock_threshold") or 0)
        affected_events = events_map.get(mat_id, [])

        is_low = mat_id in low_stock
        has_demand = demand > 0
        shortfall = max(demand - stock, 0.0)

        if not is_low and shortfall == 0:
            continue  # No issue

        # Severity
        if stock == 0:
            severity = "critical"
        elif shortfall > threshold:
            severity = "high"
        elif is_low:
            severity = "low"
        else:
            severity = "low"

        # Order deadline
        shipping_days = int(mat.get("shipping_days") or 0)
        order_by_date: str | None = None
        if affected_events and upcoming:
            # Use nearest event date
            nearest_ev = min(
                (e for e in upcoming if e.get("name") in affected_events or True),
                key=lambda e: e.get("date") or "9999",
                default=None,
            )
            if nearest_ev:
                ev_d = _parse_date(nearest_ev.get("date"))
                if ev_d:
                    deadline = ev_d - timedelta(days=_PRODUCTION_LEAD_DAYS + shipping_days)
                    order_by_date = deadline.isoformat()

        # Message
        if stock == 0 and affected_events:
            msg = (
                f"You have no {mat['material_name']} left. "
                f"Order now — needed for: {', '.join(affected_events[:2])}."
            )
        elif shortfall > 0 and affected_events:
            msg = (
                f"You will run out of {mat['material_name']} before "
                f"{affected_events[0]}. "
                f"You need {round(shortfall, 1)} more {mat['unit']}."
            )
        else:
            msg = (
                f"{mat['material_name']} is running low "
                f"({round(stock, 1)} {mat['unit']} remaining). Consider restocking."
            )

        alerts.append({
            "material_id": mat_id,
            "material_name": mat["material_name"],
            "current_stock": round(stock, 2),
            "unit": mat["unit"],
            "demand": round(demand, 2),
            "shortfall": round(shortfall, 2),
            "severity": severity,
            "events_affected": affected_events[:3],
            "message": msg,
            "order_by_date": order_by_date,
            "supplier_url": mat.get("supplier_url") or "",
        })

    # Sort: critical → high → low
    rank = {"critical": 0, "high": 1, "low": 2}
    alerts.sort(key=lambda a: rank.get(a["severity"], 9))
    return alerts
