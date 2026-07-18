"""robots.txt compliance. We fetch and honour Allow/Disallow per host.

Content-Signal directives (ai-train=no, use=reference — a non-standard Cloudflare/Google
extension seen on shb.com.vn / thuvienphapluat.vn) are recorded for transparency. We
already respect the important one: this project does NOT train models, it does RAG
(reference use). Crawling itself is gated only by standard Allow/Disallow here.
"""
from __future__ import annotations

from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests


class RobotsCache:
    def __init__(self, user_agent: str, timeout: int = 20):
        self.ua = user_agent
        self.timeout = timeout
        self._parsers: dict[str, RobotFileParser] = {}
        self.content_signals: dict[str, str] = {}

    def _origin(self, url: str) -> str:
        p = urlsplit(url)
        return f"{p.scheme}://{p.netloc}"

    def _load(self, origin: str) -> RobotFileParser:
        rp = RobotFileParser()
        try:
            r = requests.get(origin + "/robots.txt",
                             headers={"User-Agent": self.ua}, timeout=self.timeout)
            if r.status_code == 200:
                text = r.text
                rp.parse(text.splitlines())
                for line in text.splitlines():
                    if line.strip().lower().startswith("content-signal:"):
                        self.content_signals[origin] = line.split(":", 1)[1].strip()
                        break
            else:
                rp.parse([])  # no robots -> allow all
        except requests.RequestException:
            rp.parse([])       # unreachable robots -> be permissive but caller rate-limits
        return rp

    def allowed(self, url: str) -> bool:
        origin = self._origin(url)
        if origin not in self._parsers:
            self._parsers[origin] = self._load(origin)
        return self._parsers[origin].can_fetch(self.ua, url)
