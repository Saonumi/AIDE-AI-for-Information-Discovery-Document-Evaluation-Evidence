"""Service facade — the single entry point the API calls (steps 13-25 wired together).

Exposes exactly the four functions the API routes import via api._facade.call:
    answer_query, compare, graph_subgraph, list_audit

answer_query runs the full pipeline: security -> understanding -> evidence package ->
generation -> output checks, writes an AuditRow, and returns a QueryResponse.
compare runs standard_rag vs our_system head-to-head. Everything is offline-safe.
"""
from __future__ import annotations

import time
from datetime import date
from typing import List, Optional

from infra.db_models import AuditRow
from infra.postgres import init_db, session_scope
from llm.client import get_client
from packages.common.config import get_settings
from packages.common.ids import new_id
from packages.contracts.api_schemas import (
    CompareResponse,
    GraphResponse,
    GraphNode,
    GraphEdge,
    QueryResponse,
)
from packages.contracts.enums import AnswerStatus
from packages.contracts.models import Answer, EvidencePackage

from query import (
    evidence_package,
    generation,
    output_checks,
    security,
    standard_rag,
    understanding,
)


def _empty_package(query: str, query_date: date, intent) -> EvidencePackage:
    return EvidencePackage(query=query, query_date=query_date, intent=intent)


def _blocked_answer(query_date: Optional[date], reason: str) -> Answer:
    return Answer(
        text="INSUFFICIENT_EVIDENCE",
        citations=[],
        status=AnswerStatus.INSUFFICIENT_EVIDENCE,
        query_date=query_date,
        check_failures=[reason],
    )


def answer_query(
    text: str,
    query_date: Optional[date],
    username: str,
    role: str,
) -> QueryResponse:
    """Full query pipeline -> QueryResponse(answer, evidence). Writes an AuditRow."""
    t0 = time.time()

    # step 13 — security & role filter
    decision = security.check_query(text, role)
    if not decision.allowed:
        u = understanding.understand(decision.query or text, query_date)
        pkg = _empty_package(decision.query or text, u.query_date, u.intent)
        ans = _blocked_answer(u.query_date, decision.block_reason or "BLOCKED")
        _audit(username, role, decision.query or text, u.query_date, pkg, ans, t0)
        return QueryResponse(answer=ans, evidence=pkg)

    # step 14 — understanding + query date
    u = understanding.understand(decision.query, query_date)

    # steps 15-21 — deterministic evidence package
    pkg = evidence_package.build(
        query=decision.query,
        query_date=u.query_date,
        intent=u.intent,
        base_filters=decision.base_filters,
    )

    # step 22 — constrained generation
    ans = generation.generate(pkg)

    # step 23 — deterministic output checks (sets final status)
    ans = output_checks.run(ans, pkg)

    # step 25 — audit
    _audit(username, role, decision.query, u.query_date, pkg, ans, t0)

    return QueryResponse(answer=ans, evidence=pkg)


def compare(
    text: str,
    query_date: Optional[date],
    username: str,
    role: str,
) -> CompareResponse:
    """Head-to-head: naive standard RAG (version conflation) vs our temporal system."""
    decision = security.check_query(text, role)
    query = decision.query or text
    u = understanding.understand(query, query_date)

    base = standard_rag.answer(query, u.query_date)

    ours = answer_query(text, query_date, username, role).answer

    return CompareResponse(
        query=query,
        query_date=u.query_date,
        standard_rag=base,
        our_system=ours,
    )


def graph_subgraph(provision_id: str) -> GraphResponse:
    """KG visualisation around a provision (from the graph store's subgraph template)."""
    from infra.neo4j_client import get_graph

    data = get_graph().subgraph(provision_id)
    nodes = [
        GraphNode(
            id=n["id"],
            label=n.get("label", "Node"),
            title=n.get("title", n["id"]),
            props=_json_safe(n.get("props", {})),
        )
        for n in data.get("nodes", [])
    ]
    edges = [
        GraphEdge(source=e["source"], target=e["target"], label=e["label"])
        for e in data.get("edges", [])
    ]
    return GraphResponse(nodes=nodes, edges=edges)


def list_audit(limit: int = 50) -> List[dict]:
    """Recent audit rows as plain dicts (most recent first)."""
    _ensure_db()
    out: List[dict] = []
    try:
        with session_scope() as ses:
            rows = (
                ses.query(AuditRow)
                .order_by(AuditRow.created_at.desc())
                .limit(limit)
                .all()
            )
            for r in rows:
                out.append(
                    {
                        "audit_id": r.audit_id,
                        "user_id": r.user_id,
                        "role": r.role,
                        "query": r.query,
                        "query_date": r.query_date.isoformat() if r.query_date else None,
                        "status": r.status,
                        "latency_ms": r.latency_ms,
                        "prompt_version": r.prompt_version,
                        "model_version": r.model_version,
                        "payload": r.payload,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                    }
                )
    except Exception:
        pass
    return out


# --------------------------------------------------------------------------- #
# internals
# --------------------------------------------------------------------------- #
_db_ready = False


def _ensure_db() -> None:
    global _db_ready
    if _db_ready:
        return
    try:
        init_db()
        _db_ready = True
    except Exception:
        pass


def _json_safe(props: dict) -> dict:
    safe = {}
    for k, v in (props or {}).items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            safe[k] = v
        else:
            safe[k] = str(v)
    return safe


def _audit(
    username: str,
    role: str,
    query: str,
    query_date: date,
    pkg: EvidencePackage,
    ans: Answer,
    t0: float,
) -> None:
    _ensure_db()
    latency_ms = int((time.time() - t0) * 1000)
    client = get_client()
    payload = {
        "retrieved_chunks": [e.version_id for e in pkg.valid_evidence],
        "used_versions": [e.version_id for e in pkg.valid_evidence],
        "excluded_versions": [e.version_id for e in pkg.excluded_evidence],
        "graph_paths": [f"{r.from_provision}->{r.to_provision}" for r in pkg.reference_paths],
        "conflict_candidates": [
            f"{c.provision_a}|{c.provision_b}|{c.reason.value}" for c in pkg.conflict_candidates
        ],
        "impact_candidates": [
            f"{i.artifact_id}|{i.reason.value}" for i in pkg.impact_candidates
        ],
        "check_failures": ans.check_failures,
        "answer": ans.text,
    }
    try:
        with session_scope() as ses:
            ses.add(
                AuditRow(
                    audit_id=new_id("aud"),
                    user_id=username,
                    role=role,
                    query=query,
                    query_date=query_date,
                    payload=payload,
                    status=ans.status.value if ans.status else None,
                    latency_ms=latency_ms,
                    prompt_version=get_settings().prompt_version,
                    model_version=getattr(client, "model", "mock"),
                )
            )
    except Exception:
        # Audit must never break the answer path.
        pass
