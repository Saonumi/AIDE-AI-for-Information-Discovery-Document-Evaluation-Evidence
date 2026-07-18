"""Evaluation harness (Track C): metrics + head-to-head runner.

`metrics.py` holds pure, independently-unit-testable scoring functions.
`run_eval.py` seeds the demo corpus, runs every golden question through BOTH our
system and a standard-RAG baseline (in-process), and prints a comparison table.
"""
