"""SHB public-docs crawler (source name="shb").

Target: PUBLIC, bank-specific, time-versioned documents on https://www.shb.com.vn/ —
biểu phí dịch vụ (fee schedules), lãi suất tiền gửi/cho vay (deposit/loan rates),
điều khoản điều kiện sản phẩm (product T&C), and thông báo (notices). These are exactly
the artefacts that change over time and produce real amendments/version chains, which is
what the downstream temporal-RAG graph needs.

Compliance
----------
robots.txt for shb.com.vn is `User-agent: * / Allow: /` with a Content-Signal of
`search=yes, ai-train=no, use=reference`. This crawler is REFERENCE / RAG use (grounding
retrieval), NOT model training, so it honours ai-train=no. Every fetch goes through the
frozen RespectfulClient (robots + rate-limit + cache + budget). We never log in and never
solve/bypass any bot challenge.

Honest status (see recon in the task report)
--------------------------------------------
As of this build, EVERY path on www.shb.com.vn (homepage, section pages, sitemaps) returns
HTTP 403 with `cf-mitigated: challenge` — a Cloudflare *managed challenge* that requires a
JS-capable browser. Static HTTP clients (this crawler, and even a headless-renderer WebFetch)
are blocked. Solving that challenge would need a full browser and would arguably be a bypass,
which is out of scope. So in practice this source yields 0 items right now.

The crawler is still written correctly and defensively: it discovers candidate fee/rate/terms
listing + PDF pages from the homepage and known section paths, and parse() extracts title /
doc_type / effective_date. If SHB drops the challenge (or a page is already cached from a
browser session under data/crawl/shb/raw/), it will produce real CrawlItems with no changes.
discover() detects the challenge wall and stops early instead of burning the request budget.
"""
from __future__ import annotations

import re
from typing import Iterable, Iterator, Optional
from urllib.parse import urljoin, urlsplit

from crawl.base import Source
from crawl.http_client import RespectfulClient
from crawl.models import CrawlItem, DocType
from crawl.util import html_to_text, is_banking
from packages.common.vn_normalize import normalize_date, strip_accents

BASE = "https://www.shb.com.vn/"

# Section / listing pages where SHB publishes the time-versioned public docs we want.
# These are best-effort guesses at the public IA; discover() also scrapes the homepage
# for links so it adapts if the paths differ. All are fetched via RespectfulClient (robots).
SEED_PATHS = [
    "",  # homepage — primary link source
    "bieu-phi",
    "bieu-phi-dich-vu",
    "lai-suat",
    "lai-suat-tien-gui",
    "lai-suat-cho-vay",
    "dieu-khoan-dieu-kien",
    "thong-bao",
    "nha-dau-tu",
    "quan-he-co-dong",
    "cong-bo-thong-tin",
]

# Accent-folded keywords that mark a link as a target doc/listing (title or slug).
_TARGET_KWS = [
    "bieu phi", "lai suat", "dieu khoan", "dieu kien", "thong bao",
    "cong bo thong tin", "nha dau tu", "quan he co dong", "phi dich vu",
]

# Signals that a returned page is a Cloudflare bot challenge rather than real content.
_CHALLENGE_MARKERS = ("challenge-platform", "cf-mitigated", "just a moment",
                      "enable javascript to")


def _fold(s: str) -> str:
    return re.sub(r"[-_./]+", " ", strip_accents((s or "").lower()))


def _looks_like_challenge(html: str) -> bool:
    low = html[:6000].lower()
    return any(m in low for m in _CHALLENGE_MARKERS)


def _is_target_link(text: str, href: str) -> bool:
    f = _fold(text + " " + href)
    return any(k in f for k in _TARGET_KWS)


def _doc_type_for(text: str) -> Optional[DocType]:
    f = _fold(text)
    if "bieu phi" in f or "phi dich vu" in f:
        return DocType.BIEU_PHI
    if "lai suat" in f:
        return DocType.LAI_SUAT
    if "dieu khoan" in f or "dieu kien" in f:
        return DocType.DIEU_KHOAN
    if "thong bao" in f:
        return DocType.THONG_BAO
    return None


# "áp dụng từ dd/mm/yyyy", "có hiệu lực từ ngày ...", "hiệu lực kể từ ..."
_EFFECTIVE_HINT_RE = re.compile(
    r"(?:ap dung|co hieu luc|hieu luc|ke tu ngay|tu ngay)\D{0,20}"
    r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})",
    re.IGNORECASE,
)


