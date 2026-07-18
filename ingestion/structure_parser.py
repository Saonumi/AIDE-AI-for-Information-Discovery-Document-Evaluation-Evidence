"""Step 5 — Structure parsing.

Turns a flat block list into a legal hierarchy:

    Document -> Chương -> Điều -> Khoản -> Điểm

Boundaries are detected by regex on line starts (per docs/final_pipeline.md step 5):
    ^CHƯƠNG            -> Chương
    ^Điều\\s+\\d+       -> Điều (article)
    ^\\d+\\.            -> Khoản (clause)
    ^[a-z]\\)           -> Điểm (point)

A "provision" is the smallest addressable unit that carries content: a Khoản, or a
Điểm inside a Khoản, or (if an Điều has body text before any Khoản) the Điều itself.
Each provision records heading_path, article, clause, point, content and page.

Output is a list of dicts (employee-correctable later via PARSING_REVIEW):
    {"heading_path": [...], "article": str|None, "clause": str|None,
     "point": str|None, "content": str, "page": int|None,
     "chapter": str|None, "article_title": str|None}
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

Block = Dict[str, Any]
Provision = Dict[str, Any]

_RE_CHUONG = re.compile(r"^CH[ƯU]?[ƠO]NG\s+([IVXLCDM\d]+)\b(.*)$", re.IGNORECASE)
_RE_DIEU = re.compile(r"^\s*Đi[eề]u\s+(\d+)\s*[\.\:]?\s*(.*)$", re.IGNORECASE)
_RE_KHOAN = re.compile(r"^\s*(\d+)\s*[\.\)]\s+(.*)$")
_RE_DIEM = re.compile(r"^\s*([a-zđ])\s*\)\s*(.*)$", re.IGNORECASE)


def _mk_heading_path(chapter: Optional[str], article: Optional[str],
                     clause: Optional[str], point: Optional[str]) -> List[str]:
    parts: List[str] = []
    if chapter:
        parts.append(f"Chương {chapter}")
    if article:
        parts.append(f"Điều {article}")
    if clause:
        parts.append(f"Khoản {clause}")
    if point:
        parts.append(f"Điểm {point}")
    return parts


def parse_structure(blocks: List[Block]) -> List[Provision]:
    """Parse layout blocks into a flat list of provisions.

    Text lines that belong to the current-most-specific unit are appended to its
    content (so a clause split across several lines stays one provision).
    """
    provisions: List[Provision] = []

    chapter: Optional[str] = None
    article: Optional[str] = None
    article_title: Optional[str] = None
    clause: Optional[str] = None
    point: Optional[str] = None

    current: Optional[Provision] = None

    def flush():
        nonlocal current
        if current is not None and current["content"].strip():
            current["content"] = current["content"].strip()
            provisions.append(current)
        current = None

    def start(page: Optional[int], first_text: str):
        nonlocal current
        flush()
        current = {
            "heading_path": _mk_heading_path(chapter, article, clause, point),
            "chapter": chapter,
            "article": article,
            "article_title": article_title,
            "clause": clause,
            "point": point,
            "content": first_text,
            "page": page,
        }

    for blk in blocks:
        text = (blk.get("text") or "").strip()
        if not text:
            continue
        page = blk.get("page")

        m = _RE_CHUONG.match(text)
        if m:
            flush()
            chapter = m.group(1).strip()
            article = article_title = clause = point = None
            current = None
            continue

        m = _RE_DIEU.match(text)
        if m:
            flush()
            article = m.group(1).strip()
            article_title = (m.group(2) or "").strip() or None
            clause = point = None
            # An Điều may carry body text directly (rare) — start a provision only
            # when a Khoản/Điểm appears; but capture the article as an open provision
            # so content typed before the first Khoản is not lost.
            start(page, "")
            continue

        m = _RE_DIEM.match(text)
        # Điểm must sit inside a Khoản; only treat "a)" as a point if we already
        # have a clause context, else it's just body text.
        if m and clause is not None:
            point = m.group(1).strip().lower()
            start(page, m.group(2).strip())
            continue

        m = _RE_KHOAN.match(text)
        if m and article is not None:
            clause = m.group(1).strip()
            point = None
            start(page, m.group(2).strip())
            continue

        # Continuation line — append to the current provision (create one under the
        # current Điều if none open yet).
        if current is None:
            if article is not None:
                start(page, text)
            else:
                # preamble before any Điều — skip (metadata handled elsewhere)
                continue
        else:
            current["content"] = (current["content"] + " " + text).strip()
            if current.get("page") is None:
                current["page"] = page

    flush()
    return [p for p in provisions if p["content"].strip()]


def parse_document_text(text: str) -> List[Provision]:
    """Convenience: parse a raw text document (each line = a block)."""
    from ingestion.pdf_extract import extract_text_blocks_from_text
    return parse_structure(extract_text_blocks_from_text(text))
