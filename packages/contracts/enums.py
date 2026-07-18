"""Enumerations shared across the whole system (FROZEN CONTRACT).

Every status string used in the DB, graph, API and UI must come from here so the
three tracks never drift on spelling. Values are the wire format (stored as-is).
"""
from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    USER = "USER"
    EMPLOYEE = "EMPLOYEE"                      # deprecated alias of COMPLIANCE_OFFICER (Final spec §6.1)
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"  # persona duy nhất (Final spec §1.2)
    SYSTEM_ADMIN = "SYSTEM_ADMIN"              # role kỹ thuật, không phải persona


class DocumentType(str, Enum):
    REGULATION = "REGULATION"          # văn bản quy định gốc
    AMENDMENT = "AMENDMENT"            # văn bản sửa đổi
    INTERNAL_POLICY = "INTERNAL_POLICY"  # policy/quy trình nội bộ mô phỏng


class ProcessingStatus(str, Enum):
    QUARANTINED = "QUARANTINED"
    PROCESSING = "PROCESSING"
    PARSED = "PARSED"
    INDEXED = "INDEXED"
    FAILED = "FAILED"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class ReviewTaskType(str, Enum):
    PARSING_REVIEW = "PARSING_REVIEW"
    CHANGE_EVENT_REVIEW = "CHANGE_EVENT_REVIEW"
    REFERENCE_REVIEW = "REFERENCE_REVIEW"
    CONFLICT_REVIEW = "CONFLICT_REVIEW"
    IMPACT_REVIEW = "IMPACT_REVIEW"
    INJECTION_REVIEW = "INJECTION_REVIEW"


class ReviewDecision(str, Enum):
    APPROVE = "APPROVE"
    EDIT = "EDIT"
    REJECT = "REJECT"


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AmendmentOperation(str, Enum):
    REPLACE_TEXT = "REPLACE_TEXT"
    INSERT_TEXT = "INSERT_TEXT"
    DELETE_TEXT = "DELETE_TEXT"
    REPEAL_PROVISION = "REPEAL_PROVISION"


class Modality(str, Enum):
    OBLIGATION = "OBLIGATION"
    PROHIBITION = "PROHIBITION"
    PERMISSION = "PERMISSION"


class QueryIntent(str, Enum):
    CURRENT_QA = "CURRENT_QA"
    POINT_IN_TIME_QA = "POINT_IN_TIME_QA"
    VERSION_HISTORY = "VERSION_HISTORY"
    CROSS_REFERENCE_QA = "CROSS_REFERENCE_QA"
    CHANGE_EXPLANATION = "CHANGE_EXPLANATION"
    CONFLICT_CHECK = "CONFLICT_CHECK"
    IMPACT_CHECK = "IMPACT_CHECK"


class AnswerStatus(str, Enum):
    SOURCE_GROUNDED = "SOURCE_GROUNDED"
    DETERMINISTIC_CHECKS_PASSED = "DETERMINISTIC_CHECKS_PASSED"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ExclusionReason(str, Enum):
    NOT_VALID_AT_QUERY_DATE = "NOT_VALID_AT_QUERY_DATE"
    SUPERSEDED = "SUPERSEDED"
    NOT_APPROVED = "NOT_APPROVED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class ConflictReason(str, Enum):
    THRESHOLD_MISMATCH = "THRESHOLD_MISMATCH"
    MODALITY_CONFLICT = "MODALITY_CONFLICT"
    DEADLINE_MISMATCH = "DEADLINE_MISMATCH"
    SCOPE_OVERLAP_VALUE_DIFF = "SCOPE_OVERLAP_VALUE_DIFF"
