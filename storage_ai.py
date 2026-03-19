"""
storage_ai.py — AI-specific persistence layer for Vendor Atlas.

Tables owned by this module:
  vendor_event_scores  — fit scores between a vendor profile and an event
  ai_content_cache     — cached AI-generated text (bio, captions, descriptions)
  ai_usage_log         — per-user AI feature usage for billing / rate limiting

Rules:
  - This module never writes to core tables (users, vendor_profiles, events, etc.)
  - AI output is always stored as suggestions — it only reaches core tables when
    the user explicitly saves it via a POST to a core route
  - All tables are created lazily; the module is safe to import even when
    AI features are disabled
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from db_runtime import connect


def _connect():
    return connect()


def _uuid() -> str:
    return str(uuid.uuid4())


def _row_to_dict(row) -> dict[str, Any] | None:
    if not row:
        return None
    return {key: row[key] for key in row.keys()}


def _rows_to_dicts(rows) -> list[dict[str, Any]]:
    return [{key: row[key] for key in row.keys()} for row in rows]


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def init_ai_db() -> None:
    conn = _connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS vendor_event_scores (
                id TEXT PRIMARY KEY,
                vendor_id INTEGER NOT NULL,
                event_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                reason TEXT,
                model TEXT DEFAULT 'rule_based',
                scored_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(vendor_id, event_id)
            );

            CREATE TABLE IF NOT EXISTS ai_content_cache (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                content_type TEXT NOT NULL,
                input_hash TEXT NOT NULL,
                output TEXT NOT NULL,
                model TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, content_type, input_hash)
            );

            CREATE TABLE IF NOT EXISTS ai_usage_log (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                feature TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# vendor_event_scores
# ---------------------------------------------------------------------------

def get_event_score(vendor_id: int, event_id: str) -> dict[str, Any] | None:
    init_ai_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM vendor_event_scores WHERE vendor_id = ? AND event_id = ?",
            (vendor_id, str(event_id)),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row)


def get_bulk_event_scores(vendor_id: int, event_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Return {event_id: score_row} for all requested event IDs."""
    if not event_ids:
        return {}
    init_ai_db()
    placeholders = ",".join("?" for _ in event_ids)
    conn = _connect()
    try:
        rows = conn.execute(
            f"SELECT * FROM vendor_event_scores WHERE vendor_id = ? AND event_id IN ({placeholders})",
            (vendor_id, *event_ids),
        ).fetchall()
    finally:
        conn.close()
    return {row["event_id"]: _row_to_dict(row) for row in rows}


