"""Policy mapping (§7.8) + outbox-lite T10 (§8.1).

- citation-based ALIGNED_TO: an activated internal policy citing "Điều 1
  88/2026/QĐ-NHNN" links to that provision's open version; after an amendment
  closes it, the impact report lists the policy (THRESHOLD_MISMATCH).
- T10: index sync failure never rolls back the Postgres approval — the result
  and document metadata carry INDEX_SYNC_PENDING.
"""
from __future__ import annotations

import os
import sys
import tempfile
import uuid
from datetime import date, datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
    db_path = os.path.join(tempfile.gettempdir(), f"vaic_map_{uuid.uuid4().hex}.db")
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


def _mk_regulation(ses):
    from infra.db_models import DocumentRow, ProvisionRow, ProvisionVersionRow
    now = datetime(2026, 1, 1)
    ses.add(DocumentRow(document_id="doc-r88", filename="qd88.txt", type="REGULATION",
                        document_number="88/2026/QĐ-NHNN", file_hash="h1", file_path="p1",
                        processing_status="INDEXED", approval_status="APPROVED",
                        injection_suspected=False, uploaded_by="e", created_at=now))
    ses.add(ProvisionRow(provision_id="prov-r88-d1", document_id="doc-r88",
                         lookup_key="88/2026/QĐ-NHNN|1|", heading_path=["Điều 1"],
                         article="1", clause=None, point=None))
    ses.add(ProvisionVersionRow(version_id="ver-r88-v1", provision_id="prov-r88-d1",
                                document_id="doc-r88", content="Hạn mức là 500 triệu đồng.",
                                valid_from=date(2026, 1, 1), valid_to_exclusive=None,
                                approval_status="APPROVED", page=1, obligation=None,
                                scope=None, created_at=now, approved_at=now))


def test_policy_mapping_then_impact(fresh_env):
    from infra.db_models import ChangeEventRow, DocumentRow, ProvisionVersionRow
    from infra.postgres import init_db, session_scope
    from backend.app.workflows.impact_analysis import impact_engine
    from backend.app.workflows.impact_analysis.policy_mapper import map_policy_document

    init_db()
    now = datetime(2026, 1, 2)
    with session_scope() as ses:
        _mk_regulation(ses)
        ses.add(DocumentRow(document_id="doc-pol", filename="chinh_sach.txt",
                            type="INTERNAL_POLICY", document_number=None, file_hash="h2",
                            file_path="p2", processing_status="INDEXED",
                            approval_status="APPROVED", injection_suspected=False,
                            uploaded_by="e", created_at=now))
        ses.add(ProvisionVersionRow(
            version_id="ver-pol-v1", provision_id="prov-pol-d1", document_id="doc-pol",
            content="Theo Điều 1 88/2026/QĐ-NHNN, hạn mức nội bộ là 500 triệu đồng.",
            valid_from=date(2026, 1, 2), valid_to_exclusive=None,
            approval_status="APPROVED", page=1, obligation=None, scope=None,
            created_at=now, approved_at=now))

    with session_scope() as ses:
        created = map_policy_document(ses, "doc-pol")
        assert len(created) == 1  # citation resolved -> one ALIGNED_TO artifact

    # amendment closes V1 (500) and opens V2 (700)
    with session_scope() as ses:
        v1 = ses.get(ProvisionVersionRow, "ver-r88-v1")
        v1.valid_to_exclusive = date(2026, 6, 1)
        ses.add(ProvisionVersionRow(version_id="ver-r88-v2", provision_id="prov-r88-d1",
                                    document_id="doc-r88", content="Hạn mức là 700 triệu đồng.",
                                    valid_from=date(2026, 6, 1), valid_to_exclusive=None,
                                    approval_status="APPROVED", page=1, obligation=None,
                                    scope=None, created_at=now, approved_at=now))
        ses.add(DocumentRow(document_id="doc-amd", filename="sd.txt", type="AMENDMENT",
                            document_number="09/2026/QĐ-NHNN", file_hash="h3", file_path="p3",
                            processing_status="INDEXED", approval_status="APPROVED",
                            injection_suspected=False, uploaded_by="e", created_at=now))
        ses.add(ChangeEventRow(change_event_id="chg-1", amending_document_id="doc-amd",
                               target_provision_id="prov-r88-d1", operation="REPLACE_TEXT",
                               old_text="500 triệu đồng", new_text="700 triệu đồng",
                               before_version_id="ver-r88-v1", after_version_id="ver-r88-v2",
                               valid_from=date(2026, 6, 1), source_page=1,
                               review_status="APPROVED"))

    rep = impact_engine.run("doc-amd")
    assert len(rep.impacted_policies) == 1
    assert rep.impacted_policies[0].reason == "THRESHOLD_MISMATCH"
    assert rep.impacted_policies[0].severity == "HIGH"


def test_t10_index_failure_keeps_postgres_truth(fresh_env, monkeypatch):
    from ingestion import service
    from ingestion import activate as activate_mod
    from packages.contracts.enums import ReviewDecision, ReviewTaskType

    doc = ("QUY ĐỊNH PHÍ MỚI\nSố: QĐ-55/2026\nNgày hiệu lực: 01/07/2026\n\n"
           "Điều 1. Mức phí\nMức phí dịch vụ lưu ký là 5 triệu đồng.\n")
    up = service.handle_upload(doc.encode("utf-8"), "qd55.txt", "REGULATION", "employee")
    for t in service.list_review_tasks("PENDING"):
        if t.task_type != ReviewTaskType.CHANGE_EVENT_REVIEW:
            service.decide_review_task(t.task_id, ReviewDecision.APPROVE, None, "employee")

    def _boom(**kw):
        raise RuntimeError("opensearch down")
    monkeypatch.setattr(activate_mod, "_index_version", _boom)

    act = service.activate_document(up.document_id, "employee")
    assert act["sync_status"] == "INDEX_SYNC_PENDING"       # visible, not silent
    assert act["sync_pending_versions"]
    d = next(x for x in service.list_documents() if x.document_id == up.document_id)
    assert d.approval_status == "APPROVED"                   # Postgres truth intact
