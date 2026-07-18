"""In-process eval harness: our temporal/graph system vs a standard-RAG baseline.

Flow:
  1. Force demo_mode (SQLite + in-memory stores) and seed the canonical corpus.
  2. For each golden question, call BOTH:
       - query.service.answer_query(...)              (our system)
       - query.service.standard_rag(...) or .compare  (baseline)
     in-process, time them, and adapt the returned Answer/EvidencePackage into the
     primitives eval.metrics expects.
  3. Print a side-by-side comparison table.

If query.service is not importable yet (Track B still in progress), the harness
prints a clear message and exits 0 — the metric FUNCTIONS remain independently
unit-tested (see tests/test_eval_metrics.py). It never crashes the demo.

Run:  python -m eval.run_eval
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import date
from typing import Any, Callable, Dict, List, Optional, Tuple

# Windows consoles default to cp1252 and choke on the Vietnamese/table glyphs; make
# stdout UTF-8 so the report prints anywhere. Best-effort — never fatal.
try:  # pragma: no cover - platform-dependent
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# --- force offline/demo BEFORE importing anything that reads settings ---
os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("LLM_PROVIDER", "mock")

from eval import metrics as M  # noqa: E402

_GOLDEN_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "data", "golden_questions.json")

# human labels for the two seeded versions of Điều 7 Khoản 2
_VERSION_LABELS = {"ver-d7k2-v1": "V1", "ver-d7k2-v2": "V2"}
# versions that must never appear in a *current* answer (expired/superseded)
_SUPERSEDED_IDS = ["ver-d7k2-v1"]


def load_golden() -> List[Dict[str, Any]]:
    with open(os.path.abspath(_GOLDEN_PATH), encoding="utf-8") as f:
        return json.load(f)["questions"]


def _resolve_date(q: Dict[str, Any]) -> date:
    qd = q.get("query_date")
    return date.fromisoformat(qd) if qd else date.today()


# --------------------------------------------------------------------------- #
# adapt a returned Answer/EvidencePackage into metric primitives
# --------------------------------------------------------------------------- #
def _as_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return {}


def _extract(answer_obj: Any, evidence_obj: Any) -> Dict[str, Any]:
    """Pull the fields each metric needs from an Answer (+ optional EvidencePackage)."""
    ans = _as_dict(answer_obj)
    ev = _as_dict(evidence_obj)

    citations = [
        {"heading_path": c.get("heading_path") or [], "page": c.get("page"),
         "document_number": c.get("document_number")}
        for c in ans.get("citations", [])
    ]
    used_version_ids = [c.get("source_id") for c in ans.get("citations", []) if c.get("source_id")]
    # prefer evidence.valid_evidence version_ids when present (more precise)
    valid_ev = ev.get("valid_evidence", []) or ans.get("valid_evidence", [])
    if valid_ev:
        used_version_ids = [e.get("version_id") for e in valid_ev if e.get("version_id")] or used_version_ids

    ref_paths = ev.get("reference_paths", []) or ans.get("reference_paths", [])
    reference_locators = [r.get("to_locator", "") for r in ref_paths]

    conflicts = ans.get("conflict_candidates", []) or ev.get("conflict_candidates", [])
    conflict_pairs = [{"value_a": c.get("value_a"), "value_b": c.get("value_b")} for c in conflicts]

    impacts = ans.get("impact_candidates", []) or ev.get("impact_candidates", [])
    impact_titles = [i.get("artifact_title", "") for i in impacts]

    return {
        "text": ans.get("text", ""),
        "status": ans.get("status"),
        "citations": citations,
        "used_version_ids": used_version_ids,
        "reference_locators": reference_locators,
        "conflict_pairs": conflict_pairs,
        "impact_titles": impact_titles,
    }


# --------------------------------------------------------------------------- #
# score one system over all golden questions
# --------------------------------------------------------------------------- #
_METRIC_KEYS = [
    "current_version", "point_in_time", "crossref_recall", "partial_patch",
    "conflict_precision", "citation", "stale_policy", "abstention", "superseded_rate",
]


def score_system(call: Callable[[Dict[str, Any]], Tuple[Any, Any, float]],
                 golden: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Run `call(question) -> (answer, evidence, latency_ms)` for each item and score."""
    per_item: Dict[str, List[Optional[bool]]] = {k: [] for k in _METRIC_KEYS}
    latencies: List[float] = []
    errors = 0

    for q in golden:
        try:
            answer, evidence, latency = call(q)
        except Exception as e:  # a single failure must not abort the whole run
            errors += 1
            answer, evidence, latency = None, None, 0.0
            print(f"  [warn] {q['id']}: {type(e).__name__}: {e}")
        latencies.append(latency)
        d = _extract(answer, evidence)
        t = q.get("type")

        # answer correctness routed to the right accuracy bucket by type
        ac = M.answer_correct(d["text"], q)
        if t == "CURRENT":
            per_item["current_version"].append(ac)
        elif t == "POINT_IN_TIME":
            per_item["point_in_time"].append(ac)
        elif t == "PARTIAL_PATCH":
            per_item["partial_patch"].append(ac)

        if t == "CROSS_REFERENCE":
            per_item["crossref_recall"].append(
                M.crossref_recalled(d["reference_locators"], q.get("expected_reference", "")))

        if t in ("CONFLICT", "CONFLICT_NEGATIVE"):
            per_item["conflict_precision"].append(M.conflict_candidate_correct(d["conflict_pairs"], q))

        if t == "STALE_POLICY":
            per_item["stale_policy"].append(M.stale_policy_correct(d["impact_titles"], q))

        # citation correctness — applies wherever a source is expected
        cc = M.citation_correct(d["citations"], q)
        if cc is not None:
            per_item["citation"].append(cc)

        # abstention — every item is applicable (answer OR correctly abstain)
        per_item["abstention"].append(M.abstained_correctly(d["status"], q))

        # superseded-evidence leak — check on answerable (non-abstain) items
        if q.get("expected_status") != "INSUFFICIENT_EVIDENCE" and t != "ABSTENTION":
            per_item["superseded_rate"].append(
                M.superseded_evidence_used(d["used_version_ids"], _SUPERSEDED_IDS))

    summary = M.summarize(per_item, latencies)
    summary["errors"] = errors
    return summary


