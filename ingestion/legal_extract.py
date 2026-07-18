"""Step 7 — Legal information extraction (REGEX-FIRST, LLM as enhancement).

Everything here MUST work offline with the mock LLM, so regex/rules are the primary
path and `llm.client.get_client().complete_json` is only called to *fill gaps* — it
never overrides a confident regex result and never decides validity.

Extracts, validated against the frozen Pydantic models:
  - DocumentMetadata  : document_number, issued_date, valid_from
  - Obligation        : subject/action/modality/condition/value (+ value_normalized VND)
  - CrossReference    : "theo Khoản X Điều Y" / "Điều Y"
  - Amendment         : Thay "OLD" bằng "NEW" tại <locator>, hiệu lực từ <date>

Why: cross-ref traversal, partial supersession and conflict detection all depend on
these structured fields.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from packages.common.vn_normalize import money_to_vnd, normalize_date
from packages.contracts.enums import AmendmentOperation, Modality
from packages.contracts.models import (
    Amendment,
    CrossReference,
    DocumentMetadata,
    Obligation,
    Scope,
)

# --------------------------------------------------------------------------- #
# Document metadata
# --------------------------------------------------------------------------- #
# e.g. "Quyết định số 01/2026/QĐ-HĐQT", "QĐ-01/2026", "Số: 02/2026/TT-NHNN"
_RE_DOCNO = re.compile(
    r"(?:S[ốô]\s*[:.]?\s*)?"
    r"(\d{1,4}\s*/\s*\d{4}\s*/\s*[A-Za-zĐđ\-\.]+"          # 01/2026/QĐ-HĐQT
    r"|[A-Za-zĐđ]+\s*[-–]\s*\d{1,4}\s*/\s*\d{4}"           # QĐ-01/2026
    r"|\d{1,4}\s*/\s*\d{4}\s*[-–]\s*[A-Za-zĐđ]+)",         # 01/2026-QĐ
)

_RE_ISSUED = re.compile(
    r"(?:ban\s+h[àa]nh|k[ýy])\s+(?:ng[àa]y\s+)?(.{0,40})", re.IGNORECASE)
_RE_VALID_FROM = re.compile(
    r"(?:hi[eệ]u\s+l[ựu]c|[áa]p\s+d[ụu]ng|thi\s+h[àa]nh)\s+(?:k[ểe]\s+t[ừu]\s+|t[ừu]\s+)?(?:ng[àa]y\s+)?(.{0,40})",
    re.IGNORECASE)


def extract_document_metadata(text: str) -> DocumentMetadata:
    """Regex-first metadata extraction over the (whole-document) text."""
    document_number = None
    m = _RE_DOCNO.search(text or "")
    if m:
        document_number = re.sub(r"\s+", "", m.group(1)).upper()

    issued_date = None
    m = _RE_ISSUED.search(text or "")
    if m:
        issued_date = normalize_date(m.group(1))

    valid_from = None
    m = _RE_VALID_FROM.search(text or "")
    if m:
        valid_from = normalize_date(m.group(1))

    return DocumentMetadata(
        document_number=document_number,
        issued_date=issued_date,
        valid_from=valid_from,
    )


# --------------------------------------------------------------------------- #
# Obligation
# --------------------------------------------------------------------------- #
_MODALITY_PROHIBITION = re.compile(
    r"\b(kh[ôo]ng\s+đ[ưu]?[ợo]c|c[ấa]m|nghi[êe]m\s+c[ấa]m|kh[ôo]ng\s+ph[ảa]i)\b", re.IGNORECASE)
_MODALITY_OBLIGATION = re.compile(
    r"\b(ph[ảa]i|b[ắa]t\s+bu[ộo]c|c[óo]\s+ngh[ĩi]a\s+v[ụu]|y[êe]u\s+c[ầa]u|[áa]p\s+d[ụu]ng)\b",
    re.IGNORECASE)
_MODALITY_PERMISSION = re.compile(
    r"\b(đ[ưu]?[ợo]c\s+ph[ée]p|c[óo]\s+th[ểe]|đ[ưu]?[ợo]c\s+quy[ềe]n)\b", re.IGNORECASE)

# "500 triệu đồng", "12 tháng", "30 ngày", "48 giờ" — the value phrase.
# The magnitude unit (tỷ/triệu/nghìn) may be followed by a currency word (đồng/VND);
# capture the whole phrase so obligation.value reads "500 triệu đồng", not "500 triệu".
_RE_VALUE = re.compile(
    r"(\d[\d.,]*\s*(?:t[ỷỉ]|tri[ệe]u|ngh[ìi]n|ng[àa]n|tr|k)\s*(?:đ[ồo]ng|vnd|đ)?"  # money
    r"|\d[\d.,]*\s*(?:đ[ồo]ng|vnd|th[áa]ng|ng[àa]y|gi[ờo]|n[ăa]m|%))\b",             # unit-only
    re.IGNORECASE)


def _detect_modality(content: str) -> Optional[Modality]:
    if _MODALITY_PROHIBITION.search(content):
        return Modality.PROHIBITION
    if _MODALITY_PERMISSION.search(content):
        return Modality.PERMISSION
    if _MODALITY_OBLIGATION.search(content):
        return Modality.OBLIGATION
    return None


def extract_obligation(content: str, source_provision: Optional[str] = None) -> Optional[Obligation]:
    """Extract a single obligation from one provision's content (regex heuristics)."""
    if not content or not content.strip():
        return None
    modality = _detect_modality(content)
    value = None
    value_normalized = None
    m = _RE_VALUE.search(content)
    if m:
        value = m.group(1).strip()
        # Only normalise to canonical VND when a monetary magnitude/currency unit is
        # present. Time/percentage values ("12 tháng", "30%") stay value_normalized=None
        # so they never pollute money-based conflict comparison.
        if re.search(r"t[ỷỉ]|tri[ệe]u|ngh[ìi]n|ng[àa]n|đ[ồo]ng|vnd|\btr\b|\bk\b", value, re.IGNORECASE):
            value_normalized = money_to_vnd(value)

    if modality is None and value is None:
        return None

    return Obligation(
        subject=None,
        action=None,
        modality=modality,
        condition=None,
        value=value,
        value_normalized=value_normalized,
        source_provision=source_provision,
        confidence=0.6 if modality else 0.5,
    )


