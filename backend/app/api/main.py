"""FastAPI application entry point.

Wires the pipeline together. Route handlers are thin controllers that call the
per-track service facades:
    ingestion.service   (Track A)   - upload, review, activate
    query.service       (Track B)   - answer, compare, graph, audit
Handlers import their service lazily and return HTTP 503 if a facade is not yet
implemented, so the app always boots (foundation-first, tracks fill in).
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.ingestion.activation.gate import ReviewNotCompletedError
from infra.postgres import init_db
from packages.common.config import get_settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vaic")

app = FastAPI(title="VAIC2026 — Temporal Regulatory RAG (SHB1)", version="1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.exception_handler(ReviewNotCompletedError)
def _handle_review_not_completed(request: Request, exc: ReviewNotCompletedError):
    """P0 activation gate -> HTTP 409 with the stable error envelope (spec §8.1)."""
    return JSONResponse(
        status_code=409,
        content={"error": {
            "code": exc.code,
            "message": str(exc),
            "details": {"reasons": exc.reasons},
        }},
    )


@app.on_event("startup")
def _startup() -> None:
    init_db()
    from api.auth import seed_users
    seed_users()
    if get_settings().demo_mode or os.getenv("SEED_DEMO") == "1":
        try:
            from data.seed import seed_all
            seed_all()
            log.info("Demo corpus seeded.")
        except Exception as e:  # pragma: no cover
            log.warning("Demo seed skipped: %s", e)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "demo_mode": get_settings().demo_mode}


# Routers (guarded so a missing track module never blocks boot)
def _include(module_path: str, attr: str = "router") -> None:
    try:
        mod = __import__(module_path, fromlist=[attr])
        app.include_router(getattr(mod, attr))
        log.info("mounted %s", module_path)
    except Exception as e:  # pragma: no cover
        log.warning("router %s not mounted: %s", module_path, e)


_include("api.routes_auth")
_include("api.routes_ingest")
_include("api.routes_review")
_include("api.routes_query")
_include("api.routes_graph")
_include("backend.app.api.routes_chat")               # Mode-based chat (Mode spec §12.2)
_include("backend.app.api.routes_review_runs")        # Single Document Review (Mode spec)
_include("backend.app.api.routes_batch_reviews")      # Batch Document Review (Mode spec)
_include("backend.app.api.routes_compliance_checks")  # Workflow B (Final spec)
_include("backend.app.api.routes_impact_reports")     # Impact Report (Final spec §7.8)
_include("backend.app.api.routes_health")             # /health/details (Final spec §7.12)
