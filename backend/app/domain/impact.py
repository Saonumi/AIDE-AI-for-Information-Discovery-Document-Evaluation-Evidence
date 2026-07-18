"""Regulatory Impact Report contract (Final spec §6.3, §7.8, §7.11).

Stable JSON the UI renders after a regulatory source is approved + activated:
executive summary, change list with before/after + effective date, impacted
internal policies with severity, and evidence lineage (change_event -> version
ids -> policy artifact). Deterministic: rebuilt from Postgres rows, never LLM.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class ChangeSummary(BaseModel):
    """One approved ChangeEvent rendered for the report (before/after lineage)."""
    change_event_id: str
    operation: str
    target_document_number: Optional[str] = None
    target_locator: Optional[str] = None          # "Điều 16 Khoản 1"
    before_text: Optional[str] = None
    after_text: Optional[str] = None
    before_version_id: Optional[str] = None
    after_version_id: Optional[str] = None
    effective_date: Optional[date] = None
    source_page: Optional[int] = None
    review_status: str = "PENDING"


class ImpactedPolicy(BaseModel):
    """An internal policy clause whose alignment target was superseded."""
    artifact_id: str
    title: str
    reason: str                                    # THRESHOLD_MISMATCH / MODALITY_CONFLICT / ALIGNED_TO_SUPERSEDED
    severity: str                                  # HIGH / MEDIUM / LOW
    regulation_value: Optional[str] = None
    internal_policy_value: Optional[str] = None
    aligned_to_version_id: Optional[str] = None    # evidence lineage back-pointer
    review_status: str = "PENDING"


class RegulatoryImpactReport(BaseModel):
    report_id: str
    document_id: str                               # the amending/base regulatory source
    document_number: Optional[str] = None
    executive_summary: str = ""
    changes: List[ChangeSummary] = Field(default_factory=list)
    impacted_policies: List[ImpactedPolicy] = Field(default_factory=list)
    max_severity: Optional[str] = None
    status: str = "REVIEW_REQUIRED"                # REVIEW_REQUIRED until officer confirms
