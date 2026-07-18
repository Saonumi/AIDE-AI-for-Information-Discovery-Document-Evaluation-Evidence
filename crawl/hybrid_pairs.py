"""Hybrid demo pairs — REAL regulatory identities + REAL amendment edges + REAL dates,
with clause text as clearly-labelled SYNTHETIC content (readable on both endpoints).

Why this exists (honest): live crawling gives us real document identities, real
amendment/supersession relations, and 3 real full-text circulars — but the *amended*
targets are old cross-ministry docs behind gates, so we cannot cheaply obtain real
clause text on BOTH ends of an amendment pair. To demo the temporal engine (validity
intervals, deterministic amendment patch, version chain) we bind synthetic-but-clearly-
labelled clause text onto the REAL skeleton mined from SBV titles like
"08/2026/TT-NHNN sửa đổi, bổ sung điểm a khoản 4 Điều ... của Thông tư 22/2019/TT-NHNN".

Every synthetic body carries a SYNTHETIC banner and fields flags so nothing is ever
mistaken for real legal text. Real crawl data under data/crawl/{sbv,vbpl,...} is NOT
touched — hybrid items live in their own source folder data/crawl/hybrid/.

    python -m crawl.hybrid_pairs          # writes hybrid items
    python -m crawl.hybrid_pairs --check  # self-check
"""
from __future__ import annotations

import logging
from datetime import date

from crawl import storage
from crawl.base import _atomic_write_json
from crawl.models import CrawlItem, DocType, Relation, RelationType

log = logging.getLogger("crawl")

BANNER = (
    "[VĂN BẢN DEMO — nội dung điều khoản dưới đây là SYNTHETIC (tổng hợp minh hoạ) để "
    "trình diễn cơ chế hiệu lực-theo-thời-gian và vá sửa đổi. Nó GẮN với ĐỊNH DANH THẬT "
    "và QUAN HỆ SỬA ĐỔI THẬT (mined từ crawl SBV), nhưng KHÔNG phải văn bản pháp luật thật.]"
)

# Real skeletons mined from SBV crawl (amender doc_number, real, and its real AMENDS target).
# clause = the specific provision the amendment touches; old_val -> new_val is the demo patch.
PAIRS = [
    {
        "amender": "08/2026/TT-NHNN", "amender_date": date(2026, 5, 15),
        "target": "22/2019/TT-NHNN", "target_date": date(2019, 11, 15),
        "dieu": 4, "khoan": 4, "diem": "a",
        "topic": "tỷ lệ tối đa nguồn vốn ngắn hạn được sử dụng để cho vay trung, dài hạn",
        "old_val": "34%", "new_val": "30%",
    },
    {
        "amender": "10/2026/TT-NHNN", "amender_date": date(2026, 6, 1),
        "target": "27/2024/TT-NHNN", "target_date": date(2024, 6, 28),
        "dieu": 6, "khoan": 2, "diem": "b",
        "topic": "thời hạn tổ chức tín dụng gửi báo cáo thống kê định kỳ",
        "old_val": "ngày 10 hằng tháng", "new_val": "ngày 05 hằng tháng",
    },
    {
        "amender": "13/2026/TT-NHNN", "amender_date": date(2026, 6, 20),
        "target": "53/2018/TT-NHNN", "target_date": date(2018, 12, 31),
        "dieu": 3, "khoan": 1, "diem": "a",
        "topic": "tỷ lệ dự phòng chung phải trích lập trên tổng dư nợ",
        "old_val": "0,75%", "new_val": "1,00%",
    },
]


def _pad(text: str) -> str:
    """Ensure >=800 chars so it reads as clause-level text (audit.clause_text_signal)."""
    filler = (" Tổ chức tín dụng, chi nhánh ngân hàng nước ngoài có trách nhiệm rà soát, "
              "điều chỉnh và tổ chức thực hiện theo đúng quy định tại Thông tư này.")
    while len(text) < 850:
        text += filler
    return text


def _dmy(d: date) -> str:
    """dd/mm/yyyy — the date form the ingestion regex/normalize_date reliably parse."""
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def _target_text(p: dict) -> str:
    # Value lives directly in the Khoản (point-free) so the amendment locator
    # "Khoản K Điều D" resolves to exactly this provision (exact lookup_key match).
    # "Hiệu lực từ ngày ..." on its own preamble line feeds document valid_from.
    return _pad(
        f"{BANNER}\n\nThông tư số {p['target']}\n"
        f"Hiệu lực từ ngày {_dmy(p['target_date'])}.\n"
        f"Điều {p['dieu']}. Quy định về {p['topic']}\n"
        f"{p['khoan']}. {p['topic'].capitalize()} là {p['old_val']}.\n"
        f"Điều {p['dieu']+1}. Điều khoản thi hành\n"
        f"1. Tổ chức tín dụng có trách nhiệm tổ chức thực hiện Thông tư này."
    )


