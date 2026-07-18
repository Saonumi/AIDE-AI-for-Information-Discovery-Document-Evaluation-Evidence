"""API — Regulatory Impact Report (Final spec §7.8, §9).

GET /regulatory-sources/{document_id}/impact-report

Computed on demand from Postgres (deterministic recompute) — available the
moment activation commits, which satisfies the post-activation trigger without
an async queue. 404 if the document does not exist.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.auth import CurrentUser, require_authenticated

from backend.app.domain.impact import RegulatoryImpactReport
from backend.app.workflows.impact_analysis import impact_engine

router = APIRouter(tags=["impact-reports"])


@router.get("/regulatory-sources/{document_id}/impact-report")
def get_impact_report(
    document_id: str, user: CurrentUser = Depends(require_authenticated)
) -> RegulatoryImpactReport:
    try:
        return impact_engine.run(document_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
