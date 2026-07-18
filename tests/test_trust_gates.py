"""Final spec §11.2 — trust admission gates T1, T4, T11.

T1  uploaded source candidate is NOT visible to official retrieval pre-activation
T4  a review target run through Workflow B is NEVER indexed/persisted as a source
T11 DEMO_MODE=false with fallback backends -> /health/details degraded + BACKEND_DEGRADED
"""
from __future__ import annotations

import os
import sys
import tempfile
import uuid
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MARKER = "phụ cấp kim cương xanh"
BASE_DOC = f"""QUY ĐỊNH VỀ PHỤ CẤP ĐẶC BIỆT
Số: QĐ-99/2026
Ngày ban hành: 01/07/2026
Ngày hiệu lực: 01/07/2026

Điều 1. Mức phụ cấp
Mức {MARKER} là 123 triệu đồng.
"""


def _dispose_engine():
    import infra.postgres as pg
    if pg._engine is not None:
        try:
            pg._engine.dispose()
        except Exception:
            pass
    pg._engine = None
    pg._SessionLocal = None


@pytest.fixture()
def fresh_env(monkeypatch):
    db_path = os.path.join(tempfile.gettempdir(), f"vaic_trust_{uuid.uuid4().hex}.db")
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", db_path)
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    from packages.common.config import get_settings
    get_settings.cache_clear()
    _dispose_engine()

    from infra.neo4j_client import reset_graph_for_tests
    from infra.opensearch_client import reset_store_for_tests
    reset_store_for_tests()
    reset_graph_for_tests()

    yield

    get_settings.cache_clear()
    _dispose_engine()
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


def _official_hits(query: str):
    from packages.contracts.enums import QueryIntent
    from query import evidence_package
    pkg = evidence_package.build(query=query, query_date=date(2026, 7, 18),
                                 intent=QueryIntent.CURRENT_QA)
    return [e for e in pkg.valid_evidence if MARKER in (e.content or "").lower()]


def test_t1_candidate_invisible_before_activation(fresh_env):
    from ingestion import service

    up = service.handle_upload(BASE_DOC.encode("utf-8"), "qd99.txt", "REGULATION", "employee")
    assert up.approval_status == "PENDING"
    # not indexed -> official retrieval must not see it
    assert _official_hits(MARKER) == []


def test_t4_review_target_never_persisted_as_source(fresh_env):
    from infra.db_models import DocumentRow
    from infra.postgres import init_db, session_scope
    from backend.app.workflows.compliance_checks.service import run_compliance_check

    init_db()
    with session_scope() as ses:
        docs_before = ses.query(DocumentRow).count()

    report = run_compliance_check(f"Điều 1. Mức phụ cấp\nMức {MARKER} là 123 triệu đồng.",
                                  review_date=date(2026, 7, 18))
    assert report.assessments  # engine ran

    with session_scope() as ses:
        assert ses.query(DocumentRow).count() == docs_before  # no source row created
    assert _official_hits(MARKER) == []  # nothing indexed


def test_t11_demo_mode_false_reports_degraded(fresh_env, monkeypatch):
    from packages.common.config import Settings
    from backend.app.api import routes_health

    # test env has no OpenSearch/Neo4j -> singletons are in-memory fallbacks
    monkeypatch.setattr(routes_health, "get_settings",
                        lambda: Settings(demo_mode=False, llm_provider="mock"))
    detail = routes_health.health_details()
    assert detail["status"] == "degraded"
    assert detail["error_code"] == "BACKEND_DEGRADED"
    assert detail["opensearch"] == "fallback_memory"


def test_t11_demo_mode_true_is_honest_ok(fresh_env):
    from backend.app.api import routes_health
    detail = routes_health.health_details()
    assert detail["demo_mode"] is True
    assert detail["status"] == "ok"          # demo mode: fallback allowed, labeled
    assert detail["opensearch"] == "fallback_memory"  # but never hidden
