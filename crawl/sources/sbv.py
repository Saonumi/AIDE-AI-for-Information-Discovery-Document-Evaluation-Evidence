"""SBV (State Bank of Vietnam, sbv.gov.vn) source — banking Thông tư / Quyết định.

Recon summary (what the live site actually is)
----------------------------------------------
The Vietnamese legal-documents section ("Văn bản quy phạm pháp luật") lives at
``https://www.sbv.gov.vn/vi/legal-documents``. It is a Liferay *Asset Publisher*
portlet (instance id ``ncdx``). Pagination is driven by portlet query params:

    ?p_p_id=<PORTLET>&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view
    &_<PORTLET>_delta=10          # page size
    &_<PORTLET>_cur=<N>           # 1-based page number

At the time of writing there are ~63 documents across 7 pages (10/page). Each row
is an ``<a class="title-news-link" href="/vi/web/sbv_portal/w/<slug>?redirect=...">``
whose text is the full document title (e.g. "Thông tư số 06/2026/TT-NHNN quy định
về giám định tư pháp ..."). A few trailing ``title-news-link`` anchors are unrelated
news items from a sidebar block, so we filter to entries that actually look like a
legal document (doc-number in the title + banking keyword).

Detail page: a summary/landing page. It carries the H1 title, a short article body
(``div.journal-content-article``) that repeats the title + a displayed date, the
category "Văn bản quy phạm pháp luật", and — crucially — a link to a **scanned PDF**
of the real circular under ``/documents/20117/0/<file>.pdf``.

PDF vs HTML: the binding legal text is inside the scanned PDF, NOT in the HTML.
``RespectfulClient.get`` is text-only (it would mojibake PDF bytes), so per the brief
we do NOT try to decode the PDF here. We capture rich metadata from the HTML
(doc_number, title, doc_type, issued_date when shown, category/status) plus the PDF
URL (in ``fields['pdf_url']`` and as a RELATED-ish note), and we store the readable
HTML summary as ``full_text``. Relations (AMENDS/SUPERSEDES targets) are mined from
the title when it says "sửa đổi, bổ sung ... Thông tư số X".
"""
from __future__ import annotations

import logging
import re
from typing import Iterable, Iterator, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from crawl.base import Source
from crawl.http_client import RespectfulClient
from crawl.models import CrawlItem, DocType, Relation, RelationType
from crawl.util import (
    extract_doc_number,
    guess_doc_type,
    html_to_text,
    is_amendment,
    is_banking,
)
from packages.common.vn_normalize import normalize_date

log = logging.getLogger("crawl")

BASE = "https://www.sbv.gov.vn"
LISTING = f"{BASE}/vi/legal-documents"
PORTLET = "com_liferay_asset_publisher_web_portlet_AssetPublisherPortlet_INSTANCE_ncdx"
ISSUER = "Ngân hàng Nhà nước"

# A legal document title we care about: contains a doc-number token like "39/2016/TT-NHNN".
_DOCNUM_IN_TITLE = re.compile(r"\d{1,4}/\d{4}/[A-ZĐ]{1,6}(?:-[A-ZĐ]{1,8})?", re.IGNORECASE)
# "Thông tư số 27/2024/TT-NHNN" targets referenced in an amendment title.
_ALL_DOCNUMS = re.compile(r"\d{1,4}/\d{4}/[A-ZĐ]{1,6}(?:-[A-ZĐ]{1,8})?", re.IGNORECASE)


def _page_url(page: int) -> str:
    return (
        f"{LISTING}?p_p_id={PORTLET}&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view"
        f"&_{PORTLET}_delta=10&_{PORTLET}_cur={page}"
    )


def _clean_detail_url(href: str) -> str:
    """Strip the ?redirect=... portlet noise and absolutise the detail link."""
    return urljoin(BASE, href.split("?")[0])


