"""API — Workflow B: Check Document Compliance (Final spec §9).

POST /compliance-checks            upload a REVIEW_TARGET (text) and run the check
GET  /compliance-checks/{id}       status + summary
GET  /compliance-checks/{id}/report  full Compliance Review Report (Phụ lục B.3)

The uploaded document is NEVER indexed into the legal store — the engine only
reads approved evidence (Final spec T4).
"""
from __future__ import annotations

from datetime import date
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import CurrentUser, require_authenticated
from packages.common.ids import new_id

from backend.app.domain.compliance import ComplianceReviewReport, TrustClass, UploadPurpose
from backend.app.workflows.compliance_checks.service import run_compliance_check

router = APIRouter(tags=["compliance-checks"])

# ponytail: in-memory report registry; move to a Postgres table when persistence
# across restarts matters.
_REPORTS: Dict[str, ComplianceReviewReport] = {}


class ComplianceCheckRequest(BaseModel):
    text: str
    review_date: Optional[date] = None
    filename: Optional[str] = None
    upload_purpose: UploadPurpose = UploadPurpose.CHECK_DOCUMENT_COMPLIANCE


@router.post("/compliance-checks")
def create_check(
    req: ComplianceCheckRequest,
    user: CurrentUser = Depends(require_authenticated),
) -> dict:
    if req.upload_purpose != UploadPurpose.CHECK_DOCUMENT_COMPLIANCE:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_UPLOAD_PURPOSE",
                              "message": "Route này chỉ nhận CHECK_DOCUMENT_COMPLIANCE."}},
        )
    target_id = new_id("rvt")
    report = run_compliance_check(
        req.text, review_date=req.review_date, target_document_id=target_id
    )
    _REPORTS[target_id] = report
    return {
        "check_id": target_id,
        "trust_class": TrustClass.REVIEW_TARGET.value,
        "status": report.status.value,
        "summary": report.summary,
    }


def _get(check_id: str) -> ComplianceReviewReport:
    report = _REPORTS.get(check_id)
    if report is None:
        raise HTTPException(status_code=404, detail="check not found")
    return report


@router.get("/compliance-checks/{check_id}")
def get_check(check_id: str, user: CurrentUser = Depends(require_authenticated)) -> dict:
    report = _get(check_id)
    return {"check_id": check_id, "status": report.status.value, "summary": report.summary}


@router.get("/compliance-checks/{check_id}/report")
def get_report(
    check_id: str, user: CurrentUser = Depends(require_authenticated)
) -> ComplianceReviewReport:
    return _get(check_id)
