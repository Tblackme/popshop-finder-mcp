"""
Vendor Atlas — Material Search Engine

Helps vendors find and compare suppliers for raw materials.

Functions
---------
search_material_suppliers(material_name, vendor_id)
    → search stored suppliers for a material across the vendor's inventory

compare_supplier_prices(material_name, vendor_id)
    → compare price + shipping across known suppliers for this material

rank_suppliers(suppliers)
    → rank a list of supplier entries by a composite score

get_supplier_deal_suggestions(vendor_id)
    → return deal suggestions for all materials with known suppliers

Note: This engine works with data vendors have already saved in their
material_inventory records (supplier_url, last_price, shipping_days).
It ranks and compares across multiple entries for the same material name,
and can be extended to call external APIs for live price lookups.
"""
from __future__ import annotations

from typing import Any

from storage_materials import list_materials


# ── Scoring weights ───────────────────────────────────────────────────────────

_PRICE_WEIGHT = 0.50       # lower price is better
_SHIPPING_WEIGHT = 0.35    # faster shipping is better
_THRESHOLD_WEIGHT = 0.15   # higher threshold = vendor relies on it more


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize(value: float, low: float, high: float, invert: bool = False) -> float:
    """Normalize value to [0, 1]. If invert=True, lower is better."""
    if high == low:
        return 0.5
    norm = (value - low) / (high - low)
    return 1.0 - norm if invert else norm


def _score_supplier(
    price: float,
    shipping_days: int,
    low_stock_threshold: float,
    min_price: float,
    max_price: float,
    min_ship: float,
    max_ship: float,
    max_threshold: float,
) -> float:
    """Composite supplier score (higher = better deal)."""
    price_score = _normalize(price, min_price, max_price, invert=True)
    ship_score = _normalize(float(shipping_days), min_ship, max_ship, invert=True)
    threshold_score = _normalize(low_stock_threshold, 0, max(max_threshold, 1))
    return (
        price_score * _PRICE_WEIGHT
        + ship_score * _SHIPPING_WEIGHT
        + threshold_score * _THRESHOLD_WEIGHT
    )


# ── Public API ────────────────────────────────────────────────────────────────

def search_material_suppliers(
    material_name: str,
    vendor_id: int,
) -> list[dict[str, Any]]:
    """
    Search the vendor's saved materials for entries matching `material_name`.
    Returns all matching records with supplier info.
    """
    materials = list_materials(vendor_id)
    query = str(material_name or "").lower().strip()
    if not query:
        return []

    matches = [
        m for m in materials
        if query in m["material_name"].lower() and m.get("supplier_url")
    ]

    return [
        {
            "material_id": m["id"],
            "material_name": m["material_name"],
            "supplier_url": m["supplier_url"],
            "last_price": m["last_price"],
            "unit": m["unit"],
            "shipping_days": m["shipping_days"],
            "current_stock": m["quantity"],
            "low_stock_threshold": m["low_stock_threshold"],
        }
        for m in matches
    ]


def compare_supplier_prices(
    material_name: str,
    vendor_id: int,
) -> dict[str, Any]:
    """
    Compare all saved suppliers for a given material name.

    Returns:
        material_name, suppliers (ranked), cheapest, fastest, best_overall
    """
    suppliers = search_material_suppliers(material_name, vendor_id)
    if not suppliers:
        return {
            "material_name": material_name,
            "suppliers": [],
            "cheapest": None,
            "fastest": None,
            "best_overall": None,
            "note": "No suppliers found. Add supplier URLs in your Materials page.",
        }

    ranked = rank_suppliers(suppliers)

    cheapest = min(suppliers, key=lambda s: s["last_price"]) if any(s["last_price"] for s in suppliers) else None
    fastest = min(suppliers, key=lambda s: s["shipping_days"]) if suppliers else None
    best_overall = ranked[0] if ranked else None

    return {
        "material_name": material_name,
        "suppliers": ranked,
        "cheapest": cheapest,
        "fastest": fastest,
        "best_overall": best_overall,
        "note": f"{len(ranked)} supplier(s) compared.",
    }


def rank_suppliers(suppliers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Rank a list of supplier entries by composite score.
    Each entry must have: last_price, shipping_days, low_stock_threshold.
    Returns the list sorted best → worst with a `score` field added.
    """
    if not suppliers:
        return []

    prices = [s.get("last_price") or 0 for s in suppliers]
    ships = [s.get("shipping_days") or 0 for s in suppliers]
    thresholds = [s.get("low_stock_threshold") or 0 for s in suppliers]

    min_p, max_p = min(prices), max(prices)
    min_s, max_s = min(ships), max(ships)
    max_t = max(thresholds)

    scored = []
    for s in suppliers:
        score = _score_supplier(
            price=float(s.get("last_price") or 0),
            shipping_days=int(s.get("shipping_days") or 0),
            low_stock_threshold=float(s.get("low_stock_threshold") or 0),
            min_price=float(min_p),
            max_price=float(max_p),
            min_ship=float(min_s),
            max_ship=float(max_s),
            max_threshold=float(max_t),
        )
        entry = dict(s)
        entry["score"] = round(score, 3)
        scored.append(entry)

    scored.sort(key=lambda x: x["score"], reverse=True)

    # Add rank label
    for i, s in enumerate(scored):
        if i == 0:
            s["rank_label"] = "Best Deal"
        elif s.get("last_price") == min(prices):
            s["rank_label"] = "Cheapest"
        elif s.get("shipping_days") == min(ships):
            s["rank_label"] = "Fastest Shipping"
        else:
            s["rank_label"] = f"#{i + 1}"

    return scored


def get_supplier_deal_suggestions(vendor_id: int) -> list[dict[str, Any]]:
    """
    For each material in a vendor's inventory that has a supplier_url,
    surface the best deal info and flag materials where the vendor should
    consider re-ordering.

    Returns a list of deal suggestions sorted by urgency.
    """
    materials = list_materials(vendor_id)
    if not materials:
        return []

    # Group materials by name to compare when vendor has multiple suppliers
    # for the same raw material
    name_groups: dict[str, list[dict[str, Any]]] = {}
    for m in materials:
        if not m.get("supplier_url"):
            continue
        key = m["material_name"].lower().strip()
        name_groups.setdefault(key, []).append(m)

    suggestions = []
    for name_key, group in name_groups.items():
        ranked = rank_suppliers(group)
        best = ranked[0] if ranked else None
        stock = sum(m["quantity"] for m in group)
        threshold = max(m["low_stock_threshold"] for m in group)
        needs_reorder = stock <= threshold and threshold > 0

        suggestion: dict[str, Any] = {
            "material_name": group[0]["material_name"],
            "current_stock": round(stock, 2),
            "unit": group[0]["unit"],
            "low_stock_threshold": round(threshold, 2),
            "needs_reorder": needs_reorder,
            "supplier_count": len(group),
            "best_supplier": best,
            "all_suppliers": ranked,
        }

        if needs_reorder and best:
            suggestion["action"] = (
                f"Order from {best['supplier_url']} — "
                f"${best['last_price']:.2f}/{best['unit']}, "
                f"{best['shipping_days']}d shipping."
            )
        elif len(ranked) > 1:
            # Multiple suppliers — surface the best option
            suggestion["action"] = (
                f"Best deal: {best['supplier_url']} at "
                f"${best['last_price']:.2f}/{best['unit']}."
            )
        else:
            suggestion["action"] = None

        suggestions.append(suggestion)

    # Sort: needs_reorder first, then by name
    suggestions.sort(key=lambda s: (not s["needs_reorder"], s["material_name"]))
    return suggestions
