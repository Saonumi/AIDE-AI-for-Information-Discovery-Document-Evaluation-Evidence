"""Step 13 — Query security & role filter.

The USER prompt is untrusted input. Before anything touches retrieval we:
  - enforce a length limit (defence against prompt-stuffing / DoS),
  - build the *base* retrieval filter that pins retrieval to APPROVED docs only,
  - block admin/write operations for a plain USER role,
  - refuse direct system-prompt-leak / injection attempts at the query layer.

There is deliberately NO LLM here and NO way for the user text to change the
retrieval filter or emit graph traversal Cypher — graph traversal is template-only
in infra (neo4j_client.ALLOWED_RELS + parameterised templates). This module only
returns policy, never runs a model.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict

# A generous cap: real regulatory questions are short; anything longer is abuse.
MAX_QUERY_LEN = 2000

# Coarse, high-precision markers of an attempt to subvert the assistant at the
# query layer. This is a *mitigation* flag, not a claim of full injection defence.
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?(previous|above)\s+instructions",
    r"reveal\s+.*system\s+prompt",
    r"show\s+.*system\s+prompt",
    r"system\s+prompt",
    r"bỏ\s+qua\s+.*(chỉ\s*thị|hướng\s*dẫn)",
    r"tiết\s+lộ\s+.*(system|prompt|hệ\s+thống)",
    r"execute\s+command",
    r"call\s+tool",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

# Admin / write operations a plain USER may never invoke from the query surface.
_ADMIN_TOKENS = {
    "upload", "approve", "activate", "archive", "delete", "reindex",
    "admin", "audit", "review",
}


@dataclass
class SecurityDecision:
    allowed: bool
    query: str                                   # sanitised (trimmed) query text
    base_filters: Dict[str, object] = field(default_factory=dict)
    injection_suspected: bool = False
    block_reason: str = ""


def check_query(text: str, role: str) -> SecurityDecision:
    """Validate an incoming query and produce the base (approval-only) filter.

    role is the wire-format role string ("USER" / "EMPLOYEE").
    The temporal `valid_at` key is added later by temporal_filter (step 15); this
    base filter guarantees retrieval can only ever see APPROVED documents.
    """
    q = (text or "").strip()
    role_norm = (role or "").strip().upper()

    if not q:
        return SecurityDecision(allowed=False, query="", block_reason="EMPTY_QUERY")

    if len(q) > MAX_QUERY_LEN:
        # Truncate rather than hard-fail so a long-but-benign question still runs,
        # but never let unbounded text through to the model.
        q = q[:MAX_QUERY_LEN]

    injection = bool(_INJECTION_RE.search(q))

    # Only EMPLOYEE may reference admin/write verbs as an *operation*. A USER asking
    # a normal question that merely contains the word is fine; we only block when the
    # query is clearly an admin instruction (starts with an admin verb).
    first = q.lower().split()[0] if q.split() else ""
    if role_norm != "EMPLOYEE" and first in _ADMIN_TOKENS:
        return SecurityDecision(
            allowed=False,
            query=q,
            injection_suspected=injection,
            block_reason="ADMIN_OP_REQUIRES_EMPLOYEE",
        )

    return SecurityDecision(
        allowed=True,
        query=q,
        base_filters={"approved_only": True},
        injection_suspected=injection,
    )
