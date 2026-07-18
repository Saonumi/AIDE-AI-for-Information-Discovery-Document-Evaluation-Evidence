"""Ingestion pipeline (Track A).

Employee-facing pipeline that turns an untrusted uploaded document into APPROVED,
temporally-versioned, indexed knowledge. Every step is deterministic Python; the LLM
is only an *enhancement* over regex extraction and never decides validity or rewrites
a clause. See docs/final_pipeline.md section B (steps 1-12).

Public facade lives in `ingestion.service`; the API calls only that module.
"""
from __future__ import annotations
