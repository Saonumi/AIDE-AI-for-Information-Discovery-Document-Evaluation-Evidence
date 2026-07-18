"""Deterministic demo seed — the backbone that makes the whole demo answerable.

`seed_all()` populates ALL stores with the canonical VAIC2026 SHB1 scenario WITHOUT
any LLM call, so the query pipeline (Track B) and the eval harness produce
reproducible, ground-truth-checkable answers.

Canonical scenario (see docs/final_pipeline.md §A.0 and §8):
  QĐ-01/2026 (REGULATION)  Điều 7 Khoản 2  V1 "500 triệu" valid [2026-02-01, 2026-07-01)
  QĐ-02/2026 (AMENDMENT)   Thay 500→700 tại Khoản 2 Điều 7, hiệu lực 2026-07-01
                           → ChangeEvent REPLACE_TEXT (before=V1, after=V2)
  V2 "700 triệu"           valid [2026-07-01, ∞)
  QĐ-01/2026 Điều 7 Khoản 3 → "thực hiện theo Khoản 3 Điều 12" → REFERENCES Điều 12 K3
  Internal policy (INTERNAL_POLICY) "Quy trình cấp tín dụng SME nội bộ" 500 triệu
                           ALIGNED_TO V1 → STALE after V2
  QĐ-03/2026 Điều 5        "600 triệu" cùng nhóm khách hàng SME, valid [2026-07-01, ∞)
                           → POTENTIALLY_CONFLICTS_WITH V2 (700 vs 600)

The seed uses STABLE ids (not random uuids) so it is idempotent and every store
refers to the same entities. Calling `seed_all()` twice is a no-op after the first.
"""
from __future__ import annotations

from datetime import date, datetime

from infra.embeddings import embed_one
from infra.neo4j_client import get_graph
from infra.opensearch_client import get_store
from infra.postgres import init_db, session_scope
from infra.db_models import (
    ChangeEventRow,
    DocumentRow,
    InternalArtifactRow,
    ProvisionRow,
    ProvisionVersionRow,
)
from packages.common.ids import provision_lookup_key
from packages.common.vn_normalize import money_to_vnd
from packages.contracts.enums import (
    AmendmentOperation,
    ApprovalStatus,
    DocumentType,
    Modality,
    ProcessingStatus,
    ReviewStatus,
)

# --------------------------------------------------------------------------- #
# Stable identifiers (NOT random — makes seed idempotent across all 4 stores)
# --------------------------------------------------------------------------- #
# Documents
DOC_QD01 = "doc-qd01-2026"        # REGULATION (nguồn gốc)
DOC_QD02 = "doc-qd02-2026"        # AMENDMENT (sửa đổi)
DOC_QD03 = "doc-qd03-2026"        # REGULATION (điều khoản gần phạm vi -> conflict)
DOC_POLICY = "doc-internal-sme"   # INTERNAL_POLICY

# Provisions (identity is the id, NOT the locator)
PROV_D7K2 = "prov-qd01-d7k2"      # Điều 7 Khoản 2 (hạn mức SME) -> amended
PROV_D7K3 = "prov-qd01-d7k3"      # Điều 7 Khoản 3 (cross-reference nguồn)
PROV_D12K3 = "prov-qd01-d12k3"    # Điều 12 Khoản 3 (cross-reference đích)
PROV_D5_QD03 = "prov-qd03-d5"     # QĐ-03 Điều 5 (điều khoản conflict)

# Versions
VER_V1 = "ver-d7k2-v1"            # 500 triệu, [2026-02-01, 2026-07-01)
VER_V2 = "ver-d7k2-v2"            # 700 triệu, [2026-07-01, ∞)
VER_D7K3 = "ver-d7k3-v1"
VER_D12K3 = "ver-d12k3-v1"
VER_D5_QD03 = "ver-qd03-d5-v1"

# ChangeEvent, InternalArtifact
CHG_500_700 = "chg-500-to-700"
ART_POLICY = "art-internal-sme"

# --------------------------------------------------------------------------- #
# Content strings (the load-bearing ground truth text)
# --------------------------------------------------------------------------- #
V1_TEXT = "Hạn mức tín dụng SME là 500 triệu đồng, thời hạn tối đa 12 tháng."
V2_TEXT = "Hạn mức tín dụng SME là 700 triệu đồng, thời hạn tối đa 12 tháng."
D7K3_TEXT = "Việc thẩm định và phê duyệt tín dụng SME thực hiện theo Khoản 3 Điều 12."
D12K3_TEXT = (
    "Hồ sơ tín dụng SME phải được thẩm định bởi bộ phận quản lý rủi ro độc lập "
    "trước khi phê duyệt."
)
QD03_D5_TEXT = "Hạn mức với cùng nhóm khách hàng SME là 600 triệu đồng."
POLICY_TEXT = (
    "Quy trình cấp tín dụng SME nội bộ: hạn mức tín dụng SME là 500 triệu đồng, "
    "thời hạn tối đa 12 tháng."
)

