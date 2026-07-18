"""Respectful, checkpointed crawlers for PUBLIC legal/bank documents.

Feeds real Vietnamese banking regulations into the ingestion pipeline so the system
runs on real data instead of the synthetic demo corpus. SHB *internal* documents are
confidential and NOT crawlable — only public regulations (SBV, national legal DB) and
SHB *public* disclosures are collected; internal policies stay synthetic by design.

Every crawler MUST go through crawl.http_client.RespectfulClient (robots.txt aware,
rate-limited) and crawl.checkpoint.CheckpointStore (atomic, resumable).
"""
