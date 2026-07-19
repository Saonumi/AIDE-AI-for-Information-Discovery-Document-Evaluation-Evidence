"""Domain models (FROZEN CONTRACT) — the shared vocabulary of the pipeline.

These Pydantic models are the interface between tracks:
  - Track A (ingestion) produces Document/Provision/ProvisionVersion/ChangeEvent/Chunk.
  - Track B (query) consumes them and produces EvidencePackage + Answer.
  - Track C (ui/eval) renders Answer + EvidencePackage and scores against ground truth.

Temporal model: half-open interval [valid_from, valid_to_exclusive). A version is
valid at date d iff valid_from <= d AND (valid_to_exclusive is None OR d < valid_to_exclusive).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from packages.contracts.enums import (
    AmendmentOperation,
    AnswerStatus,
    ApprovalStatus,
    ConflictReason,
    DocumentType,
    ExclusionReason,
    Modality,
    ProcessingStatus,
    QueryIntent,
    ReviewDecision,
    ReviewStatus,
    ReviewTaskType,
    Role,
)


# --------------------------------------------------------------------------- #
# Structured legal information (output of Legal Information Extraction, step 7)
# --------------------------------------------------------------------------- #
class Scope(BaseModel):
    """Scope fields used for conflict/impact filtering."""
    subject: Optional[str] = None
    product: Optional[str] = None
    customer_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    authority_level: Optional[str] = None
    applicable_condition: Optional[str] = None


class Obligation(BaseModel):
    subject: Optional[str] = None
    action: Optional[str] = None
    modality: Optional[Modality] = None
    condition: Optional[str] = None
    value: Optional[str] = None            # raw text, e.g. "500 triệu đồng"
    value_normalized: Optional[int] = None  # canonical VND (from vn_normalize) if numeric
    source_provision: Optional[str] = None  # provision_id
    confidence: float = 1.0


class CrossReference(BaseModel):
    source_provision: str          # provision_id
    target_locator: str            # e.g. "Khoản 3 Điều 12"
    target_provision: Optional[str] = None  # resolved provision_id (may be None until resolved)
    confidence: float = 1.0


class Amendment(BaseModel):
    operation: AmendmentOperation
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    target_locator: str            # e.g. "Khoản 2 Điều 7"
    valid_from: date
    source_page: Optional[int] = None
    confidence: float = 1.0


class DocumentMetadata(BaseModel):
    document_number: Optional[str] = None   # e.g. "QĐ-01/2026"
    issued_date: Optional[date] = None
    valid_from: Optional[date] = None
    valid_to_exclusive: Optional[date] = None
    authority: Optional[str] = None
    scope: Optional[Scope] = None


# --------------------------------------------------------------------------- #
# Core knowledge entities
# --------------------------------------------------------------------------- #
class Document(BaseModel):
    document_id: str
    filename: str
    type: DocumentType
    document_number: Optional[str] = None
    file_hash: str
    file_path: Optional[str] = None
    processing_status: ProcessingStatus = ProcessingStatus.QUARANTINED
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    injection_suspected: bool = False
    uploaded_by: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Optional[DocumentMetadata] = None


class Provision(BaseModel):
    """Stable identity of a clause, independent of its wording/version."""
    provision_id: str
    document_id: str
    heading_path: List[str] = Field(default_factory=list)  # ["Điều 7", "Khoản 2"]
    article: Optional[str] = None
    clause: Optional[str] = None
    point: Optional[str] = None


class ProvisionVersion(BaseModel):
    version_id: str
    provision_id: str
    document_id: str
    content: str
    valid_from: date
    valid_to_exclusive: Optional[date] = None   # None == open-ended (∞)
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    page: Optional[int] = None
    obligation: Optional[Obligation] = None
    scope: Optional[Scope] = None
    created_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None

    def is_valid_at(self, d: date) -> bool:
        """Half-open interval check — the single source of temporal truth."""
        if self.approval_status != ApprovalStatus.APPROVED:
            return False
        if self.valid_from > d:
            return False
        if self.valid_to_exclusive is not None and d >= self.valid_to_exclusive:
            return False
        return True


class ChangeEvent(BaseModel):
    """Reified amendment event (not just a SUPERSEDES edge)."""
    change_event_id: str
    amending_document_id: str
    target_provision_id: str
    operation: AmendmentOperation
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    before_version_id: Optional[str] = None
    after_version_id: Optional[str] = None
    valid_from: date
    source_page: Optional[int] = None
    review_status: ReviewStatus = ReviewStatus.PENDING


class InternalArtifact(BaseModel):
    """Internal policy/process that may become stale when a regulation changes."""
    artifact_id: str
    document_id: str
    title: str
    aligned_to_version_id: Optional[str] = None  # ALIGNED_TO edge target
    obligation: Optional[Obligation] = None
    page: Optional[int] = None


class Chunk(BaseModel):
    """Retrieval unit — a clause/point, not an arbitrary 500-token window."""
    chunk_id: str
    provision_id: str
    version_id: str
    document_id: str
    heading_path: List[str] = Field(default_factory=list)
    content: str
    page: Optional[int] = None
    valid_from: date
    valid_to_exclusive: Optional[date] = None
    approval_status: ApprovalStatus = ApprovalStatus.PENDING

    def embedding_text(self) -> str:
        """Heading path is prepended so retrieval keeps structural context."""
        prefix = " > ".join(self.heading_path)
        return f"{prefix}\n{self.content}" if prefix else self.content


# --------------------------------------------------------------------------- #
# Evidence & answer (output of the query pipeline)
# --------------------------------------------------------------------------- #
class EvidenceItem(BaseModel):
    source_id: str                 # citation id used by the LLM (== version_id)
    provision_id: str
    version_id: str
    document_number: Optional[str] = None
    heading_path: List[str] = Field(default_factory=list)
    content: str
    page: Optional[int] = None
    valid_from: date
    valid_to_exclusive: Optional[date] = None
    score: float = 0.0


class ExcludedEvidence(BaseModel):
    version_id: str
    provision_id: Optional[str] = None
    heading_path: List[str] = Field(default_factory=list)
    reason: ExclusionReason


class ReferencePath(BaseModel):
    from_provision: str
    to_provision: str
    to_locator: str
    hops: int = 1


class ChangePath(BaseModel):
    provision_id: str
    before_version_id: Optional[str] = None
    after_version_id: Optional[str] = None
    change_event_id: Optional[str] = None
    operation: Optional[AmendmentOperation] = None


class ConflictCandidate(BaseModel):
    provision_a: str
    provision_b: str
    reason: ConflictReason
    value_a: Optional[str] = None
    value_b: Optional[str] = None
    temporal_overlap: bool = True
    scope_overlap: bool = True
    human_review: ReviewStatus = ReviewStatus.PENDING


class ImpactCandidate(BaseModel):
    artifact_id: str
    artifact_title: str
    reason: ConflictReason
    regulation_value: Optional[str] = None
    internal_policy_value: Optional[str] = None
    status: ReviewStatus = ReviewStatus.PENDING


class EvidencePackage(BaseModel):
    """The deterministically-assembled context handed to the LLM.

    The LLM may ONLY use valid_evidence. excluded_evidence is passed for the
    'why excluded' panel but must never be cited.
    """
    query: str
    query_date: date
    intent: QueryIntent
    valid_evidence: List[EvidenceItem] = Field(default_factory=list)
    excluded_evidence: List[ExcludedEvidence] = Field(default_factory=list)
    reference_paths: List[ReferencePath] = Field(default_factory=list)
    change_paths: List[ChangePath] = Field(default_factory=list)
    conflict_candidates: List[ConflictCandidate] = Field(default_factory=list)
    impact_candidates: List[ImpactCandidate] = Field(default_factory=list)


class Citation(BaseModel):
    source_id: str
    document_number: Optional[str] = None
    heading_path: List[str] = Field(default_factory=list)
    page: Optional[int] = None
    content: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to_exclusive: Optional[date] = None


class Answer(BaseModel):
    text: str
    citations: List[Citation] = Field(default_factory=list)
    status: AnswerStatus
    query_date: Optional[date] = None
    timeline: List[ChangePath] = Field(default_factory=list)
    conflict_candidates: List[ConflictCandidate] = Field(default_factory=list)
    impact_candidates: List[ImpactCandidate] = Field(default_factory=list)
    excluded_evidence: List[ExcludedEvidence] = Field(default_factory=list)
    check_failures: List[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Workflow / audit
# --------------------------------------------------------------------------- #
class ReviewTask(BaseModel):
    task_id: str
    task_type: ReviewTaskType
    document_id: Optional[str] = None
    source_ref: Optional[str] = None       # provision_id / locator / page
    extracted: dict = Field(default_factory=dict)
    diff_before: Optional[str] = None
    diff_after: Optional[str] = None
    confidence: float = 1.0
    valid_from: Optional[date] = None
    status: ReviewStatus = ReviewStatus.PENDING
    decision: Optional[ReviewDecision] = None
    decided_by: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditRecord(BaseModel):
    audit_id: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[Role] = None
    query: Optional[str] = None
    query_date: Optional[date] = None
    retrieved_chunks: List[str] = Field(default_factory=list)
    used_versions: List[str] = Field(default_factory=list)
    excluded_versions: List[str] = Field(default_factory=list)
    graph_paths: List[str] = Field(default_factory=list)
    conflict_candidates: List[str] = Field(default_factory=list)
    answer: Optional[str] = None
    status: Optional[AnswerStatus] = None
    latency_ms: Optional[int] = None
    prompt_version: Optional[str] = None
    model_version: Optional[str] = None
    created_at: Optional[datetime] = None
