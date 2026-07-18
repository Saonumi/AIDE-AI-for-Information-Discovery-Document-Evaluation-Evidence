"""HTTP request/response schemas (FROZEN CONTRACT).

Track B implements these routes; Track C's UI calls exactly these shapes (and mocks
them until the backend is live). Keep endpoint list in sync with docs/project.md.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel

from packages.contracts.enums import DocumentType, ReviewDecision, Role
from packages.contracts.models import Answer, EvidencePackage, ReviewTask


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    role: Role
    username: str


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    file_hash: str
    processing_status: str
    approval_status: str
    injection_suspected: bool = False


class ReviewDecisionRequest(BaseModel):
    decision: ReviewDecision
    edited_payload: Optional[dict] = None
    note: Optional[str] = None


class QueryRequest(BaseModel):
    text: str
    query_date: Optional[date] = None   # None => "today" resolved server-side
    mode: Optional[str] = None          # optional intent override


class QueryResponse(BaseModel):
    answer: Answer
    evidence: EvidencePackage


class CompareResponse(BaseModel):
    """Head-to-head: standard vector RAG vs the temporal/graph system."""
    query: str
    query_date: date
    standard_rag: Answer
    our_system: Answer


class GraphNode(BaseModel):
    id: str
    label: str        # node type: Provision / ProvisionVersion / ChangeEvent / Document
    title: str        # display text
    props: dict = {}


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str        # relationship type


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class ReviewTaskList(BaseModel):
    tasks: List[ReviewTask]
