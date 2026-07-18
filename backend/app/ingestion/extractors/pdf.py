"""Step 4 — PDF/DOCX text + layout extraction.

Produces a flat list of layout blocks:
    {"page": int, "text": str, "bbox": [x0,y0,x1,y1]|None, "is_bold": bool}

PyMuPDF (fitz) gives per-span text, bbox, font-flags (bold bit) and page number so
citations point to the right page and the structure parser can use bold as a heading
signal. python-docx handles .docx. A plain-text fallback (`extract_text_blocks_from_text`)
keeps the pipeline fully testable offline where PyMuPDF is not installed.

Imports of fitz/docx are lazy so importing this module never hard-fails.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

Block = Dict[str, Any]

# PyMuPDF font flag bit 4 (value 16) marks bold spans.
_FITZ_BOLD_FLAG = 1 << 4


def _blank(text: str) -> bool:
    return not text or not text.strip()


def extract_text_blocks_from_pdf(path: str) -> List[Block]:
    """Extract per-line blocks from a text PDF using PyMuPDF."""
    import fitz  # type: ignore  # lazy — only needed for real PDFs

    blocks: List[Block] = []
    doc = fitz.open(path)
    try:
        for pno in range(len(doc)):
            page = doc[pno]
            data = page.get_text("dict")
            for blk in data.get("blocks", []):
                for line in blk.get("lines", []):
                    spans = line.get("spans", [])
                    if not spans:
                        continue
                    text = "".join(s.get("text", "") for s in spans)
                    if _blank(text):
                        continue
                    # a line is "bold" if any span carries the bold flag
                    is_bold = any(int(s.get("flags", 0)) & _FITZ_BOLD_FLAG for s in spans)
                    bbox = list(line.get("bbox", spans[0].get("bbox", (0, 0, 0, 0))))
                    blocks.append({
                        "page": pno + 1,
                        "text": text.strip(),
                        "bbox": bbox,
                        "is_bold": bool(is_bold),
                    })
    finally:
        doc.close()
    return blocks


def extract_text_blocks_from_docx(path: str) -> List[Block]:
    """Extract paragraph blocks from a .docx. Page numbers are unknown -> None."""
    import docx  # type: ignore  # python-docx

    document = docx.Document(path)
    blocks: List[Block] = []
    for para in document.paragraphs:
        text = para.text
        if _blank(text):
            continue
        runs = para.runs
        is_bold = bool(runs) and any(r.bold for r in runs)
        blocks.append({
            "page": None,
            "text": text.strip(),
            "bbox": None,
            "is_bold": bool(is_bold),
        })
    return blocks


def extract_text_blocks_from_text(text: str, page: Optional[int] = None) -> List[Block]:
    """Plain-text fallback: one block per non-blank line (used by tests / .txt).

    A line typed in ALL CAPS or starting with a heading keyword is a weak bold
    signal, but we keep it simple: is_bold defaults False; the structure parser
    relies on regex, not font, so this is sufficient.
    """
    blocks: List[Block] = []
    cur_page = page if page is not None else 1
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        # Support an explicit page marker for tests: "<<<PAGE 3>>>"
        if line.upper().startswith("<<<PAGE") and line.endswith(">>>"):
            try:
                cur_page = int("".join(ch for ch in line if ch.isdigit()))
            except ValueError:
                pass
            continue
        blocks.append({"page": cur_page, "text": line, "bbox": None, "is_bold": False})
    return blocks


def extract_text_blocks(path_or_text: str, *, is_text: bool = False) -> List[Block]:
    """Dispatch on file extension. Pass is_text=True to treat the arg as raw text.

    - "*.pdf" -> PyMuPDF
    - "*.docx" -> python-docx
    - "*.txt" or is_text=True -> plain-text fallback
    """
    if is_text:
        return extract_text_blocks_from_text(path_or_text)
    lower = path_or_text.lower()
    if lower.endswith(".pdf"):
        return extract_text_blocks_from_pdf(path_or_text)
    if lower.endswith(".docx"):
        return extract_text_blocks_from_docx(path_or_text)
    if lower.endswith(".txt"):
        with open(path_or_text, "r", encoding="utf-8") as fh:
            return extract_text_blocks_from_text(fh.read())
    # Unknown extension but a real path — read as text.
    try:
        with open(path_or_text, "r", encoding="utf-8") as fh:
            return extract_text_blocks_from_text(fh.read())
    except (OSError, UnicodeDecodeError):
        # Treat the string itself as text content.
        return extract_text_blocks_from_text(path_or_text)


def blocks_to_text(blocks: List[Block]) -> str:
    """Join block texts back into a newline document (for regex-wide extraction)."""
    return "\n".join(b["text"] for b in blocks)
