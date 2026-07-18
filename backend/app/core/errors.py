"""Stable API error codes (Final spec §9.1).

UI/clients match on `code`, never on free-text messages. Every 4xx/5xx business
error must use the envelope {"error": {"code", "message", "details"}}.
"""
from __future__ import annotations

from typing import Any, Optional

INVALID_UPLOAD_PURPOSE = "INVALID_UPLOAD_PURPOSE"
REVIEW_NOT_COMPLETED = "REVIEW_NOT_COMPLETED"
EVIDENCE_NOT_VALID = "EVIDENCE_NOT_VALID"
TARGET_NOT_RESOLVED = "TARGET_NOT_RESOLVED"
NOT_LEGAL_GROUND_TRUTH = "NOT_LEGAL_GROUND_TRUTH"
BACKEND_DEGRADED = "BACKEND_DEGRADED"


def envelope(code: str, message: str, details: Optional[Any] = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}
