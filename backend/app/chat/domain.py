"""Chat domain (Mode spec §2, §9.1) — one assistant, two operating modes.

Conversation content may help understand the user but NEVER becomes legal
knowledge: legal truth only comes from APPROVED + ACTIVE sources (spec §3).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMode(str, Enum):
    REGULATORY_ASSISTANT = "REGULATORY_ASSISTANT"  # Ask Regulations
    DOCUMENT_REVIEW = "DOCUMENT_REVIEW"


class Conversation(BaseModel):
    id: str
    owner_id: str
    mode: ChatMode
    title: Optional[str] = None
    active_review_run_id: Optional[str] = None
    active_batch_review_id: Optional[str] = None
    retention_status: str = "ACTIVE"
    created_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None


class ChatTurn(BaseModel):
    id: str
    conversation_id: str
    role: str  # user | assistant | system
    content: str
    citations: List[dict] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class ConversationAttachment(BaseModel):
    id: str
    conversation_id: str
    filename: str
    trust_class: str = "CONVERSATION_ATTACHMENT"
    checksum: str
    created_at: Optional[datetime] = None
