"""Single Document Review — immutable Review Run (Mode spec §5, §7).

CREATE -> freeze assessment_date + knowledge snapshot + parser/prompt/schema
versions -> extract claims -> retrieve APPROVED evidence -> assess -> verify
citation allowlist -> LOCK. The locked report is never updated in place:
re-running ALWAYS creates a new run (§5.3).

The initial evaluation is an ISOLATED task: its only inputs are the target
text, the approved store at assessment_date and the frozen versions — chat
history is not an input anywhere in this module (§3.2, §4.1).
"""
from __future__ import annotations

import hashlib
from datetime import date
from typing import Optional, Tuple

from fastapi import HTTPException

from infra.db_models import ConversationRow, ProvisionVersionRow, ReviewRunRow
from infra.postgres import init_db, session_scope
from packages.common.ids import new_id

from backend.app.core.prompt_loader import load_prompt, schema_version
from backend.app.review.domain import ReviewRunState
from backend.app.workflows.compliance_checks.service import run_compliance_check

PARSER_VERSION = "review-parser-1.0"


def _versions() -> dict:
    return {
        "parser": PARSER_VERSION,
        "prompt": load_prompt("review_evaluator.system")["version"],
        "schema": schema_version("claim_assessment"),
    }


def _ensure_db() -> None:
    try:
        init_db()
    except Exception:
        pass


def compute_snapshot(assessment_date: date) -> Tuple[str, dict]:
    """Freeze the approved-corpus identity at run creation (§4.3).

    snapshot = the set of APPROVED provision versions visible to retrieval.
    Activating new sources later changes the snapshot id of FUTURE runs only.
    """
    _ensure_db()
    version_ids: list = []
    try:
        with session_scope() as ses:
            rows = (ses.query(ProvisionVersionRow.version_id)
                    .filter(ProvisionVersionRow.approval_status == "APPROVED")
                    .order_by(ProvisionVersionRow.version_id).all())
            version_ids = [r[0] for r in rows]
    except Exception:
        pass
    digest = hashlib.sha1("|".join(version_ids).encode()).hexdigest()[:10]
    snapshot_id = f"KB-{assessment_date.isoformat()}-{digest}"
    return snapshot_id, {"version_ids": version_ids, "count": len(version_ids)}


def create_review_run(
    owner_id: str,
    filename: str,
    text: str,
    assessment_date: Optional[date] = None,
    conversation_id: Optional[str] = None,
    batch_review_id: Optional[str] = None,
    snapshot: Optional[Tuple[str, dict]] = None,
) -> dict:
    """One file -> one locked Review Run. Raises on empty input (NEEDS_INPUT)."""
    _ensure_db()
    if not (text or "").strip():
        raise HTTPException(status_code=422, detail={"error": {
            "code": "NEEDS_INPUT", "message": "Review target text rỗng."}})
    # Chặn file nhị phân (PDF/DOCX/ảnh) bị đọc nhầm bằng readAsText: nội dung chứa
    # NUL (0x00) + rác. PostgreSQL text KHÔNG lưu được NUL → nếu để nguyên sẽ INSERT
    # lỗi DataError → 500 chưa xử lý → response mất header CORS (trông như lỗi CORS).
    # Trả 422 rõ ràng (có CORS header) thay vì để crash.
    if "\x00" in text or text.lstrip()[:5] == "%PDF-":
        raise HTTPException(status_code=422, detail={"error": {
            "code": "NEEDS_TEXT_EXTRACTION",
            "message": "Tệp là PDF/nhị phân chưa được trích xuất thành text. "
                       "Hãy dán nội dung dạng văn bản, hoặc tải tệp .txt/.md."}})
    assessment_date = assessment_date or date.today()
    run_id = new_id("rr")
    target_id = new_id("rvt")
    snapshot_id, snap = snapshot or compute_snapshot(assessment_date)
    versions = _versions()
    checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()

    try:
        # CREATED -> ... -> ASSESSED (state walk is synchronous; the row is
        # written once with the final state + full audit metadata)
        report = run_compliance_check(text, review_date=assessment_date,
                                      target_document_id=target_id)
        # VERIFY (§10.2): citation allowlist — every cited version must belong
        # to the frozen snapshot; anything else is dropped, never invented.
        allow = set(snap["version_ids"])
        assessments = []
        for a in report.assessments:
            dumped = a.model_dump(mode="json")
            if allow:
                dumped["valid_evidence"] = [
                    e for e in dumped["valid_evidence"] if e["version_id"] in allow]
            dumped["requires_human_review"] = a.status.value in (
                "NON_COMPLIANT", "OUTDATED_REFERENCE", "AMBIGUOUS", "NEEDS_HUMAN_REVIEW")
            assessments.append(dumped)
        state = ReviewRunState.READY if assessments else ReviewRunState.INSUFFICIENT_EVIDENCE
        locked_report = {
            "review_run_id": run_id,
            "conversation_id": conversation_id,
            "assessment_date": assessment_date.isoformat(),
            "knowledge_snapshot_id": snapshot_id,
            "target_document": {"id": target_id, "filename": filename,
                                "trust_class": "REVIEW_TARGET"},
            "versions": versions,
            "summary": report.summary,
            "assessments": assessments,
        }
        error = None
    except HTTPException:
        raise
    except Exception as e:  # per-file failure must stay contained (batch §12.3)
        state, locked_report, error = ReviewRunState.FAILED, None, str(e)

    with session_scope() as ses:
        ses.add(ReviewRunRow(
            run_id=run_id, owner_id=owner_id, conversation_id=conversation_id,
            batch_review_id=batch_review_id, state=state.value,
            assessment_date=assessment_date, knowledge_snapshot_id=snapshot_id,
            snapshot=snap, target_document_id=target_id, target_filename=filename,
            target_checksum=checksum, target_text=text,
            versions=versions, report=locked_report, error=error,
        ))
        if conversation_id:
            conv = ses.query(ConversationRow).filter_by(
                id=conversation_id, owner_id=owner_id).one_or_none()
            if conv is not None:
                conv.active_review_run_id = run_id

    if state == ReviewRunState.FAILED:
        raise HTTPException(status_code=500, detail={"error": {
            "code": "REVIEW_RUN_FAILED", "message": error, "review_run_id": run_id}})
    return {"review_run_id": run_id, "state": state.value,
            "knowledge_snapshot_id": snapshot_id, "report": locked_report}


def get_run_row(owner_id: str, run_id: str) -> ReviewRunRow:
    _ensure_db()
    with session_scope() as ses:
        row = ses.query(ReviewRunRow).filter_by(run_id=run_id).one_or_none()
        if row is None or row.owner_id != owner_id:
            raise HTTPException(status_code=404, detail="review run not found")
        ses.expunge(row)
    return row


def get_review_run(owner_id: str, run_id: str) -> dict:
    row = get_run_row(owner_id, run_id)
    return {"review_run_id": row.run_id, "state": row.state,
            "assessment_date": row.assessment_date.isoformat(),
            "knowledge_snapshot_id": row.knowledge_snapshot_id,
            "versions": row.versions, "report": row.report, "error": row.error}


def rerun(owner_id: str, run_id: str, assessment_date: Optional[date] = None) -> dict:
    """§5.3 — changed date/scope/snapshot => a NEW run; the old one is immutable."""
    old = get_run_row(owner_id, run_id)
    return create_review_run(
        owner_id=owner_id, filename=old.target_filename,
        text=old.target_text or "",
        assessment_date=assessment_date or old.assessment_date,
        conversation_id=old.conversation_id,
    )
