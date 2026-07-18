"""Shared crawl helpers: sitemap parsing, banking keyword filter, HTML->text."""
from __future__ import annotations

import re
from typing import Iterator, List, Optional

from crawl.http_client import RespectfulClient

# Banking/finance keywords to keep the pilot focused (match slug or title, accent-insensitive).
BANKING_KEYWORDS = [
    "ngan hang", "tin dung", "tien te", "tai chinh", "ngoai hoi", "lai suat",
    "thanh toan", "tai san bao dam", "bao dam tien vay", "cho vay", "huy dong von",
    "an toan von", "no xau", "phong chong rua tien", "nhnn", "to chuc tin dung",
    "bao lanh", "the ngan hang", "trung gian thanh toan", "quy tin dung",
]
AMENDMENT_KEYWORDS = ["sua doi", "bo sung", "thay the", "bai bo", "hop nhat", "dinh chinh"]


def _fold(s: str) -> str:
    from packages.common.vn_normalize import strip_accents
    # normalise slug separators (-, _, ., /) to spaces so URL slugs match keywords
    return re.sub(r"[-_./]+", " ", strip_accents((s or "").lower()))


def is_banking(text: str) -> bool:
    f = _fold(text)
    return any(k in f for k in BANKING_KEYWORDS)


def is_amendment(text: str) -> bool:
    f = _fold(text)
    return any(k in f for k in AMENDMENT_KEYWORDS)


_LOC_RE = re.compile(r"<loc>\s*([^<]+?)\s*</loc>", re.IGNORECASE)


def iter_sitemap_locs(client: RespectfulClient, sitemap_url: str) -> Iterator[str]:
    """Yield <loc> URLs from a sitemap (single level; caller recurses on indexes)."""
    xml = client.get(sitemap_url, ext="xml")
    if not xml:
        return
    for m in _LOC_RE.finditer(xml):
        yield m.group(1)


def html_to_text(html: str) -> str:
    """Extract readable text from an HTML page (drops script/style/nav)."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text("\n")
        lines = [ln.strip() for ln in text.splitlines()]
        return "\n".join(ln for ln in lines if ln)
    except Exception:
        # crude fallback
        return re.sub(r"<[^>]+>", " ", html)


# Vietnamese legal document-number pattern, e.g. 39/2016/TT-NHNN, 06/2023/TT-NHNN
DOC_NUMBER_RE = re.compile(r"\b(\d{1,4}/\d{4}/[A-ZĐ]{1,6}(?:-[A-ZĐ]{1,8})?)\b")


def extract_doc_number(text: str) -> Optional[str]:
    m = DOC_NUMBER_RE.search(text or "")
    return m.group(1) if m else None


def guess_doc_type(title_or_number: str):
    from crawl.models import DocType
    f = _fold(title_or_number)
    table = [
        ("thong tu", DocType.THONG_TU), ("nghi dinh", DocType.NGHI_DINH),
        ("quyet dinh", DocType.QUYET_DINH), ("luat", DocType.LUAT),
        ("cong van", DocType.CONG_VAN), ("chi thi", DocType.CHI_THI),
        ("nghi quyet", DocType.NGHI_QUYET), ("phap lenh", DocType.PHAP_LENH),
        ("hop nhat", DocType.VAN_BAN_HOP_NHAT), ("thong bao", DocType.THONG_BAO),
    ]
    for kw, dt in table:
        if kw in f:
            return dt
    return None
