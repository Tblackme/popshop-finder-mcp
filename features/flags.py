"""
Feature flag system for Vendor Atlas.

Flags are read from environment variables at startup. Admin overrides stored
in features/overrides.json take precedence over env vars and persist across
process restarts (but not across filesystem resets on Render ephemeral disks).

Usage:
    from features.flags import flags, Feature

    if flags.is_enabled(Feature.SOCIAL_FEED):
        ...

MVP flags default to True, non-MVP flags default to False.
All flags can be overridden via env vars or the admin panel.
"""

from __future__ import annotations

import json
import logging
import os
from enum import Enum
from pathlib import Path

logger = logging.getLogger("vendor-atlas.flags")

_OVERRIDES_PATH = Path(__file__).parent / "overrides.json"


class Feature(str, Enum):
    # ── AI features (legacy, kept for backwards compat) ──────────────────────
    AI_CONTENT   = "ai_content"
    AI_MATCHING  = "ai_matching"
    AI_MARKETING = "ai_marketing"
    AI_INSIGHTS  = "ai_insights"
    AI_ASSISTANT = "ai_assistant"

    # ── Core MVP features (default ON) ────────────────────────────────────────
    VENDOR_PROFILES       = "vendor_profiles"
    MARKET_DISCOVERY      = "market_discovery"
    MARKET_APPLICATIONS   = "market_applications"
    VENDOR_DASHBOARD      = "vendor_dashboard"
    MARKET_MAP            = "market_map"
    INVENTORY_TRACKING    = "inventory_tracking"
    VENDOR_CALENDAR       = "vendor_calendar"
    PROFIT_PLANNER        = "profit_planner"
    SHOPIFY_SYNC          = "shopify_sync"
    EVENT_RECOMMENDATIONS = "event_recommendations"

    # ── Non-MVP features (default OFF) ────────────────────────────────────────
    SOCIAL_FEED           = "social_feed"
    COMMUNITY_ROOMS       = "community_rooms"
    DIRECT_MESSAGES       = "direct_messages"
    SHOPPER_DASHBOARD     = "shopper_dashboard"
    MARKETPLACE_LISTINGS  = "marketplace_listings"
    ADVANCED_ADMIN        = "advanced_admin"

    # ── Production AI features (default ON) ──────────────────────────────────
    MATERIAL_TRACKING     = "material_tracking"
    PRODUCTION_AI         = "production_ai"


# Env var name for each feature
_ENV_MAP: dict[Feature, str] = {
    Feature.AI_CONTENT:   "AI_CONTENT_ENABLED",
    Feature.AI_MATCHING:  "AI_MATCHING_ENABLED",
    Feature.AI_MARKETING: "AI_MARKETING_ENABLED",
    Feature.AI_INSIGHTS:  "AI_INSIGHTS_ENABLED",
    Feature.AI_ASSISTANT: "AI_ASSISTANT_ENABLED",

    Feature.VENDOR_PROFILES:       "FEATURE_VENDOR_PROFILES",
    Feature.MARKET_DISCOVERY:      "FEATURE_MARKET_DISCOVERY",
    Feature.MARKET_APPLICATIONS:   "FEATURE_MARKET_APPLICATIONS",
    Feature.VENDOR_DASHBOARD:      "FEATURE_VENDOR_DASHBOARD",
    Feature.MARKET_MAP:            "FEATURE_MARKET_MAP",
    Feature.INVENTORY_TRACKING:    "FEATURE_INVENTORY_TRACKING",
    Feature.VENDOR_CALENDAR:       "FEATURE_VENDOR_CALENDAR",
    Feature.PROFIT_PLANNER:        "FEATURE_PROFIT_PLANNER",
    Feature.SHOPIFY_SYNC:          "FEATURE_SHOPIFY_SYNC",
    Feature.EVENT_RECOMMENDATIONS: "FEATURE_EVENT_RECOMMENDATIONS",

    Feature.SOCIAL_FEED:          "FEATURE_SOCIAL_FEED",
    Feature.COMMUNITY_ROOMS:      "FEATURE_COMMUNITY_ROOMS",
    Feature.DIRECT_MESSAGES:      "FEATURE_DIRECT_MESSAGES",
    Feature.SHOPPER_DASHBOARD:    "FEATURE_SHOPPER_DASHBOARD",
    Feature.MARKETPLACE_LISTINGS: "FEATURE_MARKETPLACE_LISTINGS",
    Feature.ADVANCED_ADMIN:       "FEATURE_ADVANCED_ADMIN",

    Feature.MATERIAL_TRACKING:    "FEATURE_MATERIAL_TRACKING",
    Feature.PRODUCTION_AI:        "FEATURE_PRODUCTION_AI",
}

