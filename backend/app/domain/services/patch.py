"""Step 10 — Deterministic partial patch.

Produces V2 content from V1 by editing ONLY the affected span. The LLM never rewrites
a clause — consolidation is deterministic Python so unchanged parts (e.g. "12 tháng")
are preserved byte-for-byte.

Core rule (per docs/final_pipeline.md step 10):
  - EXACTLY ONE exact match of old_text  -> produce draft V2 content (status OK)
  - ZERO or MULTIPLE matches             -> NEEDS_REVIEW (no draft applied)

Operations: REPLACE_TEXT, INSERT_TEXT, DELETE_TEXT, REPEAL_PROVISION.
A unified before/after diff (difflib) accompanies every result for the review inbox.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import List, Optional

from packages.contracts.enums import AmendmentOperation

STATUS_OK = "OK"
STATUS_NEEDS_REVIEW = "NEEDS_REVIEW"


@dataclass
class PatchResult:
    status: str                       # STATUS_OK | STATUS_NEEDS_REVIEW
    old_content: str
    new_content: Optional[str]        # None when NEEDS_REVIEW
    operation: AmendmentOperation
    reason: Optional[str] = None      # why review is needed
    match_count: int = 0
    diff: List[str] = field(default_factory=list)

    @property
    def needs_review(self) -> bool:
        return self.status == STATUS_NEEDS_REVIEW


def _diff(before: str, after: str) -> List[str]:
    return list(difflib.unified_diff(
        before.splitlines(), after.splitlines(),
        fromfile="V1", tofile="V2", lineterm="",
    ))


def apply_patch(
    content: str,
    operation: AmendmentOperation,
    old_text: Optional[str] = None,
    new_text: Optional[str] = None,
) -> PatchResult:
    """Apply one amendment operation to `content` deterministically."""
    content = content or ""

    if operation == AmendmentOperation.REPEAL_PROVISION:
        # The whole provision is repealed — content becomes empty; always applicable.
        return PatchResult(
            status=STATUS_OK,
            old_content=content,
            new_content="",
            operation=operation,
            reason="Provision repealed.",
            match_count=1,
            diff=_diff(content, ""),
        )

    if operation == AmendmentOperation.INSERT_TEXT:
        if not new_text:
            return PatchResult(STATUS_NEEDS_REVIEW, content, None, operation,
                               reason="INSERT_TEXT missing new_text.")
        # Append the inserted sentence; deterministic and non-destructive.
        sep = " " if content and not content.endswith((" ", "\n")) else ""
        new_content = f"{content}{sep}{new_text.strip()}".strip()
        return PatchResult(STATUS_OK, content, new_content, operation,
                           match_count=1, diff=_diff(content, new_content))

    # REPLACE_TEXT and DELETE_TEXT both require an exact old_text match.
    if not old_text:
        return PatchResult(STATUS_NEEDS_REVIEW, content, None, operation,
                           reason=f"{operation.value} missing old_text.")

    count = content.count(old_text)
    if count == 0:
        return PatchResult(STATUS_NEEDS_REVIEW, content, None, operation,
                           reason=f"No exact match for {old_text!r}.", match_count=0)
    if count > 1:
        return PatchResult(STATUS_NEEDS_REVIEW, content, None, operation,
                           reason=f"Ambiguous: {count} matches for {old_text!r}.",
                           match_count=count)

    if operation == AmendmentOperation.REPLACE_TEXT:
        replacement = (new_text or "").strip()
        new_content = content.replace(old_text, replacement, 1)
    else:  # DELETE_TEXT
        new_content = content.replace(old_text, "", 1)
        # tidy double spaces left by a deletion
        new_content = " ".join(new_content.split())

    return PatchResult(
        status=STATUS_OK,
        old_content=content,
        new_content=new_content,
        operation=operation,
        match_count=1,
        diff=_diff(content, new_content),
    )
