"""Workflow B step 1 — rule-based claim extraction (Final spec §7.9, §7.4).

A "claim" is any sentence in a review target that states a checkable fact:
a money amount, a percentage, a report deadline, a legal reference, or an
obligation keyword. Facts are mined deterministically with the shared VN
normalizer so the assessor can do EXACT compares — the LLM never decides facts.

ponytail: regex sentence split + keyword triggers; LLM-assisted claim extraction
can be layered on later behind the same extract() signature.
"""
from __future__ import annotations

import re
from typing import List

from packages.common.ids import new_id
from packages.common.vn_normalize import extract_all_money, normalize_date
from backend.app.domain.compliance import ComplianceClaim, StructuredFacts

# "22/2019/TT-NHNN", "53/2018/TT-NHNN", "01/2026/NĐ-CP", "12/2025/QĐ-TTg"...
_DOC_REF_RE = re.compile(r"\b(\d{1,3}/\d{4}/(?:TT|QĐ|NĐ|VBHN)-[A-ZĐ]+(?:-[A-ZĐ]+)?)\b")
_PERCENT_RE = re.compile(r"(\d{1,3}(?:[.,]\d+)?)\s*%")
_DEADLINE_RE = re.compile(
    r"(?:chậm nhất|trước|không quá|muộn nhất)\s+(?:là\s+)?(?:vào\s+)?ngày\s+(\d{1,2})\b", re.I
)
_MODALITY_RE = re.compile(
    r"\b(phải|không được|tối đa|tối thiểu|chậm nhất|bắt buộc|chỉ được|không vượt quá)\b", re.I
)
_SECTION_RE = re.compile(r"^\s*(Điều\s+\d+[a-zà-ỹ]?\b.*|Mục\s+\d+.*|[IVX]+\..*)\s*$", re.I)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.;])\s+")


def mine_facts(text: str) -> StructuredFacts:
    """Deterministic fact mining — shared by claims AND evidence (same rules both sides)."""
    percents = [float(m.group(1).replace(",", ".")) for m in _PERCENT_RE.finditer(text or "")]
    d = normalize_date(text or "")
    return StructuredFacts(
        money_vnd=extract_all_money(text or ""),
        percents=percents,
        deadline_days=[int(m.group(1)) for m in _DEADLINE_RE.finditer(text or "")],
        dates=[d] if d else [],
        doc_refs=_DOC_REF_RE.findall(text or ""),
    )


def extract(text: str, target_document_id: str) -> List[ComplianceClaim]:
    """Split the review target into sentences and keep the checkable ones."""
    claims: List[ComplianceClaim] = []
    section = None
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("["):  # banner/label lines are not claims
            continue
        # a heading is only a heading if it carries no checkable fact —
        # "Điều 1. Phí quản lý là 2 triệu đồng" is a CLAIM, not a section
        if _SECTION_RE.match(line) and len(line) < 80 and not mine_facts(line).has_comparable():
            section = line
            continue
        for sent in _SENTENCE_SPLIT_RE.split(line):
            sent = sent.strip()
            if len(sent) < 15:
                continue
            facts = mine_facts(sent)
            if facts.has_comparable() or facts.doc_refs or _MODALITY_RE.search(sent):
                claims.append(
                    ComplianceClaim(
                        claim_id=new_id("claim"),
                        target_document_id=target_document_id,
                        section=section,
                        text=sent,
                        facts=facts,
                    )
                )
    return claims