def extract_scope(content: str) -> Optional[Scope]:
    """Lightweight scope hints used later for conflict/impact filtering."""
    if not content:
        return None
    lower = content.lower()
    customer_type = None
    for kw in ("sme", "doanh nghiệp nhỏ", "cá nhân", "doanh nghiệp lớn", "khách hàng"):
        if kw in lower:
            customer_type = kw.upper() if kw == "sme" else kw
            break
    if customer_type is None:
        return None
    return Scope(customer_type=customer_type)


# --------------------------------------------------------------------------- #
# Cross-reference
# --------------------------------------------------------------------------- #
# "theo Khoản 3 Điều 12", "quy định tại Điều 12", "Khoản 2 Điều 7"
_RE_XREF = re.compile(
    r"(?:Kho[ảa]n\s+(\d+)\s+)?Đi[eề]u\s+(\d+)"
    r"|Kho[ảa]n\s+(\d+)\s+Đi[eề]u\s+(\d+)",
    re.IGNORECASE)
_RE_XREF_TRIGGER = re.compile(
    r"\b(theo|quy\s+đ[ịi]nh\s+t[ạa]i|c[ăa]n\s+c[ứu]|d[ẫa]n\s+chi[ếe]u|t[ạa]i)\b", re.IGNORECASE)


def extract_cross_references(content: str, source_provision: str,
                             self_article: Optional[str] = None,
                             self_clause: Optional[str] = None) -> List[CrossReference]:
    """Detect locators referenced by this provision (only when a trigger word appears)."""
    if not content:
        return []
    refs: List[CrossReference] = []
    seen = set()
    for m in _RE_XREF.finditer(content):
        # only accept a match that is preceded by a reference trigger word
        prefix = content[max(0, m.start() - 40):m.start()]
        if not _RE_XREF_TRIGGER.search(prefix):
            continue
        clause = m.group(1) or m.group(3)
        article = m.group(2) or m.group(4)
        if not article:
            continue
        # skip a self-reference
        if self_article == article and (clause is None or self_clause == clause):
            continue
        if clause:
            locator = f"Khoản {clause} Điều {article}"
        else:
            locator = f"Điều {article}"
        if locator in seen:
            continue
        seen.add(locator)
        refs.append(CrossReference(
            source_provision=source_provision,
            target_locator=locator,
            confidence=0.7,
        ))
    return refs


