"""API — Single Document Review runs (Mode spec §12.2).

POST /review-runs                 upload text + assessment date -> locked run
GET  /review-runs/{id}            state + locked report
POST /review-runs/{id}/questions  explainer chat (bounded to the locked run)
POST /review-runs/{id}/export     the locked report JSON
POST /review-runs/{id}/rerun      NEW run (old result never changes)
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.auth import CurrentUser, require_authenticated

from backend.app.review import explainer
from backend.app.review import service

router = APIRouter(tags=["review-runs"])


class CreateReviewRunRequest(BaseModel):
    filename: str
    text: str
    assessment_date: Optional[date] = None
    conversation_id: Optional[str] = None


class QuestionRequest(BaseModel):
    question: str
    claim_id: Optional[str] = None


class RerunRequest(BaseModel):
    assessment_date: Optional[date] = None


@router.post("/review-runs")
def create_review_run(
    req: CreateReviewRunRequest, user: CurrentUser = Depends(require_authenticated)
) -> dict:
    return service.create_review_run(
        owner_id=user.username, filename=req.filename, text=req.text,
        assessment_date=req.assessment_date, conversation_id=req.conversation_id)


@router.get("/review-runs/{run_id}")
def get_review_run(run_id: str, user: CurrentUser = Depends(require_authenticated)) -> dict:
    return service.get_review_run(user.username, run_id)


@router.post("/review-runs/{run_id}/questions")
def ask_question(
    run_id: str, req: QuestionRequest,
    user: CurrentUser = Depends(require_authenticated),
) -> dict:
    return explainer.answer(user.username, run_id, req.question, req.claim_id)


@router.post("/review-runs/{run_id}/export")
def export_report(run_id: str, user: CurrentUser = Depends(require_authenticated)) -> dict:
    data = service.get_review_run(user.username, run_id)
    return data["report"] or {"review_run_id": run_id, "state": data["state"]}


@router.post("/review-runs/{run_id}/rerun")
def rerun(
    run_id: str, req: RerunRequest,
    user: CurrentUser = Depends(require_authenticated),
) -> dict:
    return service.rerun(user.username, run_id, req.assessment_date)
