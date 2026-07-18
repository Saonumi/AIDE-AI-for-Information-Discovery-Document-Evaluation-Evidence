"""Review Run domain (Mode spec §5) — an immutable assessment execution."""
from __future__ import annotations

from enum import Enum


class ReviewRunState(str, Enum):
    CREATED = "CREATED"
    FILE_UPLOADED = "FILE_UPLOADED"
    TEXT_EXTRACTED = "TEXT_EXTRACTED"
    CLAIMS_EXTRACTED = "CLAIMS_EXTRACTED"
    EVIDENCE_RETRIEVED = "EVIDENCE_RETRIEVED"
    ASSESSED = "ASSESSED"
    VERIFIED = "VERIFIED"
    READY = "READY"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    # failure states
    NEEDS_INPUT = "NEEDS_INPUT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BatchItemStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BatchChatScope(str, Enum):
    ENTIRE_BATCH = "ENTIRE_BATCH"
    ONE_REPORT = "ONE_REPORT"
    SELECTED_FINDINGS = "SELECTED_FINDINGS"
