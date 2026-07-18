"""Standard RAG baseline (for the head-to-head).

This is the control the whole project is measured against. It does what a naive
vector-RAG stack does:
    - retrieve with filters {"approved_only": True} but NO temporal `valid_at`
      (so it sees ALL co-existing versions at once),
    - no graph expansion, no validity/supersession resolution,
    - dump the raw top-k straight into the LLM.

Because it never pins a query date, a question about the SME limit retrieves BOTH
V1 (500tr) and V2 (700tr) into the same context — version conflation. This function
demonstrates the failure mode; it is intentionally NOT correct.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from infra.embeddings import embed_one
from infra.opensearch_client import get_store
from llm.client import get_client
from llm.prompts import GENERATION_SYSTEM, build_evidence_block
from packages.contracts.enums import AnswerStatus
from packages.contracts.models import Answer, Citation, EvidenceItem

from query.hybrid_retrieval import DEFAULT_TOP_K, reciprocal_rank_fusion


def answer(text: str, query_date: Optional[date] = None, top_k: int = DEFAULT_TOP_K) -> Answer:
    """Naive RAG: no temporal filter, no graph, no validity — raw top-k to the LLM."""
    filters = {"approved_only": True}      # NOTE: deliberately no "valid_at"
    store = get_store()
    leg_k = max(top_k * 3, top_k)
    bm25 = store.bm25_search(text, filters, leg_k)
    knn = store.knn_search(embed_one(text), filters, leg_k)
    fused = reciprocal_rank_fusion([bm25, knn], top_k=top_k)

    items: List[EvidenceItem] = [_to_item(c) for c in fused]
    if not items:
        return Answer(
            text="INSUFFICIENT_EVIDENCE",
            citations=[],
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            query_date=query_date,
        )

    user = _naive_user(text, items)
    resp = get_client().complete(GENERATION_SYSTEM, user).strip()

    cited = {i.source_id for i in items if f"[{i.source_id}]" in resp}
    citations = [
        Citation(
            source_id=i.source_id,
            document_number=i.document_number,
            heading_path=list(i.heading_path),
            page=i.page,
        )
        for i in items
        if i.source_id in cited
    ]
    # Baseline reports SOURCE_GROUNDED only — it runs NO deterministic version checks,
    # so it cannot claim DETERMINISTIC_CHECKS_PASSED.
    return Answer(
        text=resp or "INSUFFICIENT_EVIDENCE",
        citations=citations,
        status=AnswerStatus.SOURCE_GROUNDED if resp else AnswerStatus.INSUFFICIENT_EVIDENCE,
        query_date=query_date,
    )


def retrieved_items(text: str, top_k: int = DEFAULT_TOP_K) -> List[EvidenceItem]:
    """Expose the raw (unfiltered-by-date) retrieval — used to show version conflation."""
    filters = {"approved_only": True}
    store = get_store()
    leg_k = max(top_k * 3, top_k)
    bm25 = store.bm25_search(text, filters, leg_k)
    knn = store.knn_search(embed_one(text), filters, leg_k)
    return [_to_item(c) for c in reciprocal_rank_fusion([bm25, knn], top_k=top_k)]


def _to_item(c: dict) -> EvidenceItem:
    def _d(v):
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v
    return EvidenceItem(
        source_id=c.get("version_id", c.get("chunk_id", "")),
        provision_id=c.get("provision_id", ""),
        version_id=c.get("version_id", ""),
        document_number=c.get("document_number"),
        heading_path=list(c.get("heading_path") or []),
        content=c.get("content", ""),
        page=c.get("page"),
        valid_from=_d(c.get("valid_from")),
        valid_to_exclusive=_d(c.get("valid_to_exclusive")),
        score=float(c.get("_rrf_score", c.get("_score", 0.0)) or 0.0),
    )


def _naive_user(text: str, items: List[EvidenceItem]) -> str:
    return (
        f"Câu hỏi: {text}\n\n<EVIDENCE>\n{build_evidence_block(items)}\n</EVIDENCE>\n\n"
        "Hãy trả lời dựa trên evidence, mỗi ý gắn [source_id]."
    )