V1_VALID_FROM = date(2026, 2, 1)
V1_VALID_TO = date(2026, 7, 1)
V2_VALID_FROM = date(2026, 7, 1)

_SME_SCOPE = {
    "subject": "khách hàng SME",
    "product": "tín dụng SME",
    "customer_type": "SME",
    "jurisdiction": "SHB",
    "authority_level": "REGULATION",
}


def _obligation(value_text: str) -> dict:
    """Structured obligation with canonical VND value (via vn_normalize)."""
    return {
        "subject": "khách hàng SME",
        "action": "được cấp hạn mức tín dụng",
        "modality": Modality.PERMISSION.value,
        "condition": "thời hạn tối đa 12 tháng",
        "value": value_text,
        "value_normalized": money_to_vnd(value_text),
        "confidence": 1.0,
    }


# --------------------------------------------------------------------------- #
# 1) Postgres / SQLite
# --------------------------------------------------------------------------- #
def _seed_postgres() -> None:
    now = datetime(2026, 1, 15, 8, 0, 0)
    approved_at = datetime(2026, 1, 20, 9, 0, 0)

    documents = [
        DocumentRow(
            document_id=DOC_QD01, filename="QD-01-2026.pdf", type=DocumentType.REGULATION.value,
            document_number="QĐ-01/2026", file_hash="sha256:qd01",
            file_path="data/corpus/QD-01-2026.pdf",
            processing_status=ProcessingStatus.INDEXED.value,
            approval_status=ApprovalStatus.APPROVED.value, injection_suspected=False,
            uploaded_by="employee", doc_metadata={
                "document_number": "QĐ-01/2026", "issued_date": "2026-01-15",
                "valid_from": "2026-02-01", "authority": "SHB", "scope": _SME_SCOPE,
            }, created_at=now,
        ),
        DocumentRow(
            document_id=DOC_QD02, filename="QD-02-2026.pdf", type=DocumentType.AMENDMENT.value,
            document_number="QĐ-02/2026", file_hash="sha256:qd02",
            file_path="data/corpus/QD-02-2026.pdf",
            processing_status=ProcessingStatus.INDEXED.value,
            approval_status=ApprovalStatus.APPROVED.value, injection_suspected=False,
            uploaded_by="employee", doc_metadata={
                "document_number": "QĐ-02/2026", "issued_date": "2026-06-15",
                "valid_from": "2026-07-01", "authority": "SHB",
            }, created_at=datetime(2026, 6, 15, 8, 0, 0),
        ),
        DocumentRow(
            document_id=DOC_QD03, filename="QD-03-2026.pdf", type=DocumentType.REGULATION.value,
            document_number="QĐ-03/2026", file_hash="sha256:qd03",
            file_path="data/corpus/QD-03-2026.pdf",
            processing_status=ProcessingStatus.INDEXED.value,
            approval_status=ApprovalStatus.APPROVED.value, injection_suspected=False,
            uploaded_by="employee", doc_metadata={
                "document_number": "QĐ-03/2026", "issued_date": "2026-06-20",
                "valid_from": "2026-07-01", "authority": "SHB", "scope": _SME_SCOPE,
            }, created_at=datetime(2026, 6, 20, 8, 0, 0),
        ),
        DocumentRow(
            document_id=DOC_POLICY, filename="quy-trinh-tin-dung-sme-noi-bo.pdf",
            type=DocumentType.INTERNAL_POLICY.value, document_number="NB-SME-01",
            file_hash="sha256:policy", file_path="data/corpus/quy-trinh-tin-dung-sme-noi-bo.pdf",
            processing_status=ProcessingStatus.INDEXED.value,
            approval_status=ApprovalStatus.APPROVED.value, injection_suspected=False,
            uploaded_by="employee", doc_metadata={
                "document_number": "NB-SME-01", "issued_date": "2026-02-05",
                "authority": "SHB", "scope": _SME_SCOPE,
            }, created_at=datetime(2026, 2, 5, 8, 0, 0),
        ),
    ]

    provisions = [
        ProvisionRow(
            provision_id=PROV_D7K2, document_id=DOC_QD01,
            lookup_key=provision_lookup_key("QĐ-01/2026", "7", "2"),
            heading_path=["Điều 7", "Khoản 2"], article="7", clause="2", point=None,
        ),
        ProvisionRow(
            provision_id=PROV_D7K3, document_id=DOC_QD01,
            lookup_key=provision_lookup_key("QĐ-01/2026", "7", "3"),
            heading_path=["Điều 7", "Khoản 3"], article="7", clause="3", point=None,
        ),
        ProvisionRow(
            provision_id=PROV_D12K3, document_id=DOC_QD01,
            lookup_key=provision_lookup_key("QĐ-01/2026", "12", "3"),
            heading_path=["Điều 12", "Khoản 3"], article="12", clause="3", point=None,
        ),
        ProvisionRow(
            provision_id=PROV_D5_QD03, document_id=DOC_QD03,
            lookup_key=provision_lookup_key("QĐ-03/2026", "5", None),
            heading_path=["Điều 5"], article="5", clause=None, point=None,
        ),
    ]

    versions = [
        ProvisionVersionRow(
            version_id=VER_V1, provision_id=PROV_D7K2, document_id=DOC_QD01,
            content=V1_TEXT, valid_from=V1_VALID_FROM, valid_to_exclusive=V1_VALID_TO,
            approval_status=ApprovalStatus.APPROVED.value, page=3,
            obligation=_obligation("500 triệu đồng"), scope=dict(_SME_SCOPE),
            created_at=now, approved_at=approved_at,
        ),
        ProvisionVersionRow(
            version_id=VER_V2, provision_id=PROV_D7K2, document_id=DOC_QD01,
            content=V2_TEXT, valid_from=V2_VALID_FROM, valid_to_exclusive=None,
            approval_status=ApprovalStatus.APPROVED.value, page=3,
            obligation=_obligation("700 triệu đồng"), scope=dict(_SME_SCOPE),
            created_at=datetime(2026, 6, 15, 8, 0, 0), approved_at=datetime(2026, 6, 25, 9, 0, 0),
        ),
        ProvisionVersionRow(
            version_id=VER_D7K3, provision_id=PROV_D7K3, document_id=DOC_QD01,
            content=D7K3_TEXT, valid_from=V1_VALID_FROM, valid_to_exclusive=None,
            approval_status=ApprovalStatus.APPROVED.value, page=3,
            obligation=None, scope=dict(_SME_SCOPE), created_at=now, approved_at=approved_at,
        ),
        ProvisionVersionRow(
            version_id=VER_D12K3, provision_id=PROV_D12K3, document_id=DOC_QD01,
            content=D12K3_TEXT, valid_from=V1_VALID_FROM, valid_to_exclusive=None,
            approval_status=ApprovalStatus.APPROVED.value, page=5,
            obligation=None, scope=dict(_SME_SCOPE), created_at=now, approved_at=approved_at,
        ),
        ProvisionVersionRow(
            version_id=VER_D5_QD03, provision_id=PROV_D5_QD03, document_id=DOC_QD03,
            content=QD03_D5_TEXT, valid_from=V2_VALID_FROM, valid_to_exclusive=None,
            approval_status=ApprovalStatus.APPROVED.value, page=2,
            obligation=_obligation("600 triệu đồng"), scope=dict(_SME_SCOPE),
            created_at=datetime(2026, 6, 20, 8, 0, 0), approved_at=datetime(2026, 6, 28, 9, 0, 0),
        ),
    ]

    change_events = [
        ChangeEventRow(
            change_event_id=CHG_500_700, amending_document_id=DOC_QD02,
            target_provision_id=PROV_D7K2, operation=AmendmentOperation.REPLACE_TEXT.value,
            old_text="500 triệu đồng", new_text="700 triệu đồng",
            before_version_id=VER_V1, after_version_id=VER_V2,
            valid_from=V2_VALID_FROM, source_page=1,
            review_status=ReviewStatus.APPROVED.value,
        ),
    ]

    artifacts = [
        InternalArtifactRow(
            artifact_id=ART_POLICY, document_id=DOC_POLICY,
            title="Quy trình cấp tín dụng SME nội bộ",
            aligned_to_version_id=VER_V1, obligation=_obligation("500 triệu đồng"), page=1,
        ),
    ]

    with session_scope() as ses:
        for row in documents + provisions + versions + change_events + artifacts:
            ses.merge(row)  # merge == idempotent upsert by primary key


