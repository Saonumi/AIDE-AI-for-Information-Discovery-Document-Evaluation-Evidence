"""Workflow B — Check Document Compliance (Final spec tests T5-T8, §11.2).

Self-seeded like test_query_pipeline.py: sqlite + in-memory store + mock LLM.
Scenario (mirrors the golden credit domain):
    SME limit   V1 = 500tr  [2026-02-01, 2026-07-01)   superseded
                V2 = 700tr  [2026-07-01, inf)          active
    ST-funding ratio V1 = 34% [2026-01-01, 2026-06-01) superseded
                     V2 = 30% [2026-06-01, inf)        active

T5 claim matches active value        -> COMPLIANT
T6 claim uses superseded value       -> OUTDATED_REFERENCE
T7 claim contradicts active value    -> NON_COMPLIANT
T8 claim with no basis in the corpus -> MISSING_EVIDENCE
"""
from __future__ import annotations

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infra.embeddings import embed_one
from infra.opensearch_client import get_store, reset_store_for_tests
from infra.neo4j_client import reset_graph_for_tests
from infra.postgres import get_engine, init_db, session_scope
from infra.db_models import Base, ProvisionRow, ProvisionVersionRow

from backend.app.domain.compliance import ComplianceStatus
from backend.app.workflows.compliance_checks import claim_extractor
from backend.app.workflows.compliance_checks.service import run_compliance_check

REVIEW_DATE = date(2026, 7, 18)


def _chunk(chunk_id, provision_id, version_id, content, valid_from, valid_to,
           heading, docno):
    return {
        "chunk_id": chunk_id,
        "provision_id": provision_id,
        "version_id": version_id,
        "document_id": "doc-1",
        "document_number": docno,
        "heading_path": heading,
        "content": content,
        "page": 3,
        "valid_from": valid_from,
        "valid_to_exclusive": valid_to,
        "approval_status": "APPROVED",
    }


def _seed():
    reset_store_for_tests()
    reset_graph_for_tests()
    init_db()
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    store = get_store()
    rows = [
        # SME limit — money scenario
        ("prov-sme7", "ver-sme-v1", "Hạn mức tín dụng SME là 500 triệu đồng, thời hạn tối đa 12 tháng.",
         date(2026, 2, 1), date(2026, 7, 1), ["Điều 7", "Khoản 2"], "QĐ-01/2026"),
        ("prov-sme7", "ver-sme-v2", "Hạn mức tín dụng SME là 700 triệu đồng, thời hạn tối đa 12 tháng.",
         date(2026, 7, 1), None, ["Điều 7", "Khoản 2"], "QĐ-01/2026"),
        # short-term funding ratio — percent scenario (golden credit domain values)
        ("prov-ratio1", "ver-ratio-v1",
         "Tỷ lệ tối đa nguồn vốn ngắn hạn được sử dụng để cho vay trung hạn và dài hạn là 34%.",
         date(2026, 1, 1), date(2026, 6, 1), ["Điều 16", "Khoản 1"], "22/2019/TT-NHNN"),
        ("prov-ratio1", "ver-ratio-v2",
         "Tỷ lệ tối đa nguồn vốn ngắn hạn được sử dụng để cho vay trung hạn và dài hạn là 30%.",
         date(2026, 6, 1), None, ["Điều 16", "Khoản 1"], "08/2026/TT-NHNN"),
    ]
    with session_scope() as ses:
        ses.add(ProvisionRow(provision_id="prov-sme7", document_id="doc-1",
                             lookup_key="QĐ-01/2026|D7|K2|P",
                             heading_path=["Điều 7", "Khoản 2"], article="7", clause="2"))
        ses.add(ProvisionRow(provision_id="prov-ratio1", document_id="doc-1",
                             lookup_key="22/2019/TT-NHNN|D16|K1|P",
                             heading_path=["Điều 16", "Khoản 1"], article="16", clause="1"))
        for i, (prov, ver, content, vf, vt, heading, docno) in enumerate(rows):
            ses.add(ProvisionVersionRow(
                version_id=ver, provision_id=prov, document_id="doc-1",
                content=content, valid_from=vf, valid_to_exclusive=vt,
                approval_status="APPROVED", page=3,
            ))
            chunk = _chunk(f"ch-{i}", prov, ver, content, vf, vt, heading, docno)
            store.index_chunk(chunk, embed_one(content + " " + " ".join(heading)))


def _single_status(text):
    report = run_compliance_check(text, review_date=REVIEW_DATE)
    assert len(report.assessments) == 1, [a.source_text for a in report.assessments]
    return report.assessments[0]


def test_t5_compliant_claim():
    _seed()
    a = _single_status("Hạn mức tín dụng SME tối đa là 700 triệu đồng.")
    assert a.status == ComplianceStatus.COMPLIANT
    assert any(e.version_id == "ver-sme-v2" for e in a.valid_evidence)


def test_t6_outdated_reference_money():
    _seed()
    a = _single_status("Hạn mức tín dụng SME tối đa là 500 triệu đồng.")
    assert a.status == ComplianceStatus.OUTDATED_REFERENCE
    assert any(e.version_id == "ver-sme-v1" for e in a.excluded_evidence)
    assert a.recommendation  # must point at the current value


def test_t6b_outdated_reference_percent():
    _seed()
    a = _single_status(
        "Tỷ lệ tối đa nguồn vốn ngắn hạn được sử dụng để cho vay trung hạn và dài hạn là 34%."
    )
    assert a.status == ComplianceStatus.OUTDATED_REFERENCE


def test_t7_non_compliant_claim():
    _seed()
    a = _single_status("Hạn mức tín dụng SME tối đa là 900 triệu đồng.")
    assert a.status == ComplianceStatus.NON_COMPLIANT
    assert a.recommendation


def test_t8_missing_evidence():
    _seed()
    a = _single_status("Phí dịch vụ chuyển tiền quốc tế tối đa là 2 triệu đồng.")
    assert a.status == ComplianceStatus.MISSING_EVIDENCE


def test_claim_extractor_facts():
    facts = claim_extractor.mine_facts(
        "Theo 22/2019/TT-NHNN, tỷ lệ tối đa là 34% và hạn mức 500 triệu đồng, "
        "báo cáo chậm nhất ngày 10 hằng tháng."
    )
    assert facts.percents == [34.0]
    assert 500_000_000 in facts.money_vnd
    assert facts.deadline_days == [10]
    assert facts.doc_refs == ["22/2019/TT-NHNN"]


def test_report_summary_counts():
    _seed()
    policy = "\n".join([
        "Điều 1. Hạn mức",
        "Hạn mức tín dụng SME tối đa là 500 triệu đồng.",
        "Điều 2. Tỷ lệ an toàn",
        "Tỷ lệ tối đa nguồn vốn ngắn hạn được sử dụng để cho vay trung hạn và dài hạn là 30%.",
    ])
    report = run_compliance_check(policy, review_date=REVIEW_DATE)
    assert report.summary["total_claims"] == 2
    assert report.summary["outdated_reference"] == 1
    assert report.summary["compliant"] == 1
    assert report.status.value == "REVIEW_REQUIRED"


if __name__ == "__main__":
    for fn in [test_t5_compliant_claim, test_t6_outdated_reference_money,
               test_t6b_outdated_reference_percent, test_t7_non_compliant_claim,
               test_t8_missing_evidence, test_claim_extractor_facts,
               test_report_summary_counts]:
        fn()
        print(f"ok {fn.__name__}")
