"""Facade the API calls (the ONLY ingestion module routes import).

Exact signatures (routes depend on these):
  - handle_upload(file_bytes, filename, doc_type, uploaded_by) -> UploadResponse
  - list_documents() -> list
  - activate_document(document_id, decided_by) -> dict
  - list_review_tasks(status) -> list[ReviewTask]
  - decide_review_task(task_id, decision, edited_payload, decided_by) -> ReviewTask

This module wires steps 2-12 together and is the single place that opens DB sessions.
On upload it runs the full offline pipeline (scan -> extract -> parse -> chunk-prep ->
provisions/versions PENDING -> amendments -> change events + review tasks), but indexes
NOTHING until an employee activates/approves (INVARIANT).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from infra.db_models import (
    ChangeEventRow,
    DocumentRow,
    ProvisionRow,
    ProvisionVersionRow,
    ReviewTaskRow,
)
from infra.postgres import init_db, session_scope
from packages.common.ids import provision_lookup_key
from packages.contracts.api_schemas import UploadResponse
from packages.contracts.enums import (
    ApprovalStatus,
    DocumentType,
    ProcessingStatus,
    ReviewDecision,
    ReviewStatus,
    ReviewTaskType,
)
from packages.contracts.models import Document, ReviewTask

from ingestion import activate as activate_mod
from ingestion import change_event as change_event_mod
from ingestion import injection_scan, legal_extract, review_inbox, upload
from ingestion.pdf_extract import blocks_to_text, extract_text_blocks
from ingestion.structure_parser import parse_structure

_DEFAULT_VALID_FROM = date(2026, 1, 1)


def _ensure_db() -> None:
    init_db()


# --------------------------------------------------------------------------- #
# Extraction: bytes -> layout blocks (offline-safe)
# --------------------------------------------------------------------------- #
def _blocks_from_bytes(file_bytes: bytes, filename: str, file_path: Optional[str]):
    """Decode uploaded bytes into layout blocks.

    PDFs/DOCX are read from the stored file (PyMuPDF/python-docx need a path); .txt
    and unknown types are decoded as UTF-8 text (offline/test path).
    """
    lower = (filename or "").lower()
    if lower.endswith((".pdf", ".docx")) and file_path:
        try:
            return extract_text_blocks(file_path)
        except Exception:
            pass  # fall through to text decode
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = file_bytes.decode("utf-8", errors="ignore")
    return extract_text_blocks(text, is_text=True)


# --------------------------------------------------------------------------- #
# Base-document pipeline: parse -> persist provisions + PENDING versions
# --------------------------------------------------------------------------- #
def _persist_provisions(session, doc: DocumentRow, provisions: List[Dict[str, Any]]) -> int:
    from packages.common.ids import new_provision_id, new_version_id
    count = 0
    for p in provisions:
        content = (p.get("content") or "").strip()
        if not content:
            continue
        provision_id = new_provision_id()
        version_id = new_version_id()
        lookup_key = provision_lookup_key(
            doc.document_number, p.get("article"), p.get("clause"), p.get("point"),
        )
        obligation = legal_extract.extract_obligation(content, source_provision=provision_id)
        scope = legal_extract.extract_scope(content)
        session.add(ProvisionRow(
            provision_id=provision_id,
            document_id=doc.document_id,
            lookup_key=lookup_key,
            heading_path=p.get("heading_path") or [],
            article=p.get("article"),
            clause=p.get("clause"),
            point=p.get("point"),
        ))
        session.add(ProvisionVersionRow(
            version_id=version_id,
            provision_id=provision_id,
            document_id=doc.document_id,
            content=content,
            valid_from=doc_valid_from(doc),
            valid_to_exclusive=None,
            approval_status=ApprovalStatus.PENDING.value,
            page=p.get("page"),
            obligation=obligation.model_dump() if obligation else None,
            scope=scope.model_dump() if scope else None,
            created_at=datetime.utcnow(),
        ))
        count += 1
    session.flush()
    return count


def doc_valid_from(doc: DocumentRow) -> date:
    md = doc.doc_metadata or {}
    vf = md.get("valid_from")
    if vf:
        try:
            return date.fromisoformat(vf)
        except (ValueError, TypeError):
            pass
    return _DEFAULT_VALID_FROM


def _run_amendment_pipeline(session, doc: DocumentRow, full_text: str) -> List[Dict[str, Any]]:
    """Extract amendments and create change events + review tasks. Returns summaries."""
    amendments = legal_extract.extract_amendments(full_text, source_page=1)
    results = []
    # An amendment doc targets the ORIGINAL regulation; its document_number is
    # usually referenced in the amendment. We resolve against ALL known provisions
    # by trying each document_number in the store (exact locator match).
    target_doc_numbers = _known_document_numbers(session)
    for amendment in amendments:
        resolved = None
        # Try resolving against every known base document number until one matches.
        for docno in target_doc_numbers + [None]:
            res = change_event_mod.create_change_event(
                session, amendment, doc.document_id, docno,
            )
            if res.get("resolved"):
                resolved = res
                break
            # keep the last (unresolved) result to surface a REFERENCE_REVIEW
            resolved = res
        results.append(resolved)
    return results


def _known_document_numbers(session) -> List[Optional[str]]:
    rows = session.execute(
        select(DocumentRow.document_number).where(DocumentRow.document_number.isnot(None))
    ).all()
    seen: List[Optional[str]] = []
    for (dn,) in rows:
        if dn and dn not in seen:
            seen.append(dn)
    return seen


# --------------------------------------------------------------------------- #
# Public facade
# --------------------------------------------------------------------------- #
def handle_upload(file_bytes: bytes, filename: str, doc_type: str, uploaded_by: str) -> UploadResponse:
    """Steps 2-11: quarantine, scan, extract, parse, extract legal info, queue reviews."""
    _ensure_db()
    with session_scope() as session:
        row, is_new = upload.register_upload(session, file_bytes, filename, doc_type, uploaded_by)
        if not is_new:
            # duplicate — return the existing registration untouched
            return UploadResponse(
                document_id=row.document_id,
                filename=row.filename,
                file_hash=row.file_hash,
                processing_status=row.processing_status,
                approval_status=row.approval_status,
                injection_suspected=row.injection_suspected,
            )

        # Step 4: extract blocks; Step 3: injection scan on the extracted text.
        blocks = _blocks_from_bytes(file_bytes, filename, row.file_path)
        full_text = blocks_to_text(blocks)

        hits = injection_scan.scan_text(full_text)
        if hits:
            row.injection_suspected = True
            review_inbox.create_task(
                session,
                ReviewTaskType.INJECTION_REVIEW,
                document_id=row.document_id,
                source_ref=row.filename,
                extracted={"phrases": hits},
                confidence=0.9,
            )

        # Step 7 (metadata): fill document_number / valid_from for the doc.
        metadata = legal_extract.extract_document_metadata(full_text)
        try:
            metadata = legal_extract.enhance_metadata_with_llm(full_text, metadata)
        except Exception:
            pass
        if metadata.document_number:
            row.document_number = metadata.document_number
        md_dump = metadata.model_dump(mode="json")
        row.doc_metadata = md_dump

        # Step 5-8: structure parse + persist provisions/versions (PENDING).
        provisions = parse_structure(blocks)
        provision_count = _persist_provisions(session, row, provisions)

        # Step 9-10: amendment detection -> change events + review tasks.
        change_results = []
        is_amendment = row.type == DocumentType.AMENDMENT.value or "thay" in full_text.lower()
        if is_amendment:
            change_results = _run_amendment_pipeline(session, row, full_text)

        # Status: PARSED (awaiting employee approval). Nothing indexed yet.
        row.processing_status = ProcessingStatus.PARSED.value

        # A base document with provisions gets a PARSING_REVIEW so an employee can
        # verify boundaries before activation.
        if provision_count and not change_results:
            review_inbox.create_task(
                session,
                ReviewTaskType.PARSING_REVIEW,
                document_id=row.document_id,
                source_ref=row.document_number or row.filename,
                extracted={"provision_count": provision_count},
                confidence=0.8,
            )

        return UploadResponse(
            document_id=row.document_id,
            filename=row.filename,
            file_hash=row.file_hash,
            processing_status=row.processing_status,
            approval_status=row.approval_status,
            injection_suspected=row.injection_suspected,
        )


def list_documents() -> List[Document]:
    _ensure_db()
    with session_scope() as session:
        rows = session.execute(
            select(DocumentRow).order_by(DocumentRow.created_at.desc())
        ).scalars().all()
        out: List[Document] = []
        for r in rows:
            out.append(Document(
                document_id=r.document_id,
                filename=r.filename,
                type=DocumentType(r.type),
                document_number=r.document_number,
                file_hash=r.file_hash,
                file_path=r.file_path,
                processing_status=ProcessingStatus(r.processing_status),
                approval_status=ApprovalStatus(r.approval_status),
                injection_suspected=r.injection_suspected,
                uploaded_by=r.uploaded_by,
                created_at=r.created_at,
            ))
        return out


def activate_document(document_id: str, decided_by: str) -> dict:
    """Approve + index a base document's provisions (step 12, path A)."""
    _ensure_db()
    with session_scope() as session:
        result = activate_mod.activate_base_document(session, document_id)
        result["decided_by"] = decided_by
        return result


def list_review_tasks(status: Optional[str] = None) -> List[ReviewTask]:
    _ensure_db()
    with session_scope() as session:
        return review_inbox.list_tasks(session, status)


def decide_review_task(
    task_id: str,
    decision: ReviewDecision,
    edited_payload: Optional[dict],
    decided_by: str,
) -> ReviewTask:
    """Record a decision and apply its side effect if it's a change-event approval."""
    _ensure_db()
    if isinstance(decision, str):
        decision = ReviewDecision(decision)
    with session_scope() as session:
        row = review_inbox.get_task(session, task_id)
        if row is None:
            raise ValueError(f"Review task {task_id} not found.")

        review_inbox.mark_decided(session, row, decision, decided_by, edited_payload)

        # Side effect: an APPROVED/EDITED CHANGE_EVENT_REVIEW activates the patch.
        if (row.task_type == ReviewTaskType.CHANGE_EVENT_REVIEW.value
                and decision != ReviewDecision.REJECT):
            change_event_id = (row.extracted or {}).get("change_event_id")
            if change_event_id:
                activate_mod.activate_change_event(session, change_event_id, edited_payload)

        return review_inbox._row_to_model(row)
