"""Workflow B orchestrator (Final spec §7.9) — the single entry the API/tests call.

run_compliance_check(text, ...) -> ComplianceReviewReport
The review target is NEVER indexed or promoted: nothing here writes to the
chunk store, the graph, or provision tables — it only reads approved evidence.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from packages.common.ids import new_id

from backend.app.domain.compliance import ComplianceReviewReport
from backend.app.workflows.compliance_checks import assessor, claim_extractor, report_builder


def run_compliance_check(
    text: str,
    review_date: Optional[date] = None,
    target_document_id: Optional[str] = None,
) -> ComplianceReviewReport:
    target_document_id = target_document_id or new_id("rvt")
    review_date = review_date or date.today()
    claims = claim_extractor.extract(text, target_document_id)
    assessments = [assessor.assess_claim(c, review_date) for c in claims]
    return report_builder.build(target_document_id, review_date, assessments)
