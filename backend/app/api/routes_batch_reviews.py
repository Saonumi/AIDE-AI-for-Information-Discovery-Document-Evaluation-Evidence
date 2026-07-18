"""API — Batch Document Review (Mode spec §12.2).

POST /batch-reviews                N files -> N independent Review Runs
GET  /batch-reviews/{id}           progress + summary + recurring issues
GET  /batch-reviews/{id}/items     per-file status
POST /batch-reviews/{id}/questions scoped chat (entire batch / one report / findings)
POST /batch-reviews/{id}/rerun     retry failed items, or full=true -> NEW batch
POST /batch-reviews/{id}/export    batch report JSON
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.auth import CurrentUser, require_authenticated

from backend.app.review import batch as batch_service
from backend.app.review import explainer
from backend.app.review.domain import BatchChatScope

router = APIRouter(tags=["batch-reviews"])


class BatchFile(BaseModel):
    filename: str
    text: str


class CreateBatchRequest(BaseModel):
    files: List[BatchFile]
    assessment_date: Optional[date] = None
    conversation_id: Optional[str] = None


class BatchQuestionRequest(BaseModel):
    question: str
    scope: BatchChatScope = BatchChatScope.ENTIRE_BATCH
    review_run_id: Optional[str] = None
    claim_ids: List[str] = Field(default_factory=list)


class BatchRerunRequest(BaseModel):
    full: bool = False
    item_id: Optional[str] = None


@router.post("/batch-reviews")
def create_batch(
    req: CreateBatchRequest, user: CurrentUser = Depends(require_authenticated)
) -> dict:
    return batch_service.create_batch_review(
        owner_id=user.username,
        files=[f.model_dump() for f in req.files],
        assessment_date=req.assessment_date,
        conversation_id=req.conversation_id)


@router.get("/batch-reviews/{batch_id}")
def get_batch(batch_id: str, user: CurrentUser = Depends(require_authenticated)) -> dict:
    return batch_service.get_batch_review(user.username, batch_id)


@router.get("/batch-reviews/{batch_id}/items")
def get_items(batch_id: str, user: CurrentUser = Depends(require_authenticated)) -> list:
    return batch_service.get_batch_review(user.username, batch_id)["items"]


@router.post("/batch-reviews/{batch_id}/questions")
def ask_batch_question(
    batch_id: str, req: BatchQuestionRequest,
    user: CurrentUser = Depends(require_authenticated),
) -> dict:
    return explainer.answer_batch(
        user.username, batch_id, req.question, req.scope.value,
        req.review_run_id, req.claim_ids or None)


@router.post("/batch-reviews/{batch_id}/rerun")
def rerun_batch(
    batch_id: str, req: BatchRerunRequest,
    user: CurrentUser = Depends(require_authenticated),
) -> dict:
    if req.full:
        return batch_service.rerun_full(user.username, batch_id)
    return batch_service.retry_failed(user.username, batch_id, req.item_id)


@router.post("/batch-reviews/{batch_id}/export")
def export_batch(batch_id: str, user: CurrentUser = Depends(require_authenticated)) -> dict:
    data = batch_service.get_batch_review(user.username, batch_id)
    data.pop("items", None)
    return data
