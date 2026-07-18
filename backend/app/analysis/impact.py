"""Step 20 — Internal impact / stale-policy detection.

When a regulation version V2 supersedes V1, any internal policy/process that was
ALIGNED_TO V1 may now be stale. We find InternalArtifactRow rows aligned to a version
that is NO LONGER valid at query_date (i.e. it has been superseded), then compare the
internal policy's obligation against the *currently valid* regulation obligation:
numeric threshold (canonical VND), deadline, modality. A mismatch => an ImpactCandidate
(STALE / NEEDS_REVIEW). Advisory only; an Employee confirms.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from infra.db_models import InternalArtifactRow, ProvisionVersionRow
from infra.postgres import session_scope
from packages.common.vn_normalize import money_to_vnd
from packages.contracts.enums import ConflictReason, Modality, ReviewStatus
from packages.contracts.models import EvidenceItem, ImpactCandidate


def detect(valid_evidence: List[EvidenceItem], query_date: date) -> List[ImpactCandidate]:
    """Find internal artifacts aligned to a now-superseded version of a valid provision."""
    if not valid_evidence:
        return []

    provision_ids = {e.provision_id for e in valid_evidence}
    current_by_prov: Dict[str, EvidenceItem] = {e.provision_id: e for e in valid_evidence}

    candidates: List[ImpactCandidate] = []
    with session_scope() as ses:
        # all approved versions of the provisions currently in evidence
        vrows = (
            ses.query(ProvisionVersionRow)
            .filter(ProvisionVersionRow.provision_id.in_(list(provision_ids)))
            .all()
        )
        version_to_prov = {v.version_id: v.provision_id for v in vrows}
        # versions of these provisions that are NO LONGER valid at query_date (superseded/expired)
        stale_version_ids = {
            v.version_id
            for v in vrows
            if _superseded_at(v.valid_from, v.valid_to_exclusive, query_date)
        }
        if not stale_version_ids:
            return []

        artifacts = (
            ses.query(InternalArtifactRow)
            .filter(InternalArtifactRow.aligned_to_version_id.in_(list(stale_version_ids)))
            .all()
        )
        for art in artifacts:
            prov_id = version_to_prov.get(art.aligned_to_version_id)
            current = current_by_prov.get(prov_id)
            if current is None:
                continue
            reg_ob = _current_obligation(ses, current.version_id)
            cand = _compare(art, reg_ob, current.content)
            if cand is not None:
                candidates.append(cand)
    return candidates


def _superseded_at(valid_from, valid_to_exclusive, query_date: date) -> bool:
    """A version is 'past' (superseded/expired) if it ended on or before query_date."""
    return valid_to_exclusive is not None and query_date >= valid_to_exclusive


def _current_obligation(ses, version_id: str) -> Dict[str, Any]:
    row = (
        ses.query(ProvisionVersionRow)
        .filter(ProvisionVersionRow.version_id == version_id)
        .one_or_none()
    )
    return (row.obligation or {}) if row else {}


def _compare(art: InternalArtifactRow, reg_ob: Dict[str, Any], reg_content: str) -> Optional[ImpactCandidate]:
    art_ob = art.obligation or {}

    # modality drift
    am, rm = art_ob.get("modality"), reg_ob.get("modality")
    if am and rm and str(am) != str(rm):
        return _mk(art, ConflictReason.MODALITY_CONFLICT, str(rm), str(am))

    # numeric threshold drift (canonical VND)
    reg_val = reg_ob.get("value_normalized") or money_to_vnd(reg_ob.get("value") or "") or money_to_vnd(reg_content)
    art_val = art_ob.get("value_normalized") or money_to_vnd(art_ob.get("value") or "")
    if reg_val is not None and art_val is not None and reg_val != art_val:
        return _mk(
            art,
            ConflictReason.THRESHOLD_MISMATCH,
            reg_ob.get("value") or str(reg_val),
            art_ob.get("value") or str(art_val),
        )
    return None


def _mk(art: InternalArtifactRow, reason: ConflictReason, reg_value: str, policy_value: str) -> ImpactCandidate:
    return ImpactCandidate(
        artifact_id=art.artifact_id,
        artifact_title=art.title,
        reason=reason,
        regulation_value=reg_value,
        internal_policy_value=policy_value,
        status=ReviewStatus.PENDING,
    )
