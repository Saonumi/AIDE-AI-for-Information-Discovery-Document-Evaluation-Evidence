from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from api._facade import call
from api.auth import CurrentUser, require_employee
from packages.contracts.api_schemas import ReviewDecisionRequest

router = APIRouter(tags=["review"])


@router.get("/review-tasks")
def list_review_tasks(status: Optional[str] = None, user: CurrentUser = Depends(require_employee)):
    return call("ingestion.service", "list_review_tasks", status)


@router.post("/review-tasks/{task_id}/decision")
def decide_review_task(
    task_id: str,
    req: ReviewDecisionRequest,
    user: CurrentUser = Depends(require_employee),
):
    return call("ingestion.service", "decide_review_task",
                task_id, req.decision, req.edited_payload, user.username)
