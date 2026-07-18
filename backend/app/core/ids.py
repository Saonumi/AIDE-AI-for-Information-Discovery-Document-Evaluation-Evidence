"""Stable identifiers.

Key invariant (SAT-Graph lesson): a locator like "Khoản 2 Điều 7" is NOT identity.
Provision identity is a UUID; the locator is metadata that can change across versions.
`provision_lookup_key` is only used to *resolve* an incoming locator to an existing
provision_id (exact match on document_number + article + clause + point).
"""
from __future__ import annotations

import uuid
from typing import Optional


def new_id(prefix: str = "") -> str:
    u = uuid.uuid4().hex[:12]
    return f"{prefix}-{u}" if prefix else u


def new_provision_id() -> str:
    return new_id("prov")


def new_version_id() -> str:
    return new_id("ver")


def new_change_event_id() -> str:
    return new_id("chg")


def provision_lookup_key(
    document_number: Optional[str],
    article: Optional[str],
    clause: Optional[str] = None,
    point: Optional[str] = None,
) -> str:
    """Deterministic key for locator->provision_id resolution (NOT the identity)."""
    parts = [
        (document_number or "").strip().upper(),
        f"D{(article or '').strip()}",
        f"K{(clause or '').strip()}",
        f"P{(point or '').strip()}",
    ]
    return "|".join(parts)
