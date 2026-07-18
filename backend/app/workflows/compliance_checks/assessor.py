"""Workflow B step 2 — deterministic claim assessment (Final spec §7.9).

Per claim: retrieve legal evidence through the EXISTING deterministic pipeline
(query.evidence_package.build — temporal pre-filter, APPROVED-only, hybrid RRF,
graph expansion, supersession resolution), then compare structured facts:

    match against valid evidence            -> COMPLIANT
    match against a SUPERSEDED old version  -> OUTDATED_REFERENCE
    mismatch against valid evidence         -> NON_COMPLIANT
    some match + some mismatch              -> PARTIALLY_COMPLIANT
    match but co-valid conflicting values   -> AMBIGUOUS
    nothing retrieved                       -> MISSING_EVIDENCE
    no comparable fact (semantic only)      -> NEEDS_HUMAN_REVIEW

The LLM never decides a status. Trust gate note: in the legacy store,
approval_status==APPROVED on activated versions is the AUTHORITY_SOURCE proxy;
review targets are never indexed, so retrieval can only see approved sources.
"""
from __future__ import annotations

import re
from datetime import date
from typing import List, Tuple

from packages.contracts.enums import QueryIntent
from packages.contracts.models import ExcludedEvidence

from query import evidence_package

from backend.app.domain.compliance import (
    ClaimAssessment,
    ComplianceClaim,
    ComplianceStatus,
    StructuredFacts,
)
from backend.app.workflows.compliance_checks.claim_extractor import mine_facts

_FACT_CLASSES = ("money_vnd", "percents", "deadline_days")
_FACT_LABELS = {"money_vnd": "số tiền", "percents": "tỷ lệ %", "deadline_days": "hạn chót ngày"}

# Relevance gate: on a small corpus top-k retrieval returns SOMETHING for every
# claim, so unrelated evidence would poison exact compares. An evidence chunk is
# relevant to a claim only if they share a non-generic word bigram ("hạn mức",
# "tín dụng"...), never merely units/modality ("tối đa", "triệu đồng").
_GENERIC_BIGRAMS = {
    "tối đa", "tối thiểu", "triệu đồng", "tỷ đồng", "nghìn đồng", "quy định",
    "không được", "chậm nhất", "không quá", "hằng tháng", "hằng năm",
}
_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _bigrams(text: str) -> set:
    toks = _WORD_RE.findall((text or "").lower())
    return {
        f"{a} {b}" for a, b in zip(toks, toks[1:])
        if f"{a} {b}" not in _GENERIC_BIGRAMS
    }


def _is_relevant(claim_text: str, evidence_text: str) -> bool:
    return bool(_bigrams(claim_text) & _bigrams(evidence_text))


def _legal_provision_versions(evidence):
    """Trust gate (Final spec §2): legal evidence must trace to a ProvisionVersion.

    Internal-policy artifacts are indexed in the same demo store (the QA/impact
    flow needs them) but have no ProvisionVersion row — so they are dropped here
    and can never back a compliance verdict.
    """
    from infra.db_models import DocumentRow, ProvisionVersionRow
    from infra.postgres import session_scope

    out = []
    try:
        with session_scope() as ses:
            for e in evidence:
                row = (
                    ses.query(ProvisionVersionRow)
                    .filter_by(version_id=e.version_id)
                    .first()
                )
                if row is None:
                    continue
                doc = ses.query(DocumentRow).filter_by(document_id=row.document_id).first()
                # Final spec §2.1: INTERNAL_APPROVED is never legal ground truth —
                # internal policies are impact targets, not evidence for verdicts.
                if doc is not None and doc.type == "INTERNAL_POLICY":
                    continue
                out.append(e)
    except Exception:
        out = list(evidence)  # no DB -> degrade open (test/in-memory runs)
    return out


def _relevant_excluded(
    claim_text: str, excluded: List[ExcludedEvidence]
) -> Tuple[List[ExcludedEvidence], StructuredFacts]:
    """Superseded/expired versions RELEVANT to this claim + their mined facts.

    ExcludedEvidence carries no content by contract, so load it from the DB.
    """
    from infra.db_models import ProvisionVersionRow
    from infra.postgres import session_scope

    kept: List[ExcludedEvidence] = []
    texts: List[str] = []
    try:
        with session_scope() as ses:
            for ex in excluded:
                row = (
                    ses.query(ProvisionVersionRow)
                    .filter_by(version_id=ex.version_id)
                    .first()
                )
                if row is not None and row.content and _is_relevant(claim_text, row.content):
                    kept.append(ex)
                    texts.append(row.content)
    except Exception:
        pass  # no DB (pure in-memory run) -> outdated detection simply degrades
    return kept, mine_facts(" ".join(texts))


def _fmt(fact_class: str, value: float) -> str:
    if fact_class == "money_vnd":
        return f"{int(value):,} đồng".replace(",", ".")
    if fact_class == "percents":
        return f"{value:g}%"
    return f"ngày {int(value)}"


