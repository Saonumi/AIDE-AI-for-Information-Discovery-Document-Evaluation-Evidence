"""Foundation self-check: money/date canonicalisation is what patch & conflict rely on."""
from datetime import date

from packages.common.vn_normalize import (
    money_equal,
    money_to_vnd,
    normalize_date,
    parse_vn_number,
    strip_accents,
)


def test_money_variants_equal_500m():
    for s in ["500 triệu đồng", "500 triệu", "500tr", "500.000.000", "500.000.000đ", "0,5 tỷ"]:
        assert money_to_vnd(s) == 500_000_000, s


def test_money_700_vs_600():
    assert money_to_vnd("700 triệu đồng") == 700_000_000
    assert money_to_vnd("600 triệu") == 600_000_000
    assert not money_equal("700 triệu", "600 triệu")
    assert money_equal("700 triệu", "700.000.000")


def test_billion():
    assert money_to_vnd("1 tỷ") == 1_000_000_000
    assert money_to_vnd("1,5 tỷ") == 1_500_000_000


def test_parse_number():
    assert parse_vn_number("500.000.000") == 500_000_000
    assert parse_vn_number("1.234.567,5") == 1234567.5
    assert parse_vn_number("0,5") == 0.5


def test_dates():
    assert normalize_date("hiệu lực từ 01/07/2026") == date(2026, 7, 1)
    assert normalize_date("ngày 01 tháng 7 năm 2026") == date(2026, 7, 1)
    assert normalize_date("2026-07-01") == date(2026, 7, 1)
    assert normalize_date("không có ngày") is None


def test_strip_accents():
    assert strip_accents("Hạn mức tín dụng") == "Han muc tin dung"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("all vn_normalize checks passed")
