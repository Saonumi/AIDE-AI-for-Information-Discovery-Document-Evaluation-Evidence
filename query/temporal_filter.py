"""Step 15 — Temporal pre-filter.

THE INVARIANT of the whole system: the temporal + approval constraint is baked into
the retrieval *filter dict*, so it participates in retrieval and top-k is drawn only
from versions valid at query_date. We never retrieve first and filter later.

infra.opensearch_client honours exactly these keys inside the search query:
    {"approved_only": True, "valid_at": <date>, "document_ids": [...]}

This module just assembles that dict; the enforcement lives in infra (both the real
OpenSearch backend and the InMemoryStore share `_passes_filter` semantics).
"""
from __future__ import annotations

from datetime import date
from typing import Dict, Optional


def build_temporal_filter(
    query_date: date,
    base_filters: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """Return the retrieval filter that pins top-k to versions valid at query_date.

    Always approved-only. `valid_at` is what makes retrieval temporal: a past-dated
    query can only ever see the version valid then, so V2 can never crowd out V1.
    """
    filters: Dict[str, object] = dict(base_filters or {})
    filters["approved_only"] = True
    filters["valid_at"] = query_date
    return filters
