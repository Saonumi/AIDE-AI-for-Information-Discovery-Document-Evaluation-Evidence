"""Workflow B step 3 — Compliance Review Report (Final spec §7.11, Phụ lục B.3)."""
from __future__ import annotations

from datetime import date
from typing import List

from packages.common.ids import new_id

from backend.app.domain.compliance import (
    ClaimAssessment,
    ComplianceReviewReport,
    ComplianceStatus,
    ReviewTargetStatus,
)


def build(
    target_document_id: str,
    review_date: date,
    assessments: List[ClaimAssessment],
) -> ComplianceReviewReport:
    summary = {s.value.lower(): 0 for s in ComplianceStatus}
    for a in assessments:
        summary[a.status.value.lower()] += 1
    summary["total_claims"] = len(assessments)
    return ComplianceReviewReport(
        report_id=new_id("crr"),
        target_document_id=target_document_id,
        review_date=review_date,
        summary=summary,
        assessments=assessments,
        status=ReviewTargetStatus.REVIEW_REQUIRED if assessments else ReviewTargetStatus.COMPLETED,
    )
