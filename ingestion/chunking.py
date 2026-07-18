"""Step 6 — Clause-aware chunking.

The retrieval unit is a Khoản/Điểm (a provision), NOT an arbitrary 500-token window.
One provision == one chunk; a very long provision is split into sub-chunks that
SHARE the same provision_id (and version_id) so the graph/temporal identity is
preserved. The heading_path is prepended to the embedding text (via Chunk.embedding_text)
so lexical/semantic retrieval keeps structural context.

`build_chunks_for_version` produces the chunk-dict SHAPE that Track B reads from the
store. Chunks are built at activation time with the resolved provision_id/version_id
and temporal window.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from packages.contracts.models import Chunk

# A provision longer than this many characters is sub-chunked.
_MAX_CHARS = 900
_OVERLAP = 80


def _split_long(content: str, max_chars: int = _MAX_CHARS, overlap: int = _OVERLAP) -> List[str]:
    """Split on sentence boundaries first, greedily packing into <= max_chars pieces."""
    content = content.strip()
    if len(content) <= max_chars:
        return [content]
    # sentence-ish split keeping delimiters
    import re
    sentences = re.split(r"(?<=[\.;:])\s+", content)
    pieces: List[str] = []
    buf = ""
    for s in sentences:
        if not s:
            continue
        if buf and len(buf) + 1 + len(s) > max_chars:
            pieces.append(buf.strip())
            # carry a short overlap for continuity
            tail = buf[-overlap:] if overlap else ""
            buf = (tail + " " + s).strip()
        else:
            buf = (buf + " " + s).strip()
    if buf.strip():
        pieces.append(buf.strip())
    # Fallback: any single sentence still too long -> hard-wrap
    out: List[str] = []
    for p in pieces:
        if len(p) <= max_chars:
            out.append(p)
        else:
            for i in range(0, len(p), max_chars - overlap):
                out.append(p[i:i + max_chars])
    return out or [content]


def chunk_texts_for_content(content: str) -> List[str]:
    """Return the list of chunk texts for one provision's content."""
    return _split_long(content)


def build_chunk_dict(
    *,
    chunk_id: str,
    provision_id: str,
    version_id: str,
    document_id: str,
    document_number: Optional[str],
    heading_path: List[str],
    content: str,
    page: Optional[int],
    valid_from: date,
    valid_to_exclusive: Optional[date],
    approval_status: str = "APPROVED",
) -> Dict[str, Any]:
    """Assemble one chunk dict in the exact SHAPE Track B consumes.

    Dates are serialised to ISO strings (the store filter accepts str or date).
    """
    return {
        "chunk_id": chunk_id,
        "provision_id": provision_id,
        "version_id": version_id,
        "document_id": document_id,
        "document_number": document_number,
        "heading_path": list(heading_path or []),
        "content": content,
        "page": page,
        "valid_from": valid_from.isoformat() if isinstance(valid_from, date) else valid_from,
        "valid_to_exclusive": (
            valid_to_exclusive.isoformat() if isinstance(valid_to_exclusive, date)
            else valid_to_exclusive
        ),
        "approval_status": approval_status,
    }


def embedding_text_for(heading_path: List[str], content: str) -> str:
    """Prepend heading path so retrieval keeps structural context.

    Mirrors Chunk.embedding_text() (the frozen contract) exactly.
    """
    return Chunk(
        chunk_id="_", provision_id="_", version_id="_", document_id="_",
        heading_path=list(heading_path or []), content=content,
        valid_from=date(2000, 1, 1),
    ).embedding_text()


def build_chunks_for_version(
    *,
    provision_id: str,
    version_id: str,
    document_id: str,
    document_number: Optional[str],
    heading_path: List[str],
    content: str,
    page: Optional[int],
    valid_from: date,
    valid_to_exclusive: Optional[date],
    new_chunk_id,
    approval_status: str = "APPROVED",
) -> List[Dict[str, Any]]:
    """Build one-or-more chunk dicts for a single provision version.

    `new_chunk_id` is a zero-arg callable returning a fresh chunk id (injected so the
    caller controls id generation, e.g. ids.new_id).
    """
    texts = chunk_texts_for_content(content)
    chunks: List[Dict[str, Any]] = []
    for text in texts:
        chunks.append(build_chunk_dict(
            chunk_id=new_chunk_id(),
            provision_id=provision_id,
            version_id=version_id,
            document_id=document_id,
            document_number=document_number,
            heading_path=heading_path,
            content=text,
            page=page,
            valid_from=valid_from,
            valid_to_exclusive=valid_to_exclusive,
            approval_status=approval_status,
        ))
    return chunks
