"""Batch Document Review (Mode spec §8).

One file = one INDEPENDENT Review Run; the batch only shares assessment_date,
knowledge snapshot, versions and queue config. Files are never concatenated
into one prompt and report A is never evidence for report B — each run only
ever sees its own text (create_review_run takes a single text).

Partial failure is contained per item (§12.3); retry re-runs FAILED items only
unless the user explicitly asks for a full re-run, which creates a NEW batch
with the LATEST approved snapshot (§8.3).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import List, Optional

from fastapi import HTTPException

from infra.db_models import BatchReviewItemRow, BatchReviewRow, ConversationRow
from infra.postgres import init_db, session_scope
from packages.common.config import get_settings
from packages.common.ids import new_id

from backend.app.review import service as review_service
from backend.app.review.domain import BatchItemStatus

_PROBLEM_STATUSES = ("OUTDATED_REFERENCE", "NON_COMPLIANT", "MISSING_EVIDENCE")


def _workers() -> int:
    # ponytail: bounded worker pool, default 1 (SQLite-safe sequential queue);
    # raise BATCH_WORKERS when running on Postgres if throughput matters.
    return max(1, int(getattr(get_settings(), "batch_workers", 1) or 1))


def _ensure_db() -> None:
    try:
        init_db()
    except Exception:
        pass


def _run_item(owner_id: str, batch_id: str, item_id: str,
              assessment_date: date, snapshot) -> None:
    """Process ONE item — its own run, its own failure domain."""
    with session_scope() as ses:
        item = ses.query(BatchReviewItemRow).filter_by(id=item_id).one_or_none()
        if item is None:
            return
        item.status = BatchItemStatus.PROCESSING.value
        filename, text = item.filename, item.target_text or ""
    try:
        result = review_service.create_review_run(
            owner_id=owner_id, filename=filename, text=text,
            assessment_date=assessment_date, batch_review_id=batch_id,
            snapshot=snapshot,
        )
        with session_scope() as ses:
            item = ses.query(BatchReviewItemRow).filter_by(id=item_id).one()
            item.review_run_id = result["review_run_id"]
            item.status = BatchItemStatus.COMPLETED.value
            item.error = None
    except Exception as e:
        detail = getattr(e, "detail", None)
        with session_scope() as ses:
            item = ses.query(BatchReviewItemRow).filter_by(id=item_id).one()
            item.status = BatchItemStatus.FAILED.value
            item.error = str(detail or e)


def _aggregate(owner_id: str, batch_id: str) -> None:
    """Batch report = sum of VERIFIED item results (§8.3) — nothing else."""
    with session_scope() as ses:
        items = ses.query(BatchReviewItemRow).filter_by(batch_id=batch_id).all()
        runs = []
        for it in items:
            if it.review_run_id and it.status == BatchItemStatus.COMPLETED.value:
                row = ses.query(review_service.ReviewRunRow).filter_by(
                    run_id=it.review_run_id).one_or_none()
                if row is not None and row.report:
                    runs.append((it.filename, row.report))

        summary: dict = {"total_claims": 0}
        groups: dict = {}
        for filename, report in runs:
            for k, v in (report.get("summary") or {}).items():
                summary[k] = summary.get(k, 0) + v
            for a in report.get("assessments", []):
                if a.get("status") not in _PROBLEM_STATUSES:
                    continue
                ev = (a.get("valid_evidence") or a.get("excluded_evidence") or [{}])[0]
                prov = ev.get("provision_id")
                facts = a.get("structured_facts") or {}
                shared_value = ",".join(
                    str(x) for fc in ("money_vnd", "percents", "deadline_days")
                    for x in (facts.get(fc) or []))
                key = (a["status"], prov or shared_value or a.get("source_text", "")[:40])
                g = groups.setdefault(key, {
                    "finding_type": a["status"], "regulatory_provision_id": prov,
                    "shared_value": shared_value or None,
                    "affected_document_ids": []})
                if filename not in g["affected_document_ids"]:
                    g["affected_document_ids"].append(filename)

        recurring = [
            {**g, "occurrence_count": len(g["affected_document_ids"])}
            for g in groups.values() if len(g["affected_document_ids"]) >= 2
        ]
        batch = ses.query(BatchReviewRow).filter_by(batch_id=batch_id).one()
        batch.summary = summary
        batch.recurring_issues = sorted(
            recurring, key=lambda g: -g["occurrence_count"])


def create_batch_review(
    owner_id: str,
    files: List[dict],  # [{"filename": ..., "text": ...}]
    assessment_date: Optional[date] = None,
    conversation_id: Optional[str] = None,
) -> dict:
    _ensure_db()
    if not files:
        raise HTTPException(status_code=422, detail="batch cần ít nhất 1 file")
    assessment_date = assessment_date or date.today()
    batch_id = new_id("br")
    # Freeze ONE shared snapshot/config for the whole batch (§8.2)
    snapshot = review_service.compute_snapshot(assessment_date)

    item_ids = []
    with session_scope() as ses:
        ses.add(BatchReviewRow(
            batch_id=batch_id, owner_id=owner_id, conversation_id=conversation_id,
            assessment_date=assessment_date, knowledge_snapshot_id=snapshot[0]))
        for f in files:
            item_id = new_id("bri")
            item_ids.append(item_id)
            # strip NUL (0x00): PostgreSQL text không lưu được — file nhị phân/PDF
            # đọc nhầm sẽ làm INSERT crash 500 (mất CORS). File nhị phân còn lại sẽ
            # bị create_review_run bắt và đánh item FAILED, không làm sập cả batch.
            ses.add(BatchReviewItemRow(
                id=item_id, batch_id=batch_id, filename=f.get("filename", item_id),
                target_text=(f.get("text") or "").replace("\x00", ""),
                status=BatchItemStatus.QUEUED.value))
        if conversation_id:
            conv = ses.query(ConversationRow).filter_by(
                id=conversation_id, owner_id=owner_id).one_or_none()
            if conv is not None:
                conv.active_batch_review_id = batch_id

    with ThreadPoolExecutor(max_workers=_workers()) as pool:
        list(pool.map(
            lambda iid: _run_item(owner_id, batch_id, iid, assessment_date, snapshot),
            item_ids))
    _aggregate(owner_id, batch_id)
    return get_batch_review(owner_id, batch_id)


def _batch_or_404(ses, owner_id: str, batch_id: str) -> BatchReviewRow:
    row = ses.query(BatchReviewRow).filter_by(batch_id=batch_id).one_or_none()
    if row is None or row.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="batch review not found")
    return row


def get_batch_review(owner_id: str, batch_id: str) -> dict:
    _ensure_db()
    with session_scope() as ses:
        batch = _batch_or_404(ses, owner_id, batch_id)
        items = (ses.query(BatchReviewItemRow).filter_by(batch_id=batch_id)
                 .order_by(BatchReviewItemRow.created_at.asc()).all())
        statuses = [i.status for i in items]
        return {
            "batch_review_id": batch.batch_id,
            "assessment_date": batch.assessment_date.isoformat(),
            "knowledge_snapshot_id": batch.knowledge_snapshot_id,
            "total_documents": len(items),
            "completed_documents": statuses.count("COMPLETED"),
            "failed_documents": statuses.count("FAILED"),
            "summary": batch.summary or {},
            "recurring_issues": batch.recurring_issues or [],
            "items": [{
                "item_id": i.id, "filename": i.filename, "status": i.status,
                "review_run_id": i.review_run_id, "error": i.error,
            } for i in items],
        }


def retry_failed(owner_id: str, batch_id: str,
                 item_id: Optional[str] = None) -> dict:
    """Re-run FAILED items only (§15.2 batch retry correctness)."""
    _ensure_db()
    with session_scope() as ses:
        batch = _batch_or_404(ses, owner_id, batch_id)
        assessment_date = batch.assessment_date
        snapshot_id = batch.knowledge_snapshot_id
        q = ses.query(BatchReviewItemRow).filter_by(
            batch_id=batch_id, status=BatchItemStatus.FAILED.value)
        if item_id:
            q = q.filter_by(id=item_id)
        failed_ids = [i.id for i in q.all()]
    # keep the batch's frozen snapshot id; version list is recomputed only for
    # the run row (the batch identity does not change on retry)
    snapshot = (snapshot_id, review_service.compute_snapshot(assessment_date)[1])
    for iid in failed_ids:
        _run_item(owner_id, batch_id, iid, assessment_date, snapshot)
    _aggregate(owner_id, batch_id)
    return get_batch_review(owner_id, batch_id)


def rerun_full(owner_id: str, batch_id: str) -> dict:
    """Re-run entire batch with the LATEST snapshot -> NEW batch (§8.3)."""
    _ensure_db()
    with session_scope() as ses:
        batch = _batch_or_404(ses, owner_id, batch_id)
        conversation_id = batch.conversation_id
        assessment_date = batch.assessment_date
        items = ses.query(BatchReviewItemRow).filter_by(batch_id=batch_id).all()
        files = [{"filename": i.filename, "text": i.target_text or ""} for i in items]
    return create_batch_review(owner_id, files, assessment_date, conversation_id)
