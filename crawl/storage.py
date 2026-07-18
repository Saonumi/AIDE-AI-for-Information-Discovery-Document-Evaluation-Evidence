"""Where crawl artifacts live. One folder per source, gitignored (data/crawl/)."""
from __future__ import annotations

import hashlib
import os

from packages.common.config import get_settings

CRAWL_ROOT = os.path.join(os.path.dirname(get_settings().file_storage_dir), "crawl")


def source_dir(source: str) -> str:
    d = os.path.join(CRAWL_ROOT, source)
    os.makedirs(os.path.join(d, "raw"), exist_ok=True)
    os.makedirs(os.path.join(d, "items"), exist_ok=True)
    return d


def url_key(url: str) -> str:
    """Stable filename-safe key for a URL."""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def raw_path(source: str, url: str, ext: str = "html") -> str:
    return os.path.join(source_dir(source), "raw", f"{url_key(url)}.{ext}")


def item_path(source: str, url: str) -> str:
    return os.path.join(source_dir(source), "items", f"{url_key(url)}.json")


def checkpoint_path(source: str) -> str:
    return os.path.join(source_dir(source), "checkpoint.json")
