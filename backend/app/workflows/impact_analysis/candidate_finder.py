"""Impact candidates (Final spec §7.8) — deterministic, evidence-linked only.

An internal policy is a candidate IFF it is ALIGNED_TO (reviewed link, stored as
InternalArtifactRow.aligned_to_version_id) a version that a ChangeEvent has just
superseded. No semantic guessing: unlinked policies are never reported.
"""
from __future__ import annotations

from typing import List, Optional

from infra.db_models import InternalArtifactRow, ProvisionVersionRow
from packages.common.vn_normalize import money_to_vnd

from backend.app.domain.impact import ImpactedPolicy

_SEVERITY = {"THRESHOLD_MISMATCH": "HIGH", "MODALITY_CONFLICT": "MEDIUM",
             "ALIGNED_TO_SUPERSEDED": "LOW"}


def find(ses, before_version_id: Optional[str], after_version_id: Optional[str]) -> List[ImpactedPolicy]:
    """Policies aligned to `before_version_id`, compared against the new version."""
    if not before_version_id:
        return []
    artifacts = (
        ses.query(InternalArtifactRow)
        .filter(InternalArtifactRow.aligned_to_version_id == before_version_id)
        .all()
    )
    if not artifacts:
        return []
    after = (
        ses.query(ProvisionVersionRow)
        .filter_by(version_id=after_version_id).first()
        if after_version_id else None
    )
    reg_ob = (after.obligation or {}) if after else {}
    reg_content = (after.content or "") if after else ""
    return [_classify(a, reg_ob, reg_content) for a in artifacts]


def _classify(art: InternalArtifactRow, reg_ob: dict, reg_content: str) -> ImpactedPolicy:
    art_ob = art.obligation or {}
    reason = "ALIGNED_TO_SUPERSEDED"
    reg_value = policy_value = None

    am, rm = art_ob.get("modality"), reg_ob.get("modality")
    reg_val = reg_ob.get("value_normalized") or money_to_vnd(reg_ob.get("value") or "") \
        or money_to_vnd(reg_content)
    art_val = art_ob.get("value_normalized") or money_to_vnd(art_ob.get("value") or "")

    if reg_val is not None and art_val is not None and reg_val != art_val:
        reason = "THRESHOLD_MISMATCH"
        reg_value = reg_ob.get("value") or str(reg_val)
        policy_value = art_ob.get("value") or str(art_val)
    elif am and rm and str(am) != str(rm):
        reason = "MODALITY_CONFLICT"
        reg_value, policy_value = str(rm), str(am)

    return ImpactedPolicy(
        artifact_id=art.artifact_id,
        title=art.title,
        reason=reason,
        severity=_SEVERITY[reason],
        regulation_value=reg_value,
        internal_policy_value=policy_value,
        aligned_to_version_id=art.aligned_to_version_id,
    )
