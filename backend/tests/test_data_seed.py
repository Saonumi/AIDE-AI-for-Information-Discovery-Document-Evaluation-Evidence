"""Tests for the deterministic demo seed (Track C).

conftest.py forces SQLite + demo_mode, so get_store()/get_graph() return the
in-memory backends and seed_all() runs with zero external services.
"""
from __future__ import annotations

from datetime import date

import pytest

from infra.opensearch_client import get_store, reset_store_for_tests
from infra.neo4j_client import get_graph, reset_graph_for_tests
from infra.postgres import session_scope
from infra.db_models import (
    ChangeEventRow,
    DocumentRow,
    InternalArtifactRow,
    ProvisionRow,
    ProvisionVersionRow,
)


@pytest.fixture(autouse=True)
def _fresh_stores():
    """Reset the in-memory OpenSearch/Neo4j stores before each test for isolation."""
    reset_store_for_tests()
    reset_graph_for_tests()
    yield


def _seed():
    from data.seed import seed_all
    seed_all()


# --------------------------------------------------------------------------- #
# idempotency
# --------------------------------------------------------------------------- #
_SEED_DOC_IDS = ["doc-qd01-2026", "doc-qd02-2026", "doc-qd03-2026", "doc-internal-sme"]
_SEED_PROV_IDS = ["prov-qd01-d7k2", "prov-qd01-d7k3", "prov-qd01-d12k3", "prov-qd03-d5"]
_SEED_VER_IDS = ["ver-d7k2-v1", "ver-d7k2-v2", "ver-d7k3-v1", "ver-d12k3-v1", "ver-qd03-d5-v1"]


def _count_seeded(ses):
    """Count only OUR seeded rows by their stable ids (the shared pytest sqlite
    file may hold unrelated rows from other tracks/runs)."""
    return {
        "docs": ses.query(DocumentRow).filter(DocumentRow.document_id.in_(_SEED_DOC_IDS)).count(),
        "provs": ses.query(ProvisionRow).filter(ProvisionRow.provision_id.in_(_SEED_PROV_IDS)).count(),
        "vers": ses.query(ProvisionVersionRow).filter(
            ProvisionVersionRow.version_id.in_(_SEED_VER_IDS)).count(),
        "chg": ses.query(ChangeEventRow).filter(
            ChangeEventRow.change_event_id == "chg-500-to-700").count(),
        "art": ses.query(InternalArtifactRow).filter(
            InternalArtifactRow.artifact_id == "art-internal-sme").count(),
    }


def test_seed_all_runs_and_is_idempotent():
    _seed()
    with session_scope() as ses:
        first = _count_seeded(ses)
    # each entity present exactly once after the first seed
    assert first == {"docs": 4, "provs": 4, "vers": 5, "chg": 1, "art": 1}

    # second call must not raise and must not duplicate any of our stable-id rows
    reset_store_for_tests()
    reset_graph_for_tests()
    _seed()
    with session_scope() as ses:
        second = _count_seeded(ses)
    assert second == first  # idempotent: re-seeding changes nothing


# --------------------------------------------------------------------------- #
# temporal pre-filter: V1 in the past, V2 today
# --------------------------------------------------------------------------- #
def test_store_returns_v1_at_past_date():
    _seed()
    hits = get_store().bm25_search(
        "hạn mức SME", {"approved_only": True, "valid_at": date(2026, 3, 1)}, 5)
    versions = {h["version_id"] for h in hits}
    assert "ver-d7k2-v1" in versions
    assert "ver-d7k2-v2" not in versions  # V2 not yet valid on 2026-03-01
    v1 = next(h for h in hits if h["version_id"] == "ver-d7k2-v1")
    assert "500 triệu" in v1["content"]
    assert v1["page"] == 3