# --------------------------------------------------------------------------- #
# Amendment  (the canonical SME 500->700 pattern)
# --------------------------------------------------------------------------- #
# Thay "500 triệu đồng" bằng "700 triệu đồng" tại Khoản 2 Điều 7, hiệu lực từ 01/07/2026
_QUOTE = r'["“”\'‘’]'
_RE_REPLACE = re.compile(
    r"Thay\s+" + _QUOTE + r"(?P<old>.+?)" + _QUOTE +
    r"\s+b[ằa]ng\s+" + _QUOTE + r"(?P<new>.+?)" + _QUOTE +
    r"\s+t[ạa]i\s+(?P<loc>.+?)"
    r"(?:,?\s*hi[eệ]u\s+l[ựu]c\s+(?:k[ểe]\s+t[ừu]\s+|t[ừu]\s+)?(?:ng[àa]y\s+)?(?P<date>.+?))?"
    r"(?:\.|$)",
    re.IGNORECASE | re.DOTALL)

# Bổ sung "..." vào <locator>, hiệu lực từ ...
_RE_INSERT = re.compile(
    r"B[ổo]\s+sung\s+" + _QUOTE + r"(?P<new>.+?)" + _QUOTE +
    r"\s+(?:v[àa]o\s+)?t[ạa]i\s+(?P<loc>.+?)"
    r"(?:,?\s*hi[eệ]u\s+l[ựu]c\s+(?:k[ểe]\s+t[ừu]\s+|t[ừu]\s+)?(?:ng[àa]y\s+)?(?P<date>.+?))?"
    r"(?:\.|$)",
    re.IGNORECASE | re.DOTALL)

# Bãi bỏ "..." tại <locator>  /  Xóa "..." tại <locator>
_RE_DELETE = re.compile(
    r"(?:X[óo]a|B[ỏo])\s+" + _QUOTE + r"(?P<old>.+?)" + _QUOTE +
    r"\s+t[ạa]i\s+(?P<loc>.+?)"
    r"(?:,?\s*hi[eệ]u\s+l[ựu]c\s+(?:k[ểe]\s+t[ừu]\s+|t[ừu]\s+)?(?:ng[àa]y\s+)?(?P<date>.+?))?"
    r"(?:\.|$)",
    re.IGNORECASE | re.DOTALL)

# Bãi bỏ Khoản 2 Điều 7 (repeal the whole provision)
_RE_REPEAL = re.compile(
    r"B[ãa]i\s+b[ỏo]\s+(?P<loc>(?:Kho[ảa]n\s+\d+\s+)?Đi[eề]u\s+\d+.*?)"
    r"(?:,?\s*hi[eệ]u\s+l[ựu]c\s+(?:k[ểe]\s+t[ừu]\s+|t[ừu]\s+)?(?:ng[àa]y\s+)?(?P<date>.+?))?"
    r"(?:\.|$)",
    re.IGNORECASE | re.DOTALL)

# Normalise a locator string to a canonical "Khoản X Điều Y" / "Điều Y".
_RE_LOC_PARTS = re.compile(
    r"(?:Kho[ảa]n\s+(?P<clause>\d+))?"
    r"[\s,]*Đi[eề]u\s+(?P<article>\d+)"
    r"(?:[\s,]*Đi[eể]m\s+(?P<point>[a-zđ]))?",
    re.IGNORECASE)


def normalize_locator(raw: str) -> Optional[Tuple[Optional[str], Optional[str], Optional[str]]]:
    """Parse a locator into (article, clause, point). Returns None if no Điều found."""
    if not raw:
        return None
    m = _RE_LOC_PARTS.search(raw)
    if not m:
        return None
    return (m.group("article"), m.group("clause"), m.group("point"))


def locator_to_text(article: Optional[str], clause: Optional[str], point: Optional[str]) -> str:
    parts = []
    if point:
        parts.append(f"Điểm {point}")
    if clause:
        parts.append(f"Khoản {clause}")
    if article:
        parts.append(f"Điều {article}")
    return " ".join(parts)


def _canon_locator(raw: str) -> str:
    parsed = normalize_locator(raw)
    if parsed:
        art, cl, pt = parsed
        canon = locator_to_text(art, cl, pt)
        if canon:
            return canon
    return raw.strip().rstrip(",.")


