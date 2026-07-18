"""Canonical import path for the API client (Final spec §5.2) — single source in ui/."""
from ui.api_client import *  # noqa: F401,F403
from ui.api_client import ApiClient, ApiResult, DEFAULT_BASE_URL  # noqa: F401