def _effective_date_from(text: str):
    """Prefer a date attached to an 'áp dụng/hiệu lực từ' phrase; else first date."""
    folded = strip_accents(text or "").lower()
    m = _EFFECTIVE_HINT_RE.search(folded)
    if m:
        d = normalize_date(m.group(1))
        if d:
            return d
    return normalize_date(text or "")


class ShbSource(Source):
    name = "shb"

    def discover(self, client: RespectfulClient, limit: int) -> Iterable[str]:
        seen: set[str] = set()
        yielded = 0
        for i, path in enumerate(SEED_PATHS):
            if yielded >= limit:
                return
            listing_url = urljoin(BASE, path)
            html = client.get(listing_url)
            if html is None:
                # RespectfulClient returns None for a 403 Cloudflare challenge (it only
                # caches/returns 200s). If even the HOMEPAGE (first seed) is unreachable,
                # the whole site is walled — stop instead of burning the budget on every
                # seed path. Honest outcome: SHB not obtainable via static HTTP right now.
                if i == 0:
                    return
                continue
            if _looks_like_challenge(html):
                # A challenge served WITH a 200 (some Cloudflare modes) — also a wall.
                return
            # Yield the listing/section page itself if it is a target (may be an
            # HTML fee/rate table).
            if path and listing_url not in seen and _is_target_link(path, listing_url):
                seen.add(listing_url)
                yield listing_url
                yielded += 1
            # Scrape links: target HTML pages and PDF fee/rate/terms docs.
            for url, text in self._links(listing_url, html):
                if yielded >= limit:
                    return
                if url in seen:
                    continue
                is_pdf = url.lower().split("?")[0].endswith(".pdf")
                if is_pdf or _is_target_link(text, url):
                    seen.add(url)
                    yield url
                    yielded += 1

    @staticmethod
    def _links(base_url: str, html: str) -> Iterator[tuple[str, str]]:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
        except Exception:  # noqa: BLE001
            return
        host = urlsplit(BASE).netloc
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            full = urljoin(base_url, href)
            # Keep same-host links (and PDFs) only.
            if urlsplit(full).netloc and urlsplit(full).netloc != host:
                if not full.lower().split("?")[0].endswith(".pdf"):
                    continue
            yield full, a.get_text(" ", strip=True)

    def parse(self, url: str, raw: str) -> Optional[CrawlItem]:
        is_pdf = url.lower().split("?")[0].endswith(".pdf")

        if is_pdf:
            # We captured the PDF URL as a reference; RespectfulClient stored bytes as
            # text. Do NOT try to parse binary — record metadata from the URL slug and
            # let the ingestion layer fetch/parse the PDF if needed. Full text optional.
            title = _title_from_slug(url)
            doc_type = _doc_type_for(title) or _doc_type_for(url)
            item = CrawlItem(
                source=self.name,
                url=url,
                title=title or None,
                doc_type=doc_type,
                effective_date=_effective_date_from(title),
                is_banking=True,  # SHB = a bank; these docs are bank-specific by construction
                fields={"is_pdf": True, "captured": "metadata_only"},
            )
            return item

        # HTML page.
        if _looks_like_challenge(raw):
            return None  # blocked page — nothing real to parse
        title = _html_title(raw) or _title_from_slug(url)
        text = html_to_text(raw)
        doc_type = _doc_type_for(title) or _doc_type_for(text[:400])
        eff = _effective_date_from(title) or _effective_date_from(text[:2000])
        banking = True if _doc_type_for(title) else is_banking(title + " " + url)
        return CrawlItem(
            source=self.name,
            url=url,
            title=title or None,
            doc_type=doc_type,
            effective_date=eff,
            full_text=text or None,
            is_banking=banking,
            fields={"is_pdf": False},
        )


def _html_title(html: str) -> str:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        # Prefer an <h1>, fall back to <title>.
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            return h1.get_text(" ", strip=True)
        if soup.title and soup.title.get_text(strip=True):
            return soup.title.get_text(" ", strip=True)
    except Exception:  # noqa: BLE001
        pass
    return ""


def _title_from_slug(url: str) -> str:
    last = urlsplit(url).path.rsplit("/", 1)[-1]
    last = re.sub(r"\.(pdf|aspx|html?)$", "", last, flags=re.IGNORECASE)
    last = re.sub(r"[-_]+", " ", last).strip()
    return last


def get_source() -> Source:
    return ShbSource()
