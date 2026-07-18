"""Step 8 — Entity resolution + stable IDs.

Key invariant (SAT-Graph lesson): a locator like "Khoản 2 Điều 7" is NOT identity.
Provision identity is a stable UUID; the locator is mutable metadata. This module:

  - assigns stable ids (ids.new_provision_id / new_version_id) to parsed provisions,
  - resolves an INCOMING locator to an EXISTING provision via an exact match on
    ProvisionRow.lookup_key = provision_lookup_key(document_number, article, clause, point).

Resolution is exact-match only; fuzzy/LLM matching would only ever produce a review
candidate, never a silent identity link.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select

from infra.db_models import ProvisionRow
from packages.common.ids import new_provision_id, new_version_id, provision_lookup_key
from ingestion.legal_extract import normalize_locator


def assign_ids(provisions: List[Dict[str, Any]], document_number: Optional[str]) -> List[Dict[str, Any]]:
    """Attach provision_id, version_id and lookup_key to each parsed provision dict."""
    out: List[Dict[str, Any]] = []
    for p in provisions:
        row = dict(p)
        row["provision_id"] = new_provision_id()
        row["version_id"] = new_version_id()
        row["lookup_key"] = provision_lookup_key(
            document_number, p.get("article"), p.get("clause"), p.get("point"),
        )
        out.append(row)
    return out


def resolve_locator(
    session,
    document_number: Optional[str],
    article: Optional[str],
    clause: Optional[str] = None,
    point: Optional[str] = None,
) -> Optional[str]:
    """Return the provision_id whose lookup_key exactly matches, else None.

    Tries the most specific key first (with point), then falls back to
    (article, clause) and finally (article) so an amendment that names only
    "Khoản 2 Điều 7" still resolves a provision stored without a point.
    """
    candidates = []
    if point:
        candidates.append((article, clause, point))
    if clause:
        candidates.append((article, clause, None))
    candidates.append((article, None, None))

    for art, cl, pt in candidates:
        key = provision_lookup_key(document_number, art, cl, pt)
        row = session.execute(
            select(ProvisionRow).where(ProvisionRow.lookup_key == key)
        ).scalars().first()
        if row is not None:
            return row.provision_id
    return None


def resolve_locator_text(
    session,
    document_number: Optional[str],
    locator: str,
) -> Optional[str]:
    """Parse a free-text locator ("Khoản 2 Điều 7") then resolve to a provision_id."""
    parsed = normalize_locator(locator)
    if not parsed:
        return None
    article, clause, point = parsed
    return resolve_locator(session, document_number, article, clause, point)
