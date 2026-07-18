"""Central settings. Read from environment (.env). One import point for every track.

Nothing here connects to a service — importing config must never fail even when no
database is running (so unit tests and the CI import-check stay green).
"""
from __future__ import annotations

from functools import lru_cache

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover - fallback if pydantic-settings missing
    from pydantic import BaseModel as BaseSettings  # type: ignore
    SettingsConfigDict = dict  # type: ignore


class Settings(BaseSettings):
    # --- Postgres (metadata, auth, review, audit) ---
    postgres_dsn: str = "postgresql+psycopg://vaic:vaic@localhost:5432/vaic"
    # SQLite fallback for local dev / tests without docker (set DB_BACKEND=sqlite)
    db_backend: str = "postgres"        # "postgres" | "sqlite"
    sqlite_path: str = "./data/vaic.db"

    # --- OpenSearch (BM25 + vector) ---
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_scheme: str = "http"
    opensearch_index: str = "provisions"
    opensearch_user: str | None = None
    opensearch_password: str | None = None

    # --- Neo4j (temporal regulatory graph) ---
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "vaic_neo4j"

    # --- Embeddings ---
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024

    # --- LLM ---
    llm_provider: str = "google"        # "google" | "openai" | "anthropic" | "openrouter" | "mock"
    llm_model: str = "gemini-flash-latest"
    google_api_key: str | None = None   # Google AI Studio (Gemini) API key
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    openrouter_api_key: str | None = None  # OpenAI-compatible; model dạng "anthropic/claude-sonnet-4.5"
    llm_temperature: float = 0.0
    llm_throttle_s: float = 0.0  # pacing giữa các call LLM (tránh 429 RPM free-tier khi batch eval)

    # --- Auth ---
    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720

    # --- Runtime ---
    file_storage_dir: str = "./data/storage"
    max_upload_mb: int = 25
    retrieval_top_k: int = 8
    prompt_version: str = "v1"
    # When True, external services (OpenSearch/Neo4j/LLM) are replaced by in-memory
    # stubs seeded from data/seed.py. Lets the demo run on a laptop with no docker.
    demo_mode: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")  # type: ignore


@lru_cache
def get_settings() -> Settings:
    return Settings()
