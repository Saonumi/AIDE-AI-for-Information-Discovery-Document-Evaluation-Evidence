"""Vietnamese legal number/date normalizer.

Why this exists: deterministic patch (step 10) and conflict/impact comparison
(steps 19-21) rely on EXACT value matching. In Vietnamese regulations the same
amount appears as "500 triệu đồng", "500.000.000", "500tr", "0,5 tỷ". Without
canonicalisation those comparisons silently fail. This module is the single place
that turns messy Vietnamese money/date text into canonical values.

Conventions handled:
  - "." is a thousands separator, "," is the decimal separator (vi-VN).
  - Units: tỷ/tỉ = 1e9, triệu/tr = 1e6, nghìn/ngàn/k = 1e3, đồng/đ/VND = 1.
  - Dates: dd/mm/yyyy, dd-mm-yyyy, yyyy-mm-dd, "ngày dd tháng mm năm yyyy".
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import List, Optional

_UNIT_MULT = {
    "tỷ": 1_000_000_000, "tỉ": 1_000_000_000, "ty": 1_000_000_000, "ti": 1_000_000_000,
    "triệu": 1_000_000, "trieu": 1_000_000, "tr": 1_000_000,
    "nghìn": 1_000, "nghin": 1_000, "ngàn": 1_000, "ngan": 1_000, "k": 1_000,
    "đồng": 1, "dong": 1, "vnd": 1, "đ": 1, "d": 1,
}

# Longest units first so "triệu" wins over "tr", "tỷ" over "ty".
_UNIT_ALT = "|".join(sorted(_UNIT_MULT.keys(), key=len, reverse=True))
_MONEY_RE = re.compile(
    r"(?P<num>\d[\d.,]*)\s*(?P<unit>" + _UNIT_ALT + r")?\b",
    re.IGNORECASE,
)


def parse_vn_number(s: str) -> Optional[float]:
    """Parse a vi-VN formatted numeric string to float."""
    s = s.strip()
    if not s:
        return None
    has_dot, has_comma = "." in s, "," in s
    try:
        if has_dot and has_comma:
            # dots = thousands, comma = decimal  -> "1.234.567,5"
            s = s.replace(".", "").replace(",", ".")
        elif has_comma:
            # comma = decimal -> "0,5"
            s = s.replace(",", ".")
        elif has_dot:
            if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
                # grouped thousands -> "500.000.000"
                s = s.replace(".", "")
            # else: a genuine decimal like "1.5" -> keep as-is
        return float(s)
    except ValueError:
        return None


def money_to_vnd(text: str) -> Optional[int]:
    """Return the first monetary amount in `text` as canonical integer VND."""
    if not text:
        return None
    m = _MONEY_RE.search(text)
    if not m:
        return None
    num = parse_vn_number(m.group("num"))
    if num is None:
        return None
    unit = (m.group("unit") or "").lower()
    mult = _UNIT_MULT.get(unit, 1)
    return int(round(num * mult))


def extract_all_money(text: str) -> List[int]:
    """All monetary amounts in text (canonical VND), in order of appearance."""
    out: List[int] = []
    for m in _MONEY_RE.finditer(text or ""):
        num = parse_vn_number(m.group("num"))
        if num is None:
            continue
        unit = (m.group("unit") or "").lower()
        # Skip bare integers with no unit that are actually part of a date etc.
        if unit == "" and num < 1000:
            continue
        out.append(int(round(num * _UNIT_MULT.get(unit, 1))))
    return out


def money_equal(a: str, b: str) -> bool:
    va, vb = money_to_vnd(a), money_to_vnd(b)
    return va is not None and va == vb


_DATE_PATTERNS = [
    (re.compile(r"\bngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})", re.I), (0, 1, 2)),
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), (2, 1, 0)),          # yyyy-mm-dd
    (re.compile(r"\b(\d{1,2})[/](\d{1,2})[/](\d{4})\b"), (0, 1, 2)),      # dd/mm/yyyy
    (re.compile(r"\b(\d{1,2})[-.](\d{1,2})[-.](\d{4})\b"), (0, 1, 2)),    # dd-mm-yyyy
]


def normalize_date(text: str) -> Optional[date]:
    """Extract the first date and return a datetime.date (or None)."""
    if not text:
        return None
    for pat, order in _DATE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        g = m.groups()
        d, mo, y = int(g[order[0]]), int(g[order[1]]), int(g[order[2]])
        try:
            return date(y, mo, d)
        except ValueError:
            continue
    return None


def strip_accents(text: str) -> str:
    """Fold Vietnamese diacritics — for accent-insensitive keyword matching."""
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")
