"""Track B — query pipeline tests (fully offline, self-seeded).

conftest forces sqlite + demo_mode + mock LLM. Each test seeds its OWN minimal
fixture directly into the in-memory store + graph + sqlite (no dependency on Track A
or Track C). The canonical scenario:

    SME limit  V1 = 500tr, valid [2026-02-01, 2026-07-01)
               V2 = 700tr, valid [2026-07-01, ∞)
    an internal policy still at 500tr (aligned to V1 -> stale after V2)
    a co-valid conflicting clause at 600tr (same scope, different provision)

Covered: point-in-time (V1), current (V2), RRF fusion, standard_rag conflation vs
our_system single version, abstention, and output_checks rejecting a fabricated cite.
"""
from __future__ import annotations

import os
import sys
from datetime import date

# allow `python tests/test_query_pipeline.py` (pytest adds rootdir automatically)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infra.embeddings import embed_one
from infra.opensearch_client import get_store, reset_store_for_tests
from infra.neo4j_client import get_graph, reset_graph_for_tests
from infra.postgres import get_engine, init_db, session_scope
from infra.db_models import (
    Base,
    InternalArtifactRow,
    ProvisionRow,
    ProvisionVersionRow,
)
from llm.client import reset_client_for_tests

from packages.contracts.enums import AnswerStatus, ConflictReason, ExclusionReason
from query import (
    evidence_package,
    generation,
    output_checks,
    service,
    standard_rag,
)
from query.hybrid_retrieval import reciprocal_rank_fusion
from query.understanding import understand

# ---- provision / version identifiers used across the scenario ----
PROV_SME = "prov-sme7"
V1 = "ver-sme-v1"     # 500tr, [2026-02-01, 2026-07-01)
V2 = "ver-sme-v2"     # 700tr, [2026-07-01, inf)
PROV_CONFLICT = "prov-other9"
V_CONFLICT = "ver-other-600"   # 600tr, co-valid with V2, same scope

DOCNO = "QĐ-01/2026"


def _chunk(chunk_id, provision_id, version_id, content, valid_from, valid_to, docno=DOCNO):
    return {
        "chunk_id": chunk_id,
        "provision_id": provision_id,
        "version_id": version_id,
        "document_id": "doc-1",
        "document_number": docno,
        "heading_path": ["Điều 7", "Khoản 2"],
        "content": content,
        "page": 3,
        "valid_from": valid_from,
        "valid_to_exclusive": valid_to,
        "approval_status": "APPROVED",
    }


def _index(store, chunk):
    store.index_chunk(chunk, embed_one(chunk["content"] + " " + " ".join(chunk["heading_path"])))


def _reset_db():
    """Fresh sqlite schema for each seed (drop + create so tests don't leak rows)."""
    init_db()
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def _seed_provision_rows():
    with session_scope() as ses:
        ses.add(ProvisionRow(
            provision_id=PROV_SME, document_id="doc-1",
            lookup_key="QĐ-01/2026|D7|K2|P", heading_path=["Điều 7", "Khoản 2"],
            article="7", clause="2",
        ))
        ses.add(ProvisionRow(
            provision_id=PROV_CONFLICT, document_id="doc-2",
            lookup_key="QĐ-03/2026|D9|K1|P", heading_path=["Điều 9", "Khoản 1"],
            article="9", clause="1",
        ))
        ses.add(ProvisionVersionRow(
            version_id=V1, provision_id=PROV_SME, document_id="doc-1",
            content="Hạn mức tín dụng SME là 500 triệu đồng, thời hạn tối đa 12 tháng.",
            valid_from=date(2026, 2, 1), valid_to_exclusive=date(2026, 7, 1),
            approval_status="APPROVED", page=3,
            obligation={"value": "500 triệu đồng", "value_normalized": 500_000_000,
                        "modality": "OBLIGATION"},
            scope={"product": "SME", "customer_type": "SME"},
        ))
        ses.add(ProvisionVersionRow(
            version_id=V2, provision_id=PROV_SME, document_id="doc-1",
            content="Hạn mức tín dụng SME là 700 triệu đồng, thời hạn tối đa 12 tháng.",
            valid_from=date(2026, 7, 1), valid_to_exclusive=None,
            approval_status="APPROVED", page=3,
            obligation={"value": "700 triệu đồng", "value_normalized": 700_000_000,
                        "modality": "OBLIGATION"},
            scope={"product": "SME", "customer_type": "SME"},
        ))


