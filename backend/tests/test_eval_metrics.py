"""Unit tests for eval.metrics — each metric with synthetic inputs (no query service).

Also a lightweight import smoke test for the UI (per Track C brief: do not unit-test
the Streamlit UI beyond an import smoke test).
"""
from __future__ import annotations

from eval import metrics as M


# --------------------------------------------------------------------------- #
# text / money matching
# --------------------------------------------------------------------------- #
def test_contains_text_money_equal_across_surface_forms():
    assert M.contains_text("Hạn mức là 500.000.000 đồng", "500 triệu")
    assert M.contains_text("Hạn mức là 0,5 tỷ", "500 triệu")
    assert not M.contains_text("Hạn mức là 700 triệu đồng", "500 triệu")


def test_contains_text_plain_substring_accent_insensitive():
    assert M.contains_text("Thời hạn tối đa 12 tháng", "12 tháng")
    assert M.contains_text("bo phan quan ly rui ro", "quản lý rủi ro")
    assert not M.contains_text("nội dung khác", "quản lý rủi ro")


def test_not_contains_text_money():
    assert M.not_contains_text("hiện tại 700 triệu", "500 triệu")
    assert not M.not_contains_text("vẫn còn 500 triệu", "500 triệu")


# --------------------------------------------------------------------------- #
# answer / version / citation
# --------------------------------------------------------------------------- #
def test_answer_correct_with_must_not_contain():
    gold = {"expected_answer_contains": "700 triệu", "must_not_contain": "500 triệu"}
    assert M.answer_correct("Hạn mức hiện tại là 700 triệu đồng", gold) is True
    assert M.answer_correct("Có thể là 500 triệu hoặc 700 triệu", gold) is False


def test_answer_correct_not_applicable():
    assert M.answer_correct("bất kỳ", {"expected_answer_contains": None}) is None


def test_version_correct():
    label_of = {"ver-d7k2-v1": "V1", "ver-d7k2-v2": "V2"}
    assert M.version_correct(["ver-d7k2-v2"], "V2", label_of) is True
    assert M.version_correct(["ver-d7k2-v1"], "V2", label_of) is False
    assert M.version_correct(["ver-d7k2-v1"], None, label_of) is None


def test_citation_correct_matches_locator_and_page():
    cites = [{"heading_path": ["Điều 7", "Khoản 2"], "page": 3, "document_number": "QĐ-01/2026"}]
    gold = {"expected_source": "Khoản 2 Điều 7", "expected_page": 3,
            "expected_document_number": "QĐ-01/2026"}
    assert M.citation_correct(cites, gold) is True


def test_citation_correct_wrong_page():
    cites = [{"heading_path": ["Điều 7", "Khoản 2"], "page": 4}]
    gold = {"expected_source": "Khoản 2 Điều 7", "expected_page": 3}
    assert M.citation_correct(cites, gold) is False


def test_citation_correct_not_applicable_without_expected_source():
    assert M.citation_correct([], {"expected_source": None}) is None


# --------------------------------------------------------------------------- #
# superseded / cross-reference
# --------------------------------------------------------------------------- #
def test_superseded_evidence_used():
    assert M.superseded_evidence_used(["ver-d7k2-v1"], ["ver-d7k2-v1"]) is True
    assert M.superseded_evidence_used(["ver-d7k2-v2"], ["ver-d7k2-v1"]) is False


def test_crossref_recalled_order_independent():
    assert M.crossref_recalled(["Khoản 3 Điều 12"], "Điều 12 Khoản 3") is True
    assert M.crossref_recalled(["Điều 12 Khoản 3"], "Khoản 3 Điều 12") is True
    assert M.crossref_recalled(["Khoản 2 Điều 7"], "Khoản 3 Điều 12") is False


# --------------------------------------------------------------------------- #
# conflict / stale / abstention
# --------------------------------------------------------------------------- #
def test_conflict_candidate_positive():
    gold = {"type": "CONFLICT", "conflict_values": ["700 triệu", "600 triệu"]}
    pairs = [{"value_a": "700 triệu đồng", "value_b": "600 triệu đồng"}]
    assert M.conflict_candidate_correct(pairs, gold) is True


