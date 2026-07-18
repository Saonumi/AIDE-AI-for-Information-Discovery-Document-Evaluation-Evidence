"""Step 21 — Evidence Package assembly.

Orchestrates steps 15-20 into a single deterministically-built EvidencePackage:
temporal filter -> hybrid retrieval -> graph expansion -> validity -> conflict ->
impact. This is the object handed to the LLM. The LLM may ONLY use valid_evidence;
excluded_evidence rides along solely for the "why excluded" panel and is never cited.

We do NOT send raw top-k to the model — that separation (deterministic evidence
selection vs LLM prose) is the whole point of the design.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from packages.contracts.enums import QueryIntent
from packages.contracts.models import (
    ChangePath,
    EvidencePackage,
    ReferencePath,
)

from query import conflict, graph_expansion, hybrid_retrieval, impact, temporal_filter, validity


def build(
    query: str,
    query_date: date,
    intent: QueryIntent,
    base_filters: Optional[Dict[str, Any]] = None,
    top_k: int = hybrid_retrieval.DEFAULT_TOP_K,
) -> EvidencePackage:
    """Run the deterministic evidence pipeline and return the package for generation."""
    # step 15 — temporal pre-filter baked into retrieval
    filters = temporal_filter.build_temporal_filter(query_date, base_filters)

    # step 16 — hybrid retrieval (BM25 + kNN + RRF), top-k drawn under the filter
    seeds = hybrid_retrieval.hybrid_search(query, filters, top_k=top_k)

    # step 17 — graph expansion (cross-reference + change paths), temporal filter reapplied
    seed_prov_ids = [s.get("provision_id") for s in seeds if s.get("provision_id")]
    exp = graph_expansion.expand(seed_prov_ids, query_date)

    candidates: List[Dict[str, Any]] = list(seeds) + list(exp.extra_chunks)

    # step 18 — deterministic validity & supersession resolution
    vr = validity.resolve(candidates, query_date)

    # step 19 — potential conflict (advisory), gated by intent-independent co-validity
    conflict_candidates = conflict.detect(vr.valid_evidence, query_date)

    # step 20 — internal impact / stale policy
    impact_candidates = impact.detect(vr.valid_evidence, query_date)

    reference_paths = [
        ReferencePath(
            from_provision=r["from_provision"],
            to_provision=r["to_provision"],
            to_locator=r.get("to_locator", ""),
            hops=r.get("hops", 1),
        )
        for r in exp.reference_paths
    ]
    change_paths = [
        ChangePath(
            provision_id=c["provision_id"],
            before_version_id=c.get("before_version_id"),
            after_version_id=c.get("after_version_id"),
            change_event_id=c.get("change_event_id"),
            operation=c.get("operation"),
        )
        for c in exp.change_paths
    ]

    return EvidencePackage(
        query=query,
        query_date=query_date,
        intent=intent,
        valid_evidence=vr.valid_evidence,
        excluded_evidence=vr.excluded_evidence,
        reference_paths=reference_paths,
        change_paths=change_paths,
        conflict_candidates=conflict_candidates,
        impact_candidates=impact_candidates,
    )