def _seed_conflict_row():
    with session_scope() as ses:
        ses.add(ProvisionVersionRow(
            version_id=V_CONFLICT, provision_id=PROV_CONFLICT, document_id="doc-2",
            content="Hạn mức tín dụng với cùng nhóm khách hàng SME là 600 triệu đồng.",
            valid_from=date(2026, 7, 1), valid_to_exclusive=None,
            approval_status="APPROVED", page=1,
            obligation={"value": "600 triệu đồng", "value_normalized": 600_000_000,
                        "modality": "OBLIGATION"},
            scope={"product": "SME", "customer_type": "SME"},
        ))


def _seed_internal_artifact():
    with session_scope() as ses:
        ses.add(InternalArtifactRow(
            artifact_id="art-1", document_id="doc-policy",
            title="Quy trình cấp tín dụng SME nội bộ",
            aligned_to_version_id=V1,   # aligned to old 500tr version -> stale after V2
            obligation={"value": "500 triệu đồng", "value_normalized": 500_000_000},
            page=2,
        ))


def _graph_wire():
    g = get_graph()
    g.upsert_node(PROV_SME, "Provision", title="Điều 7 Khoản 2")
    g.upsert_node(V1, "ProvisionVersion", valid_from="2026-02-01",
                  valid_to_exclusive="2026-07-01", approval_status="APPROVED")
    g.upsert_node(V2, "ProvisionVersion", valid_from="2026-07-01",
                  approval_status="APPROVED")
    g.upsert_edge(PROV_SME, V1, "HAS_VERSION")
    g.upsert_edge(PROV_SME, V2, "HAS_VERSION")


def seed_scenario(with_conflict=False, with_artifact=False):
    """Self-seed store + graph + sqlite for the canonical SME scenario."""
    store = reset_store_for_tests()
    reset_graph_for_tests()
    reset_client_for_tests()
    service._db_ready = False
    _reset_db()

    _index(store, _chunk("c-v1", PROV_SME, V1,
                         "Hạn mức tín dụng SME là 500 triệu đồng, thời hạn tối đa 12 tháng.",
                         "2026-02-01", "2026-07-01"))
    _index(store, _chunk("c-v2", PROV_SME, V2,
                         "Hạn mức tín dụng SME là 700 triệu đồng, thời hạn tối đa 12 tháng.",
                         "2026-07-01", None))
    _seed_provision_rows()
    _graph_wire()

    if with_conflict:
        _index(store, _chunk("c-conf", PROV_CONFLICT, V_CONFLICT,
                             "Hạn mức tín dụng với cùng nhóm khách hàng SME là 600 triệu đồng.",
                             "2026-07-01", None, docno="QĐ-03/2026"))
        _seed_conflict_row()
    if with_artifact:
        _seed_internal_artifact()
    return store


# --------------------------------------------------------------------------- #
# (a) point-in-time query -> V1 (500tr); V2 excluded NOT_VALID_AT_QUERY_DATE
# --------------------------------------------------------------------------- #
def test_point_in_time_returns_v1_and_excludes_v2():
    seed_scenario()
    resp = service.answer_query("Hạn mức SME là bao nhiêu?", date(2026, 3, 1), "user", "USER")
    pkg = resp.evidence

    valid_ids = {e.version_id for e in pkg.valid_evidence}
    assert V1 in valid_ids, "V1 (500tr) must be valid on 2026-03-01"
    assert V2 not in valid_ids, "V2 (700tr) must NOT be valid on 2026-03-01"

    excl = {e.version_id: e.reason for e in pkg.excluded_evidence}
    assert excl.get(V2) == ExclusionReason.NOT_VALID_AT_QUERY_DATE

    assert "500" in resp.answer.text
    assert resp.answer.status in (
        AnswerStatus.DETERMINISTIC_CHECKS_PASSED,
        AnswerStatus.SOURCE_GROUNDED,
    )


# --------------------------------------------------------------------------- #
# (b) current query -> V2 (700tr)
# --------------------------------------------------------------------------- #
def test_current_query_returns_v2():
    seed_scenario()
    resp = service.answer_query("Hạn mức SME hiện tại là bao nhiêu?", date(2026, 8, 1), "user", "USER")
    pkg = resp.evidence

    valid_ids = {e.version_id for e in pkg.valid_evidence}
    assert V2 in valid_ids and V1 not in valid_ids
    assert "700" in resp.answer.text


def test_current_query_default_date_uses_today():
    # no query_date + "hiện hành" phrasing -> CURRENT_QA, today (2026 is > V2 start)
    u = understand("Hạn mức SME hiện hành là bao nhiêu?", None, today=date(2026, 8, 1))
    assert u.query_date == date(2026, 8, 1)


