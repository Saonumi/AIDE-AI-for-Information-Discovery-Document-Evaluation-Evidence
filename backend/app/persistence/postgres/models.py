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
    role: Mapped[str] = mapped_column(String(16))


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
    role: Mapped[str | None] = mapped_column(String(16), nullable=True)
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
