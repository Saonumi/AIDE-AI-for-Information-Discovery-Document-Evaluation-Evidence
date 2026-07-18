"""Policy mapping (Final spec §7.8) — deterministic, citation-evidence only.

When an INTERNAL_POLICY document is activated, each of its provision versions is
scanned for explicit citations ("22/2019/TT-NHNN", optionally with "Điều N
[Khoản M]"). Only an explicit citation creates an ALIGNED_TO link — the citation
text IS the evidence; no semantic guessing (spec §7.5: KHÔNG thử mọi document).

Resolution rule per citation, at mapping time:
  - "Điều N [Khoản M]" near the citation -> that provision (lookup_key)
  - no article mentioned -> only if the cited document has EXACTLY ONE provision
  - ambiguous / not found -> skip (never guess a target)
The link points at the CURRENTLY OPEN approved version, so a later amendment
that closes it makes the policy show up in the impact report.
"""
from __future__ import annotations

import re
from typing import List, Optional

from sqlalchemy import select

from infra.db_models import DocumentRow, InternalArtifactRow, ProvisionRow, ProvisionVersionRow
from packages.common.ids import new_id
from packages.common.vn_normalize import extract_all_money

_DOC_REF_RE = re.compile(r"\b(\d{1,3}/\d{4}/(?:TT|QĐ|NĐ|VBHN)-[A-ZĐ]+(?:-[A-ZĐ]+)?)\b")
_ARTICLE_RE = re.compile(r"Điều\s+(\d+[a-z]?)(?:\s+Khoản\s+(\d+))?", re.I)


def _open_version(session, provision_id: str) -> Optional[ProvisionVersionRow]:
    return session.execute(
        select(ProvisionVersionRow)
        .where(ProvisionVersionRow.provision_id == provision_id)
        .where(ProvisionVersionRow.approval_status == "APPROVED")
        .where(ProvisionVersionRow.valid_to_exclusive.is_(None))
    ).scalars().first()


def _resolve(session, cited_docno: str, article: Optional[str], clause: Optional[str]):
    doc = session.execute(
        select(DocumentRow).where(DocumentRow.document_number == cited_docno)
    ).scalars().first()
    if doc is None:
        return None
    provs = session.execute(
        select(ProvisionRow).where(ProvisionRow.document_id == doc.document_id)
    ).scalars().all()
    if article:
        matches = [p for p in provs
                   if p.article == article and (clause is None or p.clause == clause)]
    else:
        matches = provs
    if len(matches) != 1:  # 0 or >1 -> ambiguous, never guess
        return None
    return _open_version(session, matches[0].provision_id)


def map_policy_document(session, document_id: str) -> List[str]:
    """Create ALIGNED_TO artifacts for one activated INTERNAL_POLICY doc."""
    doc = session.execute(
        select(DocumentRow).where(DocumentRow.document_id == document_id)
    ).scalars().first()
    if doc is None or doc.type != "INTERNAL_POLICY":
        return []

    created: List[str] = []
    versions = session.execute(
        select(ProvisionVersionRow).where(ProvisionVersionRow.document_id == document_id)
    ).scalars().all()
    for ver in versions:
        text = ver.content or ""
        for cited in set(_DOC_REF_RE.findall(text)):
            m = _ARTICLE_RE.search(text)
            target = _resolve(session, cited, m.group(1) if m else None,
                              m.group(2) if m else None)
            if target is None:
                continue
            money = extract_all_money(text)
            art = InternalArtifactRow(
                artifact_id=new_id("art"),
                document_id=document_id,
                title=(doc.filename or document_id),
                aligned_to_version_id=target.version_id,
                obligation={"value": f"{money[0]:,} đồng".replace(",", "."),
                            "value_normalized": money[0]} if money else None,
                page=ver.page,
            )
            session.add(art)
            created.append(art.artifact_id)
    session.flush()
    return created
