"""Activation gate — chặn activate khi còn critical review pending (HTTP 409)."""
from __future__ import annotations

from typing import List, Tuple

from sqlalchemy import select

from infra.db_models import DocumentRow, ReviewTaskRow
from packages.contracts.enums import ProcessingStatus, ReviewStatus, ReviewTaskType

_CRITICAL_TASK_TYPES = {
    ReviewTaskType.INJECTION_REVIEW.value,
    ReviewTaskType.REFERENCE_REVIEW.value,
}


class ReviewNotCompletedError(Exception):
    """Document cannot be activated while critical reviews are pending.

    Carries the stable error code (spec §8.1) and the blocking reasons so the API
    layer can return HTTP 409 without re-deriving them.
    """

    code = "REVIEW_NOT_COMPLETED"

    def __init__(self, reasons: List[str]) -> None:
        self.reasons = reasons
        super().__init__("Document cannot be activated while critical reviews are pending.")


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
        ProcessingStatus.QUARANTINED.value,
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


def ensure_can_activate(session, document_id: str) -> None:
    """Service-layer guard (spec §7.5): raise if the document has blocking reviews.

    Every activation path must call this — not just one route — so the gate can't
    be bypassed. Raises ReviewNotCompletedError (-> HTTP 409) when blocked.
    """
    # ponytail: a missing/wrong-status doc also lands here as 409; the downstream
    # activate still raises ValueError for genuinely absent docs, so the only path
    # that reaches activation is a real, review-clear document.
    can, reasons = check_can_activate(session, document_id)
    if not can:
        raise ReviewNotCompletedError(reasons)
