"""Atomic, resumable checkpoint (per the global long-running-script rule).

Records which URLs were completed so a re-run skips them and continues. Writes are
atomic (temp file + os.replace) so a kill mid-write never corrupts the checkpoint.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional

from crawl import storage


class CheckpointStore:
    def __init__(self, source: str):
        self.source = source
        self.path = storage.checkpoint_path(source)
        self.done: Dict[str, str] = {}     # url -> item_path
        self.failed: Dict[str, str] = {}   # url -> reason
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.done = data.get("done", {})
            self.failed = data.get("failed", {})
        except (OSError, json.JSONDecodeError):
            self.done, self.failed = {}, {}

    def _save(self) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"done": self.done, "failed": self.failed}, f, ensure_ascii=False, indent=0)
        os.replace(tmp, self.path)  # atomic

    def is_done(self, url: str) -> bool:
        return url in self.done

    def mark_done(self, url: str, item_path: str) -> None:
        self.done[url] = item_path
        self.failed.pop(url, None)
        self._save()

    def mark_failed(self, url: str, reason: str) -> None:
        self.failed[url] = reason
        self._save()

    def stats(self) -> Dict[str, int]:
        return {"done": len(self.done), "failed": len(self.failed)}
