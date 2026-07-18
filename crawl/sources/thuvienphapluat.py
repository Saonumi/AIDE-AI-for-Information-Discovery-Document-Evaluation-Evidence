"""thuvienphapluat.vn crawler — METADATA ONLY (source name="thuvienphapluat").

Hard compliance rules (from the task brief), enforced by this module's design:
  * Metadata ONLY. We never fetch, parse, or store full document text.
  * We NEVER log in, and never attempt to bypass any paywall / captcha / bot-challenge.
  * We touch ONLY genuinely-public pages. Tiny volume (limit <= 8 recommended).

Honest access situation (verified during recon)
-----------------------------------------------
On thuvienphapluat.vn the *document detail* pages (`/van-ban/.../<id>.aspx`) — where the
issued/effective dates, status, and relation panel live — are served behind a Cloudflare
"Just a moment..." managed challenge (HTTP 403, cf-mitigated: challenge) to any non-browser
client, and the full text itself is behind a member login/paywall. So the detail pages are
NOT viably obtainable, and we deliberately do not fetch them.

What IS public and fetchable (HTTP 200, no login): the site's sitemaps —
`/sitemap.xml` (a sitemap index) -> `/resitemapN.xml` (each ~1000 `/van-ban/...aspx` URLs).
Crucially, thuvienphapluat encodes real metadata in the URL slug itself, e.g.
`.../Tien-te-Ngan-hang/Thong-tu-05-2026-TT-NHNN-han-muc-chi-tra-...-714771.aspx` gives us
doc_number (05/2026/TT-NHNN), doc_type (Thông tư), year (2026), a human title, the subject
category (Tiền tệ - Ngân hàng), the site doc id (714771), and often an amendment relation
(`...-sua-doi-Thong-tu-14-2024-TT-NHNN-...`). That is public sitemap metadata — no paywall.

Therefore this source harvests banking-domain document metadata FROM THE PUBLIC SITEMAPS ONLY.
It fetches sitemaps via the frozen RespectfulClient (robots + rate-limit + cache), extracts
per-doc metadata from each URL slug, and — to fit the frozen run loop without ever hitting a
paywalled detail page — primes the RespectfulClient disk cache with a tiny sitemap-derived
stub per doc URL, so run_source's `client.get(url)` reads that stub (0 network requests, no
403) and parse() builds the CrawlItem from the slug. No detail page is ever requested.

Verdict: usable but LIMITED — we get reliable doc_number / title / doc_type / year / subject
and amendment *labels* from slugs, but NOT issued_date / effective_date / status (those live
only on the challenged, paywalled detail page). Honest and paywall-respecting by construction.
"""
from __future__ import annotations

import re
from typing import Iterable, List, Optional
from urllib.parse import unquote, urlsplit

from crawl import storage
from crawl.base import Source
from crawl.http_client import RespectfulClient
from crawl.models import CrawlItem, DocType, Relation, RelationType
from crawl.util import guess_doc_type, is_banking, iter_sitemap_locs
from packages.common.vn_normalize import strip_accents

SITEMAP_INDEX = "https://thuvienphapluat.vn/sitemap.xml"
HOST = "thuvienphapluat.vn"

# How many child resitemapN.xml files to scan before giving up (budget-safe; each ~1000 urls).
_MAX_CHILD_SITEMAPS = 12

# Vietnamese doc-type tokens as they appear slugified (accent-stripped, hyphen-joined) at the
# START of a document slug, mapped to (canonical short code used in doc_number, DocType).
# Order matters: multi-word forms first.
_TYPE_TOKENS = [
    ("van-ban-hop-nhat", "VBHN", DocType.VAN_BAN_HOP_NHAT),
    ("nghi-quyet", "NQ", DocType.NGHI_QUYET),
    ("nghi-dinh", "ND", DocType.NGHI_DINH),
    ("phap-lenh", "PL", DocType.PHAP_LENH),
    ("quyet-dinh", "QD", DocType.QUYET_DINH),
    ("chi-thi", "CT", DocType.CHI_THI),
    ("thong-tu-lien-tich", "TTLT", DocType.THONG_TU),
    ("thong-tu", "TT", DocType.THONG_TU),
    ("thong-bao", "TB", DocType.THONG_BAO),
    ("cong-van", "CV", DocType.CONG_VAN),
    ("cong-dien", "CD", DocType.CONG_VAN),
    ("luat", "LUAT", DocType.LUAT),
]

