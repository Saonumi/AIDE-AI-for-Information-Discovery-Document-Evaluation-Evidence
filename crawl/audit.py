"""Source audit + registry — the professional 'is this source trustworthy for what?'
step, borrowed from the vn-gold-market-analysis project's SourceAuditor/registry.

Instead of the naive stop criterion "10 files", we classify each crawled source by
what it actually DELIVERS and gate ingestion on status, not count:

    blocked        -> 0 items reachable (Cloudflare/DNS/robots)
    metadata_only  -> items exist but ~no clause text and ~no relations
    relations_only -> real amendment/supersession edges, but full clause text is gated
    text_partial   -> some items carry real clause-level text (Điều/Khoản)
    text_ok        -> most items carry real clause text

The single most important metric for a *temporal* RAG demo is amendment-pair
completeness: how many relations have BOTH endpoints (original + amending doc)
present as real crawled items — a dangling edge cannot demonstrate versioning.

Pure Python over already-persisted items (no network). Run:
    python -m crawl.audit
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Dict, List

from crawl.base import load_items
from crawl.models import CrawlItem

SOURCES = ["vbpl", "sbv", "thuvienphapluat", "shb"]

# A real clause-level body names multiple articles ("Điều 1", "Điều 2", ...).
# The SBV HTML *summary* repeats the title once and has at most one "Điều" — so
# requiring >=2 distinct article markers separates real legal text from a landing blurb.
_ARTICLE = re.compile(r"\bĐiều\s+\d{1,3}\b", re.IGNORECASE)


def _norm(num: str | None) -> str:
    return re.sub(r"\s+", "", (num or "").upper())


def clause_text_signal(full_text: str | None) -> bool:
    """True if full_text looks like real clause-level legal text, not a summary blurb."""
    if not full_text or len(full_text) < 800:
        return False
    return len(set(_ARTICLE.findall(full_text))) >= 2


@dataclass(frozen=True)
class SourceReport:
    source: str
    n_items: int
    n_clause_text: int          # items with real Điều/Khoản-level text
    n_pdf_url: int              # items pointing at a (real-text) PDF attachment
    n_with_relations: int
    n_relations: int
    status: str
    parser_status: str          # ok / gated_fulltext / not_available
    coverage: str
    note: str = ""


def _classify(source: str, items: List[CrawlItem]) -> SourceReport:
    n = len(items)
    n_clause = sum(clause_text_signal(i.full_text) for i in items)
    n_pdf = sum(1 for i in items if (i.fields or {}).get("pdf_url"))
    n_rel_items = sum(1 for i in items if i.relations)
    n_rel = sum(len(i.relations) for i in items)

    if n == 0:
        status, parser, note = "blocked", "not_available", "0 items reachable (Cloudflare/DNS/robots)."
    elif n_clause >= max(2, n // 2):
        status, parser, note = "text_ok", "ok", ""
    elif n_clause > 0:
        status, parser, note = "text_partial", "ok", "some clause text; rest gated (PDF/api/paywall)."
    elif n_rel > 0:
        status, parser, note = "relations_only", "gated_fulltext", "real amendment edges; clause text gated."
    else:
        status, parser, note = "metadata_only", "gated_fulltext", "metadata only; no clause text, no relations."

    # A source with real-text PDFs it hasn't decoded yet is 'relations_only'/'metadata'
    # but recoverable — flag that the text is one extraction step away.
    if status in ("relations_only", "metadata_only") and n_pdf > 0:
        note = f"{note} {n_pdf} items carry a PDF full-text link (extract to upgrade to text_*)."

    coverage = f"{n_clause}/{n} clause_text; {n_pdf}/{n} pdf_link; {n_rel_items}/{n} with_rel; {n_rel} edges"
    return SourceReport(source, n, n_clause, n_pdf, n_rel_items, n_rel, status, parser, coverage, note.strip())


def amendment_pairs(all_items: List[CrawlItem]) -> Dict[str, object]:
    """Cross-source: which relations have BOTH endpoints present as real crawled items."""
    known = {_norm(i.doc_number) for i in all_items if i.doc_number}
    complete: List[str] = []
    dangling: List[str] = []
    for i in all_items:
        for r in i.relations:
            if not r.target_doc_number:
                continue
            edge = f"{_norm(i.doc_number)} -{r.type.value}-> {_norm(r.target_doc_number)}"
            (complete if _norm(r.target_doc_number) in known else dangling).append(edge)
    return {
        "complete_pairs": complete,
        "dangling_edges": dangling,
        "n_complete": len(complete),
        "n_dangling": len(dangling),
    }


def build_registry() -> Dict[str, object]:
    reports: List[SourceReport] = []
    all_items: List[CrawlItem] = []
    for s in SOURCES:
        try:
            items = load_items(s)
        except (FileNotFoundError, OSError):
            items = []
        all_items.extend(items)
        reports.append(_classify(s, items))

    pairs = amendment_pairs(all_items)
    text_sources = [r.source for r in reports if r.status in ("text_ok", "text_partial")]
    rel_sources = [r.source for r in reports if r.n_relations > 0]

    # Demo-ready gate (replaces "10 files"): >=1 real-text source AND >=2 complete pairs.
    ready = bool(text_sources) and pairs["n_complete"] >= 2
    return {
        "sources": [asdict(r) for r in reports],
        "amendment_pairs": pairs,
        "text_sources": text_sources,
        "relation_sources": rel_sources,
        "demo_ready": ready,
        "gate": ">=1 text source AND >=2 complete amendment pairs (both endpoints crawled)",
    }


def _atomic_write_json(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def main() -> None:
    reg = build_registry()
    out = os.path.join("data", "crawl", "source_registry.json")
    _atomic_write_json(out, reg)

    print("SOURCE REGISTRY")
    print(f"{'source':<18}{'status':<16}{'parser':<16}coverage")
    print("-" * 100)
    for r in reg["sources"]:
        print(f"{r['source']:<18}{r['status']:<16}{r['parser_status']:<16}{r['coverage']}")
        if r["note"]:
            print(f"{'':<50}note: {r['note']}")
    p = reg["amendment_pairs"]
    print("-" * 100)
    print(f"amendment pairs: {p['n_complete']} complete (both ends crawled) | {p['n_dangling']} dangling")
    for e in p["complete_pairs"][:8]:
        print(f"  [OK] {e}")
    print(f"text sources: {reg['text_sources'] or '-'} | relation sources: {reg['relation_sources'] or '-'}")
    print(f"DEMO-READY: {reg['demo_ready']}  (gate: {reg['gate']})")
    print(f"\nwrote {out}")


def _self_check() -> None:
    # clause_text_signal must separate a real multi-article body from a summary blurb.
    real = "THÔNG TƯ ... Điều 1. Phạm vi ... " + "x" * 900 + " Điều 2. Đối tượng ... Điều 3. ..."
    blurb = "Thông tư số 06/2026/TT-NHNN quy định về giám định tư pháp trong lĩnh vực ngân hàng."
    assert clause_text_signal(real) is True, "real clause text should pass"
    assert clause_text_signal(blurb) is False, "summary blurb should fail"
    # pair completeness: A->B counts complete only if B is also a crawled doc_number.
    from crawl.models import Relation, RelationType
    a = CrawlItem(source="t", url="u1", doc_number="35/2026/TT-NHNN",
                  relations=[Relation(type=RelationType.AMENDS, target_doc_number="15/2026/TT-NHNN")])
    b = CrawlItem(source="t", url="u2", doc_number="15/2026/TT-NHNN")
    c = CrawlItem(source="t", url="u3", doc_number="99/2020/TT-NHNN",
                  relations=[Relation(type=RelationType.AMENDS, target_doc_number="00/0000/XX")])
    p = amendment_pairs([a, b, c])
    assert p["n_complete"] == 1 and p["n_dangling"] == 1, p
    print("self-check OK")


if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        _self_check()
    else:
        main()
