"""SQLAlchemy ORM rows (PostgreSQL, SQLite-compatible).

Only relational/workflow data lives here: users, documents, provisions, versions,
change events, internal artifacts, review tasks, audit, feedback. Chunk text +
embeddings live in OpenSearch; the temporal graph lives in Neo4j.
JSON columns hold nested contract objects (obligation, scope, metadata, extracted).
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    # 32: COMPLIANCE_OFFICER (18 chars) overflows 16 on Postgres (SQLite không enforce)
    role: Mapped[str] = mapped_column(String(32))


class DocumentRow(Base):
    __tablename__ = "documents"
    document_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(String(512))
    type: Mapped[str] = mapped_column(String(32))
    document_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_hash: Mapped[str] = mapped_column(String(80), index=True)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(32), default="QUARANTINED")
    approval_status: Mapped[str] = mapped_column(String(32), default="PENDING")
    injection_suspected: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    doc_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProvisionRow(Base):
    __tablename__ = "provisions"
    provision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(64), ForeignKey("documents.document_id"))
    lookup_key: Mapped[str] = mapped_column(String(256), index=True)
    heading_path: Mapped[list | None] = mapped_column(JSON, nullable=True)
    article: Mapped[str | None] = mapped_column(String(32), nullable=True)
    clause: Mapped[str | None] = mapped_column(String(32), nullable=True)
    point: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ProvisionVersionRow(Base):
    __tablename__ = "provision_versions"
    version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provision_id: Mapped[str] = mapped_column(String(64), index=True)
    document_id: Mapped[str] = mapped_column(String(64), index=True)
    content: Mapped[str] = mapped_column(Text)
    valid_from: Mapped[date] = mapped_column(Date, index=True)
    valid_to_exclusive: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    approval_status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    obligation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scope: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ChangeEventRow(Base):
    __tablename__ = "change_events"
    change_event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    amending_document_id: Mapped[str] = mapped_column(String(64))
    target_provision_id: Mapped[str] = mapped_column(String(64), index=True)
    operation: Mapped[str] = mapped_column(String(32))
    old_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    before_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    after_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    valid_from: Mapped[date] = mapped_column(Date)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), default="PENDING")


class InternalArtifactRow(Base):
    __tablename__ = "internal_artifacts"
    artifact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(512))
    aligned_to_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    obligation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ReviewTaskRow(Base):
    __tablename__ = "review_tasks"
    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_type: Mapped[str] = mapped_column(String(32), index=True)
    document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    extracted: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    diff_before: Mapped[str | None] = mapped_column(Text, nullable=True)
    diff_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditRow(Base):
    __tablename__ = "audit_logs"
    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    query_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FeedbackRow(Base):
    __tablename__ = "feedback"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# --------------------------------------------------------------------------- #
# Mode-based chat + Review Run expansion (Mode spec §9.1, §12.1)
# Chat data belongs ONLY to its conversation/review run — never indexed into
# OpenSearch/Neo4j. Isolation is enforced by owner_id + conversation_id filters.
# --------------------------------------------------------------------------- #
class ConversationRow(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    mode: Mapped[str] = mapped_column(String(32))  # REGULATORY_ASSISTANT | DOCUMENT_REVIEW
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    active_review_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    active_batch_review_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retention_status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatTurnRow(Base):
    __tablename__ = "chat_turns"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant | system
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ConversationAttachmentRow(Base):
    __tablename__ = "conversation_attachments"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    trust_class: Mapped[str] = mapped_column(String(48), default="CONVERSATION_ATTACHMENT")
    filename: Mapped[str] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text)  # local context only, never legal evidence
    checksum: Mapped[str] = mapped_column(String(80))
    retention_status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReviewRunRow(Base):
    __tablename__ = "review_runs"
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    batch_review_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(32), default="CREATED", index=True)
    assessment_date: Mapped[date] = mapped_column(Date)
    knowledge_snapshot_id: Mapped[str] = mapped_column(String(128))
    snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # frozen version ids
    target_document_id: Mapped[str] = mapped_column(String(64))
    target_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    target_checksum: Mapped[str | None] = mapped_column(String(80), nullable=True)
    target_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # for re-run
    versions: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # parser/prompt/schema
    report: Mapped[dict | None] = mapped_column(JSON, nullable=True)   # locked result
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BatchReviewRow(Base):
    __tablename__ = "batch_reviews"
    batch_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    assessment_date: Mapped[date] = mapped_column(Date)
    knowledge_snapshot_id: Mapped[str] = mapped_column(String(128))
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recurring_issues: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BatchReviewItemRow(Base):
    __tablename__ = "batch_review_items"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    review_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    filename: Mapped[str] = mapped_column(String(512))
    target_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # for retry
    status: Mapped[str] = mapped_column(String(16), default="QUEUED", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