# Amendment relation cues that appear inside slugs, mapped to a RelationType.
# "van ban A sua doi van ban B" => A AMENDS B.
_REL_CUES = [
    ("sua-doi", RelationType.AMENDS),
    ("bo-sung", RelationType.AMENDS),
    ("thay-the", RelationType.SUPERSEDES),
    ("bai-bo", RelationType.SUPERSEDES),
    ("huong-dan", RelationType.GUIDES),
    ("dinh-chinh", RelationType.AMENDS),
]

# Reconstruct a doc number like "05/2026/TT-NHNN" from a slug fragment "05-2026-TT-NHNN".
# num / year / type-abbrev / (optional) issuer-abbrev.
_DOCNUM_SLUG_RE = re.compile(
    r"\b(\d{1,4})-(\d{4})-([A-Za-z]{1,6})(?:-([A-Za-z]{2,10}))?\b"
)
# Fallback A: type/issuer BEFORE year, e.g. "1279-QD-TTg-2026" -> 1279/2026/QD-TTg
_DOCNUM_TYPE_FIRST_RE = re.compile(
    r"\b(\d{1,4})-([A-Za-z]{1,6})-([A-Za-z]{2,10})-(\d{4})\b"
)
# Fallback B: single token combining chamber+term, e.g. "32-2024-QH15" -> 32/2024/QH15
_DOCNUM_QH_RE = re.compile(r"\b(\d{1,4})-(\d{4})-(QH\d{1,2})\b", re.IGNORECASE)


def _fold(s: str) -> str:
    return strip_accents((s or "").lower())


def _is_bank_regulation(slug: str, category: Optional[str]) -> bool:
    """Strict filter for genuine BANKING-REGULATOR documents (what a bank-RAG needs).

    The site's generic banking keywords (cho vay / tin dung / von) also match provincial
    HĐND budget & agriculture resolutions, which are noise here. We instead require a strong
    signal that the doc is from/about the banking sector:
      * doc number issued by the State Bank (…-NHNN), OR
      * subject category 'Tiền tệ - Ngân hàng', OR
      * an explicit banking-institution term in the slug.
    """
    low = _fold(slug)
    cat = _fold(category or "")
    if "nhnn" in low:                       # e.g. TT-NHNN, QD-NHNN, CT-NHNN
        return True
    if "tien te ngan hang" in cat:          # the dedicated banking category
        return True
    strong = ("to chuc tin dung", "ngan hang thuong mai", "ngan hang nha nuoc",
              "ngan hang hop tac", "quy tin dung", "bao hiem tien gui", "ngoai hoi",
              "trung gian thanh toan", "cong ty tai chinh", "cho thue tai chinh")
    return any(k in low for k in strong)


def _slug_last_segment(url: str) -> str:
    """The final path segment of a /van-ban/.../slug-<id>.aspx URL (the metadata-bearing slug)."""
    path = unquote(urlsplit(url).path)
    seg = path.rsplit("/", 1)[-1]
    return re.sub(r"\.aspx$", "", seg, flags=re.IGNORECASE)


def _category_from(url: str) -> Optional[str]:
    """The subject category, e.g. 'Tien-te-Ngan-hang', sits between /van-ban/ and the slug."""
    parts = [p for p in urlsplit(url).path.split("/") if p]
    # .../van-ban/<Category>/<slug>.aspx
    if "van-ban" in parts:
        i = parts.index("van-ban")
        if i + 2 < len(parts):
            return parts[i + 1].replace("-", " ")
    return None