def test_store_returns_v2_today():
    _seed()
    hits = get_store().bm25_search(
        "hạn mức SME", {"approved_only": True, "valid_at": date(2026, 8, 15)}, 5)
    versions = {h["version_id"] for h in hits}
    assert "ver-d7k2-v2" in versions
    assert "ver-d7k2-v1" not in versions  # V1 expired 2026-07-01
    v2 = next(h for h in hits if h["version_id"] == "ver-d7k2-v2")
    assert "700 triệu" in v2["content"]


def test_store_returns_nothing_before_any_version():
    _seed()
    hits = get_store().bm25_search(
        "hạn mức SME", {"approved_only": True, "valid_at": date(2026, 1, 1)}, 5)
    versions = {h["version_id"] for h in hits}
    # neither the SME-limit versions are valid before 2026-02-01
    assert "ver-d7k2-v1" not in versions
    assert "ver-d7k2-v2" not in versions


# --------------------------------------------------------------------------- #
# postgres: obligation carries normalized VND and page/scope
# --------------------------------------------------------------------------- #
def test_version_obligation_normalized_and_page():
    _seed()
    with session_scope() as ses:
        v1 = ses.get(ProvisionVersionRow, "ver-d7k2-v1")
        v2 = ses.get(ProvisionVersionRow, "ver-d7k2-v2")
        assert v1.obligation["value_normalized"] == 500_000_000
        assert v2.obligation["value_normalized"] == 700_000_000
        assert v1.valid_to_exclusive == date(2026, 7, 1)
        assert v2.valid_to_exclusive is None
        assert v1.page == 3 and v2.page == 3
        assert v1.scope["customer_type"] == "SME"


def test_provision_lookup_key_present():
    _seed()
    with session_scope() as ses:
        p = ses.get(ProvisionRow, "prov-qd01-d7k2")
        assert p.lookup_key  # non-empty, deterministic key
        assert "QĐ-01/2026".upper() in p.lookup_key
        assert p.heading_path == ["Điều 7", "Khoản 2"]


def test_change_event_wires_before_after():
    _seed()
    with session_scope() as ses:
        ce = ses.get(ChangeEventRow, "chg-500-to-700")
        assert ce.before_version_id == "ver-d7k2-v1"
        assert ce.after_version_id == "ver-d7k2-v2"
        assert ce.operation == "REPLACE_TEXT"
        assert ce.valid_from == date(2026, 7, 1)


# --------------------------------------------------------------------------- #
# neo4j graph: cross-reference, version chain, conflict, alignment
# --------------------------------------------------------------------------- #
def test_graph_cross_reference_expand():
    _seed()
    result = get_graph().expand(["prov-qd01-d7k3"], max_hops=2)
    # Điều 7 Khoản 3 REFERENCES Điều 12 Khoản 3
    assert "prov-qd01-d12k3" in result["provision_ids"]
    locs = {r["to_locator"] for r in result["reference_paths"]}
    assert any("12" in loc for loc in locs)


def test_graph_version_chain():
    _seed()
    chain = get_graph().version_chain("prov-qd01-d7k2")
    ids = [c["version_id"] for c in chain]
    assert ids == ["ver-d7k2-v1", "ver-d7k2-v2"]  # ordered by valid_from


def test_graph_change_paths():
    _seed()
    result = get_graph().expand(["prov-qd01-d7k2"], max_hops=1)
    cps = result["change_paths"]
    assert any(c["before_version_id"] == "ver-d7k2-v1" and
               c["after_version_id"] == "ver-d7k2-v2" for c in cps)


def test_graph_subgraph_has_conflict_and_alignment_edges():
    _seed()
    sg = get_graph().subgraph("prov-qd01-d7k2", depth=2)
    labels = {e["label"] for e in sg["edges"]}
    assert "HAS_VERSION" in labels
    assert "SUPERSEDES" in labels
    # V2 is reachable; conflict/alignment edges touch V2 / V1
    assert "POTENTIALLY_CONFLICTS_WITH" in labels
    assert "ALIGNED_TO" in labels
