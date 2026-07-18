"""Review Explainer chat (Mode spec §5, §7.3, §10.3) — bounded to the LOCKED run.

Allowed context: locked ReviewRun JSON + its evidence + the current question.
It can explain, summarize and draft revisions — it can NEVER change a status,
add evidence, or re-assess. Parameter-change requests return the action
CREATE_NEW_REVIEW_RUN. Deterministic first: the answer is composed from the
frozen report, then optionally phrased by the LLM under the review_explainer
prompt — with a citation-allowlist check that falls back to the deterministic
text on any violation.
"""
from __future__ import annotations

import re
from typing import List, Optional

from llm.client import get_client

from backend.app.core.prompt_loader import system_prompt
from backend.app.review import service as review_service

# "change my verdict" — request to alter the locked result with words alone (§7.3)
_CHANGE_RE = re.compile(
    r"(đổi|sửa|thay|chuyển|hãy\s+coi|update|change|set)\b.{0,60}"
    r"(compliant|kết\s*luận|status|trạng\s*thái|kết\s*quả|verdict)",
    re.IGNORECASE | re.DOTALL,
)
# "assess with other parameters" — needs a NEW run (§5.3, §10.3)
_NEW_PARAMS_RE = re.compile(
    r"(ngày\s+khác|ngày\s+\d{1,2}[/-]|assessment\s*date|đánh\s*giá\s*lại"
    r"|snapshot\s*mới|file\s*khác|phiên\s*bản\s*file|rerun|re-run|chạy\s*lại)",
    re.IGNORECASE,
)
_REVISION_RE = re.compile(r"(đề\s*xuất|viết\s*lại|draft|sửa\s*thế\s*nào|revision)", re.IGNORECASE)

_LOCKED_MSG = (
    "Kết quả của Review Run này đã được KHÓA. Theo trust rule (§4.2), kết luận "
    "chỉ thay đổi khi có nguồn pháp lý APPROVED mới và một Review Run mới — "
    "không thể thay đổi bằng yêu cầu trong chat. Status giữ nguyên."
)


def _citations(assessment: dict) -> List[dict]:
    return [
        {"source_id": e.get("source_id"), "document_number": e.get("document_number"),
         "heading_path": e.get("heading_path", []), "page": e.get("page"),
         "valid_from": e.get("valid_from")}
        for e in assessment.get("valid_evidence", [])
    ]


def _pick_assessment(report: dict, question: str, claim_id: Optional[str] = None) -> Optional[dict]:
    assessments = report.get("assessments", [])
    if not assessments:
        return None
    if claim_id:
        for a in assessments:
            if a.get("claim_id") == claim_id:
                return a
    q_words = set(re.findall(r"\w+", question.lower()))
    scored = sorted(
        assessments,
        key=lambda a: len(q_words & set(re.findall(r"\w+", a.get("source_text", "").lower()))),
        reverse=True,
    )
    best = scored[0]
    overlap = len(q_words & set(re.findall(r"\w+", best.get("source_text", "").lower())))
    # weak overlap -> prefer the first problematic finding (the demo question "vì sao?")
    if overlap < 2:
        for a in assessments:
            if a.get("status") != "COMPLIANT":
                return a
    return best


def _deterministic_answer(assessment: dict, question: str) -> str:
    lines = [
        f"CLAIM: \"{assessment.get('source_text', '')}\"",
        f"STATUS: {assessment.get('status')}",
    ]
    if assessment.get("findings"):
        lines.append("SO SÁNH: " + "; ".join(assessment["findings"]))
    lines.append(f"GIẢI THÍCH: {assessment.get('explanation', '')}")
    for e in assessment.get("valid_evidence", [])[:3]:
        heading = " · ".join(e.get("heading_path", []) or [])
        lines.append(
            f"EVIDENCE: {e.get('document_number') or e.get('source_id')} · {heading}"
            f" · hiệu lực từ {e.get('valid_from')} · trang {e.get('page')}")
    if _REVISION_RE.search(question):
        rev = assessment.get("recommendation")
        lines.append("ĐỀ XUẤT SỬA: " + (rev if rev else
                     "Chưa đủ evidence để đề xuất tự động — cần Human Review."))
    if assessment.get("requires_human_review"):
        lines.append("HUMAN REVIEW: Required")
    return "\n".join(lines)


