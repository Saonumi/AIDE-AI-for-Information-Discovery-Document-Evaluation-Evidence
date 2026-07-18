"""Track B — Query pipeline + Standard RAG baseline.

Implements steps 13-25 of docs/final_pipeline.md as one function per module:

    security -> understanding -> temporal_filter -> hybrid_retrieval ->
    graph_expansion -> validity -> conflict -> impact -> evidence_package ->
    generation -> output_checks

`service` is the facade the API calls. `standard_rag` is the head-to-head baseline
that deliberately omits the temporal pre-filter (so it conflates versions).

INVARIANTS (the differentiators — never broken here):
  - The temporal/approval filter is passed INTO retrieval, so top-k is drawn only
    from versions valid at query_date. Never filter after top-k.
  - The LLM never decides validity/version, never applies amendments, never
    finalises a conflict. Those are Python + graph only.
  - Every answer carries citation ids traceable to valid_evidence; abstain when
    there is no valid evidence.
  - Excluded evidence always keeps an ExclusionReason (for the "why excluded" panel).
"""
from __future__ import annotations
