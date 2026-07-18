"""Step 23 — Deterministic output checks.

After generation we verify the prose against the deterministic evidence, in Python
only. A second LLM verifier does not guarantee correctness, so these checks are rule
based:
    - every [source_id] cited in the answer exists in valid_evidence (no fabrication),
    - the answer never uses a numeric value that only appears in excluded_evidence,
    - the answer is non-empty when valid_evidence exists,
    - no system-prompt leak.

Status is then set precisely — never a vague "VERIFIED":
    SOURCE_GROUNDED + DETERMINISTIC_CHECKS_PASSED  (all checks pass, evidence cited),
    INSUFFICIENT_EVIDENCE                           (no evidence / abstained),
    NEEDS_REVIEW                                    (a check failed).
check_failures lists exactly what failed, for the audit + review panel.
"""
from __future__ import annotations

import re
from typing import List, Tuple

from packages.common.vn_normalize import extract_all_money
from packages.contracts.enums import AnswerStatus
from packages.contracts.models import Answer, EvidencePackage

_CITE_RE = re.compile(r"\[([^\]\s]+)\]")
_LEAK_MARKERS = [
    "trợ lý pháp chế ngân hàng",   # opening line of GENERATION_SYSTEM
    "DỮ LIỆU THAM KHẢO KHÔNG ĐÁNG TIN",
    "quy tắc bắt buộc",
    "system prompt",
]


def run(answer: Answer, pkg: EvidencePackage) -> Answer:
    """Validate `answer` against `pkg`, set status + check_failures, return it."""
    failures: List[str] = []

    if answer.status == AnswerStatus.INSUFFICIENT_EVIDENCE:
        answer.check_failures = []
        return answer

    valid_ids = {e.source_id for e in pkg.valid_evidence}
    excluded_ids = {e.version_id for e in pkg.excluded_evidence}

    # 1. non-empty when evidence exists
    if pkg.valid_evidence and not answer.text.strip():
        failures.append("EMPTY_ANSWER_WITH_EVIDENCE")

    # 2. every cited id exists in valid_evidence; none is an excluded id
    cited = set(_CITE_RE.findall(answer.text))
    fabricated = [c for c in cited if c not in valid_ids]
    if fabricated:
        failures.append(f"FABRICATED_CITATION:{','.join(sorted(fabricated))}")
    cited_excluded = [c for c in cited if c in excluded_ids]
    if cited_excluded:
        failures.append(f"CITED_EXCLUDED_EVIDENCE:{','.join(sorted(cited_excluded))}")

    # 3. at least one grounded citation for a non-abstention answer
    if pkg.valid_evidence and not (cited & valid_ids):
        failures.append("NO_GROUNDED_CITATION")

    # 4. no numeric value that appears ONLY in excluded_evidence
    if _uses_excluded_only_number(answer.text, pkg):
        failures.append("USES_EXCLUDED_NUMBER")

    # 5. system-prompt leak
    low = answer.text.lower()
    if any(m.lower() in low for m in _LEAK_MARKERS):
        failures.append("SYSTEM_PROMPT_LEAK")

    answer.check_failures = failures
    if failures:
        answer.status = AnswerStatus.NEEDS_REVIEW
    else:
        # passed all deterministic checks and is grounded in a valid source
        answer.status = AnswerStatus.DETERMINISTIC_CHECKS_PASSED
    return answer


def _uses_excluded_only_number(text: str, pkg: EvidencePackage) -> bool:
    """True if the answer states a money value that is present in some excluded
    evidence but in NO valid evidence (i.e. it leaked a stale/superseded number)."""
    answer_vals = set(extract_all_money(text))
    if not answer_vals:
        return False
    valid_vals = set()
    for e in pkg.valid_evidence:
        valid_vals.update(extract_all_money(e.content))
        if e.document_number:
            valid_vals.update(extract_all_money(e.document_number))
    excluded_vals = set()
    for ex in pkg.excluded_evidence:
        # excluded_evidence carries no content; use its heading only (best-effort).
        excluded_vals.update(extract_all_money(" ".join(ex.heading_path)))
    leaked = answer_vals & excluded_vals - valid_vals
    return bool(leaked)


def status_pair(answer: Answer) -> Tuple[AnswerStatus, List[str]]:
    return answer.status, answer.check_failures
