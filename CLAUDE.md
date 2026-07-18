# VAIC2026 — Advanced Banking RAG (SHB1)

## Project
48-hour hackathon: Temporal Regulatory RAG for SHB bank.
Stack: FastAPI · Streamlit · PyMuPDF · OpenSearch (BM25 + vector) · Neo4j · PostgreSQL · Docker Compose.
Language: Python 3.11+, Vietnamese regulatory documents.

3 parallel tracks:
- **Track A** — Ingestion pipeline (upload → parse → extract → version graph → review inbox)
- **Track B** — Query pipeline (retrieval → graph expansion → validity → conflict → LLM generation)
- **Track C** — UI + eval harness + demo corpus

Contracts frozen in `packages/contracts/` (Pydantic models, OpenAPI spec, Neo4j schema).

## ECC workflow (always active)

ECC plugin is enabled. Use these skills during coding:

- **Before implementing a new module:** `/ecc:plan`
- **Python code review:** `/ecc:python-review`
- **FastAPI patterns:** `/ecc:backend-patterns`
- **TDD (retrieval logic, validators, patch engine):** `/ecc:tdd-workflow`
- **Before merging a track:** `/ecc:verification-loop`
- **Security (prompt injection, auth):** `/ecc:security-review`

## Key invariants (never break)
- Temporal pre-filter runs BEFORE top-k retrieval
- LLM never decides validity or applies amendments — only Python deterministic rules
- Every answer must carry citation IDs traceable to valid_evidence
- Employee review required before any document activates in retrieval
- Prompt: evidence wrapped in `<EVIDENCE>...</EVIDENCE>` delimiters, not treated as instructions

## Git rules
See docs/AGENTS.md — no self-commit, no push without explicit user confirmation.