def test_conflict_candidate_missing_pair():
    gold = {"type": "CONFLICT", "conflict_values": ["700 triệu", "600 triệu"]}
    assert M.conflict_candidate_correct([], gold) is False


def test_conflict_candidate_negative_expects_none_flagged():
    gold = {"type": "CONFLICT_NEGATIVE", "conflict_expected": False}
    assert M.conflict_candidate_correct([], gold) is True
    assert M.conflict_candidate_correct([{"value_a": "700 triệu", "value_b": "600 triệu"}], gold) is False


def test_stale_policy_correct():
    gold = {"stale_policy": "Quy trình cấp tín dụng SME nội bộ"}
    assert M.stale_policy_correct(["Quy trình cấp tín dụng SME nội bộ"], gold) is True
    assert M.stale_policy_correct(["Chính sách khác"], gold) is False
    assert M.stale_policy_correct([], {"stale_policy": None}) is None


def test_abstained_correctly():
    abstain_gold = {"type": "ABSTENTION", "expected_status": "INSUFFICIENT_EVIDENCE"}
    assert M.abstained_correctly("INSUFFICIENT_EVIDENCE", abstain_gold) is True
    assert M.abstained_correctly("SOURCE_GROUNDED", abstain_gold) is False
    answerable = {"type": "CURRENT", "expected_status": "SOURCE_GROUNDED"}
    assert M.abstained_correctly("SOURCE_GROUNDED", answerable) is True
    assert M.abstained_correctly("INSUFFICIENT_EVIDENCE", answerable) is False


# --------------------------------------------------------------------------- #
# aggregation
# --------------------------------------------------------------------------- #
def test_accuracy_ignores_none():
    assert M.accuracy([True, False, None, True]) == 2 / 3
    assert M.accuracy([None, None]) is None


def test_rate_for_bad_events():
    # 1 of 4 answerable items leaked a superseded version -> 25% rate
    assert M.rate([False, False, True, False]) == 0.25


def test_mean_latency():
    assert M.mean_latency_ms([100.0, 200.0, None]) == 150.0
    assert M.mean_latency_ms([]) is None


def test_summarize_routes_superseded_as_rate():
    per_item = {
        "current_version": [True, True],
        "superseded_rate": [False, True],   # rate = 0.5
    }
    out = M.summarize(per_item, [10.0, 20.0])
    assert out["current_version"] == 1.0
    assert out["superseded_rate"] == 0.5
    assert out["latency_ms"] == 15.0


# --------------------------------------------------------------------------- #
# UI import smoke test (no Streamlit behaviour tested)
# --------------------------------------------------------------------------- #
def test_ui_imports():
    import ui.api_client as api_client
    import ui.app as app
    # api client constructs without a live server and never raises on a down API
    client = api_client.ApiClient(base_url="http://127.0.0.1:59999")
    res = client.health()
    assert res.ok is False and res.error  # connection refused -> friendly result
    # pure render helper works without streamlit installed
    assert "Không đủ bằng chứng" in app.status_badge("INSUFFICIENT_EVIDENCE")


def test_golden_questions_wellformed():
    import json
    import os
    # golden_questions.json is canonical at the repo-root data/ (backend/ has no data/ copy).
    path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "data", "golden_questions.json")
    with open(os.path.abspath(path), encoding="utf-8") as f:
        data = json.load(f)
    qs = data["questions"]
    assert 15 <= len(qs) <= 25
    ids = [q["id"] for q in qs]
    assert len(ids) == len(set(ids))  # unique ids
    types = {q["type"] for q in qs}
    # every required category is represented
    for needed in ("POINT_IN_TIME", "CURRENT", "CROSS_REFERENCE", "PARTIAL_PATCH",
                   "CONFLICT", "STALE_POLICY", "ABSTENTION", "CITATION"):
        assert needed in types, needed
