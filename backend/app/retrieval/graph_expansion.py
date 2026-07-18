"""Step 17 — Graph expansion & cross-reference resolution.

From the seed provisions (chunks that survived retrieval) we walk the temporal graph
(<=2 hops, relation allowlist enforced in infra) to pull in:
  - REFERENCES targets (a clause that says "thực hiện theo Khoản 3 Điều 12"), and
  - change_paths (which ChangeEvent produced the current version — for the timeline).

For each newly-referenced provision we fetch its version that is VALID at query_date
(the temporal filter applies again — a reference must not drag in a stale version) and
turn it into an extra evidence chunk. This is how multi-hop / cross-document evidence
enters the package without ever letting the LLM traverse the graph itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List

from infra.neo4j_client import get_graph
from infra.postgres import session_scope
from infra.db_models import ProvisionVersionRow, ProvisionRow

MAX_HOPS = 2


@dataclass
class Expansion:
    extra_chunks: List[Dict[str, Any]] = field(default_factory=list)
    reference_paths: List[dict] = field(default_factory=list)
    change_paths: List[dict] = field(default_factory=list)


def _valid_version_chunk(provision_id: str, query_date: date) -> Dict[str, Any] | None:
    """Fetch the APPROVED version of `provision_id` valid at query_date as a chunk dict."""
    with session_scope() as ses:
        rows = (
            ses.query(ProvisionVersionRow)
            .filter(ProvisionVersionRow.provision_id == provision_id)
            .filter(ProvisionVersionRow.approval_status == "APPROVED")
            .all()
        )
        prov = (
            ses.query(ProvisionRow)
            .filter(ProvisionRow.provision_id == provision_id)
            .one_or_none()
        )
        heading = list(prov.heading_path) if prov and prov.heading_path else []
        for r in rows:
            vf = r.valid_from
            vte = r.valid_to_exclusive
            if vf is not None and vf > query_date:
                continue
            if vte is not None and query_date >= vte:
                continue
            return {
                "chunk_id": f"xref::{r.version_id}",
                "provision_id": r.provision_id,
                "version_id": r.version_id,
                "document_id": r.document_id,
                "heading_path": heading,
                "content": r.content,
                "page": r.page,
                "valid_from": r.valid_from,
                "valid_to_exclusive": r.valid_to_exclusive,
                "approval_status": r.approval_status,
                "_from_graph": True,
            }
    return None


def expand(seed_provision_ids: List[str], query_date: date, max_hops: int = MAX_HOPS) -> Expansion:
    """Expand seeds through REFERENCES/change edges and pull valid referenced versions."""
    seed_provision_ids = [p for p in dict.fromkeys(seed_provision_ids) if p]
    if not seed_provision_ids:
        return Expansion()

    graph = get_graph()
    result = graph.expand(seed_provision_ids, max_hops=max_hops)

    reference_paths: List[dict] = result.get("reference_paths", [])
    change_paths: List[dict] = result.get("change_paths", [])

    # newly reached provisions (referenced ones we didn't already have as seeds)
    reached = [p for p in result.get("provision_ids", []) if p not in set(seed_provision_ids)]

    extra: List[Dict[str, Any]] = []
    for pid in reached:
        chunk = _valid_version_chunk(pid, query_date)
        if chunk is not None:
            extra.append(chunk)

    return Expansion(extra_chunks=extra, reference_paths=reference_paths, change_paths=change_paths)
