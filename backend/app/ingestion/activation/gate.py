"""Activation gate — chặn activate khi còn critical review pending (HTTP 409)."""
from __future__ import annotations

from typing import List, Tuple

from sqlalchemy import select

from infra.db_models import DocumentRow, ReviewTaskRow
from packages.contracts.enums import ProcessingStatus, ReviewStatus, ReviewTaskType

_CRITICAL_TASK_TYPES = {
    ReviewTaskType.INJECTION_REVIEW.value,
    ReviewTaskType.PARSING_REVIEW.value,
    ReviewTaskType.REFERENCE_REVIEW.value,
}


def check_can_activate(session, document_id: str) -> Tuple[bool, List[str]]:
    """Return (can_activate, blocking_reasons).

    Caller raises HTTP 409 with reasons when can_activate is False.
    """
    doc = session.execute(
        select(DocumentRow).where(DocumentRow.document_id == document_id)
    ).scalars().first()

    if doc is None:
        return False, [f"Document {document_id} not found"]

    if doc.processing_status not in (
        ProcessingStatus.PARSED.value,
        ProcessingStatus.REVIEW_REQUIRED.value,
    ):
        return False, [
            f"Document must be PARSED before activation (current: {doc.processing_status})"
        ]

    pending = session.execute(
        select(ReviewTaskRow).where(
            ReviewTaskRow.document_id == document_id,
            ReviewTaskRow.task_type.in_(list(_CRITICAL_TASK_TYPES)),
            ReviewTaskRow.status == ReviewStatus.PENDING.value,
        )
    ).scalars().all()

    if pending:
        reasons = [
            f"Pending {row.task_type} review (task_id={row.task_id})"
            for row in pending
        ]
        return False, reasons

    return True, []
