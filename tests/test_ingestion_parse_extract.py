"""Ingestion unit tests: structure parser, amendment regex, cross-refs, obligations.

Covers requirement (a) structure parser and (b) amendment regex extraction.
Runs fully offline (conftest forces sqlite + demo_mode + mock LLM).
"""
from datetime import date

from packages.contracts.enums import AmendmentOperation, Modality
from ingestion.legal_extract import (
    extract_amendments,
    extract_cross_references,
    extract_document_metadata,
    extract_obligation,
    normalize_locator,
)
from ingestion.structure_parser import parse_document_text

SAMPLE = """Quyết định số 01/2026/QĐ-HĐQT
Hiệu lực từ ngày 01/02/2026.
CHƯƠNG II CẤP TÍN DỤNG
Điều 7. Hạn mức cấp tín dụng
1. Nguyên tắc chung được áp dụng.
2. Hạn mức tín dụng SME là 500 triệu đồng, thời hạn tối đa 12 tháng.
Điều 12. Điều kiện thực hiện
1. Ngân hàng phải thực hiện theo Khoản 2 Điều 7.
"""


# ---------------------------------------------------------------- (a) parser
def test_structure_parser_hierarchy():
    provs = parse_document_text(SAMPLE)
    # 3 provisions: Điều7/Khoản1, Điều7/Khoản2, Điều12/Khoản1
    assert len(provs) == 3, provs
    p2 = next(p for p in provs if p["article"] == "7" and p["clause"] == "2")
    assert p2["heading_path"] == ["Chương II", "Điều 7", "Khoản 2"]
    assert "500 triệu đồng" in p2["content"]
    assert "12 tháng" in p2["content"]
    assert p2["page"] == 1


def test_structure_parser_article_and_clause_fields():
    provs = parse_document_text(SAMPLE)
    p12 = next(p for p in provs if p["article"] == "12")
    assert p12["clause"] == "1"
    assert p12["heading_path"] == ["Chương II", "Điều 12", "Khoản 1"]


def test_points_inside_clause():
    text = (
        "Điều 3. Phân loại\n"
        "1. Nhóm khách hàng gồm:\n"
        "a) Khách hàng cá nhân;\n"
        "b) Khách hàng SME.\n"
    )
    provs = parse_document_text(text)
    points = [p for p in provs if p.get("point")]
    assert {p["point"] for p in points} == {"a", "b"}
    a = next(p for p in points if p["point"] == "a")
    assert a["heading_path"] == ["Điều 3", "Khoản 1", "Điểm a"]


# ---------------------------------------------------------------- metadata
def test_metadata_extraction():
    md = extract_document_metadata(SAMPLE)
    assert md.document_number == "01/2026/QĐ-HĐQT"
    assert md.valid_from == date(2026, 2, 1)


# ---------------------------------------------------------------- (b) amendment regex
def test_amendment_replace_text_canonical():
    text = 'Thay "500 triệu đồng" bằng "700 triệu đồng" tại Khoản 2 Điều 7, hiệu lực từ 01/07/2026.'
    ams = extract_amendments(text, source_page=2)
    assert len(ams) == 1
    a = ams[0]
    assert a.operation == AmendmentOperation.REPLACE_TEXT
    assert a.old_text == "500 triệu đồng"
    assert a.new_text == "700 triệu đồng"
    assert a.target_locator == "Khoản 2 Điều 7"
    assert a.valid_from == date(2026, 7, 1)
    assert a.source_page == 2


def test_amendment_curly_quotes():
    text = 'Thay “500 triệu đồng” bằng “700 triệu đồng” tại Khoản 2 Điều 7, hiệu lực từ 01/07/2026.'
    ams = extract_amendments(text)
    assert len(ams) == 1
    assert ams[0].new_text == "700 triệu đồng"


def test_amendment_repeal_provision():
    text = "Bãi bỏ Khoản 2 Điều 7, hiệu lực từ 01/07/2026."
    ams = extract_amendments(text)
    assert any(a.operation == AmendmentOperation.REPEAL_PROVISION for a in ams)


def test_amendment_without_date_is_skipped():
    # no parseable effective date -> not emitted (caller can't set a temporal window)
    text = 'Thay "500 triệu đồng" bằng "700 triệu đồng" tại Khoản 2 Điều 7.'
    ams = extract_amendments(text)
    assert ams == []


# ---------------------------------------------------------------- cross-reference
def test_cross_reference_detection():
    refs = extract_cross_references(
        "Ngân hàng phải thực hiện theo Khoản 2 Điều 7.",
        source_provision="prov-x", self_article="12", self_clause="1",
    )
    assert len(refs) == 1
    assert refs[0].target_locator == "Khoản 2 Điều 7"


def test_cross_reference_ignores_non_trigger_number():
    # a bare "Điều 7" mention without a trigger word is not a cross-ref
    refs = extract_cross_references("Hạn mức là 500 triệu đồng.", source_provision="p")
    assert refs == []


# ---------------------------------------------------------------- obligation
def test_obligation_value_normalized():
    ob = extract_obligation("Hạn mức tín dụng SME là 500 triệu đồng.", "prov-y")
    assert ob is not None
    assert ob.value == "500 triệu đồng"
    assert ob.value_normalized == 500_000_000


def test_obligation_modality_prohibition():
    ob = extract_obligation("Ngân hàng không được cấp tín dụng vượt hạn mức.", "p")
    assert ob is not None
    assert ob.modality == Modality.PROHIBITION


def test_normalize_locator():
    assert normalize_locator("Khoản 2 Điều 7") == ("7", "2", None)
    assert normalize_locator("Điều 12") == ("12", None, None)