class SbvSource(Source):
    name = "sbv"

    # How many listing pages we are willing to walk in one run (politeness cap).
    max_pages = 12

    def discover(self, client: RespectfulClient, limit: int) -> Iterable[str]:
        yielded = 0
        seen: set[str] = set()
        for page in range(1, self.max_pages + 1):
            if yielded >= limit:
                break
            html = client.get(_page_url(page))
            if not html:
                log.warning("[sbv] listing page %d unreachable — stopping", page)
                break
            page_had_candidate = False
            for url, title in self._iter_listing(html):
                page_had_candidate = True
                if url in seen:
                    continue
                seen.add(url)
                # Keep only real banking circulars/decisions.
                if not _DOCNUM_IN_TITLE.search(title):
                    continue
                if guess_doc_type(title) not in (DocType.THONG_TU, DocType.QUYET_DINH):
                    continue
                if not is_banking(title):
                    # SBV titles are overwhelmingly banking; keep amendment/QPPL ones too.
                    if not is_amendment(title):
                        continue
                yield url
                yielded += 1
                if yielded >= limit:
                    break
            if not page_had_candidate:
                # Empty page => past the end of the listing.
                log.info("[sbv] no rows on page %d — assuming end of listing", page)
                break

    def _iter_listing(self, html: str) -> Iterator[tuple[str, str]]:
        soup = BeautifulSoup(html, "lxml")
        for a in soup.select("a.title-news-link[href]"):
            title = a.get_text(" ", strip=True)
            if not title:
                continue
            yield _clean_detail_url(a["href"]), title

    def parse(self, url: str, raw: str) -> Optional[CrawlItem]:
        soup = BeautifulSoup(raw, "lxml")

        # Title: prefer the H1, fall back to <title> (minus site suffix).
        title = None
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(" ", strip=True)
        if not title:
            t = soup.find("title")
            if t:
                title = t.get_text(strip=True).split(" - Ngân hàng")[0].strip()
        if not title:
            return None

        doc_number = extract_doc_number(title)

        # The short article body repeats title + shows a displayed date + PDF link.
        art = soup.select_one("div.journal-content-article")
        body_text = art.get_text(" ", strip=True) if art else ""

        # issued_date: from the title's "ngày dd tháng mm năm yyyy" / "ngày dd/mm/yyyy"
        # first (authoritative), else the first date shown in the article body.
        issued_date = normalize_date(title)
        if issued_date is None and body_text:
            # Skip the title portion inside the body, look at what follows.
            tail = body_text[len(title):] if body_text.startswith(title[:40]) else body_text
            issued_date = normalize_date(tail) or normalize_date(body_text)

        doc_type = guess_doc_type(title) or guess_doc_type(doc_number or "")

        # Scanned-PDF attachment of the real circular text.
        pdf_url = self._find_pdf(soup, art)

        # full_text: readable HTML summary of the landing page (real legal text is in the PDF).
        full_text = html_to_text(raw)

        # status/category — SBV tags these as "Văn bản quy phạm pháp luật".
        status = "Văn bản quy phạm pháp luật" if "quy phạm pháp luật" in body_text.lower() else None

        relations = self._extract_relations(title, doc_number)

        fields = {"category": "van_ban_quy_pham_phap_luat"}
        if pdf_url:
            fields["pdf_url"] = pdf_url
            fields["has_scanned_pdf"] = True
            fields["note"] = "Binding legal text is in the scanned PDF (not decoded here)."

        return CrawlItem(
            source=self.name,
            url=url,
            doc_number=doc_number,
            title=title,
            doc_type=doc_type,
            issuer=ISSUER,
            issued_date=issued_date,
            effective_date=None,  # not present in HTML; lives inside the scanned PDF
            status=status,
            full_text=full_text,
            relations=relations,
            is_banking=True,
            fields=fields,
        )

    @staticmethod
    def _find_pdf(soup: BeautifulSoup, art) -> Optional[str]:
        scope = art if art is not None else soup
        for a in scope.find_all("a", href=True):
            href = a["href"]
            if re.search(r"\.pdf(\?|$)", href, re.I) or "/documents/" in href:
                if re.search(r"\.(pdf|doc|docx)", href, re.I) or "/documents/" in href:
                    return urljoin(BASE, href)
        return None

    @staticmethod
    def _extract_relations(title: str, self_docnum: Optional[str]) -> List[Relation]:
        """Mine AMENDS/SUPERSEDES targets from an amendment title.

        SBV titles like "... sửa đổi, bổ sung một số điều của Thông tư số
        27/2024/TT-NHNN ..." name the target explicitly. We treat "sửa đổi/bổ sung"
        as AMENDS and "thay thế/bãi bỏ" as SUPERSEDES.
        """
        rels: List[Relation] = []
        if not is_amendment(title):
            return rels
        low = title.lower()
        rtype = RelationType.SUPERSEDES if ("thay thế" in low or "bãi bỏ" in low) else RelationType.AMENDS
        for m in _ALL_DOCNUMS.finditer(title):
            target = m.group(0)
            if self_docnum and target == self_docnum:
                continue  # don't relate a doc to itself
            if any(r.target_doc_number == target for r in rels):
                continue
            rels.append(Relation(type=rtype, target_doc_number=target))
        return rels


def get_source() -> Source:
    return SbvSource()
