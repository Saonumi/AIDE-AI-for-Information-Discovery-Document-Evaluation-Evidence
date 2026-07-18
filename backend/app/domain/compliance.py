"""Final spec (VAIC2026_Final_Compliance_Knowledge_Review_Master_Spec) domain delta.

Trust model (§2) + Workflow B contracts (§6.3, §6.5, Phụ lục B.2/B.3).
Self-contained on purpose: the legacy frozen contract (packages/contracts) is the
live runtime; this file ADDS the Final-spec vocabulary without editing frozen files,
so the parallel refactor session never collides with us here.

Reused from the frozen contract: EvidenceItem / ExcludedEvidence / ReviewStatus —
a ClaimAssessment cites evidence in exactly the same shape the query pipeline emits.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from packages.contracts.models import EvidenceItem, ExcludedEvidence
from packages.contracts.enums import ReviewStatus


# --------------------------------------------------------------------------- #
# Trust model (Final spec §2)
# --------------------------------------------------------------------------- #
class TrustClass(str, Enum):
    AUTHORITY_SOURCE_CANDIDATE = "AUTHORITY_SOURCE_CANDIDATE"
    AUTHORITY_SOURCE = "AUTHORITY_SOURCE"
    INTERNAL_APPROVED = "INTERNAL_APPROVED"
    REVIEW_TARGET = "REVIEW_TARGET"
    UNVERIFIED = "UNVERIFIED"
    # Mode spec §4 — chat-scope classes; NONE of these is ever legal evidence.
    CONVERSATION_ATTACHMENT = "CONVERSATION_ATTACHMENT"
    USER_MESSAGE = "USER_MESSAGE"
    REVIEW_RESULT = "REVIEW_RESULT"


class UploadPurpose(str, Enum):
    ADD_REGULATORY_SOURCE = "ADD_REGULATORY_SOURCE"
    CHECK_DOCUMENT_COMPLIANCE = "CHECK_DOCUMENT_COMPLIANCE"


class ReviewTargetStatus(str, Enum):
    """State machine of a review target (Final spec §2.4) — separate from sources."""
    RECEIVED = "RECEIVED"
    QUARANTINED = "QUARANTINED"
    EXTRACTED = "EXTRACTED"
    CLAIMS_PARSED = "CLAIMS_PARSED"
    CHECKING = "CHECKING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    COMPLETED = "COMPLETED"
    NEEDS_CORRECTION = "NEEDS_CORRECTION"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class ComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
    OUTDATED_REFERENCE = "OUTDATED_REFERENCE"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    AMBIGUOUS = "AMBIGUOUS"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


# --------------------------------------------------------------------------- #
# Workflow B entities (Final spec §6.3)
# --------------------------------------------------------------------------- #
class StructuredFacts(BaseModel):
    """Deterministic facts mined from a claim — the ONLY basis for exact compare."""
    money_vnd: List[int] = Field(default_factory=list)
    percents: List[float] = Field(default_factory=list)
    deadline_days: List[int] = Field(default_factory=list)   # "chậm nhất ngày 10" -> 10
    dates: List[date] = Field(default_factory=list)
    doc_refs: List[str] = Field(default_factory=list)        # "22/2019/TT-NHNN"

    def has_comparable(self) -> bool:
        return bool(self.money_vnd or self.percents or self.deadline_days)


class ComplianceClaim(BaseModel):
    claim_id: str
    target_document_id: str
    section: Optional[str] = None          # "Điều 3" / heading the claim sits under
    text: str
    facts: StructuredFacts = Field(default_factory=StructuredFacts)
    source_page: Optional[int] = None


class ClaimAssessment(BaseModel):
    """Per-claim verdict (Phụ lục B.2). Evidence shapes reused from frozen contract."""
    claim_id: str
    source_text: str
    status: ComplianceStatus
    structured_facts: StructuredFacts = Field(default_factory=StructuredFacts)
    valid_evidence: List[EvidenceItem] = Field(default_factory=list)
    excluded_evidence: List[ExcludedEvidence] = Field(default_factory=list)
    findings: List[str] = Field(default_factory=list)   # deterministic compare notes
    explanation: str = ""
    recommendation: Optional[str] = None
    confidence: float = 0.0
    review_status: ReviewStatus = ReviewStatus.PENDING


class ReviewTargetDocument(BaseModel):
    document_id: str
    filename: str
    upload_purpose: UploadPurpose = UploadPurpose.CHECK_DOCUMENT_COMPLIANCE
    trust_class: TrustClass = TrustClass.REVIEW_TARGET
    status: ReviewTargetStatus = ReviewTargetStatus.RECEIVED
    review_date: Optional[date] = None
    uploaded_by: Optional[str] = None


class ComplianceReviewReport(BaseModel):
    """Report contract (Phụ lục B.3) — stable JSON the UI renders."""
    report_id: str
    target_document_id: str
    review_date: date
    summary: Dict[str, int] = Field(default_factory=dict)  # status value -> count
    assessments: List[ClaimAssessment] = Field(default_factory=list)
    status: ReviewTargetStatus = ReviewTargetStatus.REVIEW_REQUIRED


def is_legal_ground_truth(
    trust_class: TrustClass,
    approval_status: str,
    lifecycle_active: bool,
    valid_from: Optional[date],
    valid_to_exclusive: Optional[date],
    query_date: date,
) -> bool:
    """Final spec §2.2 — the single admission rule for legal evidence."""
    return (
        trust_class == TrustClass.AUTHORITY_SOURCE
        and approval_status == "APPROVED"
        and lifecycle_active
        and valid_from is not None
        and valid_from <= query_date
        and (valid_to_exclusive is None or query_date < valid_to_exclusive)
    )
