"""Step 2 — Upload, quarantine & file registration.

Every uploaded file is untrusted: it is hashed (SHA-256, dedup), type/size checked,
written to local storage, and registered as a DocumentRow in QUARANTINED / PENDING
state. Nothing is parsed or indexed until an employee approves it — a quarantined
doc can never leak into retrieval.

File-type allowlist: pdf, docx (txt allowed for demo/offline tests). Size limit from
settings.max_upload_mb.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import select

from infra.db_models import DocumentRow
from packages.common.config import get_settings
from packages.common.ids import new_id
from packages.contracts.enums import ApprovalStatus, DocumentType, ProcessingStatus

# Allowlisted extensions -> True. .txt supported so offline/demo ingestion works.
_ALLOWED_EXT = {".pdf", ".docx", ".txt"}


class UploadError(ValueError):
    """Raised when a file is rejected (bad type / too large)."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ext(filename: str) -> str:
    return os.path.splitext(filename or "")[1].lower()


def validate_file(filename: str, data: bytes) -> None:
    ext = _ext(filename)
    if ext not in _ALLOWED_EXT:
        raise UploadError(f"File type '{ext}' not allowed (pdf/docx only).")
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise UploadError(f"File too large ({len(data)} bytes > {max_bytes}).")
    if not data:
        raise UploadError("Empty file.")


def find_by_hash(session, file_hash: str) -> Optional[DocumentRow]:
    return session.execute(
        select(DocumentRow).where(DocumentRow.file_hash == file_hash)
    ).scalars().first()


def store_file(document_id: str, filename: str, data: bytes) -> str:
    """Write bytes to file_storage_dir/<document_id><ext>; return the path."""
    storage = get_settings().file_storage_dir
    os.makedirs(storage, exist_ok=True)
    ext = _ext(filename) or ".bin"
    path = os.path.join(storage, f"{document_id}{ext}")
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def _coerce_type(doc_type: str) -> str:
    try:
        return DocumentType(doc_type).value
    except ValueError:
        return DocumentType.REGULATION.value


def register_upload(
    session,
    file_bytes: bytes,
    filename: str,
    doc_type: str,
    uploaded_by: Optional[str],
) -> Tuple[DocumentRow, bool]:
    """Validate, dedup-by-hash, store and insert a DocumentRow.

    Returns (row, is_new). If a document with the same hash exists, that row is
    returned with is_new=False (no duplicate file written).
    """
    validate_file(filename, file_bytes)
    file_hash = sha256_hex(file_bytes)

    existing = find_by_hash(session, file_hash)
    if existing is not None:
        return existing, False

    document_id = new_id("doc")
    path = store_file(document_id, filename, file_bytes)
    row = DocumentRow(
        document_id=document_id,
        filename=filename,
        type=_coerce_type(doc_type),
        document_number=None,
        file_hash=file_hash,
        file_path=path,
        processing_status=ProcessingStatus.QUARANTINED.value,
        approval_status=ApprovalStatus.PENDING.value,
        injection_suspected=False,
        uploaded_by=uploaded_by,
        created_at=datetime.utcnow(),
    )
    session.add(row)
    session.flush()
    return row, True