def extract_amendments(text: str, source_page: Optional[int] = None) -> List[Amendment]:
    """Detect amendment operations anywhere in an amending document's text.

    Handles REPLACE_TEXT (the canonical case), INSERT_TEXT, DELETE_TEXT and
    REPEAL_PROVISION. valid_from is parsed via normalize_date; if absent it defaults
    to date.min sentinel is avoided — instead we skip amendments with no parseable
    date only when required. Here we keep them but caller may review.
    """
    amendments: List[Amendment] = []
    if not text:
        return amendments

    def _date(mgroup: Optional[str]) -> Optional[date]:
        return normalize_date(mgroup) if mgroup else None

    for m in _RE_REPLACE.finditer(text):
        vf = _date(m.group("date"))
        if vf is None:
            continue
        amendments.append(Amendment(
            operation=AmendmentOperation.REPLACE_TEXT,
            old_text=m.group("old").strip(),
            new_text=m.group("new").strip(),
            target_locator=_canon_locator(m.group("loc")),
            valid_from=vf,
            source_page=source_page,
            confidence=0.9,
        ))

    for m in _RE_INSERT.finditer(text):
        vf = _date(m.group("date"))
        if vf is None:
            continue
        amendments.append(Amendment(
            operation=AmendmentOperation.INSERT_TEXT,
            old_text=None,
            new_text=m.group("new").strip(),
            target_locator=_canon_locator(m.group("loc")),
            valid_from=vf,
            source_page=source_page,
            confidence=0.8,
        ))

    for m in _RE_DELETE.finditer(text):
        vf = _date(m.group("date"))
        if vf is None:
            continue
        amendments.append(Amendment(
            operation=AmendmentOperation.DELETE_TEXT,
            old_text=m.group("old").strip(),
            new_text=None,
            target_locator=_canon_locator(m.group("loc")),
            valid_from=vf,
            source_page=source_page,
            confidence=0.8,
        ))

    for m in _RE_REPEAL.finditer(text):
        vf = _date(m.group("date"))
        if vf is None:
            continue
        loc = _canon_locator(m.group("loc"))
        amendments.append(Amendment(
            operation=AmendmentOperation.REPEAL_PROVISION,
            old_text=None,
            new_text=None,
            target_locator=loc,
            valid_from=vf,
            source_page=source_page,
            confidence=0.85,
        ))

    return amendments


# --------------------------------------------------------------------------- #
# LLM enhancement (optional, gap-filling only)
# --------------------------------------------------------------------------- #
def enhance_metadata_with_llm(text: str, base: DocumentMetadata) -> DocumentMetadata:
    """Ask the LLM only for fields regex could not fill. Never overrides regex.

    Uses the mock-safe get_client().complete_json (returns {} in demo/tests).
    """
    if base.document_number and base.valid_from and base.issued_date:
        return base
    try:
        from llm.client import get_client
        from llm.prompts import EXTRACTION_SYSTEM
        data = get_client().complete_json(
            EXTRACTION_SYSTEM,
            "Trích xuất metadata (document_number, issued_date, valid_from) dạng "
            "JSON từ văn bản sau:\n" + text[:4000],
        )
    except Exception:
        return base
    if not isinstance(data, dict) or not data:
        return base
    updated = base.model_copy()
    if not updated.document_number and data.get("document_number"):
        updated.document_number = str(data["document_number"])
    if not updated.issued_date and data.get("issued_date"):
        updated.issued_date = normalize_date(str(data["issued_date"]))
    if not updated.valid_from and data.get("valid_from"):
        updated.valid_from = normalize_date(str(data["valid_from"]))
    return updated


def llm_extract_provisions(full_text: str) -> List[Dict[str, Any]]:
    """LLM trích xuất điều khoản từ toàn văn — fallback về [] nếu lỗi/demo."""
    try:
        from llm.client import get_client
        from llm.prompts import PROVISION_EXTRACTION_SYSTEM
        chunk_size = 3500
        text = full_text.strip()
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        all_provisions: List[Dict[str, Any]] = []
        for chunk in chunks:
            data = get_client().complete_json(PROVISION_EXTRACTION_SYSTEM, chunk)
            items = data.get("provisions") if isinstance(data, dict) else None
            if isinstance(items, list):
                all_provisions.extend(items)
        return all_provisions
    except Exception:
        return []


def extract_all(text: str, source_page: Optional[int] = None, use_llm: bool = True) -> Dict[str, Any]:
    """Convenience aggregate over a whole document's text."""
    metadata = extract_document_metadata(text)
    if use_llm:
        metadata = enhance_metadata_with_llm(text, metadata)
    return {
        "metadata": metadata,
        "amendments": extract_amendments(text, source_page=source_page),
    }