# --------------------------------------------------------------------------- #
# 2) OpenSearch (index every APPROVED version as a chunk)
# --------------------------------------------------------------------------- #
def _chunk(chunk_id, provision_id, version_id, document_id, document_number,
           heading_path, content, page, valid_from, valid_to_exclusive) -> dict:
    return {
        "chunk_id": chunk_id,
        "provision_id": provision_id,
        "version_id": version_id,
        "document_id": document_id,
        "document_number": document_number,
        "heading_path": heading_path,
        "content": content,
        "page": page,
        "valid_from": valid_from,                     # "YYYY-MM-DD"
        "valid_to_exclusive": valid_to_exclusive,     # "YYYY-MM-DD" | None
        "approval_status": ApprovalStatus.APPROVED.value,
    }


def _seed_opensearch() -> None:
    store = get_store()
    store.ensure_index()
    chunks = [
        _chunk("chunk-v1", PROV_D7K2, VER_V1, DOC_QD01, "QĐ-01/2026",
               ["Điều 7", "Khoản 2"], V1_TEXT, 3, "2026-02-01", "2026-07-01"),
        _chunk("chunk-v2", PROV_D7K2, VER_V2, DOC_QD01, "QĐ-01/2026",
               ["Điều 7", "Khoản 2"], V2_TEXT, 3, "2026-07-01", None),
        _chunk("chunk-d7k3", PROV_D7K3, VER_D7K3, DOC_QD01, "QĐ-01/2026",
               ["Điều 7", "Khoản 3"], D7K3_TEXT, 3, "2026-02-01", None),
        _chunk("chunk-d12k3", PROV_D12K3, VER_D12K3, DOC_QD01, "QĐ-01/2026",
               ["Điều 12", "Khoản 3"], D12K3_TEXT, 5, "2026-02-01", None),
        _chunk("chunk-qd03-d5", PROV_D5_QD03, VER_D5_QD03, DOC_QD03, "QĐ-03/2026",
               ["Điều 5"], QD03_D5_TEXT, 2, "2026-07-01", None),
        _chunk("chunk-policy", ART_POLICY, ART_POLICY, DOC_POLICY, "NB-SME-01",
               ["Quy trình cấp tín dụng SME nội bộ"], POLICY_TEXT, 1, "2026-02-05", None),
    ]
    for ch in chunks:
        store.index_chunk(ch, embed_one(ch["content"]))


