"""
Feature flag system for Vendor Atlas.

All AI features are gated behind flags so the app runs fully without them.
Flags are read from environment variables at startup — no restart required
if you use a secrets manager that injects env vars per-request (e.g. Doppler).

Usage:
    from features.flags import flags, Feature

    if flags.is_enabled(Feature.AI_CONTENT):
        # call AI service
        ...
    else:
        # return core result
        ...

Environment variables (all default to disabled):
    AI_CONTENT_ENABLED=true        — vendor bio / product description generation
    AI_MATCHING_ENABLED=true       — smart vendor-event matching
    AI_MARKETING_ENABLED=true      — marketing copy / social post generation
    AI_ALL_ENABLED=true            — master switch (overrides all above)
"""

from __future__ import annotations

import os
from enum import Enum


class Feature(str, Enum):
    AI_CONTENT = "ai_content"
    AI_MATCHING = "ai_matching"
    AI_MARKETING = "ai_marketing"


_ENV_MAP: dict[Feature, str] = {
    Feature.AI_CONTENT: "AI_CONTENT_ENABLED",
    Feature.AI_MATCHING: "AI_MATCHING_ENABLED",
    Feature.AI_MARKETING: "AI_MARKETING_ENABLED",
}

_MASTER_KEY = "AI_ALL_ENABLED"


def _bool(val: str | None) -> bool:
    return str(val).lower() in ("1", "true", "yes", "on")


class FeatureFlags:
    """Read-only view of current feature flags from environment."""

    def is_enabled(self, feature: Feature) -> bool:
        if _bool(os.environ.get(_MASTER_KEY)):
            return True
        env_key = _ENV_MAP.get(feature)
        if not env_key:
            return False
        return _bool(os.environ.get(env_key))

    def all_flags(self) -> dict[str, bool]:
        master = _bool(os.environ.get(_MASTER_KEY))
        return {
            f.value: master or _bool(os.environ.get(_ENV_MAP[f]))
            for f in Feature
        }

    def require(self, feature: Feature) -> None:
        """Raise RuntimeError if feature is disabled — use in AI endpoints."""
        if not self.is_enabled(feature):
            raise FeatureDisabledError(feature)


class FeatureDisabledError(RuntimeError):
    def __init__(self, feature: Feature) -> None:
        self.feature = feature
        super().__init__(
            f"Feature '{feature.value}' is disabled. "
            f"Set {_ENV_MAP.get(feature, 'AI_ALL_ENABLED')}=true to enable."
        )


# Singleton — import this everywhere
flags = FeatureFlags()
