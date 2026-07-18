"""RespectfulClient — the ONLY way crawlers hit the network.

Guarantees:
  - robots.txt honoured (skips disallowed URLs, returns None).
  - polite per-host rate limiting (min delay between requests).
  - bounded retries with backoff on 5xx / timeout.
  - raw responses cached to disk (re-parsing never re-hits the site).
  - a hard request budget per run (pilot safety — never hammer a site).
Crawlers must not create their own requests.Session.
"""
from __future__ import annotations

import time
from typing import Optional
from urllib.parse import urlsplit

import requests

from crawl import storage
from crawl.robots import RobotsCache

DEFAULT_UA = "VAIC2026-research-crawler/0.1 (academic RAG; respects robots.txt; contact: team)"


class RequestBudgetExceeded(RuntimeError):
    pass


class RespectfulClient:
    def __init__(
        self,
        source: str,
        user_agent: str = DEFAULT_UA,
        min_delay: float = 1.5,
        timeout: int = 30,
        max_requests: int = 400,
        max_retries: int = 3,
    ):
        self.source = source
        self.ua = user_agent
        self.min_delay = min_delay
        self.timeout = timeout
        self.max_requests = max_requests
        self.max_retries = max_retries
        self._robots = RobotsCache(user_agent, timeout)
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": user_agent, "Accept-Language": "vi,en"})
        self._last_hit: dict[str, float] = {}
        self._count = 0

    def _throttle(self, url: str) -> None:
        host = urlsplit(url).netloc
        last = self._last_hit.get(host, 0.0)
        wait = self.min_delay - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        self._last_hit[host] = time.time()

    def get(self, url: str, ext: str = "html", use_cache: bool = True) -> Optional[str]:
        """Fetch text with robots+rate-limit+cache. Returns None if disallowed/failed."""
        raw = storage.raw_path(self.source, url, ext)
        if use_cache:
            try:
                with open(raw, "r", encoding="utf-8") as f:
                    return f.read()
            except OSError:
                pass
        if not self._robots.allowed(url):
            return None
        if self._count >= self.max_requests:
            raise RequestBudgetExceeded(f"{self.source}: hit max_requests={self.max_requests}")
        backoff = 1.0
        for attempt in range(self.max_retries):
            self._throttle(url)
            self._count += 1
            try:
                r = self._session.get(url, timeout=self.timeout)
                if r.status_code == 200:
                    r.encoding = r.apparent_encoding or r.encoding
                    text = r.text
                    try:
                        with open(raw, "w", encoding="utf-8") as f:
                            f.write(text)
                    except OSError:
                        pass
                    return text
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                return None  # 4xx (except 429) -> give up on this url
            except requests.RequestException:
                time.sleep(backoff)
                backoff *= 2
        return None

    def get_bytes(self, url: str, ext: str = "pdf", use_cache: bool = True) -> Optional[bytes]:
        """Fetch raw bytes (PDF/DOC) with robots+rate-limit+cache. None if disallowed/failed."""
        raw = storage.raw_path(self.source, url, ext)
        if use_cache:
            try:
                with open(raw, "rb") as f:
                    return f.read()
            except OSError:
                pass
        if not self._robots.allowed(url):
            return None
        if self._count >= self.max_requests:
            raise RequestBudgetExceeded(f"{self.source}: hit max_requests={self.max_requests}")
        backoff = 1.0
        for _ in range(self.max_retries):
            self._throttle(url)
            self._count += 1
            try:
                r = self._session.get(url, timeout=self.timeout)
                if r.status_code == 200 and r.content:
                    try:
                        with open(raw, "wb") as f:
                            f.write(r.content)
                    except OSError:
                        pass
                    return r.content
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                return None
            except requests.RequestException:
                time.sleep(backoff)
                backoff *= 2
        return None

    @property
    def requests_made(self) -> int:
        return self._count

    def content_signal(self, url: str) -> Optional[str]:
        self._robots.allowed(url)  # ensures robots loaded
        from urllib.parse import urlsplit as _s
        p = _s(url)
        return self._robots.content_signals.get(f"{p.scheme}://{p.netloc}")
