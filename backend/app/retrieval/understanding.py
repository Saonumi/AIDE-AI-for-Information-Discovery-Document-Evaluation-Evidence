"""Step 14 — Query understanding + query-date resolution.

Classifies the QueryIntent and resolves the effective query_date. This decides
whether retrieval targets the *current* version or a *point-in-time* version, and
which optional analyses (conflict / impact / cross-reference) to run.

Design: deterministic regex/rules first (cheap, auditable). An LLM classifier is
only a *fallback* when rules are ambiguous, and it may only pick an intent label —
it never resolves the date and never touches retrieval. The date is always resolved
by vn_normalize (the single source of date truth), never by the LLM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from packages.common.vn_normalize import normalize_date, strip_accents
from packages.contracts.enums import QueryIntent

# accent-folded keyword groups (matched against strip_accents(query))
_CURRENT_WORDS = ["hien tai", "hien hanh", "bay gio", "hien nay", "moi nhat", "dang ap dung"]
_PAST_WORDS = ["truoc day", "truoc kia", "luc truoc", "tai thoi diem", "vao ngay", "ngay"]
_HISTORY_WORDS = ["lich su", "cac phien ban", "qua cac", "thay doi qua", "version"]
_CHANGE_WORDS = ["thay doi", "sua doi", "sua nhu the nao", "vi sao thay doi", "amendment", "da thay the"]
_CONFLICT_WORDS = ["xung dot", "mau thuan", "trai nhau", "conflict", "khong tuong thich"]
_IMPACT_WORDS = ["policy noi bo", "quy trinh noi bo", "loi thoi", "con hieu luc khong", "stale", "anh huong noi bo"]
_XREF_WORDS = ["dan chieu", "tham chieu", "theo khoan", "theo dieu", "cross reference", "lien quan toi dieu"]

# light entity cues for the demo domain
_ENTITY_CUES = [
    "SME", "hạn mức", "tín dụng", "khách hàng", "doanh nghiệp", "thời hạn",
    "lãi suất", "bảo đảm", "thế chấp", "quy định",
]


@dataclass
class Understanding:
    intent: QueryIntent
    query_date: date
    entities: List[str] = field(default_factory=list)
    date_explicit: bool = False   # True when the user named a date / "hiện tại"


def _contains_any(folded: str, words: List[str]) -> bool:
    return any(w in folded for w in words)


def _extract_entities(text: str) -> List[str]:
    found: List[str] = []
    low = text.lower()
    for cue in _ENTITY_CUES:
        if cue.lower() in low and cue not in found:
            found.append(cue)
    return found


def understand(
    text: str,
    query_date: Optional[date] = None,
    today: Optional[date] = None,
    llm_fallback: bool = False,
) -> Understanding:
    """Resolve intent + query_date.

    query_date (from the API request) wins if provided. Otherwise we read an explicit
    date out of the text; "hiện tại/hiện hành" => today; nothing => today (CURRENT_QA).
    `today` is injectable for deterministic tests.
    """
    today = today or date.today()
    folded = strip_accents(text or "").lower()
    entities = _extract_entities(text or "")

    text_date = normalize_date(text or "")
    wants_current = _contains_any(folded, _CURRENT_WORDS)

    # ---- resolve query_date (deterministic, never the LLM) ----
    if query_date is not None:
        resolved = query_date
        date_explicit = True
    elif text_date is not None:
        resolved = text_date
        date_explicit = True
    else:
        resolved = today
        date_explicit = wants_current

    # ---- classify intent (rules first) ----
    intent: Optional[QueryIntent] = None
    if _contains_any(folded, _CONFLICT_WORDS):
        intent = QueryIntent.CONFLICT_CHECK
    elif _contains_any(folded, _IMPACT_WORDS):
        intent = QueryIntent.IMPACT_CHECK
    elif _contains_any(folded, _HISTORY_WORDS):
        intent = QueryIntent.VERSION_HISTORY
    elif _contains_any(folded, _CHANGE_WORDS):
        intent = QueryIntent.CHANGE_EXPLANATION
    elif _contains_any(folded, _XREF_WORDS):
        intent = QueryIntent.CROSS_REFERENCE_QA
    elif (query_date is not None or text_date is not None) and not wants_current:
        # an explicit past/other date with no "current" cue => point in time
        intent = QueryIntent.POINT_IN_TIME_QA
    elif wants_current:
        intent = QueryIntent.CURRENT_QA

    if intent is None and llm_fallback:
        intent = _llm_classify(text or "")

    if intent is None:
        intent = QueryIntent.CURRENT_QA

    return Understanding(
        intent=intent,
        query_date=resolved,
        entities=entities,
        date_explicit=date_explicit,
    )


def _llm_classify(text: str) -> Optional[QueryIntent]:
    """Optional LLM intent classifier (label only — never the date, never retrieval)."""
    try:
        from llm.client import get_client
        system = (
            "Phân loại ý định câu hỏi pháp chế thành DUY NHẤT một nhãn trong: "
            "CURRENT_QA, POINT_IN_TIME_QA, VERSION_HISTORY, CROSS_REFERENCE_QA, "
            "CHANGE_EXPLANATION, CONFLICT_CHECK, IMPACT_CHECK. "
            'Trả JSON {"intent": "<nhãn>"}.'
        )
        out = get_client().complete_json(system, f"Câu hỏi: {text}")
        label = (out or {}).get("intent")
        if label in QueryIntent.__members__:
            return QueryIntent[label]
    except Exception:
        pass
    return None
