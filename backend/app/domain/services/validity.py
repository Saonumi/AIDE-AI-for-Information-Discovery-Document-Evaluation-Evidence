"""Step 18 — Validity & supersession resolution.

The deterministic final gate. Retrieval already pre-filtered temporally, but graph
expansion can add chunks and we never trust a single layer for correctness. Per
candidate version we re-check, in Python only (NO LLM), whether it is:
    - APPROVED,
    - valid at query_date (half-open interval, via ProvisionVersion.is_valid_at),
    - not superseded by a later version that is itself valid at query_date.

Each survivor becomes an EvidenceItem; each reject becomes an ExcludedEvidence with a
precise ExclusionReason so the UI's "why excluded" panel can explain it. This is the
module that makes version-conflation impossible on our side.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

from infra.db_models import ProvisionVersionRow
from infra.postgres import session_scope
from packages.contracts.enums import ApprovalStatus, ExclusionReason
from packages.contracts.models import (
    EvidenceItem,
    ExcludedEvidence,
    ProvisionVersion,
)


@dataclass
class ValidityResult:
    valid_evidence: List[EvidenceItem] = field(default_factory=list)
    excluded_evidence: List[ExcludedEvidence] = field(default_factory=list)
    valid_version_ids: List[str] = field(default_factory=list)


def _row_to_version(row: ProvisionVersionRow) -> ProvisionVersion:
    return ProvisionVersion(
        version_id=row.version_id,
        provision_id=row.provision_id,
        document_id=row.document_id,
        content=row.content,
        valid_from=row.valid_from,
        valid_to_exclusive=row.valid_to_exclusive,
        approval_status=ApprovalStatus(row.approval_status),
        page=row.page,
    )


def _load_versions(version_ids: List[str]) -> Dict[str, ProvisionVersion]:
    if not version_ids:
        return {}
    with session_scope() as ses:
        rows = (
            ses.query(ProvisionVersionRow)
            .filter(ProvisionVersionRow.version_id.in_(list(version_ids)))
            .all()
        )
        return {r.version_id: _row_to_version(r) for r in rows}


def resolve(
    candidates: List[Dict[str, Any]],
    query_date: date,
    document_numbers: Optional[Dict[str, str]] = None,
) -> ValidityResult:
    """Split retrieved+expanded candidate chunks into valid vs excluded.

    `candidates` are chunk dicts (from retrieval / graph). We authoritatively re-read
    each version from the DB so validity is decided on stored temporal facts, not on
    possibly-stale chunk metadata. When a version is absent from the DB (e.g. a
    self-seeded test chunk), we fall back to the chunk's own fields.
    """
    document_numbers = document_numbers or {}

    # de-dup candidates by version_id, keep best score
    by_version: Dict[str, Dict[str, Any]] = {}
    for c in candidates:
        vid = c.get("version_id")
        if not vid:
            continue
        prev = by_version.get(vid)
        score = c.get("_rrf_score", c.get("_score", 0.0)) or 0.0
        if prev is None or score > (prev.get("_rrf_score", prev.get("_score", 0.0)) or 0.0):
            by_version[vid] = c

    versions = _load_versions(list(by_version.keys()))

    result = ValidityResult()

    for vid, chunk in by_version.items():
        pv = versions.get(vid) or _chunk_as_version(chunk)
        reason = _exclusion_reason(pv, query_date)
        if reason is None:
            result.valid_evidence.append(_to_item(chunk, pv, document_numbers))
            result.valid_version_ids.append(vid)
        else:
            result.excluded_evidence.append(
                ExcludedEvidence(
                    version_id=vid,
                    provision_id=chunk.get("provision_id"),
                    heading_path=list(chunk.get("heading_path") or []),
                    reason=reason,
                )
            )

    # SUPERSEDED refinement: if two valid versions share a provision_id, the one with
    # the earlier valid_from is superseded (its successor is also valid at query_date,
    # which only happens for overlapping/mis-bounded data — mark the older excluded).
    result = _mark_superseded(result, versions)

    # "Why excluded" panel: for every provision we DO surface, list its sibling
    # versions that are not valid at query_date. These were correctly removed by the
    # temporal pre-filter before top-k (so they never reached retrieval) — we add them
    # here purely so the UI can explain "this other version exists but isn't valid now".
    _add_sibling_exclusions(result, query_date)

    # stable ordering: keep retrieval score order for valid evidence
    result.valid_evidence.sort(
        key=lambda e: e.score, reverse=True
    )
    return result


def _add_sibling_exclusions(result: ValidityResult, query_date: date) -> None:
    valid_prov_ids = {e.provision_id for e in result.valid_evidence}
    already = {e.version_id for e in result.valid_evidence} | {
        x.version_id for x in result.excluded_evidence
    }
    if not valid_prov_ids:
        return
    with session_scope() as ses:
        rows = (
            ses.query(ProvisionVersionRow)
            .filter(ProvisionVersionRow.provision_id.in_(list(valid_prov_ids)))
            .all()
        )
    for r in rows:
        if r.version_id in already:
            continue
        pv = _row_to_version(r)
        reason = _exclusion_reason(pv, query_date)
        if reason is None:
            continue
        result.excluded_evidence.append(
            ExcludedEvidence(
                version_id=r.version_id,
                provision_id=r.provision_id,
                heading_path=[],
                reason=reason,
            )
        )
        already.add(r.version_id)


def _chunk_as_version(chunk: Dict[str, Any]) -> ProvisionVersion:
    def _d(v):
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v
    return ProvisionVersion(
        version_id=chunk.get("version_id", ""),
        provision_id=chunk.get("provision_id", ""),
        document_id=chunk.get("document_id", ""),
        content=chunk.get("content", ""),
        valid_from=_d(chunk.get("valid_from")),
        valid_to_exclusive=_d(chunk.get("valid_to_exclusive")),
        approval_status=ApprovalStatus(chunk.get("approval_status", "PENDING")),
        page=chunk.get("page"),
    )


def _exclusion_reason(pv: ProvisionVersion, query_date: date) -> Optional[ExclusionReason]:
    if pv.approval_status != ApprovalStatus.APPROVED:
        return ExclusionReason.NOT_APPROVED
    if not pv.is_valid_at(query_date):
        return ExclusionReason.NOT_VALID_AT_QUERY_DATE
    return None


def _mark_superseded(result: ValidityResult, versions: Dict[str, ProvisionVersion]) -> ValidityResult:
    by_prov: Dict[str, List[EvidenceItem]] = {}
    for item in result.valid_evidence:
        by_prov.setdefault(item.provision_id, []).append(item)

    kept: List[EvidenceItem] = []
    kept_ids: List[str] = []
    for prov_id, items in by_prov.items():
        if len(items) <= 1:
            kept.extend(items)
            kept_ids.extend(i.version_id for i in items)
            continue
        # newest by valid_from wins; older co-valid ones are SUPERSEDED
        items_sorted = sorted(items, key=lambda i: i.valid_from)
        winner = items_sorted[-1]
        kept.append(winner)
        kept_ids.append(winner.version_id)
        for loser in items_sorted[:-1]:
            result.excluded_evidence.append(
                ExcludedEvidence(
                    version_id=loser.version_id,
                    provision_id=loser.provision_id,
                    heading_path=list(loser.heading_path),
                    reason=ExclusionReason.SUPERSEDED,
                )
            )
    result.valid_evidence = kept
    result.valid_version_ids = kept_ids
    return result


def _to_item(
    chunk: Dict[str, Any],
    pv: ProvisionVersion,
    document_numbers: Dict[str, str],
) -> EvidenceItem:
    return EvidenceItem(
        source_id=pv.version_id,          # source_id == version_id (contract)
        provision_id=pv.provision_id,
        version_id=pv.version_id,
        document_number=chunk.get("document_number") or document_numbers.get(pv.document_id),
        heading_path=list(chunk.get("heading_path") or []),
        content=pv.content or chunk.get("content", ""),
        page=pv.page if pv.page is not None else chunk.get("page"),
        valid_from=pv.valid_from,
        valid_to_exclusive=pv.valid_to_exclusive,
        score=float(chunk.get("_rrf_score", chunk.get("_score", 0.0)) or 0.0),
    )
