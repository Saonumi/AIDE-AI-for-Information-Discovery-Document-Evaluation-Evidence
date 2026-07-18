"""Offline tests for the VBPL source (no network).

VBPL is a Next.js app: document metadata is a schema.org/Legislation JSON-LD object
streamed inside `self.__next_f.push([...])` script chunks, and relationships are encoded
in the URL slug (the authoritative relationship tab is /api/-only = robots-Disallowed).
These tests cover both the flight-data parse and the slug relation-mining.

Run: PYTHONIOENCODING=utf-8 python -m pytest tests/test_crawl_vbpl.py -q
(or plain `python tests/test_crawl_vbpl.py` to run the asserts directly).
"""
from __future__ import annotations

import json
from datetime import date

from crawl.models import DocType, RelationType
from crawl.sources.vbpl import (
    VbplSource,
    _relations_from_slug,
    _slug_and_itemid,
    get_source,
)


def _make_detail_html(legislation: dict) -> str:
    """Wrap a Legislation JSON-LD object in a Next.js flight chunk, exactly like vbpl.vn.

    The real page double-encodes: the JSON-LD is a JSON string whose quotes are \\-escaped,
    and that whole thing is itself a JS string literal inside `self.__next_f.push([1, "..."])`.
    """
    ld_json = json.dumps(legislation, ensure_ascii=False)
    # Build the flight payload string: [["$","script",null,{"...__html":"<escaped ld>"...}]]
    payload = (
        '2:[["$","script",null,{"type":"application/ld+json",'
        '"dangerouslySetInnerHTML":{"__html":' + json.dumps(ld_json, ensure_ascii=False) + "}}]]"
    )
    chunk = json.dumps(payload, ensure_ascii=False)  # JS string literal
    return (
        "<html><body>"
        "<script>self.__next_f=self.__next_f||[]</script>"
        f'<script>self.__next_f.push([1,{chunk}])</script>'
        "</body></html>"
    )


# A real NHNN banking amendment URL (from sitemap-trung-uong-1.xml), trimmed.
NHNN_URL = (
    "https://vbpl.vn/van-ban/chi-tiet/"
    "thong-tu-so-39-2016-tt-nhnn-sua-doi-bo-sung-mot-so-dieu-cua-thong-tu-so-"
    "36-2014-tt-nhnn-duoc-thay-the-boi-thong-tu-so-22-2019-tt-nhnn--123456"
)

NHNN_LEGISLATION = {
    "@context": "https://schema.org",
    "@type": "Legislation",
    "name": "Thông tư số 39/2016/TT-NHNN quy định về hoạt động cho vay",
    "legislationIdentifier": "39/2016/TT-NHNN",
    "legislationType": "Thông tư",
    "legislationDate": "2016-12-30T00:00:00",
    "legislationLegalForce": "InForce",
    "legislationPassedBy": {"@type": "Organization", "name": "Ngân hàng Nhà nước Việt Nam"},
    "url": NHNN_URL,
    "inLanguage": "vi",
}


def test_slug_and_itemid():
    slug, item_id = _slug_and_itemid(NHNN_URL)
    assert item_id == "123456"
    assert slug.startswith("thong-tu-so-39-2016-tt-nhnn")


def test_slug_relations_map_amends_supersededby_and_skip_self():
    slug, _ = _slug_and_itemid(NHNN_URL)
    rels = _relations_from_slug(slug)
    targets = {(r.type, r.target_doc_number) for r in rels}
    # this doc AMENDS 36/2014 (…-sua-doi-bo-sung…-cua-…36-2014…)
    assert (RelationType.AMENDS, "36/2014/TT-NHNN") in targets
    # this doc is SUPERSEDED_BY 22/2019 (…-duoc-thay-the-boi-…22-2019…)
    assert (RelationType.SUPERSEDED_BY, "22/2019/TT-NHNN") in targets
    # the document's OWN number is never emitted as a relation target
    assert all(t != "39/2016/TT-NHNN" for _, t in targets)


def test_slug_relations_active_vs_passive_direction():
    # active "thay the" (no "boi") -> SUPERSEDES
    active = "quyet-dinh-so-1-2020-qd-ttg-thay-the-quyet-dinh-so-2-2010-qd-ttg"
    rels = _relations_from_slug(active)
    assert (RelationType.SUPERSEDES, "2/2010/QD-TTG") in {
        (r.type, r.target_doc_number) for r in rels
    }
    # passive "duoc huong dan boi" -> GUIDED_BY
    passive = "nghi-dinh-so-10-2019-nd-cp-duoc-huong-dan-boi-thong-tu-so-5-2020-tt-nhnn"
    rels = _relations_from_slug(passive)
    assert (RelationType.GUIDED_BY, "5/2020/TT-NHNN") in {
        (r.type, r.target_doc_number) for r in rels
    }


def test_parse_extracts_metadata_from_flight_jsonld():
    html = _make_detail_html(NHNN_LEGISLATION)
    item = VbplSource().parse(NHNN_URL, html)
    assert item is not None
    assert item.doc_number == "39/2016/TT-NHNN"
    assert item.doc_type == DocType.THONG_TU
    assert item.issuer == "Ngân hàng Nhà nước Việt Nam"
    assert item.issued_date == date(2016, 12, 30)
    assert item.status == "Còn hiệu lực"  # InForce
    assert item.is_banking is True
    # relations come from the slug, not the JSON-LD
    targets = {(r.type, r.target_doc_number) for r in item.relations}
    assert (RelationType.AMENDS, "36/2014/TT-NHNN") in targets
    assert (RelationType.SUPERSEDED_BY, "22/2019/TT-NHNN") in targets
    # full_text limitation is documented in fields
    assert item.fields.get("full_text_available") is False
    assert item.fields.get("relations_source") == "slug"


def test_parse_handles_cyrillic_confusable_in_docnumber():
    """vbpl.vn sometimes emits a Cyrillic 'С' in codes like 'TT-BTС'; we fold to Latin."""
    leg = dict(NHNN_LEGISLATION)
    leg["legislationIdentifier"] = "06/2026/TT-BTС"  # trailing Cyrillic Es
    leg["url"] = "https://vbpl.vn/van-ban/chi-tiet/thong-tu-so-06-2026-tt-btc--1"
    item = VbplSource().parse(leg["url"], _make_detail_html(leg))
    assert item.doc_number == "06/2026/TT-BTC"  # all-Latin


def test_get_source_returns_named_source():
    s = get_source()
    assert s.name == "vbpl"


if __name__ == "__main__":
    test_slug_and_itemid()
    test_slug_relations_map_amends_supersededby_and_skip_self()
    test_slug_relations_active_vs_passive_direction()
    test_parse_extracts_metadata_from_flight_jsonld()
    test_parse_handles_cyrillic_confusable_in_docnumber()
    test_get_source_returns_named_source()
    print("all vbpl tests passed")