# Default state when env var is absent
_DEFAULTS: dict[Feature, bool] = {
    Feature.AI_CONTENT:   False,
    Feature.AI_MATCHING:  False,
    Feature.AI_MARKETING: False,
    Feature.AI_INSIGHTS:  False,
    Feature.AI_ASSISTANT: False,

    Feature.VENDOR_PROFILES:       True,
    Feature.MARKET_DISCOVERY:      True,
    Feature.MARKET_APPLICATIONS:   True,
    Feature.VENDOR_DASHBOARD:      True,
    Feature.MARKET_MAP:            True,
    Feature.INVENTORY_TRACKING:    True,
    Feature.VENDOR_CALENDAR:       True,
    Feature.PROFIT_PLANNER:        True,
    Feature.SHOPIFY_SYNC:          True,
    Feature.EVENT_RECOMMENDATIONS: True,

    Feature.SOCIAL_FEED:          False,
    Feature.COMMUNITY_ROOMS:      False,
    Feature.DIRECT_MESSAGES:      False,
    Feature.SHOPPER_DASHBOARD:    False,
    Feature.MARKETPLACE_LISTINGS: False,
    Feature.ADVANCED_ADMIN:       False,

    Feature.MATERIAL_TRACKING:    True,
    Feature.PRODUCTION_AI:        True,
}

_AI_MASTER_KEY = "AI_ALL_ENABLED"


def _parse_bool(val: str | None, default: bool = False) -> bool:
    if val is None:
        return default
    return str(val).lower() in ("1", "true", "yes", "on")


class FeatureFlags:
    """
    Layered feature flag resolver.
    Priority (highest first): admin override file → env var → hardcoded default.
    """

    def __init__(self) -> None:
        self._overrides: dict[str, bool] = {}
        self._load_overrides()

    # ── Override persistence ──────────────────────────────────────────────────

    def _load_overrides(self) -> None:
        try:
            if _OVERRIDES_PATH.exists():
                data = json.loads(_OVERRIDES_PATH.read_text())
                self._overrides = {k: bool(v) for k, v in data.items()}
        except Exception as exc:
            logger.warning("Could not load flag overrides: %s", exc)
            self._overrides = {}

    def _save_overrides(self) -> None:
        try:
            _OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
            _OVERRIDES_PATH.write_text(json.dumps(self._overrides, indent=2))
        except Exception as exc:
            logger.warning("Could not save flag overrides: %s", exc)

    def set_override(self, feature: Feature, enabled: bool) -> None:
        """Set a runtime override (persisted to overrides.json)."""
        self._overrides[feature.value] = enabled
        self._save_overrides()

    def clear_override(self, feature: Feature) -> None:
        """Remove admin override; flag falls back to env/default."""
        self._overrides.pop(feature.value, None)
        self._save_overrides()

    def clear_all_overrides(self) -> None:
        self._overrides.clear()
        self._save_overrides()

    # ── Core resolution ───────────────────────────────────────────────────────

    def is_enabled(self, feature: Feature) -> bool:
        # AI master switch still works for legacy AI flags
        if feature in (
            Feature.AI_CONTENT, Feature.AI_MATCHING,
            Feature.AI_MARKETING, Feature.AI_INSIGHTS, Feature.AI_ASSISTANT,
        ) and _parse_bool(os.environ.get(_AI_MASTER_KEY)):
            return True

        # Admin override takes highest priority
        if feature.value in self._overrides:
            return self._overrides[feature.value]

        # Env var
        env_key = _ENV_MAP.get(feature)
        env_val = os.environ.get(env_key) if env_key else None
        if env_val is not None:
            return _parse_bool(env_val)

        # Hardcoded default
        return _DEFAULTS.get(feature, False)

    def all_flags(self) -> dict[str, bool]:
        """Return state of every feature flag."""
        return {f.value: self.is_enabled(f) for f in Feature}

    def mvp_flags(self) -> dict[str, bool]:
        """Return only the product feature flags (excludes AI sub-flags)."""
        ai_flags = {Feature.AI_CONTENT, Feature.AI_MATCHING, Feature.AI_MARKETING,
                    Feature.AI_INSIGHTS, Feature.AI_ASSISTANT}
        return {f.value: self.is_enabled(f) for f in Feature if f not in ai_flags}

    def require(self, feature: Feature) -> None:
        """Raise FeatureDisabledError if feature is off — for use in endpoints."""
        if not self.is_enabled(feature):
            raise FeatureDisabledError(feature)


class FeatureDisabledError(RuntimeError):
    def __init__(self, feature: Feature) -> None:
        self.feature = feature
        env_key = _ENV_MAP.get(feature, "FEATURE_" + feature.value.upper())
        super().__init__(
            f"Feature '{feature.value}' is disabled. "
            f"Set {env_key}=true to enable."
        )


# Singleton — import this everywhere
flags = FeatureFlags()