# --------------------------------------------------------------------------- #
# wire the real query service (graceful if absent)
# --------------------------------------------------------------------------- #
def _make_calls():
    """Return (our_call, baseline_call) or (None, None, reason) if unavailable."""
    try:
        from query import service as qs  # type: ignore
    except Exception as e:
        return None, None, f"query.service not importable yet ({e})"

    def _our(q):
        t0 = time.perf_counter()
        res = qs.answer_query(q["query"], _resolve_date(q), "eval", "EMPLOYEE")
        dt = (time.perf_counter() - t0) * 1000
        answer, evidence = _split_query_result(res)
        return answer, evidence, dt

    def _baseline(q):
        # The documented head-to-head path: compare() returns both sides. We use its
        # standard_rag side as the naive baseline (all versions in one index, top-k).
        t0 = time.perf_counter()
        cmp = qs.compare(q["query"], _resolve_date(q), "eval", "EMPLOYEE")
        cmp_d = _as_dict(cmp)
        dt = (time.perf_counter() - t0) * 1000
        return cmp_d.get("standard_rag"), None, dt

    return _our, _baseline, None


def _split_query_result(res: Any) -> Tuple[Any, Any]:
    """answer_query may return an Answer, or a QueryResponse{answer, evidence}."""
    d = _as_dict(res)
    if "answer" in d:
        return d.get("answer"), d.get("evidence")
    return res, None


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #
_ROWS = [
    ("Current-version accuracy", "current_version"),
    ("Point-in-time accuracy", "point_in_time"),
    ("Cross-reference recall", "crossref_recall"),
    ("Partial-patch exact match", "partial_patch"),
    ("Conflict-candidate precision", "conflict_precision"),
    ("Citation correctness", "citation"),
    ("Stale-policy precision", "stale_policy"),
    ("Abstention accuracy", "abstention"),
    ("Superseded-evidence rate (lower=better)", "superseded_rate"),
    ("Mean latency (ms)", "latency_ms"),
]


def _fmt(key: str, val: Optional[float]) -> str:
    if val is None:
        return "  n/a"
    if key == "latency_ms":
        return f"{val:6.1f}"
    return f"{val*100:5.1f}%"


def print_table(our: Dict[str, Any], base: Optional[Dict[str, Any]]) -> None:
    w = 40
    print("\n" + "=" * (w + 22))
    print(f"{'Metric':<{w}}{'Our system':>11}{'Std RAG':>11}")
    print("-" * (w + 22))
    for label, key in _ROWS:
        ours = _fmt(key, our.get(key))
        theirs = _fmt(key, base.get(key)) if base else "   —"
        print(f"{label:<{w}}{ours:>11}{theirs:>11}")
    print("=" * (w + 22))
    if our.get("errors"):
        print(f"(our system: {our['errors']} question(s) raised errors)")


def main() -> int:
    golden = load_golden()
    print(f"Loaded {len(golden)} golden questions.")

    # seed all stores deterministically
    try:
        from data.seed import seed_all
        seed_all()
        print("Seeded demo corpus (all stores).")
    except Exception as e:
        print(f"[error] could not seed demo corpus: {e}")
        return 1

    our_call, base_call, reason = _make_calls()
    if our_call is None:
        print(f"\n[degraded] {reason}")
        print("Track B's query.service is not ready — cannot run end-to-end scoring yet.")
        print("The metric functions themselves are unit-tested (tests/test_eval_metrics.py).")
        return 0

    print("\nScoring our system ...")
    our = score_system(our_call, golden)
    print("Scoring standard-RAG baseline ...")
    try:
        base = score_system(base_call, golden)
    except Exception as e:
        print(f"[warn] baseline scoring failed: {e}")
        base = None

    print_table(our, base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