def upsert_event_score(
    vendor_id: int,
    event_id: str,
    score: int,
    reason: str = "",
    model: str = "rule_based",
) -> dict[str, Any]:
    init_ai_db()
    row_id = _uuid()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO vendor_event_scores (id, vendor_id, event_id, score, reason, model, scored_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(vendor_id, event_id) DO UPDATE SET
                score = excluded.score,
                reason = excluded.reason,
                model = excluded.model,
                scored_at = CURRENT_TIMESTAMP
            """,
            (row_id, vendor_id, str(event_id), int(score), reason, model),
        )
        conn.commit()
    finally:
        conn.close()
    return get_event_score(vendor_id, event_id) or {}


def score_and_store_events(vendor_id: int, vendor_profile: dict[str, Any], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score a list of events for a vendor and persist results. Returns scored events."""
    results = []
    for event in events:
        score, reason = _rule_based_score(vendor_profile, event)
        event_id = str(event.get("id") or event.get("event_id") or "")
        if event_id:
            upsert_event_score(vendor_id, event_id, score, reason, model="rule_based")
        results.append({**event, "fit_score": score, "fit_reason": reason})
    return results


# ---------------------------------------------------------------------------
# Rule-based event fit scorer
# ---------------------------------------------------------------------------

# Category keyword groups — events matching a vendor's category get bonus points
_CATEGORY_GROUPS: list[set[str]] = [
    {"jewelry", "jewel", "accessories", "gems", "beads"},
    {"ceramics", "pottery", "clay", "stoneware"},
    {"art", "prints", "illustration", "painting", "photography"},
    {"apparel", "clothing", "fashion", "textile", "fabric", "embroidery", "sewing"},
    {"vintage", "antique", "thrift", "retro", "collectible", "oddity", "curiosity"},
    {"food", "treats", "baked", "candy", "jam", "sauce", "spice", "snack"},
    {"candle", "soap", "body", "skincare", "bath", "fragrance", "lotion"},
    {"plant", "flower", "succulent", "botanical", "garden"},
    {"woodwork", "furniture", "carved", "timber"},
    {"leather", "bag", "wallet", "belt"},
    {"sticker", "paper", "zine", "print", "card", "stationary"},
    {"home", "decor", "housewares", "kitchenware", "linen"},
    {"craft", "handmade", "maker", "artisan", "hand-made"},
    {"market", "bazaar", "fair", "festival", "popup", "pop-up"},
]


def _category_overlap(vendor_cat: str, event_cat: str) -> int:
    """Return 0 (no match), 1 (same group), or 2 (direct keyword match)."""
    if not vendor_cat or not event_cat:
        return 0
    v = vendor_cat.lower()
    e = event_cat.lower()
    # Direct substring match
    if v in e or e in v:
        return 2
    # Same group match
    for group in _CATEGORY_GROUPS:
        v_in = any(kw in v for kw in group)
        e_in = any(kw in e for kw in group)
        if v_in and e_in:
            return 1
    return 0


def _rule_based_score(vendor_profile: dict[str, Any], event: dict[str, Any]) -> tuple[int, str]:
    """
    Pure rule-based fit score between a vendor profile and an event.
    Returns (score 0-100, human-readable reason).
    No external calls — deterministic.
    """
    score = 50
    reasons: list[str] = []

    # ── Category match ──
    vendor_cat = str(vendor_profile.get("category") or "")
    event_cat = str(event.get("vendor_category") or event.get("category") or "")
    cat_match = _category_overlap(vendor_cat, event_cat)
    if cat_match == 2:
        score += 22
        reasons.append("strong category match")
    elif cat_match == 1:
        score += 10
        reasons.append("related category")
    elif vendor_cat and event_cat:
        score -= 5  # different niches

    # ── Booth fee vs budget ──
    raw_fee = vendor_profile.get("max_booth_price")
    max_fee = float(raw_fee) if raw_fee is not None else 0.0
    event_fee = float(event.get("booth_price") or event.get("vendor_fee") or 0)
    if max_fee > 0 and event_fee > 0:
        ratio = event_fee / max_fee
        if ratio <= 1.0:
            score += 15
            reasons.append("fee fits budget")
        elif ratio <= 1.25:
            score += 5
        elif ratio <= 1.75:
            score -= 10
            reasons.append("fee slightly over budget")
        else:
            score -= 20
            reasons.append("fee over budget")
    elif max_fee > 0 and event_fee == 0:
        score += 8  # free booth is always good

    # ── Traffic vs goal ──
    goal = str(vendor_profile.get("main_goal") or "")
    traffic = int(event.get("estimated_traffic") or 0)
    if goal == "grow_audience":
        if traffic >= 1000:
            score += 12
            reasons.append("high traffic for audience growth")
        elif traffic >= 300:
            score += 6
        elif traffic > 0 and traffic < 100:
            score -= 5
    elif goal == "sell_out":
        if traffic >= 500:
            score += 10
            reasons.append("strong buying crowd")
        elif traffic >= 200:
            score += 5
    elif goal == "test_ideas":
        # Smaller, lower-risk events are ideal
        event_size = str(event.get("event_size") or "").lower()
        if event_size in ("small", "med"):
            score += 8
            reasons.append("good size to test products")
    elif goal == "community":
        # Local / craft focus preferred
        if cat_match >= 1:
            score += 5

    # ── Event size vs experience ──
    experience = str(vendor_profile.get("experience_level") or "")
    event_size = str(event.get("event_size") or "").lower()
    if experience == "early_stage":
        if event_size in ("small", "med"):
            score += 7
            reasons.append("beginner-friendly size")
        elif event_size == "large":
            score -= 5
    elif experience == "experienced":
        if event_size in ("large", "high"):
            score += 5
            reasons.append("experienced vendor fit")

    # ── Risk tolerance vs popularity ──
    risk = str(vendor_profile.get("risk_tolerance") or "")
    pop = int(event.get("popularity_score") or 0)
    if risk == "low" and pop >= 70:
        score += 6
        reasons.append("proven popular event")
    elif risk == "low" and pop > 0 and pop < 50:
        score -= 8
        reasons.append("lower-proven event")
    elif risk == "high" and pop > 0 and pop < 60:
        score += 4  # willing to try newer events

    # ── Price range alignment ──
    price_range = str(vendor_profile.get("price_range") or "")
    if price_range == "high":
        if event_size in ("large",) or traffic >= 500:
            score += 5
    elif price_range == "low":
        if event_size in ("small",) or (event_fee > 0 and event_fee <= 50):
            score += 5

    score = max(0, min(100, score))

    # Build readable reason
    if not reasons:
        if score >= 70:
            reason = "generally good fit"
        elif score >= 50:
            reason = "moderate fit"
        else:
            reason = "limited match"
    else:
        reason = ", ".join(reasons[:2])

    return score, reason


# ---------------------------------------------------------------------------
# ai_content_cache
# ---------------------------------------------------------------------------

def _hash_input(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def get_ai_cache(user_id: int, content_type: str, input_data: str) -> str | None:
    """Return cached AI output or None."""
    init_ai_db()
    input_hash = _hash_input(input_data)
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT output FROM ai_content_cache WHERE user_id = ? AND content_type = ? AND input_hash = ?",
            (user_id, content_type, input_hash),
        ).fetchone()
    finally:
        conn.close()
    return row["output"] if row else None


def set_ai_cache(user_id: int, content_type: str, input_data: str, output: str, model: str = "") -> None:
    init_ai_db()
    input_hash = _hash_input(input_data)
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO ai_content_cache (id, user_id, content_type, input_hash, output, model)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, content_type, input_hash) DO UPDATE SET
                output = excluded.output,
                model = excluded.model,
                created_at = CURRENT_TIMESTAMP
            """,
            (_uuid(), user_id, content_type, input_hash, output, model),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# ai_usage_log
# ---------------------------------------------------------------------------

def log_ai_usage(user_id: int, feature: str, tokens_used: int = 0, cost_usd: float = 0.0) -> None:
    init_ai_db()
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO ai_usage_log (id, user_id, feature, tokens_used, cost_usd) VALUES (?, ?, ?, ?, ?)",
            (_uuid(), user_id, feature, tokens_used, cost_usd),
        )
        conn.commit()
    finally:
        conn.close()


def get_user_ai_usage(user_id: int, days: int = 30) -> dict[str, Any]:
    """Return usage summary for the last N days — used for billing / rate limiting."""
    init_ai_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT feature, COUNT(*) AS calls, SUM(tokens_used) AS tokens, SUM(cost_usd) AS cost
            FROM ai_usage_log
            WHERE user_id = ?
              AND created_at >= datetime('now', ? || ' days')
            GROUP BY feature
            """,
            (user_id, f"-{days}"),
        ).fetchall()
        total = conn.execute(
            """
            SELECT COUNT(*) AS calls, SUM(tokens_used) AS tokens, SUM(cost_usd) AS cost
            FROM ai_usage_log
            WHERE user_id = ?
              AND created_at >= datetime('now', ? || ' days')
            """,
            (user_id, f"-{days}"),
        ).fetchone()
    finally:
        conn.close()
    return {
        "user_id": user_id,
        "period_days": days,
        "by_feature": _rows_to_dicts(rows),
        "total_calls": int(total["calls"] or 0),
        "total_tokens": int(total["tokens"] or 0),
        "total_cost_usd": round(float(total["cost"] or 0), 4),
    }
