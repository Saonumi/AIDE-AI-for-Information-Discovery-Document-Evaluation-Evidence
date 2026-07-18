"""Step 3 — File/Text security & prompt-injection scan.

A document is DATA, never instructions. Before anything else we scan the raw text
for known indirect-injection phrases ("ignore previous instructions", "system
prompt", "execute command", "call tool", "send data"). A hit does not block the
pipeline — it flags `injection_suspected=True` and raises an INJECTION_REVIEW task
so an employee inspects the source before the doc is ever activated/indexed.

Detection is accent-insensitive (Vietnamese docs may fold diacritics) and matches
both English and common Vietnamese equivalents.
"""
from __future__ import annotations

import re
from typing import List

from packages.common.vn_normalize import strip_accents

# Patterns are matched against the accent-folded, lower-cased text.
_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions"),
    re.compile(r"ignore\s+(all\s+)?prior\s+instructions"),
    re.compile(r"disregard\s+(all\s+)?previous\s+instructions"),
    re.compile(r"bo\s+qua\s+(moi\s+|tat\s+ca\s+|cac\s+)?(chi\s+dan|huong\s+dan|lenh)"),  # bỏ qua ... chỉ dẫn
    re.compile(r"system\s+prompt"),
    re.compile(r"reveal\s+.{0,20}?(system|confidential)\s+prompt"),
    re.compile(r"execute\s+command"),
    re.compile(r"run\s+command"),
    re.compile(r"call\s+tool"),
    re.compile(r"send\s+data"),
    re.compile(r"exfiltrate"),
]


def scan_text(text: str) -> List[str]:
    """Return the list of injection phrases detected (empty == clean)."""
    if not text:
        return []
    folded = strip_accents(text).lower()
    hits: List[str] = []
    for pat in _INJECTION_PATTERNS:
        m = pat.search(folded)
        if m:
            hits.append(m.group(0).strip())
    # de-dup preserving order
    seen = set()
    out = []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def is_suspicious(text: str) -> bool:
    return bool(scan_text(text))
