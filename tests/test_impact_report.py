"""Regulatory Impact Report engine (Final spec §7.8) over the seeded golden domain.

Seed ships: ChangeEvent QĐ-02/2026 REPLACE_TEXT 500→700 triệu (APPROVED) targeting
QĐ-01/2026 Điều 7, and one internal policy ALIGNED_TO the superseded V1 with an
obligation of 500 triệu -> expected THRESHOLD_MISMATCH / HIGH.
"""
from __future__ import annotations

import pytest

from infra.neo4j_client import reset_graph_for_tests
from infra.opensearch_client import reset_store_for_tests


@pytest.fixture()
def seeded():
    reset_store_for_tests()
    reset_graph_for_tests()
    from infra.postgres import get_engine, init_db
    from infra.db_models import Base
    init_db()
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    from data.seed import seed_all
    seed_all()
    yield


def test_impact_report_full_lineage(seeded):
    from backend.app.workflows.impact_analysis import impact_engine

    rep = impact_engine.run("doc-qd02-2026")

    assert rep.document_number  # amending source resolved
    assert len(rep.changes) == 1
    ch = rep.changes[0]
    assert ch.operation == "REPLACE_TEXT"
    assert "500" in (ch.before_text or "") and "700" in (ch.after_text or "")
    assert ch.before_version_id and ch.after_version_id  # evidence lineage
    assert ch.review_status == "APPROVED"

    assert len(rep.impacted_policies) == 1
    pol = rep.impacted_policies[0]
    assert pol.reason == "THRESHOLD_MISMATCH"
    assert pol.severity == "HIGH"
    assert pol.aligned_to_version_id == ch.before_version_id
    assert rep.max_severity == "HIGH"
    assert rep.status == "REVIEW_REQUIRED"
    assert "policy" in rep.executive_summary


def test_impact_report_unknown_document(seeded):
    from backend.app.workflows.impact_analysis import impact_engine
    with pytest.raises(ValueError):
        impact_engine.run("doc-khong-ton-tai")


def test_impact_report_base_doc_no_changes(seeded):
    """A base regulation that amends nothing -> empty, honest report."""
    from backend.app.workflows.impact_analysis import impact_engine
    rep = impact_engine.run("doc-qd01-2026")
    assert rep.changes == []
    assert rep.impacted_policies == []
    assert rep.status == "COMPLETED"
