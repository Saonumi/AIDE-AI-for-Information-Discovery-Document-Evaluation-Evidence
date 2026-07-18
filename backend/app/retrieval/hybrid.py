"""Step 16 — Hybrid retrieval (BM25 + kNN) fused with Reciprocal Rank Fusion.

BM25 is strong on exact tokens (document numbers, "Điều/Khoản", product codes);
dense kNN is strong on paraphrase / natural-language questions. We run both against
the SAME temporal filter (so both legs are already pinned to versions valid at
query_date), then fuse their rankings with RRF (k≈60) — rank-based fusion needs no
score calibration between the two very different scoring scales.

Output: a small ranked list (top 5–10) of seed chunk dicts.
"""
from __future__ import annotations

from typing import Any, Dict, List

from infra.embeddings import embed_one
from infra.opensearch_client import get_store

RRF_K = 60
DEFAULT_TOP_K = 8
# Pull a few more per leg than we keep, so fusion has material to work with.
LEG_MULTIPLIER = 3
RELEVANCE_THRESHOLD = 0.005  # ponytail: RRF score cutoff, tăng nếu false positive nhiều


def _key(doc: Dict[str, Any]) -> str:
    return doc.get("chunk_id") or doc.get("version_id") or id(doc)


def reciprocal_rank_fusion(
    ranked_lists: List[List[Dict[str, Any]]],
    k: int = RRF_K,
    top_k: int = DEFAULT_TOP_K,
) -> List[Dict[str, Any]]:
    """Fuse several ranked lists of chunk dicts into one, by RRF.

    RRF score(d) = sum over lists of 1 / (k + rank_in_list(d)), rank starting at 1.
    """
    scores: Dict[str, float] = {}
    docs: Dict[str, Dict[str, Any]] = {}
    for ranked in ranked_lists:
        for rank, doc in enumerate(ranked, start=1):
            kk = _key(doc)
            scores[kk] = scores.get(kk, 0.0) + 1.0 / (k + rank)
            # keep the first-seen doc payload (they're identical across legs)
            docs.setdefault(kk, doc)
    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    out: List[Dict[str, Any]] = []
    for kk, score in fused[:top_k]:
        d = dict(docs[kk])
        d["_rrf_score"] = score
        out.append(d)
    return out


def hybrid_search(
    text: str,
    filters: Dict[str, Any],
    top_k: int = DEFAULT_TOP_K,
    require_lexical: bool = True,
) -> List[Dict[str, Any]]:
    """Run BM25 + kNN under the given (temporal) filter and fuse with RRF.

    Abstention gate: with `require_lexical` (default), if BM25 returns nothing the
    query has no lexical grounding in the corpus so we abstain entirely (return []).
    When BM25 does return results, both legs are fused independently via RRF — kNN
    is NOT filtered down to lexical hits so semantic recall is preserved. A final
    RELEVANCE_THRESHOLD on the RRF score drops near-zero-relevance candidates.
    """
    store = get_store()
    leg_k = max(top_k * LEG_MULTIPLIER, top_k)
    bm25 = store.bm25_search(text, filters, leg_k)

    if require_lexical and not bm25:
        return []  # no lexical grounding -> abstain

    query_embedding = embed_one(text)
    knn = store.knn_search(query_embedding, filters, leg_k)

    fused = reciprocal_rank_fusion([bm25, knn], k=RRF_K, top_k=top_k)
    # ponytail: threshold loại chunks gần như không liên quan
    return [d for d in fused if d.get("_rrf_score", 0) >= RELEVANCE_THRESHOLD]
