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

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Create a ServerConfig from environment variables."""
        return cls(
            port=int(os.environ.get("SERVER_PORT", "3000")),
            host=os.environ.get("SERVER_HOST", "0.0.0.0"),
            auth_token=os.environ.get("SERVER_AUTH_TOKEN", ""),
            transport=os.environ.get("SERVER_TRANSPORT", "sse"),
            session_secret=os.environ.get("SESSION_SECRET", "vendor-atlas-dev-session-secret"),
            signal_capture_enabled=os.environ.get("SIGNAL_CAPTURE_ENABLED", "true").lower() not in ("false", "0", "no"),
            signal_log_path=os.environ.get("SIGNAL_LOG_PATH", "/data/signals/signals.json"),
            serper_api_key=os.environ.get("SERPER_API_KEY", ""),
            serper_tools=os.environ.get("SERPER_TOOLS", "all"),
            sync_endpoint=os.environ.get("SYNC_ENDPOINT", ""),
            session_tracking_enabled=os.environ.get("SESSION_TRACKING_ENABLED", "true").lower() not in ("false", "0", "no"),
        )


_config: ServerConfig | None = None


def get_config() -> ServerConfig:
    """Get the global ServerConfig singleton (lazy-loaded from env)."""
    global _config
    if _config is None:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        _config = ServerConfig.from_env()
    return _config
