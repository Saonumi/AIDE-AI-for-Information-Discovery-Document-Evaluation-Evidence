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

# Dòng "khung" của văn bản: lời mở đầu, căn cứ, nơi nhận, chữ ký, tiêu đề ban
# hành, quốc hiệu... KHÔNG phải điều khoản quy phạm → bỏ để tránh finding nhiễu
# (§7.9). Neo ^ + cho phép "(" đầu dòng: chỉ chặn khi dòng BẮT ĐẦU bằng các mẫu
# này, nên claim thật như "Giám đốc phải phê duyệt khoản vay 500 triệu" không bị lọc.
_BOILERPLATE_RE = re.compile(
    r"^\s*\(?\s*("
    r"ban hành kèm theo|căn cứ\b|xét đề nghị|theo đề nghị|nơi nhận|"
    r"thay mặt|tm\.|đã ký|quyết định số|nghị định số|thông tư số|nghị quyết số|"
    r"cộng hòa xã hội|độc lập\s*[-–]\s*tự do|kính gửi|số\s*:\s*\d)",
    re.I,
)


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
    """LLM identifies actual legal claims. Empty list if LLM unavailable."""
    return _extract_with_llm(text, target_document_id)


def _extract_with_llm(text: str, target_document_id: str) -> List[ComplianceClaim]:
    """LLM xác định điều khoản/nghĩa vụ thực sự — bỏ qua header/boilerplate."""
    try:
        from llm.client import get_client
        from llm.prompts import CLAIM_EXTRACTION_SYSTEM
        chunk_size = 4000
        chunks = [(text or "")[i:i + chunk_size] for i in range(0, len(text or ""), chunk_size)]
        claims: List[ComplianceClaim] = []
        current_section = None
        for chunk in chunks:
            data = get_client().complete_json(CLAIM_EXTRACTION_SYSTEM, chunk)
            items = data.get("claims") if isinstance(data, dict) else None
            if not isinstance(items, list):
                return []  # demo/mock → fallback to rule-based
            for item in items:
                claim_text = (item.get("text") or "").strip()
                if len(claim_text) < 15:
                    continue
                if item.get("section"):
                    current_section = item["section"]
                facts = mine_facts(claim_text)
                claims.append(ComplianceClaim(
                    claim_id=new_id("claim"),
                    target_document_id=target_document_id,
                    section=current_section,
                    text=claim_text,
                    facts=facts,
                ))
        return claims
    except Exception:
        return []


def _extract_rule_based(text: str, target_document_id: str) -> List[ComplianceClaim]:
    """Fallback rule-based extraction (original logic)."""
    claims: List[ComplianceClaim] = []
    section = None
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("[") or _BOILERPLATE_RE.match(line):
            continue
        if _SECTION_RE.match(line) and len(line) < 80 and not mine_facts(line).has_comparable():
            section = line
            continue
        for sent in _SENTENCE_SPLIT_RE.split(line):
            sent = sent.strip()
            if len(sent) < 15:
                continue
            facts = mine_facts(sent)
            if facts.has_comparable() or facts.doc_refs or _MODALITY_RE.search(sent):
                claims.append(ComplianceClaim(
                    claim_id=new_id("claim"),
                    target_document_id=target_document_id,
                    section=section,
                    text=sent,
                    facts=facts,
                ))
    return claims
