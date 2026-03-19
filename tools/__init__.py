from tools.example import TOOLS as _BASE_TOOLS, HANDLERS as _BASE_HANDLERS
from tools.vendoratlas import TOOLS as _VA_TOOLS, HANDLERS as _VA_HANDLERS
from tools.vendor_atlas_pipeline import HANDLERS as _PIPELINE_HANDLERS

# Pipeline handlers override the seed-data vendoratlas handlers for core tools:
# discover_events, extract_event, enrich_event, score_event, save_event, search_events
ALL_TOOLS = _BASE_TOOLS + _VA_TOOLS
ALL_HANDLERS = {**_BASE_HANDLERS, **_VA_HANDLERS, **_PIPELINE_HANDLERS}