def _llm_polish(context: str, question: str, fallback: str, allow_ids: set) -> str:
    client = get_client()
    if getattr(client, "provider", "mock") == "mock":
        return fallback
    try:
        out = client.complete(
            system_prompt("review_explainer.system"),
            f"<EVIDENCE>\n{context}\n</EVIDENCE>\n\nCâu hỏi: {question}")
        cited = set(re.findall(r"\[([^\]\s]+)\]", out))
        if cited - allow_ids:  # invented citation -> refuse the LLM text
            return fallback
        return out or fallback
    except Exception:
        return fallback


def answer(owner_id: str, run_id: str, question: str,
           claim_id: Optional[str] = None) -> dict:
    row = review_service.get_run_row(owner_id, run_id)
    report = row.report or {}

    if _CHANGE_RE.search(question):
        return {"answer": _LOCKED_MSG, "citations": [], "result_locked": True,
                "review_run_id": run_id}
    if _NEW_PARAMS_RE.search(question):
        return {"answer": "Thay đổi file/ngày đánh giá/phạm vi/snapshot cần một "
                          "Review Run mới — kết quả run hiện tại giữ nguyên. "
                          "Dùng nút Create New Review Run.",
                "citations": [], "action": "CREATE_NEW_REVIEW_RUN",
                "review_run_id": run_id}

    assessment = _pick_assessment(report, question, claim_id)
    if assessment is None:
        return {"answer": "Run này chưa có finding nào để giải thích "
                          f"(state={row.state}).", "citations": [],
                "review_run_id": run_id}

    det = _deterministic_answer(assessment, question)
    allow = {e.get("source_id") for e in assessment.get("valid_evidence", [])}
    text = _llm_polish(det, question, det, allow)
    return {"answer": text, "citations": _citations(assessment),
            "claim_id": assessment.get("claim_id"), "review_run_id": run_id}


def answer_batch(owner_id: str, batch_id: str, question: str,
                 scope: str = "ENTIRE_BATCH",
                 review_run_id: Optional[str] = None,
                 claim_ids: Optional[List[str]] = None) -> dict:
    """Batch chat scopes (§8.4): sources are bounded per scope, nothing else."""
    from backend.app.review import batch as batch_service

    if scope == "ONE_REPORT" and review_run_id:
        return answer(owner_id, review_run_id, question)

    data = batch_service.get_batch_review(owner_id, batch_id)
    if _CHANGE_RE.search(question):
        return {"answer": _LOCKED_MSG, "citations": [], "result_locked": True,
                "batch_review_id": batch_id}
    if scope == "SELECTED_FINDINGS" and claim_ids:
        found = []
        for item in data["items"]:
            if not item.get("review_run_id"):
                continue
            try:
                run = review_service.get_run_row(owner_id, item["review_run_id"])
            except Exception:
                continue
            for a in (run.report or {}).get("assessments", []):
                if a.get("claim_id") in set(claim_ids):
                    found.append((item["filename"], a))
        lines = [f"[{fn}] {_deterministic_answer(a, question)}" for fn, a in found]
        return {"answer": "\n\n".join(lines) or "Không tìm thấy finding được chọn.",
                "citations": [c for _, a in found for c in _citations(a)],
                "batch_review_id": batch_id}

    s = data["summary"] or {}
    lines = [
        f"Batch {batch_id}: {data['total_documents']} tài liệu — "
        f"{data['completed_documents']} hoàn thành, {data['failed_documents']} lỗi.",
        "Tổng hợp status: " + ", ".join(f"{k}={v}" for k, v in s.items() if v),
    ]
    for g in data.get("recurring_issues", []):
        lines.append(
            f"Vấn đề lặp lại: {g['finding_type']} × {g['occurrence_count']} "
            f"({', '.join(g['affected_document_ids'])})"
            + (f" — giá trị: {g['shared_value']}" if g.get("shared_value") else ""))
    return {"answer": "\n".join(lines), "citations": [], "batch_review_id": batch_id}