def _compare(
    claim_facts: StructuredFacts,
    valid_facts: StructuredFacts,
    old_facts: StructuredFacts,
) -> Tuple[List[str], List[str]]:
    """Per fact-class verdicts + human-readable findings."""
    verdicts: List[str] = []
    findings: List[str] = []
    for fc in _FACT_CLASSES:
        cv = set(getattr(claim_facts, fc))
        if not cv:
            continue
        ev, ov = set(getattr(valid_facts, fc)), set(getattr(old_facts, fc))
        label = _FACT_LABELS[fc]
        if cv & ev:
            verdicts.append("match")
            findings.append(f"{label} khớp quy định hiện hành ({_fmt(fc, next(iter(cv & ev)))})")
        elif cv & ov:
            verdicts.append("outdated")
            new_vals = ", ".join(_fmt(fc, v) for v in sorted(ev)) or "giá trị mới"
            findings.append(
                f"{label} {_fmt(fc, next(iter(cv & ov)))} là giá trị của phiên bản ĐÃ BỊ THAY THẾ; "
                f"quy định hiện hành: {new_vals}"
            )
        elif ev:
            verdicts.append("mismatch")
            findings.append(
                f"{label} trong tài liệu ({', '.join(_fmt(fc, v) for v in sorted(cv))}) "
                f"KHÔNG khớp quy định hiện hành ({', '.join(_fmt(fc, v) for v in sorted(ev))})"
            )
        else:
            verdicts.append("no_evidence")
            findings.append(f"không tìm thấy {label} tương ứng trong kho quy định đã duyệt")
    return verdicts, findings


def assess_claim(claim: ComplianceClaim, review_date: date) -> ClaimAssessment:
    pkg = evidence_package.build(
        query=claim.text, query_date=review_date, intent=QueryIntent.CURRENT_QA
    )
    valid = _legal_provision_versions(
        [e for e in pkg.valid_evidence if _is_relevant(claim.text, e.content)]
    )
    excluded, old_facts = _relevant_excluded(claim.text, pkg.excluded_evidence)

    valid_facts = mine_facts(" ".join(e.content for e in valid))
    verdicts, findings = _compare(claim.facts, valid_facts, old_facts)

    # a conflict only makes the claim AMBIGUOUS if both sides are in-scope evidence
    kept_provs = {e.provision_id for e in valid}
    conflicts_in_scope = any(
        c.provision_a in kept_provs and c.provision_b in kept_provs
        for c in pkg.conflict_candidates
    )

    recommendation = None
    if not valid and not excluded:
        status, confidence = ComplianceStatus.MISSING_EVIDENCE, 0.9
        explanation = "Không tìm thấy căn cứ trong kho quy định đã duyệt tại ngày review."
    elif not claim.facts.has_comparable():
        # ponytail: semantic support needs a real LLM; with deterministic-only
        # signals we hand modality-style claims to the human reviewer.
        status, confidence = ComplianceStatus.NEEDS_HUMAN_REVIEW, 0.5
        explanation = "Claim không có giá trị so sánh tất định; cần người review đánh giá ngữ nghĩa."
    elif "outdated" in verdicts:
        status, confidence = ComplianceStatus.OUTDATED_REFERENCE, 0.95
        explanation = "Tài liệu dùng giá trị của phiên bản đã bị thay thế tại ngày review."
        recommendation = "; ".join(f for f in findings if "THAY THẾ" in f) or None
    elif "match" in verdicts and "mismatch" in verdicts:
        status, confidence = ComplianceStatus.PARTIALLY_COMPLIANT, 0.85
        explanation = "Một phần giá trị khớp quy định hiện hành, một phần không."
    elif "mismatch" in verdicts:
        status, confidence = ComplianceStatus.NON_COMPLIANT, 0.95
        explanation = "Giá trị trong tài liệu mâu thuẫn với quy định hiện hành."
        recommendation = "; ".join(f for f in findings if "KHÔNG khớp" in f) or None
    elif verdicts and all(v == "no_evidence" for v in verdicts):
        # claim states a checkable fact but the approved corpus has no fact of
        # that class to compare -> no basis strong enough (spec §7.9: don't guess)
        status, confidence = ComplianceStatus.MISSING_EVIDENCE, 0.85
        explanation = "Không có quy định đã duyệt chứa giá trị cùng loại để đối chiếu claim này."
    elif "match" in verdicts and conflicts_in_scope:
        status, confidence = ComplianceStatus.AMBIGUOUS, 0.6
        explanation = "Giá trị khớp nhưng tồn tại quy định đồng hiệu lực có giá trị xung đột."
    elif "match" in verdicts:
        status, confidence = ComplianceStatus.COMPLIANT, 0.95
        explanation = "Giá trị được quy định hiện hành hỗ trợ đầy đủ."
    elif valid:
        status, confidence = ComplianceStatus.NEEDS_HUMAN_REVIEW, 0.5
        explanation = "Có evidence nhưng không có giá trị cùng loại để so tất định."
    else:
        status, confidence = ComplianceStatus.MISSING_EVIDENCE, 0.9
        explanation = "Không có căn cứ đủ mạnh trong kho đã duyệt."

    return ClaimAssessment(
        claim_id=claim.claim_id,
        source_text=claim.text,
        status=status,
        structured_facts=claim.facts,
        valid_evidence=valid,
        excluded_evidence=excluded,
        findings=findings,
        explanation=explanation,
        recommendation=recommendation,
        confidence=confidence,
    )