def _site_doc_id(slug: str) -> Optional[str]:
    m = re.search(r"-(\d{4,})$", slug)
    return m.group(1) if m else None


def _reconstruct_doc_number(slug: str) -> Optional[str]:
    """Rebuild a Vietnamese doc number (e.g. '05/2026/TT-NHNN') from a slug fragment.

    Handles the three slug layouts seen on the site:
      A. 'NN-YYYY-TYPE[-ISSUER]'  -> NN/YYYY/TYPE[-ISSUER]   (Thông tư / Nghị định …)
      B. 'NN-TYPE-ISSUER-YYYY'    -> NN/YYYY/TYPE-ISSUER      (Quyết định 1279-QD-TTg-2026)
      C. 'NN-YYYY-QHk'            -> NN/YYYY/QHk              (Luật … 32-2024-QH15)
    Returns the earliest-appearing match so the doc's OWN number wins over any target it amends.
    """
    candidates = []
    m = _DOCNUM_SLUG_RE.search(slug)
    if m:
        num, year, typ = m.group(1), m.group(2), m.group(3).upper()
        issuer = m.group(4)
        val = f"{num}/{year}/{typ}"
        if issuer and issuer.isalpha() and 2 <= len(issuer) <= 10:
            val = f"{val}-{issuer.upper()}"
        candidates.append((m.start(), val))
    m = _DOCNUM_TYPE_FIRST_RE.search(slug)
    if m:
        candidates.append((m.start(), f"{m.group(1)}/{m.group(4)}/{m.group(2).upper()}-{m.group(3).upper()}"))
    m = _DOCNUM_QH_RE.search(slug)
    if m:
        candidates.append((m.start(), f"{m.group(1)}/{m.group(2)}/{m.group(3).upper()}"))
    if not candidates:
        return None
    return min(candidates, key=lambda c: c[0])[1]


def _doc_type_from_slug(slug: str) -> Optional[DocType]:
    low = slug.lower()
    for token, _code, dt in _TYPE_TOKENS:
        if low.startswith(token) or low.startswith("circular"):
            if low.startswith("circular"):
                return DocType.THONG_TU
            return dt
    # fall back to the frozen guesser on the de-slugged text
    return guess_doc_type(slug.replace("-", " "))


def _title_from_slug(slug: str) -> str:
    """Human-ish title: drop trailing numeric doc id, turn hyphens into spaces."""
    s = re.sub(r"-\d{4,}$", "", slug)  # strip site doc id
    return s.replace("-", " ").strip()


def _relations_from_slug(slug: str) -> List[Relation]:
    """Detect amendment relations encoded in the slug and the target doc it acts on.

    e.g. 'Thong-tu-24-2026-TT-NHNN-sua-doi-Thong-tu-14-2024-TT-NHNN-...' =>
         AMENDS  target 14/2024/TT-NHNN.
    We only capture the FIRST relation cue + the first doc number appearing AFTER it, to stay
    conservative (labels only; no full parsing of the paywalled relation panel).
    """
    low = slug.lower()
    rels: List[Relation] = []
    seen_targets: set[str] = set()
    for cue, rtype in _REL_CUES:
        idx = low.find(cue)
        if idx == -1:
            continue
        after = slug[idx + len(cue):]
        m = _DOCNUM_SLUG_RE.search(after)
        target = None
        if m:
            tnum, tyear, ttyp = m.group(1), m.group(2), m.group(3).upper()
            tiss = m.group(4)
            target = f"{tnum}/{tyear}/{ttyp}" + (f"-{tiss.upper()}" if tiss and tiss.isalpha() else "")
        if target and target in seen_targets:
            continue
        if target:
            seen_targets.add(target)
        rels.append(Relation(type=rtype, target_doc_number=target))
        # one relation per cue type is plenty for the label-level signal we promise
    return rels


