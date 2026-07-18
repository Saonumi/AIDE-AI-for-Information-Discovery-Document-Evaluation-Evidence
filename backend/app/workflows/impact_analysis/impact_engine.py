"""Impact engine (Final spec §7.8) — ChangeEvents of a source -> impact report.

run(document_id) is deterministic and read-only: it loads the approved change
lineage from Postgres, finds ALIGNED_TO policies of superseded versions, and
hands everything to report_builder. Callable any time after activation — the
"trigger" after the activation gate is simply this recompute (ponytail: no
async queue; add an outbox worker if report latency ever matters).
"""
from __future__ import annotations

from typing import Dict, List

from infra.db_models import ChangeEventRow, DocumentRow, ProvisionRow
from infra.postgres import session_scope

from backend.app.domain.impact import ChangeSummary, ImpactedPolicy, RegulatoryImpactReport
from backend.app.workflows.impact_analysis import candidate_finder, report_builder

_SEV_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}


def _locator(prov: ProvisionRow) -> str:
    parts = []
    if prov.article:
        parts.append(f"Điều {prov.article}")
    if prov.clause:
        parts.append(f"Khoản {prov.clause}")
    if prov.point:
        parts.append(f"Điểm {prov.point}")
    return " ".join(parts) or prov.lookup_key


def run(document_id: str) -> RegulatoryImpactReport:
    with session_scope() as ses:
        doc = ses.query(DocumentRow).filter_by(document_id=document_id).first()
        if doc is None:
            raise ValueError(f"document not found: {document_id}")

        events = (
            ses.query(ChangeEventRow)
            .filter_by(amending_document_id=document_id)
            .order_by(ChangeEventRow.valid_from)
            .all()
        )

        changes: List[ChangeSummary] = []
        impacted: Dict[str, ImpactedPolicy] = {}
        for ev in events:
            prov = ses.query(ProvisionRow).filter_by(provision_id=ev.target_provision_id).first()
            target_doc = (
                ses.query(DocumentRow).filter_by(document_id=prov.document_id).first()
                if prov else None
            )
            changes.append(ChangeSummary(
                change_event_id=ev.change_event_id,
                operation=ev.operation,
                target_document_number=target_doc.document_number if target_doc else None,
                target_locator=_locator(prov) if prov else None,
                before_text=ev.old_text,
                after_text=ev.new_text,
                before_version_id=ev.before_version_id,
                after_version_id=ev.after_version_id,
                effective_date=ev.valid_from,
                source_page=ev.source_page,
                review_status=ev.review_status,
            ))
            if ev.review_status == "APPROVED":
                for pol in candidate_finder.find(ses, ev.before_version_id, ev.after_version_id):
                    prev = impacted.get(pol.artifact_id)
                    if prev is None or _SEV_ORDER[pol.severity] > _SEV_ORDER[prev.severity]:
                        impacted[pol.artifact_id] = pol

        return report_builder.build(doc, changes, list(impacted.values()))
