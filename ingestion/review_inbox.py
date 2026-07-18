"""Step 11 — Employee Review Inbox.

A single table (review_tasks) holds every human-in-the-loop candidate, regardless of
type: PARSING_REVIEW, CHANGE_EVENT_REVIEW, REFERENCE_REVIEW, CONFLICT_REVIEW,
IMPACT_REVIEW, INJECTION_REVIEW. One inbox, not six screens.

This module only creates/lists/reads/decides tasks and converts rows <-> the frozen
ReviewTask contract. The *effect* of an approval (creating V2, activating) lives in
activate.py — deciding a task is separated from applying it so the audit trail is clean.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import select

from infra.db_models import ReviewTaskRow
from packages.common.ids import new_id
from packages.contracts.enums import ReviewDecision, ReviewStatus, ReviewTaskType
from packages.contracts.models import ReviewTask


def _row_to_model(row: ReviewTaskRow) -> ReviewTask:
    return ReviewTask(
        task_id=row.task_id,
        task_type=ReviewTaskType(row.task_type),
        document_id=row.document_id,
        source_ref=row.source_ref,
        extracted=row.extracted or {},
        diff_before=row.diff_before,
        diff_after=row.diff_after,
        confidence=row.confidence if row.confidence is not None else 1.0,
        valid_from=row.valid_from,
        status=ReviewStatus(row.status),
        decision=ReviewDecision(row.decision) if row.decision else None,
        decided_by=row.decided_by,
        created_at=row.created_at,
    )


def create_task(
    session,
    task_type: ReviewTaskType,
    *,
    document_id: Optional[str] = None,
    source_ref: Optional[str] = None,
    extracted: Optional[dict] = None,
    diff_before: Optional[str] = None,
    diff_after: Optional[str] = None,
    confidence: float = 1.0,
    valid_from: Optional[date] = None,
) -> ReviewTaskRow:
    """Insert a PENDING review task. Returns the ORM row (id populated)."""
    row = ReviewTaskRow(
        task_id=new_id("task"),
        task_type=task_type.value,
        document_id=document_id,
        source_ref=source_ref,
        extracted=extracted or {},
        diff_before=diff_before,
        diff_after=diff_after,
        confidence=confidence,
        valid_from=valid_from,
        status=ReviewStatus.PENDING.value,
        created_at=datetime.utcnow(),
    )
    session.add(row)
    session.flush()
    return row


def list_tasks(session, status: Optional[str] = None) -> List[ReviewTask]:
    stmt = select(ReviewTaskRow)
    if status:
        stmt = stmt.where(ReviewTaskRow.status == status)
    stmt = stmt.order_by(ReviewTaskRow.created_at.asc())
    rows = session.execute(stmt).scalars().all()
    return [_row_to_model(r) for r in rows]


def get_task(session, task_id: str) -> Optional[ReviewTaskRow]:
    return session.execute(
        select(ReviewTaskRow).where(ReviewTaskRow.task_id == task_id)
    ).scalars().first()


def mark_decided(
    session,
    row: ReviewTaskRow,
    decision: ReviewDecision,
    decided_by: str,
    edited_payload: Optional[dict] = None,
) -> ReviewTaskRow:
    """Record the employee decision on a task row (does NOT apply side effects).

    APPROVE / EDIT -> status APPROVED (EDIT merges edited_payload into extracted).
    REJECT         -> status REJECTED.
    """
    if edited_payload:
        merged = dict(row.extracted or {})
        merged.update(edited_payload)
        row.extracted = merged
    row.decision = decision.value
    row.decided_by = decided_by
    if decision == ReviewDecision.REJECT:
        row.status = ReviewStatus.REJECTED.value
    else:
        row.status = ReviewStatus.APPROVED.value
    session.flush()
    return row
