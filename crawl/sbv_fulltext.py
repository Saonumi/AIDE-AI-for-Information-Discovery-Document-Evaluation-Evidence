"""Harvest real clause-level text from SBV circular PDFs (the free win, no new deps).

Each crawled SBV item carries fields['pdf_url'] -> the real circular PDF. Direction-1
showed ~1/3 of those PDFs embed a clean Unicode text layer (e.g. 35/2026/TT-NHNN
extracts "... Điều 1 ..."), while the rest use legacy TCVN3/VNI fonts that extract as
garbled ASCII ("NGAN HANG NHA NIXOC"). We download each PDF (respectfully), extract
with the project's own ingestion.pdf_extract, keep the CLEAN ones as full_text, and
flag the garbled ones for a later OCR/Playwright pass. This upgrades sbv from
'relations_only' toward 'text_partial' in the source registry — on real documents.

Checkpointed + resumable + atomic (global rule): per-item checkpoint, re-run skips
already-harvested PDFs; PDF bytes are disk-cached by RespectfulClient.get_bytes.

    python -m crawl.sbv_fulltext
"""
from __future__ import annotations

import logging
import os
import tempfile

from crawl import storage
from crawl.audit import clause_text_signal
from crawl.base import _atomic_write_json, load_items
from crawl.checkpoint import CheckpointStore
from crawl.http_client import RequestBudgetExceeded, RespectfulClient
from ingestion.pdf_extract import blocks_to_text, extract_text_blocks

log = logging.getLogger("crawl")


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    tmp = os.path.join(tempfile.gettempdir(), "sbv_fulltext_probe.pdf")
    with open(tmp, "wb") as f:
        f.write(pdf_bytes)
    try:
        return blocks_to_text(extract_text_blocks(tmp))
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def harvest(*, max_requests: int = 60, min_delay: float = 1.5) -> dict:
    client = RespectfulClient("sbv", min_delay=min_delay, max_requests=max_requests)
    cp = CheckpointStore("sbv_fulltext")
    resumed = cp.stats()["done"]
    log.info("[sbv_fulltext] start — %d already harvested (skipped/resumed)", resumed)

    clean = garbled = failed = skipped = 0
    try:
        for item in load_items("sbv"):
            pdf_url = (item.fields or {}).get("pdf_url")
            if not pdf_url:
                continue
            if cp.is_done(pdf_url):
                skipped += 1
                continue
            data = client.get_bytes(pdf_url)
            if not data:
                cp.mark_failed(pdf_url, "download_failed_or_disallowed")
                failed += 1
                continue
            try:
                text = _extract_pdf_text(data)
            except Exception as e:  # noqa: BLE001
                cp.mark_failed(pdf_url, f"extract_error:{type(e).__name__}")
                failed += 1
                continue

            ip = storage.item_path("sbv", item.url)
            if clause_text_signal(text):
                item.full_text = text.strip()
                item.fields = {**(item.fields or {}), "fulltext_source": "pdf",
                               "pdf_encoding": "clean_unicode"}
                _atomic_write_json(ip, item.model_dump(mode="json"))
                cp.mark_done(pdf_url, ip)
                clean += 1
                log.info("[sbv_fulltext] CLEAN %s (%d chars)", item.doc_number, len(text))
            else:
                # Text layer exists but legacy-font garbled -> leave summary, flag for OCR/Playwright.
                item.fields = {**(item.fields or {}), "pdf_encoding": "garbled_legacy_font",
                               "needs_ocr_or_render": True}
                _atomic_write_json(ip, item.model_dump(mode="json"))
                cp.mark_done(pdf_url, ip)   # done = classified; won't re-download
                garbled += 1
                log.info("[sbv_fulltext] GARBLED %s (legacy font)", item.doc_number)
    except RequestBudgetExceeded as e:
        log.warning("[sbv_fulltext] stopped: %s", e)

    result = {"clean": clean, "garbled": garbled, "failed": failed,
              "skipped_resumed": skipped, "requests_made": client.requests_made}
    log.info("[sbv_fulltext] done — clean=%d garbled=%d failed=%d skipped=%d requests=%d",
             clean, garbled, failed, skipped, client.requests_made)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(harvest())
