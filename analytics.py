"""
PostHog analytics for Vendor Atlas.

Usage
-----
from analytics import track

track("user_signed_up", user_id=42, properties={"role": "vendor"})

All calls are fire-and-forget and never raise — a broken analytics
connection must not take down the app.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("vendor-atlas.analytics")

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    try:
        import posthog as ph

        key = os.environ.get("POSTHOG_KEY", "")
        host = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com")
        if not key:
            return None
        ph.project_api_key = key
        ph.host = host
        # Disable the default stdout debug logging
        ph.debug = False
        _client = ph
        return _client
    except Exception as exc:  # noqa: BLE001
        logger.debug("PostHog unavailable: %s", exc)
        return None


def track(
    event: str,
    *,
    user_id: int | str | None = None,
    properties: dict[str, Any] | None = None,
) -> None:
    """Capture a server-side PostHog event. Never raises."""
    try:
        ph = _get_client()
        if ph is None:
            return
        distinct_id = str(user_id) if user_id is not None else "anonymous"
        ph.capture(distinct_id, event, properties or {})
    except Exception as exc:  # noqa: BLE001
        logger.debug("analytics.track failed: %s", exc)


def identify(
    user_id: int | str,
    properties: dict[str, Any] | None = None,
) -> None:
    """Set user properties in PostHog. Never raises."""
    try:
        ph = _get_client()
        if ph is None:
            return
        ph.identify(str(user_id), properties or {})
    except Exception as exc:  # noqa: BLE001
        logger.debug("analytics.identify failed: %s", exc)


def shutdown() -> None:
    """Flush pending events on app shutdown."""
    try:
        ph = _get_client()
        if ph is not None:
            ph.shutdown()
    except Exception:  # noqa: BLE001
        pass
