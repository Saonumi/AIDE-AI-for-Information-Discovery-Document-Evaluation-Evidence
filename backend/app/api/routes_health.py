"""API — /health/details (Final spec §7.12).

Reports which backend is REALLY serving each dependency by introspecting the
live singletons (class name), never by echoing config. DEMO_MODE=false with any
fallback -> status "degraded" + stable code BACKEND_DEGRADED (spec §9.1):
honest degradation instead of pretending production.
"""
from __future__ import annotations

from fastapi import APIRouter

from packages.common.config import get_settings

router = APIRouter(tags=["health"])

_REAL = {
    "postgres": "connected",
    "OpenSearchStore": "connected",
    "Neo4jGraph": "connected",
    "_BGEEmbedder": "bge-m3",
}
_FALLBACK = {
    "InMemoryStore": "fallback_memory",
    "InMemoryGraph": "fallback_memory",
    "_HashEmbedder": "hash_fallback",
}


def _postgres_state() -> str:
    try:
        from sqlalchemy import text

        from infra.postgres import session_scope
        with session_scope() as ses:
            ses.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        return "unavailable"


def _state_of(instance) -> str:
    name = type(instance).__name__
    return _REAL.get(name) or _FALLBACK.get(name, name)


@router.get("/health/details")
def health_details() -> dict:
    from infra.embeddings import get_embedder
    from infra.neo4j_client import get_graph
    from infra.opensearch_client import get_store

    s = get_settings()
    detail = {
        "demo_mode": s.demo_mode,
        "postgres": _postgres_state(),
        "opensearch": _state_of(get_store()),
        "neo4j": _state_of(get_graph()),
        "embedding": _state_of(get_embedder()),
        "llm": "mock" if s.demo_mode or s.llm_provider == "mock" else s.llm_provider,
    }
    degraded = detail["postgres"] != "connected" or any(
        v in ("fallback_memory", "hash_fallback", "mock")
        for k, v in detail.items() if k not in ("demo_mode", "postgres")
    )
    detail["status"] = "degraded" if (degraded and not s.demo_mode) else "ok"
    if detail["status"] == "degraded":
        detail["error_code"] = "BACKEND_DEGRADED"
    return detail
