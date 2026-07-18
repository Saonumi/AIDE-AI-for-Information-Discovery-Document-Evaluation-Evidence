"""Source interface + the run loop (checkpointed, resumable, run-boundary logging).

A source implements discover() (yield detail URLs) and parse() (raw -> CrawlItem).
run_source() handles rate-limited fetching, atomic per-item persistence, checkpoint
skip/resume, and honest logging of skipped(resumed) vs newly-processed.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable, List, Optional

from crawl import storage
from crawl.checkpoint import CheckpointStore
from crawl.http_client import RequestBudgetExceeded, RespectfulClient
from crawl.models import CrawlItem

log = logging.getLogger("crawl")


class Source(ABC):
    name: str = "source"

    @abstractmethod
    def discover(self, client: RespectfulClient, limit: int) -> Iterable[str]:
        """Yield candidate document detail URLs (may fetch sitemaps via client)."""

    @abstractmethod
    def parse(self, url: str, raw: str) -> Optional[CrawlItem]:
        """Parse a fetched page into a CrawlItem (or None to skip)."""


def _atomic_write_json(path: str, obj: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def run_source(source: Source, *, limit: int = 50, min_delay: float = 1.5,
               max_requests: int = 400) -> dict:
    client = RespectfulClient(source.name, min_delay=min_delay, max_requests=max_requests)
    cp = CheckpointStore(source.name)
    resumed_before = cp.stats()["done"]
    log.info("[%s] start — %d already done (will be skipped/resumed)", source.name, resumed_before)

    new = skipped = failed = 0
    try:
        for url in source.discover(client, limit):
            if new >= limit:
                break
            if cp.is_done(url):
                skipped += 1
                continue
            raw = client.get(url)
            if raw is None:
                cp.mark_failed(url, "fetch_failed_or_disallowed")
                failed += 1
                continue
            try:
                item = source.parse(url, raw)
            except Exception as e:  # noqa: BLE001
                cp.mark_failed(url, f"parse_error:{type(e).__name__}:{e}")
                failed += 1
                continue
            if item is None:
                cp.mark_failed(url, "parse_returned_none")
                failed += 1
                continue
            item.fetched_at = datetime.utcnow().isoformat()
            item.raw_sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            ip = storage.item_path(source.name, url)
            _atomic_write_json(ip, item.model_dump(mode="json"))
            cp.mark_done(url, ip)
            new += 1
            log.info("[%s] %d new — %s", source.name, new, (item.doc_number or item.title or url)[:70])
    except RequestBudgetExceeded as e:
        log.warning("[%s] stopped: %s", source.name, e)

    result = {"source": source.name, "new": new, "skipped_resumed": skipped,
              "failed": failed, "requests_made": client.requests_made,
              "total_done": cp.stats()["done"]}
    log.info("[%s] done — new=%d skipped=%d failed=%d requests=%d",
             source.name, new, skipped, failed, client.requests_made)
    return result


def load_items(source_name: str) -> List[CrawlItem]:
    """Load all persisted CrawlItems for a source (for the ingestion step)."""
    d = os.path.join(storage.source_dir(source_name), "items")
    out: List[CrawlItem] = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, fn), "r", encoding="utf-8") as f:
                out.append(CrawlItem(**json.load(f)))
        except Exception:  # noqa: BLE001
            continue
    return out
