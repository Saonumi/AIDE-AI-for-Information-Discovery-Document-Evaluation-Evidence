"""Demo corpus, ground-truth golden questions, and deterministic seed (Track C).

This package is the *backbone* of the demo: `seed.seed_all()` populates all four
stores (Postgres/SQLite, OpenSearch, Neo4j) deterministically — no LLM — so the
query pipeline can answer every golden question reproducibly.
"""
