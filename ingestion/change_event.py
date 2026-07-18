"""Step 9 — ChangeEvent & version resolution.

An amendment is reified as a ChangeEvent so the graph can answer WHO changed WHAT,
WHEN and by WHICH document — a bare "V2 SUPERSEDES V1" edge cannot. This module,
given an extracted Amendment:

  1. resolves the target provision via entity_resolution (locator -> provision_id),
  2. creates a PENDING ChangeEventRow (operation, old/new text, valid_from, source page),
  3. computes the deterministic draft patch (before/after) for the review inbox,
  4. raises a CHANGE_EVENT_REVIEW task (or PARSING/CHANGE review if the target or patch
     needs a human).

SUPERSEDES / before-after version ids are only filled at activation (after approval),
never here.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import select

from infra.db_models import ChangeEventRow, ProvisionVersionRow
from packages.common.ids import new_change_event_id
from packages.contracts.enums import ReviewStatus, ReviewTaskType
from packages.contracts.models import Amendment
from ingestion import patch as patch_mod
from ingestion import review_inbox
from ingestion.entity_resolution import resolve_locator_text


def _current_version_content(session, provision_id: str) -> Optional[ProvisionVersionRow]:
    """Return the latest APPROVED (or newest) version row for a provision."""
    rows = session.execute(
        select(ProvisionVersionRow)
        .where(ProvisionVersionRow.provision_id == provision_id)
        .order_by(ProvisionVersionRow.valid_from.desc())
    ).scalars().all()
    if not rows:
        return None
    approved = [r for r in rows if r.approval_status == "APPROVED"]
    return (approved or rows)[0]


def create_change_event(
    session,
    amendment: Amendment,
    amending_document_id: str,
    target_document_number: Optional[str],
) -> Dict[str, Any]:
    """Create a ChangeEvent row + review task from one amendment.

    Returns a dict describing what happened (for the service layer / tests):
        {"change_event_id", "target_provision_id"|None, "review_task_id",
         "patch_status", "resolved": bool}
    """
    target_provision_id = resolve_locator_text(
        session, target_document_number, amendment.target_locator,
    )

    change_event_id = new_change_event_id()
    row = ChangeEventRow(
        change_event_id=change_event_id,
        amending_document_id=amending_document_id,
        target_provision_id=target_provision_id or "",
        operation=amendment.operation.value,
        old_text=amendment.old_text,
        new_text=amendment.new_text,
        before_version_id=None,
        after_version_id=None,
        valid_from=amendment.valid_from,
        source_page=amendment.source_page,
        review_status=ReviewStatus.PENDING.value,
    )
    session.add(row)
    session.flush()

    # Compute the deterministic draft patch against the current version (if resolved).
    patch_status = None
    diff_before = None
    diff_after = None
    if target_provision_id:
        cur = _current_version_content(session, target_provision_id)
        if cur is not None:
            result = patch_mod.apply_patch(
                cur.content, amendment.operation,
                old_text=amendment.old_text, new_text=amendment.new_text,
            )
            patch_status = result.status
            diff_before = cur.content
            diff_after = result.new_content

    extracted = {
        "change_event_id": change_event_id,
        "operation": amendment.operation.value,
        "old_text": amendment.old_text,
        "new_text": amendment.new_text,
        "target_locator": amendment.target_locator,
        "target_provision_id": target_provision_id,
        "amending_document_id": amending_document_id,
        "valid_from": amendment.valid_from.isoformat(),
        "patch_status": patch_status,
    }

    # If the target didn't resolve, this is a reference/parsing problem for a human.
    if not target_provision_id:
        task_type = ReviewTaskType.REFERENCE_REVIEW
    else:
        task_type = ReviewTaskType.CHANGE_EVENT_REVIEW

    task = review_inbox.create_task(
        session,
        task_type,
        document_id=amending_document_id,
        source_ref=amendment.target_locator,
        extracted=extracted,
        diff_before=diff_before,
        diff_after=diff_after,
        confidence=amendment.confidence,
        valid_from=amendment.valid_from,
    )

    return {
        "change_event_id": change_event_id,
        "target_provision_id": target_provision_id,
        "review_task_id": task.task_id,
        "patch_status": patch_status,
        "resolved": bool(target_provision_id),
    }


def get_change_event(session, change_event_id: str) -> Optional[ChangeEventRow]:
    return session.execute(
        select(ChangeEventRow).where(ChangeEventRow.change_event_id == change_event_id)
    ).scalars().first()
