"""Step 22 — Constrained LLM generation.

The LLM writes PROSE ONLY. It synthesises an answer strictly from valid_evidence,
tagging each point with a [source_id]. It must not choose versions, apply amendments,
invent citations, or finalise a conflict — all of that was decided upstream by
deterministic Python + graph. If there is no valid evidence we abstain here without
ever calling the model.

Offline: the MockClient echoes the first cited evidence line back as
"<content> [source_id]", so the answer is grounded and deterministic checks pass.
"""
from __future__ import annotations

from typing import List

from llm.client import get_client
from llm.prompts import (
    GENERATION_SYSTEM,
    GENERATION_USER_TEMPLATE,
    PROMPT_VERSION,
    build_evidence_block,
)
from packages.contracts.enums import AnswerStatus
from packages.contracts.models import (
    Answer,
    Citation,
    EvidencePackage,
)

INSUFFICIENT = "INSUFFICIENT_EVIDENCE"


def _summary(items: List, render) -> str:
    if not items:
        return "(không có)"
    return "; ".join(render(i) for i in items)


def generate(pkg: EvidencePackage) -> Answer:
    """Produce a grounded Answer from an EvidencePackage (abstain if no evidence)."""
    if not pkg.valid_evidence:
        return Answer(
            text=INSUFFICIENT,
            citations=[],
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            query_date=pkg.query_date,
            timeline=pkg.change_paths,
            conflict_candidates=pkg.conflict_candidates,
            impact_candidates=pkg.impact_candidates,
            excluded_evidence=pkg.excluded_evidence,
        )

    evidence_block = build_evidence_block(pkg.valid_evidence)
    user = GENERATION_USER_TEMPLATE.format(
        query=pkg.query,
        query_date=pkg.query_date.isoformat(),
        intent=pkg.intent.value,
        evidence_block=evidence_block,
        excluded_summary=_summary(
            pkg.excluded_evidence, lambda e: f"{e.version_id}:{e.reason.value}"
        ),
        change_summary=_summary(
            pkg.change_paths,
            lambda c: f"{c.provision_id}:{(c.operation.value if c.operation else 'CHANGE')}",
        ),
        conflict_summary=_summary(
            pkg.conflict_candidates,
            lambda c: f"{c.reason.value}({c.value_a} vs {c.value_b})",
        ),
        impact_summary=_summary(
            pkg.impact_candidates,
            lambda i: f"{i.artifact_title}:{i.reason.value}",
        ),
    )

    # If the live LLM fails (rate limit / timeout / network), degrade gracefully to a
    # deterministic grounded answer instead of crashing the query. The evidence was
    # already selected deterministically upstream, so a fallback answer is still correct.
    try:
        text = get_client().complete(GENERATION_SYSTEM, user).strip()
    except Exception:  # noqa: BLE001 - any LLM/transport error must not break the demo
        text = _fallback_text(pkg)

    if not text or text == INSUFFICIENT:
        return Answer(
            text=INSUFFICIENT,
            citations=[],
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            query_date=pkg.query_date,
            timeline=pkg.change_paths,
            conflict_candidates=pkg.conflict_candidates,
            impact_candidates=pkg.impact_candidates,
            excluded_evidence=pkg.excluded_evidence,
        )

    citations = _citations_from(text, pkg)
    return Answer(
        text=text,
        citations=citations,
        status=AnswerStatus.SOURCE_GROUNDED,   # refined by output_checks (step 23)
        query_date=pkg.query_date,
        timeline=pkg.change_paths,
        conflict_candidates=pkg.conflict_candidates,
        impact_candidates=pkg.impact_candidates,
        excluded_evidence=pkg.excluded_evidence,
    )


def _fallback_text(pkg: EvidencePackage) -> str:
    """Deterministic grounded answer from the top valid evidence (LLM-free)."""
    top = pkg.valid_evidence[0]
    return f"{top.content.strip()} [{top.source_id}]"


def _citations_from(text: str, pkg: EvidencePackage) -> List[Citation]:
    """Build Citation objects for every valid source_id actually referenced in text."""
    by_id = {e.source_id: e for e in pkg.valid_evidence}
    out: List[Citation] = []
    seen = set()
    for sid, e in by_id.items():
        if f"[{sid}]" in text and sid not in seen:
            seen.add(sid)
            out.append(
                Citation(
                    source_id=sid,
                    document_number=e.document_number,
                    heading_path=list(e.heading_path),
                    page=e.page,
                )
            )
    return out


def prompt_version() -> str:
    return PROMPT_VERSION
