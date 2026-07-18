"""Vietnamese word segmentation for BM25.

Vietnamese does not delimit words by spaces the way English does ("hạn mức" is one
concept). Feeding whitespace tokens to BM25 weakens lexical matching. We segment
with underthesea when available and fall back to a safe whitespace tokenizer so the
module never hard-fails if the optional dependency is missing.
"""
from __future__ import annotations

import re

_WORD_RE = re.compile(r"\w+", re.UNICODE)
_seg = None
_seg_tried = False

# Interrogatives / copulas / function words. Removed from the QUERY side of BM25 so
# an out-of-corpus question doesn't match a clause merely by sharing "là"/"bao nhiêu"
# (that would defeat abstention on the in-memory demo backend).
STOPWORDS = {
    "là", "và", "của", "cho", "các", "những", "được", "có", "không", "bao",
    "nhiêu", "ở", "tại", "một", "để", "với", "khi", "thì", "mà", "này", "đó",
    "gì", "nào", "ra", "vào", "đây", "đâu", "bằng", "trong", "trên", "dưới",
    "hay", "hoặc", "nếu", "vì", "do", "bởi", "về", "từ", "đến", "sẽ", "đã",
}


def _get_segmenter():
    global _seg, _seg_tried
    if _seg_tried:
        return _seg
    _seg_tried = True
    try:
        from underthesea import word_tokenize  # type: ignore
        _seg = word_tokenize
    except Exception:  # pragma: no cover - optional dep
        _seg = None
    return _seg


def tokenize(text: str) -> str:
    """Return a space-joined token string suitable for a BM25 analyzer."""
    if not text:
        return ""
    seg = _get_segmenter()
    if seg is not None:
        try:
            # format="text" joins multi-syllable words with underscores
            return seg(text.lower(), format="text")
        except Exception:  # pragma: no cover
            pass
    return " ".join(_WORD_RE.findall(text.lower()))


def tokens(text: str) -> list[str]:
    return tokenize(text).split()


def content_tokens(text: str) -> list[str]:
    """Tokens with stopwords removed — for lexical-overlap scoring / abstention."""
    return [t for t in tokens(text) if t not in STOPWORDS and len(t) > 1]
