"""OpenSearch store: BM25 + kNN vector, with temporal/approval pre-filtering.

CRITICAL INVARIANT: the approval + temporal filter is applied INSIDE the search
query (a filter clause), so top-k is drawn only from versions valid at query_date.
This is the temporal pre-filter — it must run before ranking, never after.

`get_store()` returns a real OpenSearchStore, or an InMemoryStore (demo_mode / no
service) that honours the same filter semantics so behaviour is identical in demos.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from infra.embeddings import cosine
from packages.common.config import get_settings
from packages.common.vn_tokenize import content_tokens, tokens

_store = None


def _passes_filter(doc: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """Shared filter semantics: approval + half-open temporal validity."""
    if filters.get("approved_only", True) and doc.get("approval_status") != "APPROVED":
        return False
    valid_at: Optional[date] = filters.get("valid_at")
    if valid_at is not None:
        vf = doc.get("valid_from")
        vte = doc.get("valid_to_exclusive")
        vf = date.fromisoformat(vf) if isinstance(vf, str) else vf
        vte = date.fromisoformat(vte) if isinstance(vte, str) else vte
        if vf is not None and vf > valid_at:
            return False
        if vte is not None and valid_at >= vte:
            return False
    doc_ids = filters.get("document_ids")
    if doc_ids and doc.get("document_id") not in doc_ids:
        return False
    return True


class InMemoryStore:
    """Dict-backed store used in demo_mode / when OpenSearch is unavailable."""

    def __init__(self):
        self._docs: Dict[str, Dict[str, Any]] = {}

    def ensure_index(self) -> None:  # no-op
        pass

    def index_chunk(self, chunk: Dict[str, Any], embedding: List[float]) -> None:
        d = dict(chunk)
        d["embedding"] = embedding
        d["_tokens"] = set(tokens(chunk.get("content", "") + " " + " ".join(chunk.get("heading_path", []))))
        self._docs[chunk["chunk_id"]] = d

    def delete_document(self, document_id: str) -> None:
        self._docs = {k: v for k, v in self._docs.items() if v.get("document_id") != document_id}

    def bm25_search(self, text: str, filters: Dict[str, Any], k: int) -> List[Dict[str, Any]]:
        # Query side drops stopwords so an out-of-corpus question can't match a clause
        # purely on shared function words (keeps abstention working on the demo backend).
        q = set(content_tokens(text))
        if not q:
            return []
        scored = []
        for d in self._docs.values():
            if not _passes_filter(d, filters):
                continue
            overlap = len(q & d["_tokens"])
            if overlap:
                scored.append((overlap / (len(q) or 1), d))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [dict(_score=s, **{kk: vv for kk, vv in d.items() if kk not in ("_tokens", "embedding")})
                for s, d in scored[:k]]

    def knn_search(self, vector: List[float], filters: Dict[str, Any], k: int) -> List[Dict[str, Any]]:
        scored = []
        for d in self._docs.values():
            if not _passes_filter(d, filters):
                continue
            scored.append((cosine(vector, d["embedding"]), d))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [dict(_score=s, **{kk: vv for kk, vv in d.items() if kk not in ("_tokens", "embedding")})
                for s, d in scored[:k]]


class OpenSearchStore:
    """Real OpenSearch backend (BM25 + knn_vector)."""

    def __init__(self):
        from opensearchpy import OpenSearch
        s = get_settings()
        auth = (s.opensearch_user, s.opensearch_password) if s.opensearch_user else None
        self.index = s.opensearch_index
        self.dim = s.embedding_dim
        self.client = OpenSearch(
            hosts=[{"host": s.opensearch_host, "port": s.opensearch_port}],
            http_auth=auth,
            use_ssl=(s.opensearch_scheme == "https"),
            verify_certs=False,
        )

    def ensure_index(self) -> None:
        if self.client.indices.exists(index=self.index):
            return
        body = {
            "settings": {"index": {"knn": True}},
            "mappings": {"properties": {
                "chunk_id": {"type": "keyword"},
                "provision_id": {"type": "keyword"},
                "version_id": {"type": "keyword"},
                "document_id": {"type": "keyword"},
                "document_number": {"type": "keyword"},
                "heading_path": {"type": "text"},
                "content": {"type": "text"},
                "page": {"type": "integer"},
                "valid_from": {"type": "date"},
                "valid_to_exclusive": {"type": "date"},
                "approval_status": {"type": "keyword"},
                "embedding": {"type": "knn_vector", "dimension": self.dim},
            }},
        }
        self.client.indices.create(index=self.index, body=body)

    def index_chunk(self, chunk: Dict[str, Any], embedding: List[float]) -> None:
        body = dict(chunk)
        body["embedding"] = embedding
        self.client.index(index=self.index, id=chunk["chunk_id"], body=body, refresh=True)

    def delete_document(self, document_id: str) -> None:
        self.client.delete_by_query(
            index=self.index,
            body={"query": {"term": {"document_id": document_id}}},
            refresh=True,
        )

    def _filter_clauses(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        clauses: List[Dict[str, Any]] = []
        if filters.get("approved_only", True):
            clauses.append({"term": {"approval_status": "APPROVED"}})
        valid_at = filters.get("valid_at")
        if valid_at is not None:
            iso = valid_at.isoformat()
            clauses.append({"range": {"valid_from": {"lte": iso}}})
            # valid_to_exclusive is None OR query_date < valid_to_exclusive
            clauses.append({"bool": {"should": [
                {"bool": {"must_not": {"exists": {"field": "valid_to_exclusive"}}}},
                {"range": {"valid_to_exclusive": {"gt": iso}}},
            ]}})
        if filters.get("document_ids"):
            clauses.append({"terms": {"document_id": filters["document_ids"]}})
        return clauses

    def bm25_search(self, text: str, filters: Dict[str, Any], k: int) -> List[Dict[str, Any]]:
        body = {"size": k, "query": {"bool": {
            "must": {"match": {"content": text}},
            "filter": self._filter_clauses(filters),
        }}}
        res = self.client.search(index=self.index, body=body)
        return [dict(_score=h["_score"], **h["_source"]) for h in res["hits"]["hits"]]

    def knn_search(self, vector: List[float], filters: Dict[str, Any], k: int) -> List[Dict[str, Any]]:
        body = {"size": k, "query": {"bool": {
            "must": {"knn": {"embedding": {"vector": vector, "k": k}}},
            "filter": self._filter_clauses(filters),
        }}}
        res = self.client.search(index=self.index, body=body)
        return [dict(_score=h["_score"], **h["_source"]) for h in res["hits"]["hits"]]


def get_store():
    global _store
    if _store is not None:
        return _store
    s = get_settings()
    if not s.demo_mode:
        try:
            store = OpenSearchStore()
            store.ensure_index()
            _store = store
            return _store
        except Exception:
            pass
    _store = InMemoryStore()
    return _store


def reset_store_for_tests(store=None):
    """Test hook to inject an InMemoryStore."""
    global _store
    _store = store or InMemoryStore()
    return _store