# --------------------------------------------------------------------------- #
# 3) Neo4j (temporal regulatory graph)
# --------------------------------------------------------------------------- #
def _seed_neo4j() -> None:
    g = get_graph()

    # Documents
    g.upsert_node(DOC_QD01, "Document", title="QĐ-01/2026", document_number="QĐ-01/2026",
                  type=DocumentType.REGULATION.value)
    g.upsert_node(DOC_QD02, "Document", title="QĐ-02/2026", document_number="QĐ-02/2026",
                  type=DocumentType.AMENDMENT.value)
    g.upsert_node(DOC_QD03, "Document", title="QĐ-03/2026", document_number="QĐ-03/2026",
                  type=DocumentType.REGULATION.value)
    g.upsert_node(DOC_POLICY, "Document", title="Quy trình cấp tín dụng SME nội bộ",
                  document_number="NB-SME-01", type=DocumentType.INTERNAL_POLICY.value)

    # Provisions (locator + title props for expand()/subgraph())
    g.upsert_node(PROV_D7K2, "Provision", title="Điều 7 Khoản 2 (Hạn mức SME)",
                  locator="Khoản 2 Điều 7", document_number="QĐ-01/2026")
    g.upsert_node(PROV_D7K3, "Provision", title="Điều 7 Khoản 3 (Thẩm định)",
                  locator="Khoản 3 Điều 7", document_number="QĐ-01/2026")
    g.upsert_node(PROV_D12K3, "Provision", title="Điều 12 Khoản 3 (Quản lý rủi ro)",
                  locator="Khoản 3 Điều 12", document_number="QĐ-01/2026")
    g.upsert_node(PROV_D5_QD03, "Provision", title="Điều 5 (Hạn mức nhóm SME)",
                  locator="Điều 5", document_number="QĐ-03/2026")

    # ProvisionVersions (temporal props)
    g.upsert_node(VER_V1, "ProvisionVersion", title="V1 500 triệu",
                  valid_from="2026-02-01", valid_to_exclusive="2026-07-01",
                  approval_status=ApprovalStatus.APPROVED.value, content=V1_TEXT)
    g.upsert_node(VER_V2, "ProvisionVersion", title="V2 700 triệu",
                  valid_from="2026-07-01", valid_to_exclusive=None,
                  approval_status=ApprovalStatus.APPROVED.value, content=V2_TEXT)
    g.upsert_node(VER_D7K3, "ProvisionVersion", title="Điều 7 Khoản 3",
                  valid_from="2026-02-01", valid_to_exclusive=None,
                  approval_status=ApprovalStatus.APPROVED.value, content=D7K3_TEXT)
    g.upsert_node(VER_D12K3, "ProvisionVersion", title="Điều 12 Khoản 3",
                  valid_from="2026-02-01", valid_to_exclusive=None,
                  approval_status=ApprovalStatus.APPROVED.value, content=D12K3_TEXT)
    g.upsert_node(VER_D5_QD03, "ProvisionVersion", title="QĐ-03 Điều 5 600 triệu",
                  valid_from="2026-07-01", valid_to_exclusive=None,
                  approval_status=ApprovalStatus.APPROVED.value, content=QD03_D5_TEXT)

    # ChangeEvent + InternalArtifact
    g.upsert_node(CHG_500_700, "ChangeEvent", title="REPLACE 500→700 triệu",
                  operation=AmendmentOperation.REPLACE_TEXT.value,
                  before_version_id=VER_V1, after_version_id=VER_V2,
                  old_text="500 triệu đồng", new_text="700 triệu đồng", valid_from="2026-07-01")
    g.upsert_node(ART_POLICY, "InternalArtifact", title="Quy trình cấp tín dụng SME nội bộ",
                  content=POLICY_TEXT)

    # Edges
    # Document CONTAINS Provision
    g.upsert_edge(DOC_QD01, PROV_D7K2, "CONTAINS")
    g.upsert_edge(DOC_QD01, PROV_D7K3, "CONTAINS")
    g.upsert_edge(DOC_QD01, PROV_D12K3, "CONTAINS")
    g.upsert_edge(DOC_QD03, PROV_D5_QD03, "CONTAINS")

    # Provision HAS_VERSION ProvisionVersion
    g.upsert_edge(PROV_D7K2, VER_V1, "HAS_VERSION")
    g.upsert_edge(PROV_D7K2, VER_V2, "HAS_VERSION")
    g.upsert_edge(PROV_D7K3, VER_D7K3, "HAS_VERSION")
    g.upsert_edge(PROV_D12K3, VER_D12K3, "HAS_VERSION")
    g.upsert_edge(PROV_D5_QD03, VER_D5_QD03, "HAS_VERSION")

    # ProvisionVersion DECLARES obligation is implicit here (obligation kept on version node)

    # ChangeEvent TARGETS Provision; BEFORE/AFTER wire the version chain
    g.upsert_edge(CHG_500_700, PROV_D7K2, "TARGETS")
    g.upsert_edge(CHG_500_700, VER_V1, "BEFORE")
    g.upsert_edge(CHG_500_700, VER_V2, "AFTER")
    # V2 SUPERSEDES V1
    g.upsert_edge(VER_V2, VER_V1, "SUPERSEDES")
    # amending document is the source of the change (TARGETS from doc too, for provenance)
    g.upsert_edge(DOC_QD02, PROV_D7K2, "TARGETS")

    # Cross-reference: Điều 7 Khoản 3 REFERENCES Điều 12 Khoản 3
    g.upsert_edge(PROV_D7K3, PROV_D12K3, "REFERENCES", to_locator="Khoản 3 Điều 12")

    # Internal policy ALIGNED_TO V1 (-> becomes stale after V2)
    g.upsert_edge(ART_POLICY, VER_V1, "ALIGNED_TO")

    # Conflict: QĐ-03 Điều 5 (600) POTENTIALLY_CONFLICTS_WITH V2 (700), co-valid & same scope
    g.upsert_edge(PROV_D5_QD03, VER_V2, "POTENTIALLY_CONFLICTS_WITH",
                  reason="THRESHOLD_MISMATCH", value_a="600 triệu đồng", value_b="700 triệu đồng")


# --------------------------------------------------------------------------- #
# public entry point
# --------------------------------------------------------------------------- #
def seed_all() -> None:
    """Populate every store with the canonical demo scenario. Idempotent."""
    init_db()
    _seed_postgres()
    _seed_opensearch()
    _seed_neo4j()


if __name__ == "__main__":  # pragma: no cover - manual run
    seed_all()
    print("Seeded demo corpus into all stores.")