# --------------------------------------------------------------------------- #
# (c) RRF fuses bm25 + knn
# --------------------------------------------------------------------------- #
def test_rrf_fuses_two_lists():
    la = [{"chunk_id": "a"}, {"chunk_id": "b"}, {"chunk_id": "c"}]
    lb = [{"chunk_id": "b"}, {"chunk_id": "a"}, {"chunk_id": "d"}]
    fused = reciprocal_rank_fusion([la, lb], top_k=4)
    ids = [d["chunk_id"] for d in fused]
    # 'a' and 'b' appear in both lists near the top -> ranked above 'c'/'d'
    assert set(ids[:2]) == {"a", "b"}
    assert "c" in ids and "d" in ids
    # fusion score is monotonically non-increasing
    scores = [d["_rrf_score"] for d in fused]
    assert scores == sorted(scores, reverse=True)


# --------------------------------------------------------------------------- #
# (d) standard_rag sees BOTH versions (conflation); our_system returns ONE
# --------------------------------------------------------------------------- #
def test_standard_rag_conflates_versions_our_system_does_not():
    seed_scenario()
    q = "Hạn mức SME là bao nhiêu?"

    baseline_items = standard_rag.retrieved_items(q)
    baseline_versions = {i.version_id for i in baseline_items}
    assert V1 in baseline_versions and V2 in baseline_versions, \
        "Standard RAG (no valid_at) must retrieve BOTH co-existing versions"

    # head-to-head: standard_rag conflates, our_system pins to one version
    cmp = service.compare(q, date(2026, 8, 1), "user", "USER")
    assert cmp.standard_rag.status != AnswerStatus.INSUFFICIENT_EVIDENCE

    resp = service.answer_query(q, date(2026, 8, 1), "user", "USER")
    ours_versions = {e.version_id for e in resp.evidence.valid_evidence if e.provision_id == PROV_SME}
    assert ours_versions == {V2}, f"our_system must pick exactly V2, got {ours_versions}"


# --------------------------------------------------------------------------- #
# (e) abstention on out-of-corpus query -> INSUFFICIENT_EVIDENCE
# --------------------------------------------------------------------------- #
def test_abstain_out_of_corpus():
    seed_scenario()
    resp = service.answer_query("Quy định về vận tải hàng không vũ trụ?", date(2026, 8, 1), "user", "USER")
    assert not resp.evidence.valid_evidence
    assert resp.answer.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert resp.answer.text == "INSUFFICIENT_EVIDENCE"


# --------------------------------------------------------------------------- #
# (f) output_checks rejects a fabricated citation
# --------------------------------------------------------------------------- #
def test_output_checks_reject_fabricated_citation():
    seed_scenario()
    pkg = evidence_package.build(
        "Hạn mức SME hiện tại?", date(2026, 8, 1),
        understand("Hạn mức SME hiện tại?", date(2026, 8, 1)).intent,
        base_filters={"approved_only": True},
    )
    assert pkg.valid_evidence, "need at least one valid evidence to test citation checks"

    ans = generation.generate(pkg)
    # tamper: replace the real cited id with a non-existent one
    ans.text = ans.text.replace(f"[{V2}]", "[ver-FAKE-999]")
    checked = output_checks.run(ans, pkg)

    assert checked.status == AnswerStatus.NEEDS_REVIEW
    assert any(f.startswith("FABRICATED_CITATION") for f in checked.check_failures)


# --------------------------------------------------------------------------- #
# bonus: conflict + impact candidates surface in the current-day package
# --------------------------------------------------------------------------- #
def test_conflict_and_impact_candidates():
    seed_scenario(with_conflict=True, with_artifact=True)
    resp = service.answer_query("Hạn mức SME hiện tại là bao nhiêu?", date(2026, 8, 1), "user", "USER")
    pkg = resp.evidence

    # co-valid 700 vs 600, same scope, different provision -> a threshold-mismatch candidate
    reasons = {c.reason for c in pkg.conflict_candidates}
    assert ConflictReason.THRESHOLD_MISMATCH in reasons

    # internal policy aligned to superseded V1 (500tr) vs current 700tr -> impact candidate
    assert any(i.reason == ConflictReason.THRESHOLD_MISMATCH for i in pkg.impact_candidates)


def test_role_filter_blocks_user_admin_op():
    seed_scenario()
    resp = service.answer_query("upload tài liệu mới", date(2026, 8, 1), "user", "USER")
    assert resp.answer.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert "ADMIN_OP_REQUIRES_EMPLOYEE" in resp.answer.check_failures


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("all query pipeline checks passed")
