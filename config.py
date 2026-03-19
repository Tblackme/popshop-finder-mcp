"""
Configuration for Vendor Atlas.

Loads all settings from environment variables with sensible defaults.
Uses a singleton pattern so config is only parsed once.

Environment Variables:
    SERVER_PORT         - HTTP port for SSE transport (default: 3000)
    SERVER_HOST         - Bind address (default: 0.0.0.0)
    SERVER_AUTH_TOKEN   - Bearer token for authentication (optional)
    SERVER_TRANSPORT    - Transport mode: sse, stdio, both (default: sse)
    SESSION_SECRET      - Secret used for signed session cookies
"""

import os
from dataclasses import dataclass


@dataclass
class ServerConfig:
    port: int = 3000
    host: str = "0.0.0.0"
    auth_token: str = ""
    transport: str = "sse"  # sse | stdio | both
    session_secret: str = "vendor-atlas-dev-session-secret"

    # --- Data Collection + Enrichment ---
    signal_capture_enabled: bool = True
    signal_log_path: str = "/data/signals/signals.json"
    serper_api_key: str = ""
    serper_tools: str = "all"   # comma-separated tool names, or "all"
    sync_endpoint: str = ""     # URL to POST signals to / GET context from
    session_tracking_enabled: bool = True

    # --- Shopify ---
    shopify_api_key: str = ""
    shopify_api_secret: str = ""
    shopify_scopes: str = "read_products,read_inventory"
    app_base_url: str = "http://localhost:3000"  # For OAuth redirect_uri

    # --- AI feature flags ---
    # Master switch — turns all AI features on/off
    ai_enabled: bool = False
    # Sub-flags — each can be toggled independently (only active when ai_enabled=True)
    ai_content_enabled: bool = False   # bio writer, product descriptions, captions
    ai_match_enabled: bool = False     # event fit scoring + "why this event"
    ai_discovery_enabled: bool = False # Serper-backed "find more events"
    # API key for Anthropic (Content AI + explanation features)
    anthropic_api_key: str = ""

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Create a ServerConfig from environment variables."""
        def _bool(key: str, default: bool = False) -> bool:
            val = os.environ.get(key, "")
            if not val:
                return default
            return val.lower() not in ("false", "0", "no", "off")

        return cls(
            port=int(os.environ.get("SERVER_PORT", "3000")),
            host=os.environ.get("SERVER_HOST", "0.0.0.0"),
            auth_token=os.environ.get("SERVER_AUTH_TOKEN", ""),
            transport=os.environ.get("SERVER_TRANSPORT", "sse"),
            session_secret=os.environ.get("SESSION_SECRET", "vendor-atlas-dev-session-secret"),
            signal_capture_enabled=_bool("SIGNAL_CAPTURE_ENABLED", True),
            signal_log_path=os.environ.get("SIGNAL_LOG_PATH", "/data/signals/signals.json"),
            serper_api_key=os.environ.get("SERPER_API_KEY", ""),
            serper_tools=os.environ.get("SERPER_TOOLS", "all"),
            sync_endpoint=os.environ.get("SYNC_ENDPOINT", ""),
            session_tracking_enabled=_bool("SESSION_TRACKING_ENABLED", True),
            shopify_api_key=os.environ.get("SHOPIFY_API_KEY", ""),
            shopify_api_secret=os.environ.get("SHOPIFY_API_SECRET", ""),
            shopify_scopes=os.environ.get("SHOPIFY_SCOPES", "read_products,read_inventory"),
            app_base_url=os.environ.get("APP_BASE_URL", "http://localhost:3000").rstrip("/"),
            ai_enabled=_bool("AI_ENABLED"),
            ai_content_enabled=_bool("AI_CONTENT_ENABLED"),
            ai_match_enabled=_bool("AI_MATCH_ENABLED"),
            ai_discovery_enabled=_bool("AI_DISCOVERY_ENABLED"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        )


_config: ServerConfig | None = None


def get_config() -> ServerConfig:
    """Get the global ServerConfig singleton (lazy-loaded from env)."""
    global _config
    if _config is None:
        try:
            from dotenv import load_dotenv
            # Load .env file — works for local dev and Render Secret Files
            load_dotenv(override=True)
        except ImportError:
            pass
        _config = ServerConfig.from_env()
    return _config
