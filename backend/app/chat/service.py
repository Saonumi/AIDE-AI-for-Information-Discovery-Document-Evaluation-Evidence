"""Conversation service + isolation policy (Mode spec §3.1, §9).

Every read/write is scoped by owner_id + conversation_id AT THIS LAYER — routes
never pass a free-form owner. Chat turns and attachments live ONLY in the
conversation tables: nothing here writes to OpenSearch or Neo4j, so chat
content can never leak into global retrieval (spec §9.3).

Mode contract (§3):
    REGULATORY_ASSISTANT  multi-turn RAG; history = this conversation only.
    DOCUMENT_REVIEW       messages route to the explainer of the ACTIVE locked
                          Review Run; without a run -> 409 REVIEW_RUN_REQUIRED.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import List, Optional

from fastapi import HTTPException

from infra.db_models import ChatTurnRow, ConversationAttachmentRow, ConversationRow
from infra.postgres import init_db, session_scope
from packages.common.ids import new_id

from backend.app.chat.domain import ChatMode, ChatTurn, Conversation

_FOLLOWUP_HINTS = (
    "đó", "này", "ấy", "nó", "vậy", "thì sao", "khi nào", "bao giờ",
    "trước đây", "trước đó", "còn", "cũ",
)
_ATTACHMENT_HINTS = ("đính kèm", "tệp", "file", "tài liệu tôi gửi", "tài liệu này", "tài liệu", "nội dung này", "văn bản này")

_CHITCHAT_TRIGGERS = (
    "hello", "hi ", "hi!", "xin chào", "chào bạn", "chào aide", "hey",
    "bạn là ai", "tên bạn", "aide là gì", "aide là ai", "bạn tên gì",
    "bạn làm được gì", "bạn có thể làm gì", "giới thiệu", "mày là ai",
    "cảm ơn", "thank", "tạm biệt", "bye", "ok bạn", "được rồi", "tốt lắm",
    "bạn có khỏe", "hôm nay thế nào",
)
_LEGAL_SIGNALS = (
    "quy định", "điều ", "khoản ", "thông tư", "nghị định", "quyết định",
    "luật ", "lãi suất", "tín dụng", "vốn", "tỷ lệ", "hạn mức", "phí",
    "hiệu lực", "sửa đổi", "bổ sung", "áp dụng", "tuân thủ",
)

def _aide_persona_system() -> str:
    try:
        from llm.prompts import AIDE_PERSONA_SYSTEM
        return AIDE_PERSONA_SYSTEM
    except Exception:
        return "Bạn là AIDE — trợ lý pháp chế SHB. Trả lời thân thiện tiếng Việt."


def _is_chitchat(text: str) -> bool:
    """True nếu câu hỏi là chào hỏi, hỏi về AIDE, hoặc không liên quan pháp lý."""
    low = text.lower().strip()
    if any(t in low for t in _CHITCHAT_TRIGGERS):
        return True
    # Câu rất ngắn không có từ khóa pháp lý
    if len(low) < 40 and not any(s in low for s in _LEGAL_SIGNALS):
        return True
    return False


def _ensure_db() -> None:
    try:
        init_db()
    except Exception:
        pass


def _conv_or_404(ses, owner_id: str, conversation_id: str) -> ConversationRow:
    row = ses.query(ConversationRow).filter_by(id=conversation_id).one_or_none()
    # Ownership check (spec §12.3): someone else's conversation is
    # indistinguishable from a missing one — 404, no existence leak.
    if row is None or row.owner_id != owner_id or row.retention_status != "ACTIVE":
        raise HTTPException(status_code=404, detail="conversation not found")
    return row


def _to_model(row: ConversationRow) -> Conversation:
    return Conversation(
        id=row.id, owner_id=row.owner_id, mode=ChatMode(row.mode), title=row.title,
        active_review_run_id=row.active_review_run_id,
        active_batch_review_id=row.active_batch_review_id,
        retention_status=row.retention_status,
        created_at=row.created_at, last_activity_at=row.last_activity_at,
    )


def create_conversation(owner_id: str, mode: ChatMode, title: Optional[str] = None) -> Conversation:
    _ensure_db()
    conv_id = new_id("conv")
    with session_scope() as ses:
        ses.add(ConversationRow(id=conv_id, owner_id=owner_id, mode=mode.value,
                                title=title or ("Document Review" if mode == ChatMode.DOCUMENT_REVIEW
                                                else "Ask Regulations")))
    with session_scope() as ses:
        return _to_model(_conv_or_404(ses, owner_id, conv_id))


def list_conversations(owner_id: str) -> List[Conversation]:
    _ensure_db()
    with session_scope() as ses:
        rows = (ses.query(ConversationRow)
                .filter_by(owner_id=owner_id, retention_status="ACTIVE")
                .order_by(ConversationRow.last_activity_at.desc()).all())
        return [_to_model(r) for r in rows]


def get_conversation(owner_id: str, conversation_id: str) -> dict:
    _ensure_db()
    with session_scope() as ses:
        conv = _to_model(_conv_or_404(ses, owner_id, conversation_id))
        turns = _turns(ses, owner_id, conversation_id)
        atts = (ses.query(ConversationAttachmentRow)
                .filter_by(conversation_id=conversation_id, owner_id=owner_id,
                           retention_status="ACTIVE").all())
    return {
        "conversation": conv.model_dump(mode="json"),
        "turns": [t.model_dump(mode="json") for t in turns],
        "attachments": [{"id": a.id, "filename": a.filename, "trust_class": a.trust_class,
                         "checksum": a.checksum} for a in atts],
    }


def delete_conversation(owner_id: str, conversation_id: str) -> dict:
    """Retention (spec §9.3): expire the conversation AND its local attachments."""
    _ensure_db()
    with session_scope() as ses:
        conv = _conv_or_404(ses, owner_id, conversation_id)
        conv.retention_status = "DELETED"
        for att in ses.query(ConversationAttachmentRow).filter_by(
                conversation_id=conversation_id, owner_id=owner_id).all():
            att.retention_status = "EXPIRED"
    return {"deleted": conversation_id}


def add_attachment(owner_id: str, conversation_id: str, filename: str, text: str) -> dict:
    """Store a CONVERSATION_ATTACHMENT — local context only, never indexed,
    never legal evidence, never routed through source activation (spec §3.3)."""
    _ensure_db()
    att_id = new_id("att")
    checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
    with session_scope() as ses:
        _conv_or_404(ses, owner_id, conversation_id)
        ses.add(ConversationAttachmentRow(
            id=att_id, conversation_id=conversation_id, owner_id=owner_id,
            filename=filename, content=text, checksum=checksum))
    return {"attachment_id": att_id, "trust_class": "CONVERSATION_ATTACHMENT",
            "checksum": checksum,
            "notice": "Attachment là context cục bộ của hội thoại này; "
                      "KHÔNG phải nguồn pháp lý và không vào knowledge base."}


def _turns(ses, owner_id: str, conversation_id: str) -> List[ChatTurn]:
    rows = (ses.query(ChatTurnRow)
            .filter_by(conversation_id=conversation_id, owner_id=owner_id)
            .order_by(ChatTurnRow.created_at.asc(), ChatTurnRow.id.asc()).all())
    return [ChatTurn(id=r.id, conversation_id=r.conversation_id, role=r.role,
                     content=r.content, citations=r.citations or [],
                     created_at=r.created_at) for r in rows]


def _contextualize(text: str, history: List[ChatTurn]) -> str:
    # ponytail: deterministic follow-up resolver — short/pronoun-bearing
    # questions get the previous user question prepended; upgrade to an LLM
    # condenser when real multi-turn conversations outgrow this heuristic.
    low = text.lower()
    if len(text) >= 80 or not any(h in low for h in _FOLLOWUP_HINTS):
        return text
    prev = [t.content for t in history if t.role == "user"]
    return f"{prev[-1]} — {text}" if prev else text


def _attachment_context(ses, owner_id: str, conversation_id: str, text: str) -> Optional[str]:
    """If the user asks about their attachment, surface it as LOCAL context."""
    low = text.lower()
    if not any(h in low for h in _ATTACHMENT_HINTS):
        return None
    att = (ses.query(ConversationAttachmentRow)
           .filter_by(conversation_id=conversation_id, owner_id=owner_id,
                      retention_status="ACTIVE")
           .order_by(ConversationAttachmentRow.created_at.desc()).first())
    if att is None:
        return None
    return (f"[Context cục bộ — tệp đính kèm '{att.filename}', không phải nguồn pháp lý]\n"
            f"{att.content[:400]}")


def post_message(
    owner_id: str,
    username: str,
    role: str,
    conversation_id: str,
    text: str,
    query_date: Optional[date] = None,
) -> dict:
    _ensure_db()
    with session_scope() as ses:
        conv = _conv_or_404(ses, owner_id, conversation_id)
        mode = ChatMode(conv.mode)
        active_run = conv.active_review_run_id
        active_batch = conv.active_batch_review_id
        history = _turns(ses, owner_id, conversation_id)
        attachment_ctx = _attachment_context(ses, owner_id, conversation_id, text)
        ses.add(ChatTurnRow(id=new_id("trn"), conversation_id=conversation_id,
                            owner_id=owner_id, role="user", content=text))
        conv.last_activity_at = datetime.utcnow()

    extra: dict = {}
    if mode == ChatMode.DOCUMENT_REVIEW:
        from backend.app.review import explainer  # lazy: avoids import cycle

        if active_run:
            result = explainer.answer(owner_id, active_run, text)
        elif active_batch:
            result = explainer.answer_batch(owner_id, active_batch, text)
        else:
            raise HTTPException(status_code=409, detail={"error": {
                "code": "REVIEW_RUN_REQUIRED",
                "message": "Document Review cần upload file + assessment date "
                           "để tạo Review Run trước khi chat."}})
        answer_text = result["answer"]
        citations = result.get("citations", [])
        extra = {k: v for k, v in result.items() if k not in ("answer", "citations")}
    elif _is_chitchat(text) and not attachment_ctx:
        # Chitchat / hỏi về AIDE → trả lời bằng persona, không qua RAG
        from llm.client import get_client
        try:
            answer_text = get_client().complete(_aide_persona_system(), text)
        except Exception:
            answer_text = ("Xin chào! Tôi là AIDE — trợ lý pháp chế của ngân hàng SHB. "
                           "Tôi có thể giúp bạn tra cứu quy định pháp lý và kiểm tra tuân thủ tài liệu. "
                           "Bạn muốn hỏi về quy định nào?")
        citations = []
        extra = {"status": "CHITCHAT"}
    else:
        from query.service import answer_query  # Ask Regulations = existing RAG

        ctx_query = _contextualize(text, history)
        resp = answer_query(ctx_query, query_date, username, role)
        answer_text = resp.answer.text
        if attachment_ctx:
            if answer_text == "INSUFFICIENT_EVIDENCE":
                answer_text = attachment_ctx
            else:
                answer_text = f"{attachment_ctx}\n\n{answer_text}"
        citations = [c.model_dump(mode="json") for c in resp.answer.citations]
        extra = {"status": resp.answer.status.value,
                 "query_date": resp.answer.query_date.isoformat()
                 if resp.answer.query_date else None,
                 "resolved_query": ctx_query if ctx_query != text else None}

    with session_scope() as ses:
        turn_id = new_id("trn")
        ses.add(ChatTurnRow(id=turn_id, conversation_id=conversation_id,
                            owner_id=owner_id, role="assistant",
                            content=answer_text, citations=citations))
    return {"turn_id": turn_id, "mode": mode.value, "answer": answer_text,
            "citations": citations, **extra}