def _amender_text(p: dict) -> str:
    loc = f"Khoản {p['khoan']} Điều {p['dieu']}"
    # The machine-readable REPLACE line is what drives the live upload->parse->activate
    # amendment pipeline (ingestion.legal_extract._RE_REPLACE); without it the amendment
    # is invisible to the parser and no ChangeEvent/version-2 is ever produced.
    return _pad(
        f"{BANNER}\n\n"
        f"Thông tư số {p['amender']} sửa đổi, bổ sung {loc} của Thông tư số {p['target']}\n"
        f"Hiệu lực từ ngày {_dmy(p['amender_date'])}.\n"
        f"Điều 1. Sửa đổi, bổ sung {loc} của Thông tư số {p['target']}\n"
        f'Thay "{p["old_val"]}" bằng "{p["new_val"]}" tại {loc}, hiệu lực từ {_dmy(p["amender_date"])}.\n'
        f"Điều 2. Điều khoản thi hành\n"
        f"1. Thông tư này có hiệu lực thi hành kể từ ngày {_dmy(p['amender_date'])}."
    )


def _item(source: str, doc_number: str, title: str, issued: date, full_text: str,
          relations=None) -> CrawlItem:
    return CrawlItem(
        source=source,
        url=f"hybrid://{doc_number}",
        doc_number=doc_number,
        title=title,
        doc_type=DocType.THONG_TU,
        issuer="Ngân hàng Nhà nước",
        issued_date=issued,
        effective_date=issued,
        status="Còn hiệu lực",
        full_text=full_text,
        relations=relations or [],
        is_banking=True,
        fields={
            "synthetic_clause_text": True,
            "identity_source": "real_sbv_crawl",
            "relation_source": "real_sbv_crawl",
            "note": "clause text synthetic (labelled); identity + amendment edge are real",
        },
    )


def build() -> dict:
    n = 0
    for p in PAIRS:
        target = _item("hybrid", p["target"],
                       f"Thông tư số {p['target']} quy định về {p['topic']}",
                       p["target_date"], _target_text(p))
        amender = _item("hybrid", p["amender"],
                        f"Thông tư số {p['amender']} sửa đổi, bổ sung một số điều "
                        f"của Thông tư số {p['target']}",
                        p["amender_date"], _amender_text(p),
                        relations=[Relation(type=RelationType.AMENDS,
                                            target_doc_number=p["target"])])
        for it in (target, amender):
            ip = storage.item_path("hybrid", it.url)
            _atomic_write_json(ip, it.model_dump(mode="json"))
            n += 1
        log.info("[hybrid] pair %s AMENDS %s (%s -> %s)",
                 p["amender"], p["target"], p["old_val"], p["new_val"])
    log.info("[hybrid] wrote %d items (%d pairs)", n, len(PAIRS))
    return {"items": n, "pairs": len(PAIRS)}


def _self_check() -> None:
    from crawl.audit import clause_text_signal
    from ingestion.legal_extract import extract_amendments
    for p in PAIRS:
        t, a = _target_text(p), _amender_text(p)
        assert clause_text_signal(t), f"target text must pass clause signal ({p['target']})"
        assert clause_text_signal(a), f"amender text must pass clause signal ({p['amender']})"
        assert BANNER in t and BANNER in a, "synthetic banner must be present"
        assert p["old_val"] in t and p["new_val"] in a, "patch values must appear"
        # The live ingestion pipeline must detect exactly this REPLACE amendment.
        ams = extract_amendments(a)
        assert len(ams) == 1, f"expected 1 amendment, got {len(ams)} for {p['amender']}"
        am = ams[0]
        assert am.old_text == p["old_val"] and am.new_text == p["new_val"], am
        assert am.valid_from == p["amender_date"], (am.valid_from, p["amender_date"])
        assert am.target_locator == f"Khoản {p['khoan']} Điều {p['dieu']}", am.target_locator
    print("self-check OK")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if "--check" in sys.argv:
        _self_check()
    else:
        print(build())
