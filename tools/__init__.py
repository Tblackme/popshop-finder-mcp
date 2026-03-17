"""
Tool Registry for Vendor Atlas.

Aggregates all tool definitions and handlers from sub-modules.
Import your tool modules here and extend ALL_TOOLS / ALL_HANDLERS.

To add a new tool module:
    1. Create tools/my_tools.py with TOOLS list and HANDLERS dict
    2. Import and extend below
"""

from collections.abc import Callable, Coroutine
from typing import Any

from tools.example import HANDLERS as EXAMPLE_HANDLERS
from tools.example import TOOLS as EXAMPLE_TOOLS
from tools.vendor_atlas_events import HANDLERS as VENDOR_EVENT_HANDLERS
from tools.vendor_atlas_events import TOOLS as VENDOR_EVENT_TOOLS
from tools.vendor_atlas_ingest import HANDLERS as VENDOR_INGEST_HANDLERS
from tools.vendor_atlas_ingest import TOOLS as VENDOR_INGEST_TOOLS
from tools.vendor_atlas_markets import HANDLERS as VENDOR_MARKET_HANDLERS
from tools.vendor_atlas_markets import TOOLS as VENDOR_MARKET_TOOLS
from tools.vendor_atlas_pipeline import HANDLERS as VENDOR_PIPELINE_HANDLERS
from tools.vendor_atlas_pipeline import TOOLS as VENDOR_PIPELINE_TOOLS
from tools.vendor_atlas_profile import HANDLERS as VENDOR_PROFILE_HANDLERS
from tools.vendor_atlas_profile import TOOLS as VENDOR_PROFILE_TOOLS
from tools.vendor_atlas_scoring import HANDLERS as VENDOR_SCORING_HANDLERS
from tools.vendor_atlas_scoring import TOOLS as VENDOR_SCORING_TOOLS

# ---------------------------------------------------------------------------
# Aggregate all tool definitions and handler functions
# ---------------------------------------------------------------------------

ALL_TOOLS: list[dict[str, Any]] = [
    *EXAMPLE_TOOLS,
    *VENDOR_EVENT_TOOLS,
    *VENDOR_PIPELINE_TOOLS,
    *VENDOR_MARKET_TOOLS,
    *VENDOR_PROFILE_TOOLS,
    *VENDOR_SCORING_TOOLS,
    *VENDOR_INGEST_TOOLS,
]

ALL_HANDLERS: dict[str, Callable[..., Coroutine]] = {
    **EXAMPLE_HANDLERS,
    **VENDOR_EVENT_HANDLERS,
    **VENDOR_PIPELINE_HANDLERS,
    **VENDOR_MARKET_HANDLERS,
    **VENDOR_PROFILE_HANDLERS,
    **VENDOR_SCORING_HANDLERS,
    **VENDOR_INGEST_HANDLERS,
}
