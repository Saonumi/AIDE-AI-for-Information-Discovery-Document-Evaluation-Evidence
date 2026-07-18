"""Map crawled CrawlItems -> a REAL document-level regulatory graph.

Honest scope: crawling yields real document identities + real amendment/supersession
RELATIONS, but NOT clause-level full text (that is behind /api/, scanned PDFs, or
paywalls). So this builds a Document-level graph (real NHNN circulars + their
supersession/reference edges) — the versioning/timeline feature on real data. It does
NOT fabricate clause text; feeding real article text still needs a full-text source.

Relation -> edge mapping (onto the frozen ALLOWED_RELS):
  AMENDS / SUPERSEDES              -> (this)-[SUPERSEDES]->(target)
  AMENDED_BY / SUPERSEDED_BY       -> (target)-[SUPERSEDES]->(this)
  GUIDES / GUIDED_BY / RELATED     -> (this)-[REFERENCES]->(target)
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from crawl.base import load_items
from crawl.models import CrawlItem, RelationType
from infra.neo4j_client import get_graph

_SOURCES = ["vbpl", "sbv", "thuvienphapluat", "shb", "hybrid"]


def _norm(num: str) -> str:
    return re.sub(r"\s+", "", (num or "").upper())


def _node_id(doc_number: str) -> str:
    return f"doc:{_norm(doc_number)}"


def _edge_for(rt: RelationType):
    """Return (label, reversed) — reversed=True means target->this."""
    if rt in (RelationType.AMENDS, RelationType.SUPERSEDES, RelationType.EXPIRES):
        return "SUPERSEDES", False
    if rt in (RelationType.AMENDED_BY, RelationType.SUPERSEDED_BY):
        return "SUPERSEDES", True
    return "REFERENCES", False   # GUIDES / GUIDED_BY / RELATED


def build_graph(items: Optional[List[CrawlItem]] = None) -> Dict[str, int]:
    if items is None:
        items = []
        for s in _SOURCES:
            items.extend(load_items(s))

    graph = get_graph()
    known = {_norm(i.doc_number) for i in items if i.doc_number}
    stats = {"documents": 0, "edges": 0, "stub_targets": 0, "relations_seen": 0}

    def ensure_doc(doc_number: str, item: Optional[CrawlItem] = None, stub: bool = False):
        nid = _node_id(doc_number)
        props = {"doc_number": _norm(doc_number)}
        if item is not None:
            props.update({
                "title": (item.title or "")[:200],
                "issued_date": item.issued_date.isoformat() if item.issued_date else None,
                "effective_date": item.effective_date.isoformat() if item.effective_date else None,
                "doc_type": item.doc_type.value if item.doc_type else None,
                "issuer": item.issuer,
                "source": item.source,
                "url": item.url,
                "status": item.status,
                "stub": False,
            })
        else:
            props["stub"] = stub
        graph.upsert_node(nid, "Document", **props)
        return nid

    for i in items:
        if not i.doc_number:
            continue
        ensure_doc(i.doc_number, i)
        stats["documents"] += 1

    for i in items:
        if not i.doc_number:
            continue
        src_id = _node_id(i.doc_number)
        for r in i.relations:
            stats["relations_seen"] += 1
            if not r.target_doc_number:
                continue
            if _norm(r.target_doc_number) not in known:
                ensure_doc(r.target_doc_number, None, stub=True)
                stats["stub_targets"] += 1
            tgt_id = _node_id(r.target_doc_number)
            label, reverse = _edge_for(r.type)
            a, b = (tgt_id, src_id) if reverse else (src_id, tgt_id)
            graph.upsert_edge(a, b, label, via=r.type.value)
            stats["edges"] += 1
    return stats


def amendment_chains(items: Optional[List[CrawlItem]] = None) -> List[str]:
    """Human-readable real supersession/amendment edges (for verification/demo)."""
    if items is None:
        items = []
        for s in _SOURCES:
            items.extend(load_items(s))
    out = []
    for i in items:
        for r in i.relations:
            if r.target_doc_number:
                out.append(f"{_norm(i.doc_number)}  {r.type.value}  {_norm(r.target_doc_number)}")
    return out
