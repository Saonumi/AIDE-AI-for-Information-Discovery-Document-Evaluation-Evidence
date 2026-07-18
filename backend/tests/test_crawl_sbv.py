"""Offline tests for the SBV source (no network — uses a static fixture + cached raw).

Run: PYTHONIOENCODING=utf-8 python -m pytest tests/test_crawl_sbv.py -q
(or plain `python tests/test_crawl_sbv.py` to run the asserts directly).
"""
from __future__ import annotations

from datetime import date

from crawl.models import DocType, RelationType
from crawl.sources.sbv import SbvSource, _clean_detail_url, _page_url, get_source

# A trimmed but structurally-faithful slice of a real SBV /vi/legal-documents listing page.
LISTING_FIXTURE = """
<html><body>
<ul>
  <li><a class="title-news-link"
        href="/vi/web/sbv_portal/w/thong-tu-so-08-2026?redirect=%2Fvi%2Flegal-documents%3Fp_p_id">
        Thông tư số 08/2026/TT-NHNN ngày 15 tháng 5 năm 2026 Sửa đổi, bổ sung điểm a khoản 4
        Điều 20 Thông tư số 22/2019/TT-NHNN</a></li>
  <li><a class="title-news-link"
        href="/vi/web/sbv_portal/w/thong-tu-so-31-2026?redirect=x">
        Thông tư số 31/2026/TT-NHNN ngày 30/6/2026 quy định về hoạt động cho thuê tài chính</a></li>
  <li><a class="title-news-link" href="/vi/web/sbv_portal/w/tin-tuc-nam-2026?redirect=x">
        Hành trình 75 năm Ngành Ngân hàng - vì một Việt Nam</a></li>
</ul>
</body></html>
"""

# A trimmed detail page mirroring div.journal-content-article + scanned-PDF link.
DETAIL_FIXTURE = """
<html><head><title>Thông tư số 08/2026/TT-NHNN ... - Ngân hàng Nhà nước Việt Nam</title></head>
<body>
<h1>Thông tư số 08/2026/TT-NHNN ngày 15 tháng 5 năm 2026 Sửa đổi, bổ sung điểm a khoản 4
Điều 20 Thông tư số 22/2019/TT-NHNN</h1>
<div class="journal-content-article">
  Thông tư số 08/2026/TT-NHNN ngày 15 tháng 5 năm 2026 Sửa đổi, bổ sung ...
  Đính kèm
  <a href="/documents/20117/0/08.2026.TT-NHNN.pdf/abc?t=1">Thông tư số 08/2026/TT-NHNN</a>
  Các chuyên mục: Văn bản quy phạm pháp luật
</div>
</body></html>
"""


def test_page_url_has_portlet_pagination():
    u = _page_url(3)
    assert "AssetPublisherPortlet_INSTANCE_ncdx_cur=3" in u
    assert "_delta=10" in u


def test_clean_detail_url_strips_redirect():
    got = _clean_detail_url("/vi/web/sbv_portal/w/foo?redirect=%2Fvi%2Flegal-documents")
    assert got == "https://www.sbv.gov.vn/vi/web/sbv_portal/w/foo"


def test_listing_filters_to_banking_docs_only():
    src = SbvSource()
    rows = list(src._iter_listing(LISTING_FIXTURE))
    assert len(rows) == 3  # all three anchors are seen...
    # ...but discover-style filtering keeps only the two real circulars.
    from crawl.util import guess_doc_type, is_banking, is_amendment
    import re
    keep = [
        (u, t) for u, t in rows
        if re.search(r"\d+/\d{4}/[A-ZĐ]", t)
        and guess_doc_type(t) in (DocType.THONG_TU, DocType.QUYET_DINH)
        and (is_banking(t) or is_amendment(t))
    ]
    assert len(keep) == 2
    assert all("TT-NHNN" in t for _, t in keep)


def test_parse_extracts_full_metadata_and_relation():
    item = SbvSource().parse("https://www.sbv.gov.vn/vi/web/sbv_portal/w/thong-tu-so-08-2026",
                             DETAIL_FIXTURE)
    assert item is not None
    assert item.doc_number == "08/2026/TT-NHNN"
    assert item.doc_type == DocType.THONG_TU
    assert item.issuer == "Ngân hàng Nhà nước"
    assert item.issued_date == date(2026, 5, 15)
    assert item.is_banking is True
    assert item.full_text and len(item.full_text) > 50
    assert item.fields.get("pdf_url", "").endswith("08.2026.TT-NHNN.pdf/abc?t=1")
    # amendment title -> AMENDS relation to the target it modifies (not itself).
    targets = {(r.type, r.target_doc_number) for r in item.relations}
    assert (RelationType.AMENDS, "22/2019/TT-NHNN") in targets
    assert (RelationType.AMENDS, "08/2026/TT-NHNN") not in targets


def test_get_source_returns_named_source():
    s = get_source()
    assert s.name == "sbv"


if __name__ == "__main__":
    test_page_url_has_portlet_pagination()
    test_clean_detail_url_strips_redirect()
    test_listing_filters_to_banking_docs_only()
    test_parse_extracts_full_metadata_and_relation()
    test_get_source_returns_named_source()
    print("all sbv tests passed")
