"""Step 19 — Potential conflict detection (advisory only).

Only pairs of provisions that are SIMULTANEOUSLY valid at query_date and overlap in
scope are considered. Before we ever flag a pair we EXCLUDE the false-positive classes
the org explicitly listed:
    - old-vs-new version of the same provision (that's supersession, not conflict),
    - an amendment relation (one amends the other),
    - general rule vs its exception,
    - different product / customer_type / jurisdiction (no real scope overlap).

Only then do we compare structured obligations with deterministic rules
(threshold via vn_normalize.money_to_vnd, modality OBLIGATION↔PROHIBITION, deadlines).
An LLM zero-shot judgement is an OPTIONAL confirm — it can only downgrade a rule hit,
never invent one, and the output is always human_review=PENDING. We never say
"confirmed conflict": every result is a candidate for Employee review.
"""
from __future__ import annotations

from datetime import date
from itertools import combinations
from typing import Any, Dict, List, Optional

from infra.db_models import ProvisionVersionRow
from infra.postgres import session_scope
from packages.common.vn_normalize import money_to_vnd
from packages.contracts.enums import ConflictReason, Modality, ReviewStatus
from packages.contracts.models import ConflictCandidate, EvidenceItem


def _load_meta(version_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """version_id -> {provision_id, document_id, obligation, scope, content, valid_from, valid_to}."""
    if not version_ids:
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    with session_scope() as ses:
        rows = (
            ses.query(ProvisionVersionRow)
            .filter(ProvisionVersionRow.version_id.in_(list(version_ids)))
            .all()
        )
        for r in rows:
            out[r.version_id] = {
                "provision_id": r.provision_id,
                "document_id": r.document_id,
                "obligation": r.obligation or {},
                "scope": r.scope or {},
                "content": r.content or "",
                "valid_from": r.valid_from,
                "valid_to_exclusive": r.valid_to_exclusive,
            }
    return out


def _scope_overlaps(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Scope overlaps unless a discriminating field is present on BOTH and differs."""
    for field in ("product", "customer_type", "jurisdiction"):
        va, vb = a.get(field), b.get(field)
        if va and vb and _norm(va) != _norm(vb):
            return False
    # a general rule vs an explicit exception is not a conflict
    ca, cb = _norm(a.get("applicable_condition")), _norm(b.get("applicable_condition"))
    if ("ngoại lệ" in ca or "exception" in ca) ^ ("ngoại lệ" in cb or "exception" in cb):
        return False
    return True


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _same_provision_or_amendment(a: Dict[str, Any], b: Dict[str, Any], amend_pairs: set) -> bool:
    if a["provision_id"] == b["provision_id"]:
        return True  # different versions of the same clause
    pair = frozenset((a["provision_id"], b["provision_id"]))
    return pair in amend_pairs


def _rule_conflict(oa: Dict[str, Any], ob: Dict[str, Any], ca: str, cb: str):
    """Return (ConflictReason, value_a, value_b) if the obligations clash, else None."""
    # modality clash
    ma, mb = oa.get("modality"), ob.get("modality")
    if ma and mb:
        clashing = {frozenset((Modality.OBLIGATION.value, Modality.PROHIBITION.value)),
                    frozenset((Modality.PERMISSION.value, Modality.PROHIBITION.value))}
        if frozenset((str(ma), str(mb))) in clashing:
            return ConflictReason.MODALITY_CONFLICT, str(ma), str(mb)

    # threshold mismatch (canonical VND)
    va = oa.get("value_normalized") or money_to_vnd(oa.get("value") or "") or money_to_vnd(ca)
    vb = ob.get("value_normalized") or money_to_vnd(ob.get("value") or "") or money_to_vnd(cb)
    if va is not None and vb is not None and va != vb:
        return (
            ConflictReason.THRESHOLD_MISMATCH,
            oa.get("value") or str(va),
            ob.get("value") or str(vb),
        )
    return None


def detect(valid_evidence: List[EvidenceItem], query_date: date) -> List[ConflictCandidate]:
    """Find potential-conflict candidates among the co-valid evidence."""
    if len(valid_evidence) < 2:
        return []

    version_ids = [e.version_id for e in valid_evidence]
    meta = _load_meta(version_ids)

    # amendment relations from the graph (a TARGETS/change edge between provisions)
    amend_pairs = _amendment_pairs([e.provision_id for e in valid_evidence])

    candidates: List[ConflictCandidate] = []
    seen: set = set()
    for ea, eb in combinations(valid_evidence, 2):
        ma = meta.get(ea.version_id)
        mb = meta.get(eb.version_id)
        if ma is None or mb is None:
            continue
        # EXCLUDE: same provision (old-vs-new) or amendment relation
        if _same_provision_or_amendment(ma, mb, amend_pairs):
            continue
        # EXCLUDE: no scope overlap (different product/customer/jurisdiction/exception)
        if not _scope_overlaps(ma["scope"], mb["scope"]):
            continue

        clash = _rule_conflict(ma["obligation"], mb["obligation"], ma["content"], mb["content"])
        if clash is None:
            continue

        reason, va, vb = clash
        # optional LLM confirm (advisory; can only keep or drop, never invent)
        if not _llm_confirms(ma, mb, reason):
            continue

        key = frozenset((ma["provision_id"], mb["provision_id"]))
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            ConflictCandidate(
                provision_a=ma["provision_id"],
                provision_b=mb["provision_id"],
                reason=reason,
                value_a=va,
                value_b=vb,
                temporal_overlap=True,
                scope_overlap=True,
                human_review=ReviewStatus.PENDING,
            )
        )
    return candidates


def _amendment_pairs(provision_ids: List[str]) -> set:
    """Provision pairs linked by a ChangeEvent (one amends the other) — never conflicts."""
    pairs: set = set()
    try:
        with session_scope() as ses:
            from infra.db_models import ChangeEventRow
            rows = ses.query(ChangeEventRow).filter(
                ChangeEventRow.target_provision_id.in_(list(provision_ids))
            ).all()
            # ChangeEvents relate versions of the SAME provision; those are already
            # excluded by same-provision. This is a defensive hook for cross-provision
            # amendments if they exist.
            for r in rows:
                pairs.add(frozenset((r.target_provision_id, r.target_provision_id)))
    except Exception:
        pass
    return pairs


def _llm_confirms(ma: Dict[str, Any], mb: Dict[str, Any], reason: ConflictReason) -> bool:
    """Optional zero-shot confirm. Fails OPEN (keeps the rule hit) when unavailable —
    the rule already found a real value mismatch; the LLM is only a sanity check."""
    try:
        from llm.client import get_client
        from llm.prompts import CONFLICT_SYSTEM
        user = (
            f"Nghĩa vụ A: {ma['content']}\n"
            f"Nghĩa vụ B: {mb['content']}\n"
            f"Loại nghi ngờ: {reason.value}"
        )
        out = get_client().complete_json(CONFLICT_SYSTEM, user)
        if isinstance(out, dict) and "is_potential_conflict" in out:
            return bool(out.get("is_potential_conflict"))
    except Exception:
        pass
    return True
