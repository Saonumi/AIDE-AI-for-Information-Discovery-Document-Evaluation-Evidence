"""Regulatory Impact Report assembly (Final spec §7.11)."""
from __future__ import annotations

from typing import List

from infra.db_models import DocumentRow
from packages.common.ids import new_id

from backend.app.domain.impact import ChangeSummary, ImpactedPolicy, RegulatoryImpactReport

_SEV_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}


def build(
    doc: DocumentRow,
    changes: List[ChangeSummary],
    impacted: List[ImpactedPolicy],
) -> RegulatoryImpactReport:
    approved = sum(1 for c in changes if c.review_status == "APPROVED")
    pending = len(changes) - approved
    max_sev = max((p.severity for p in impacted), key=_SEV_ORDER.get, default=None)

    parts = [f"Văn bản {doc.document_number or doc.document_id}: "
             f"{approved} thay đổi đã duyệt"]
    if pending:
        parts.append(f"{pending} thay đổi chờ duyệt")
    if impacted:
        parts.append(
            f"{len(impacted)} policy nội bộ bị ảnh hưởng (mức cao nhất: {max_sev})"
        )
    else:
        parts.append("không phát hiện policy nội bộ bị ảnh hưởng")

    return RegulatoryImpactReport(
        report_id=new_id("imp"),
        document_id=doc.document_id,
        document_number=doc.document_number,
        executive_summary="; ".join(parts) + ".",
        changes=changes,
        impacted_policies=impacted,
        max_severity=max_sev,
        status="REVIEW_REQUIRED" if impacted or pending else "COMPLETED",
    )
