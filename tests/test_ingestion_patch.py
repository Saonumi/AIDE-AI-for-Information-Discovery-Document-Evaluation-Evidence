"""Deterministic patch tests — covers requirements (c) and (d).

(c) REPLACE_TEXT producing "700 triệu" while KEEPING "12 tháng".
(d) NEEDS_REVIEW on an ambiguous (multiple) match.
"""
from packages.contracts.enums import AmendmentOperation
from ingestion.patch import STATUS_NEEDS_REVIEW, STATUS_OK, apply_patch

V1 = "Hạn mức tín dụng SME là 500 triệu đồng, thời hạn tối đa 12 tháng."


# ---------------------------------------------------------------- (c)
def test_replace_keeps_unchanged_parts():
    r = apply_patch(V1, AmendmentOperation.REPLACE_TEXT,
                    old_text="500 triệu đồng", new_text="700 triệu đồng")
    assert r.status == STATUS_OK
    assert "700 triệu" in r.new_content
    assert "12 tháng" in r.new_content          # unchanged part preserved
    assert "500 triệu" not in r.new_content
    assert r.match_count == 1
    assert r.diff  # a before/after diff is produced


# ---------------------------------------------------------------- (d)
def test_ambiguous_match_needs_review():
    content = "Mức 5 áp dụng khi 5 điều kiện, ngoại trừ trường hợp 5."
    r = apply_patch(content, AmendmentOperation.REPLACE_TEXT, old_text="5", new_text="9")
    assert r.status == STATUS_NEEDS_REVIEW
    assert r.match_count == 3
    assert r.new_content is None
    assert r.needs_review


def test_no_match_needs_review():
    r = apply_patch(V1, AmendmentOperation.REPLACE_TEXT,
                    old_text="999 triệu đồng", new_text="700 triệu đồng")
    assert r.status == STATUS_NEEDS_REVIEW
    assert r.match_count == 0
    assert r.new_content is None


def test_delete_text():
    r = apply_patch("Hạn mức là 500 triệu đồng và không đổi.",
                    AmendmentOperation.DELETE_TEXT, old_text=" và không đổi")
    assert r.status == STATUS_OK
    assert "không đổi" not in r.new_content


def test_insert_text_is_non_destructive():
    r = apply_patch("Điều khoản gốc.", AmendmentOperation.INSERT_TEXT,
                    new_text="Bổ sung điểm mới.")
    assert r.status == STATUS_OK
    assert "Điều khoản gốc." in r.new_content
    assert "Bổ sung điểm mới." in r.new_content


def test_repeal_provision_empties_content():
    r = apply_patch(V1, AmendmentOperation.REPEAL_PROVISION)
    assert r.status == STATUS_OK
    assert r.new_content == ""
