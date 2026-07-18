"""Pure, independently-testable evaluation metrics.

Design rule: every function here takes plain data (strings / lists / dicts) — NOT a
live query service — so each metric is unit-tested with synthetic inputs and the
suite runs offline. `run_eval.py` adapts real Answer/EvidencePackage objects into
these primitives, then calls these functions.

Vietnamese numbers are compared via packages.common.vn_normalize so "500 triệu",
"500.000.000" and "0,5 tỷ" all match — comparisons never rely on surface strings.

Each per-item metric returns a bool (or None when "not applicable" to this item).
Each aggregate metric returns a float accuracy in [0, 1] over the applicable items.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import re

from packages.common.vn_normalize import extract_all_money, money_to_vnd, strip_accents

# a monetary amount is one that carries a currency unit (triệu/tỷ/nghìn/đồng/vnd/…),
# so "12 tháng" is NOT read as 12 VND — only real amounts switch to money-comparison.
_MONEY_UNIT_RE = re.compile(
    r"\d[\d.,]*\s*(tỷ|tỉ|triệu|trieu|tr|nghìn|nghin|ngàn|ngan|tỉ|đồng|dong|vnd|đ)\b",
    re.IGNORECASE,
)


def _money_if_currency(text: Optional[str]) -> Optional[int]:
    """Canonical VND iff `text` contains an amount WITH a currency unit, else None."""
    if not text or not _MONEY_UNIT_RE.search(text):
        return None
    return money_to_vnd(text)


# --------------------------------------------------------------------------- #
# text helpers
# --------------------------------------------------------------------------- #
def _norm(text: Optional[str]) -> str:
    """Accent-folded, lowercased, whitespace-collapsed — for robust substring checks."""
    if not text:
        return ""
    return " ".join(strip_accents(text).lower().split())


def contains_text(answer: Optional[str], expected: Optional[str]) -> bool:
    """Substring match, accent- and case-insensitive.

    If both sides carry a monetary amount, require the amounts to be equal too, so
    "700 triệu" in the answer never satisfies an expected "500 triệu".
    """
    if not expected:
        return True
    a, e = _norm(answer), _norm(expected)
    exp_money = _money_if_currency(expected)
    if exp_money is not None:
        # a currency amount was requested -> require the answer to carry that exact
        # amount (so "700 triệu" never satisfies an expected "500 triệu").
        return exp_money in extract_all_money(answer or "")
    return e in a


def not_contains_text(answer: Optional[str], forbidden: Optional[str]) -> bool:
    """True iff `forbidden` (a stale/superseded value) is absent from the answer."""
    if not forbidden:
        return True
    fb_money = _money_if_currency(forbidden)
    if fb_money is not None:
        # forbidden is a money value -> absent iff the answer carries no equal amount
        return fb_money not in extract_all_money(answer or "")
    return _norm(forbidden) not in _norm(answer)


# --------------------------------------------------------------------------- #
# per-item metrics — each returns bool | None (None == not applicable)
# --------------------------------------------------------------------------- #
def answer_correct(answer_text: str, gold: Dict[str, Any]) -> Optional[bool]:
    """Does the answer contain the expected value (and not the forbidden one)?"""
    expected = gold.get("expected_answer_contains")
    if expected is None:
        return None
    ok = contains_text(answer_text, expected)
    forbidden = gold.get("must_not_contain")
    if forbidden:
        ok = ok and not_contains_text(answer_text, forbidden)
    return ok


def version_correct(used_version_ids: Sequence[str], expected_label: Optional[str],
                    label_of: Dict[str, str]) -> Optional[bool]:
    """Was the expected version (by human label V1/V2) actually used?

    `label_of` maps version_id -> human label so the metric is store-agnostic.
    """
    if not expected_label:
        return None
    used_labels = {label_of.get(v, v) for v in used_version_ids}
    return expected_label in used_labels


def citation_correct(citations: Sequence[Dict[str, Any]], gold: Dict[str, Any]) -> Optional[bool]:
    """Is there a citation matching expected source (Điều/Khoản) and page?

    A citation is a dict with keys: heading_path (list), page (int), document_number.
    Matches if the expected locator tokens all appear in some citation's heading_path
    AND (if expected_page given) that citation's page equals it.
    """
    expected_source = gold.get("expected_source")
    if not expected_source:
        return None
    exp_tokens = [t for t in _norm(expected_source).split() if t.isdigit() or t in ("dieu", "khoan", "diem")]
    exp_page = gold.get("expected_page")
    exp_doc = gold.get("expected_document_number")
    for c in citations:
        hp = _norm(" ".join(c.get("heading_path") or []))
        if not all(tok in hp for tok in exp_tokens):
            continue
        if exp_page is not None and c.get("page") != exp_page:
            continue
        if exp_doc is not None and _norm(c.get("document_number")) != _norm(exp_doc):
            continue
        return True
    return False


def superseded_evidence_used(used_version_ids: Sequence[str],
                             superseded_ids: Sequence[str]) -> bool:
    """True (BAD) if any superseded/expired version leaked into the used evidence."""
    return bool(set(used_version_ids) & set(superseded_ids))


def crossref_recalled(reference_locators: Sequence[str], expected_locator: str) -> bool:
    """Was the expected cross-referenced locator recalled (accent/case-insensitive)?

    Locators may be written "Khoản 3 Điều 12" or "Điều 12 Khoản 3"; compare on the
    multiset of numeric+keyword tokens so order does not matter.
    """
    def key(s: str):
        return frozenset(t for t in _norm(s).split() if t.isdigit() or t in ("dieu", "khoan", "diem"))
    want = key(expected_locator)
    return any(key(loc) == want for loc in reference_locators)


def conflict_candidate_correct(conflict_pairs: Sequence[Dict[str, Any]],
                               gold: Dict[str, Any]) -> Optional[bool]:
    """For CONFLICT items: were the two conflicting values both flagged?

    For CONFLICT_NEGATIVE items: assert NO conflict was raised.
    conflict_pairs: list of dicts with value_a/value_b (any surface form).
    """
    t = gold.get("type")
    if t == "CONFLICT_NEGATIVE" or gold.get("conflict_expected") is False:
        return len(conflict_pairs) == 0
    if t != "CONFLICT":
        return None
    wanted = {money_to_vnd(v) for v in gold.get("conflict_values", [])}
    wanted.discard(None)
    if not wanted:
        return None
    for p in conflict_pairs:
        got = {money_to_vnd(p.get("value_a") or ""), money_to_vnd(p.get("value_b") or "")}
        got.discard(None)
        if wanted <= got:
            return True
    return False


def stale_policy_correct(impact_titles: Sequence[str], gold: Dict[str, Any]) -> Optional[bool]:
    """Was the expected stale internal policy identified as an impact candidate?"""
    expected = gold.get("stale_policy")
    if not expected:
        return None
    return any(_norm(expected) in _norm(t) or _norm(t) in _norm(expected) for t in impact_titles)


def abstained_correctly(status: Optional[str], gold: Dict[str, Any]) -> Optional[bool]:
    """Abstention accuracy: for ABSTENTION items require INSUFFICIENT_EVIDENCE;
    for answerable items require that we did NOT abstain."""
    is_abstain_item = gold.get("type") == "ABSTENTION" or \
        gold.get("expected_status") == "INSUFFICIENT_EVIDENCE"
    abstained = status == "INSUFFICIENT_EVIDENCE"
    if is_abstain_item:
        return abstained
    # answerable item: correct iff we did not wrongly abstain
    return not abstained


# --------------------------------------------------------------------------- #
# aggregation helpers
# --------------------------------------------------------------------------- #
def accuracy(results: Sequence[Optional[bool]]) -> Optional[float]:
    """Mean over applicable (non-None) items; None if nothing applicable."""
    vals = [r for r in results if r is not None]
    if not vals:
        return None
    return sum(1 for r in vals if r) / len(vals)


def rate(results: Sequence[Optional[bool]]) -> Optional[float]:
    """Fraction of applicable items that are True (used for 'bad-event' rates)."""
    return accuracy(results)


def mean_latency_ms(latencies: Sequence[float]) -> Optional[float]:
    vals = [x for x in latencies if x is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


# --------------------------------------------------------------------------- #
# metric registry — maps a type to the per-item metrics it feeds, used by run_eval
# --------------------------------------------------------------------------- #
def summarize(per_item: Dict[str, List[Optional[bool]]],
              latencies: Sequence[float]) -> Dict[str, Optional[float]]:
    """Aggregate a dict of metric_name -> list[bool|None] into headline numbers.

    Recognised keys (aggregated as accuracy unless noted):
      current_version, point_in_time, crossref_recall, partial_patch,
      conflict_precision, citation, stale_policy, abstention
      superseded_rate (aggregated as a RATE — lower is better)
    """
    out: Dict[str, Optional[float]] = {}
    for name, results in per_item.items():
        if name == "superseded_rate":
            out[name] = rate(results)
        else:
            out[name] = accuracy(results)
    out["latency_ms"] = mean_latency_ms(latencies)
    return out
