"""VBPL crawler (vbpl.vn — Cơ sở dữ liệu quốc gia về pháp luật).

This is the PRIMARY source for the banking-RAG versioning feature: it must surface
document RELATIONSHIPS (sửa đổi / thay thế / hết hiệu lực) so the ingestion layer can
build version chains.

--- WHAT LIVES WHERE (from live recon; see tmp/vbpl_probe.py, tmp/vbpl_flight.py) ---
vbpl.vn is a Next.js app. A fetched /van-ban/chi-tiet/<slug>--<ItemID> page renders only
~300-450 chars of visible HTML; everything else is React "flight" data streamed inside
`self.__next_f.push(...)` <script> chunks, plus the interactive tabs (properties / full
text / "Văn bản liên quan") which are loaded CLIENT-SIDE from the site's JSON API.

robots.txt: Allow: /  ; Disallow: /api/ ; Disallow: /Pages/
  -> The full-text tab and the structured relationship tab are served from /api/ (an XHR),
     which is robots-DISALLOWED. We do NOT fetch them (RespectfulClient would refuse anyway).

What we CAN extract from the robots-allowed detail page (server-rendered flight data):
  1. A schema.org/Legislation JSON-LD object embedded in the flight stream, giving
     doc_number (legislationIdentifier), title (name), doc_type (legislationType),
     issued_date (legislationDate), issuer (legislationPassedBy.name), and legal force
     (legislationLegalForce: InForce/PartialInForce/Expired -> status).
  2. The URL SLUG, which reliably names the related documents and the relationship verb
     ("sua-doi-bo-sung ... cua <DOC>" = this AMENDS <DOC>; "...-boi-<DOC>" = AMENDED_BY, etc).

LIMITATIONS (honest):
  - full_text is NOT available under robots (it is an /api/ XHR). We fall back to the
    JSON-LD title as `full_text` and record the limitation in `fields`.
  - effective_date / expiry_date are NOT in the server HTML (also /api/-only), so they
    are left None unless the JSON-LD ever carries them.
  - Relations come from the SLUG, not the authoritative relationship API. They are a
    high-precision signal (the slug is generated from the real relationships) but may be
    truncated for documents with very long relationship lists.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Iterable, List, Optional

from bs4 import BeautifulSoup

from crawl.base import Source
from crawl.http_client import RespectfulClient
from crawl.models import CrawlItem, DocType, Relation, RelationType
from crawl.util import (
    guess_doc_type,
    is_amendment,
    is_banking,
    iter_sitemap_locs,
)
from packages.common.vn_normalize import normalize_date, strip_accents

log = logging.getLogger("crawl")

SITEMAPS = [f"https://vbpl.vn/sitemap-trung-uong-{i}.xml" for i in range(1, 8)]
DETAIL_MARKER = "/van-ban/chi-tiet/"

# Vietnamese legal document-type prefixes that begin a valid doc-number's agency code.
# The FIRST suffix segment must be one of these — this rejects slug noise where the
# regex would otherwise latch onto Vietnamese connective words (cua/va/ngay/theo/...)
# that happen to follow a "NN-YYYY-" fragment. Longest-first so "ttlt"/"nqlt" win.
_DOCTYPE_CODES = [
    "ttlt", "nqlt", "qdlt", "vbhn", "ubtvqh", "lct", "pltn",
    "tt", "nd", "qd", "nq", "pl", "ct", "vb", "qh", "sl", "hd", "cv", "tb", "l",
]
_DOCTYPE_ALT = "|".join(sorted(_DOCTYPE_CODES, key=len, reverse=True))

# Doc-number token as it appears in a slug: "39-2016-tt-nhnn" -> "39/2016/TT-NHNN".
# Shape: <number>-<year>-<doctype>[-<agency>], e.g. tt-nhnn, nd-cp, qd-ttg, ttlt-btc.
_SLUG_DOCNUM_RE = re.compile(
    r"(?<![0-9a-z])(\d{1,4})-(\d{4})-(" + _DOCTYPE_ALT + r")(?:-([a-z]{2,10}))?(?![0-9a-z])"
)

# ---------------------------------------------------------------------------
# Next.js flight-data parsing
# ---------------------------------------------------------------------------
_PUSH_RE = re.compile(r'self\.__next_f\.push\(\[\d+,\s*("(?:\\.|[^"\\])*")\s*\]\)', re.S)


def _flight_blob(html: str) -> str:
    """Concatenate all `self.__next_f.push([n, "<chunk>"])` string chunks into one blob."""
    soup = BeautifulSoup(html, "lxml")
    parts: List[str] = []
    for s in soup.find_all("script"):
        txt = s.string or s.get_text() or ""
        if "self.__next_f" not in txt:
            continue
        for chunk in _PUSH_RE.findall(txt):
            try:
                parts.append(json.loads(chunk))  # decode the JS string literal
            except Exception:  # noqa: BLE001
                continue
    return "".join(parts)


def _match_brace_forward(blob: str, start: int) -> int:
    """Return index just past the '}' that matches the '{' at `start`, honouring \\ escapes."""
    depth = 0
    k = start
    n = len(blob)
    while k < n:
        c = blob[k]
        if c == "\\":
            k += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return k + 1
        k += 1
    return -1


def _extract_legislation_ld(blob: str) -> Optional[dict]:
    """Find the schema.org/Legislation JSON-LD object in the flight blob.

    The blob contains the object in one of two serialisations:
      - PLAIN:   "legislationIdentifier":"06/2026/TT-BTC"
      - ESCAPED: \\"legislationIdentifier\\":\\"85/2025/TT-NHNN\\"
    We locate the key, then walk backward over candidate '{' positions until the
    brace-matched object both encloses the key and parses as JSON.
    """
    i = blob.find("legislationIdentifier")
    if i < 0:
        return None
    escaped = i >= 2 and blob[i - 2] == "\\"
    b = i
    while True:
        start = blob.rfind("{", 0, b)
        if start < 0:
            return None
        end = _match_brace_forward(blob, start)
        if end > i:
            frag = blob[start:end]
            try:
                obj = json.loads(json.loads('"' + frag + '"')) if escaped else json.loads(frag)
                if isinstance(obj, dict) and obj.get("legislationIdentifier"):
                    return obj
            except Exception:  # noqa: BLE001
                pass
        b = start


# The site occasionally emits doc numbers with a Cyrillic "С" (U+0421) instead of Latin "C"
# (e.g. "TT-BTС"). Fold confusable Cyrillic look-alikes back to Latin for clean matching.
_CYRILLIC_FIX = {
    "С": "C", "А": "A", "В": "B", "Е": "E", "К": "K",
    "М": "M", "Н": "H", "О": "O", "Р": "P", "Т": "T",
    "Х": "X", "І": "I",
}


def _fix_confusables(s: Optional[str]) -> Optional[str]:
    if not s:
        return s
    return "".join(_CYRILLIC_FIX.get(ch, ch) for ch in s)


_LEGAL_FORCE_STATUS = {
    "inforce": "Còn hiệu lực",
    "partialinforce": "Còn hiệu lực một phần",
    "expired": "Hết hiệu lực",
    "notinforce": "Chưa có hiệu lực",
    "repealed": "Hết hiệu lực",
}


def _status_from_force(force: Optional[str]) -> Optional[str]:
    if not force:
        return None
    return _LEGAL_FORCE_STATUS.get(force.replace(" ", "").lower(), None)


# ---------------------------------------------------------------------------
# Relationship mining from the slug
# ---------------------------------------------------------------------------
def _slug_and_itemid(url: str) -> tuple[str, Optional[str]]:
    """Return (slug, ItemID) from a /van-ban/chi-tiet/<slug>--<ItemID> URL."""
    tail = url.rsplit(DETAIL_MARKER, 1)[-1]
    m = re.search(r"--(\d+)/?$", tail)
    item_id = m.group(1) if m else None
    slug = tail[: m.start()] if m else tail
    return slug, item_id


def _token_to_docnum(m: re.Match) -> str:
    num, year, a, b = m.group(1), m.group(2), m.group(3), m.group(4)
    suffix = a.upper() + ("-" + b.upper() if b else "")
    return f"{num}/{year}/{suffix}"


def _classify_relation(preceding: str) -> Optional[RelationType]:
    """Map the slug phrase immediately before a target doc-number to a RelationType.

    `preceding` is accent-folded lowercase slug text (hyphens kept). The Vietnamese "bởi"
    (folded "boi") marks the PASSIVE direction (this doc is the object, target is the actor).
    """
    p = preceding
    passive = "-boi-" in p or p.endswith("-boi") or "duoc-" in p or "bi-" in p

    if "thay-the" in p or "bai-bo" in p:
        return RelationType.SUPERSEDED_BY if passive else RelationType.SUPERSEDES
    if "sua-doi" in p or "bo-sung" in p or "dinh-chinh" in p:
        return RelationType.AMENDED_BY if passive else RelationType.AMENDS
    if "huong-dan" in p or "quy-dinh-chi-tiet" in p:
        return RelationType.GUIDED_BY if passive else RelationType.GUIDES
    if "het-hieu-luc" in p:
        return RelationType.EXPIRES
    return None


def _relations_from_slug(slug: str) -> List[Relation]:
    """Extract relationships from the slug. The FIRST doc-number token is this document
    itself; every later token is a related document, classified by the phrase before it."""
    folded = strip_accents(slug.lower())
    matches = list(_SLUG_DOCNUM_RE.finditer(folded))
    if len(matches) <= 1:
        return []

    relations: List[Relation] = []
    seen: set[tuple[str, str]] = set()
    for m in matches[1:]:  # skip [0] = this document
        target = _token_to_docnum(m)
        window = folded[max(0, m.start() - 60):m.start()]
        rel_type = _classify_relation(window)
        if rel_type is None:
            rel_type = RelationType.RELATED
        key = (rel_type.value, target)
        if key in seen:
            continue
        seen.add(key)
        relations.append(Relation(type=rel_type, target_doc_number=target))
    return relations


# ---------------------------------------------------------------------------
# Source implementation
# ---------------------------------------------------------------------------
class VbplSource(Source):
    name = "vbpl"

    # Cap how many sitemap URLs we scan while hunting for `limit` banking candidates,
    # so discovery on a tiny pilot limit never walks all 35k central URLs.
    MAX_SCAN_PER_LIMIT = 400

    def discover(self, client: RespectfulClient, limit: int) -> Iterable[str]:
        """Yield banking-related detail URLs, amendments FIRST (they carry the version
        relationships). Two passes over the sitemaps: pass 1 amendments, pass 2 the rest.
        We cap the candidate scan relative to `limit` to stay a polite pilot."""
        scan_cap = max(200, limit * self.MAX_SCAN_PER_LIMIT)
        yielded: set[str] = set()

        def _iter_all_detail_urls():
            for sm in SITEMAPS:
                for loc in iter_sitemap_locs(client, sm):
                    if DETAIL_MARKER in loc and is_banking(loc):
                        yield loc

        # Pass 1: amendments (version relationships) — highest value first.
        scanned = 0
        for url in _iter_all_detail_urls():
            scanned += 1
            if scanned > scan_cap:
                break
            if is_amendment(url) and url not in yielded:
                yielded.add(url)
                yield url

        # Pass 2: remaining banking docs, to top up toward `limit`.
        if len(yielded) < limit:
            scanned = 0
            for url in _iter_all_detail_urls():
                scanned += 1
                if scanned > scan_cap:
                    break
                if url not in yielded:
                    yielded.add(url)
                    yield url

    def parse(self, url: str, raw: str) -> Optional[CrawlItem]:
        slug, item_id = _slug_and_itemid(url)
        blob = _flight_blob(raw)
        ld = _extract_legislation_ld(blob) or {}

        doc_number = _fix_confusables(ld.get("legislationIdentifier"))
        title = None
        if ld.get("name"):
            title = re.sub(r"\s+", " ", _fix_confusables(ld["name"])).strip()

        # doc_type: prefer the JSON-LD legislationType, else guess from title/slug.
        doc_type: Optional[DocType] = guess_doc_type(ld.get("legislationType") or "")
        if doc_type is None:
            doc_type = guess_doc_type(title or slug)

        issuer = None
        passed_by = ld.get("legislationPassedBy")
        if isinstance(passed_by, dict):
            issuer = passed_by.get("name")

        # legislationDate is ISO "2025-12-31T00:00:00"; normalize_date's yyyy-mm-dd
        # matcher needs a word boundary, so drop the time part first.
        issued_date = normalize_date((ld.get("legislationDate") or "").split("T", 1)[0])
        status = _status_from_force(ld.get("legislationLegalForce"))

        relations = _relations_from_slug(slug)

        # full_text is /api/-only (robots-disallowed). Use the title as the best available
        # textual content and record the limitation transparently.
        full_text = title
        full_text_available = False

        item = CrawlItem(
            source=self.name,
            url=url,
            doc_number=doc_number,
            title=title,
            doc_type=doc_type,
            issuer=issuer,
            issued_date=issued_date,
            effective_date=None,   # /api/-only, not in server HTML
            expiry_date=None,      # /api/-only
            status=status,
            full_text=full_text,
            relations=relations,
            is_banking=True,
            fields={
                "item_id": item_id,
                "slug": slug,
                "legislation_type": ld.get("legislationType"),
                "legislation_legal_force": ld.get("legislationLegalForce"),
                "full_text_available": full_text_available,
                "full_text_note": (
                    "Full document text is served from vbpl.vn/api/ (robots-Disallowed) "
                    "via a client-side XHR; not fetchable. Title used as content proxy."
                ),
                "relations_source": "slug",
                "json_ld_found": bool(ld),
            },
        )
        return item


def get_source() -> Source:
    return VbplSource()