class ThuVienPhapLuatSource(Source):
    """Metadata-only banking-doc harvester over thuvienphapluat's PUBLIC sitemaps."""

    name = "thuvienphapluat"

    def discover(self, client: RespectfulClient, limit: int) -> Iterable[str]:
        yielded = 0
        seen: set[str] = set()
        # sitemap.xml is a sitemap INDEX -> child resitemapN.xml files. Walk children,
        # collect banking /van-ban/ doc URLs, prime cache with a slug-stub, yield URL.
        child_sitemaps = list(iter_sitemap_locs(client, SITEMAP_INDEX))
        # Keep only the resitemap children (the doc-URL sitemaps); cap for budget.
        children = [u for u in child_sitemaps if "resitemap" in u.lower()][:_MAX_CHILD_SITEMAPS]
        if not children:
            # sitemap.xml itself might already be a url-set (not an index)
            children = [SITEMAP_INDEX]

        for sm in children:
            if yielded >= limit:
                return
            for doc_url in iter_sitemap_locs(client, sm):
                if yielded >= limit:
                    return
                if "/van-ban/" not in doc_url or urlsplit(doc_url).netloc != HOST:
                    continue
                if doc_url in seen:
                    continue
                # English mirror slugs ("Circular-...") duplicate the VN doc — skip to
                # avoid double-counting; VN slug carries the canonical doc_number.
                slug = _slug_last_segment(doc_url)
                if slug.lower().startswith(("circular", "law-", "decree", "decision")):
                    continue
                # Strict banking-REGULATOR filter (NHNN / Tiền tệ-Ngân hàng / TCTD terms).
                # The broad is_banking() keyword set matches provincial budget resolutions,
                # which are noise for a bank-RAG source, so we require a strong signal.
                if not _is_bank_regulation(slug, _category_from(doc_url)):
                    continue
                seen.add(doc_url)
                self._prime_cache(doc_url, slug)
                yield doc_url
                yielded += 1

    @staticmethod
    def _prime_cache(doc_url: str, slug: str) -> None:
        """Write a tiny sitemap-derived stub to the raw cache so run_source's client.get()
        reads it (0 network, no 403) and never touches the paywalled detail page.

        This is NOT the document body — it is a marker recording that the metadata came from
        the public sitemap. parse() ignores this content and reads the URL slug.
        """
        path = storage.raw_path("thuvienphapluat", doc_url, "html")
        try:
            with open(path, "x", encoding="utf-8") as f:  # x: never clobber a real fetch
                f.write("<!-- thuvienphapluat: PUBLIC SITEMAP metadata only; "
                        "detail page is paywalled/challenged and was NOT fetched. slug="
                        + slug + " -->")
        except FileExistsError:
            pass  # already primed or a real page cached — leave it
        except OSError:
            pass

    def parse(self, url: str, raw: str) -> Optional[CrawlItem]:
        # Everything comes from the PUBLIC URL slug; `raw` is our sitemap stub (ignored).
        slug = _slug_last_segment(url)
        if not slug:
            return None
        doc_number = _reconstruct_doc_number(slug)
        title = _title_from_slug(slug)
        doc_type = _doc_type_from_slug(slug)
        category = _category_from(url)
        rels = _relations_from_slug(slug)
        # True by construction (discover applies the strict bank-regulation filter), but
        # recompute so parse() is correct even if called directly.
        banking = _is_bank_regulation(slug, category) or is_banking(slug + " " + (category or ""))

        return CrawlItem(
            source=self.name,
            url=url,
            doc_number=doc_number,
            title=title or None,
            doc_type=doc_type,
            # issued_date / effective_date / status are ONLY on the paywalled detail page,
            # which we do not fetch — left None honestly.
            relations=rels,
            is_banking=banking,
            fields={
                "captured": "public_sitemap_metadata_only",
                "category": category,
                "site_doc_id": _site_doc_id(slug),
                "note": "detail page paywalled/challenged; no full text, no dates",
            },
        )


def get_source() -> Source:
    return ThuVienPhapLuatSource()
