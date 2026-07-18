"""Standard offline test environment for ALL tracks.

Forces SQLite + demo_mode + mock LLM so unit tests run with zero external services.
Every track's tests inherit this — do not require docker to test.
"""
import os
import tempfile

os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("SQLITE_PATH", os.path.join(tempfile.gettempdir(), "vaic_pytest.db"))
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("LLM_PROVIDER", "mock")

from packages.common.config import get_settings  # noqa: E402

get_settings.cache_clear()
