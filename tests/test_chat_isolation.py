"""Mode spec §9.3 + §15.1 — conversation memory & cross-chat isolation.

Required invariants covered here:
    - Cross-conversation leakage         = 0 (attachments AND messages)
    - New chat starts with empty memory
    - Ownership: other users get 404
    - Chat messages are NEVER indexed into the global store
    - Delete conversation expires local attachments
    - Ask Regulations multi-turn follow-up resolves within ONE conversation
"""
from __future__ import annotations

import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infra.opensearch_client import get_store

from backend.app.chat import service as chat
from backend.app.chat.domain import ChatMode
from tests.test_compliance_check import _seed

OWNER = "compliance"
OTHER = "user2"
ROLE = "EMPLOYEE"


def _spy_store_writes(monkeypatch):
    calls = []
    store = get_store()
    original = store.index_chunk
    monkeypatch.setattr(store, "index_chunk",
                        lambda *a, **k: (calls.append(a), original(*a, **k)))
    return calls


def test_cross_conversation_attachment_isolation():
    _seed()
    conv_a = chat.create_conversation(OWNER, ChatMode.REGULATORY_ASSISTANT)
    conv_b = chat.create_conversation(OWNER, ChatMode.REGULATORY_ASSISTANT)
    chat.add_attachment(OWNER, conv_a.id, "note_a.txt", "SECRET-A-CONTENT hạn mức nội bộ")

    b = chat.get_conversation(OWNER, conv_b.id)
    assert b["attachments"] == []  # leakage rate must be 0%

    # asking chat B about "the attachment" must not surface A's file
    resp = chat.post_message(OWNER, OWNER, ROLE, conv_b.id, "file đính kèm nói gì?")
    assert "SECRET-A-CONTENT" not in resp["answer"]

    # while chat A itself CAN see its own attachment as local context
    resp_a = chat.post_message(OWNER, OWNER, ROLE, conv_a.id, "file đính kèm nói gì?")
    assert "SECRET-A-CONTENT" in resp_a["answer"]
    assert "không phải nguồn pháp lý" in resp_a["answer"]


def test_new_chat_empty_memory():
    _seed()
    conv_a = chat.create_conversation(OWNER, ChatMode.REGULATORY_ASSISTANT)
    chat.post_message(OWNER, OWNER, ROLE, conv_a.id,
                      "Hạn mức tín dụng SME tối đa là bao nhiêu?")
    conv_b = chat.create_conversation(OWNER, ChatMode.REGULATORY_ASSISTANT)
    b = chat.get_conversation(OWNER, conv_b.id)
    assert b["turns"] == []  # New Chat -> memory starts empty (§3.1)
    # a follow-up in the NEW chat has no previous question to resolve against
    resp = chat.post_message(OWNER, OWNER, ROLE, conv_b.id, "còn trước đây thì sao?")
    assert not resp.get("resolved_query")  # nothing borrowed from conv A


def test_multi_turn_followup_same_conversation():
    _seed()
    conv = chat.create_conversation(OWNER, ChatMode.REGULATORY_ASSISTANT)
    chat.post_message(OWNER, OWNER, ROLE, conv.id,
                      "Hạn mức tín dụng SME tối đa là bao nhiêu?")
    resp = chat.post_message(OWNER, OWNER, ROLE, conv.id, "còn trước đây thì sao?")
    assert resp.get("resolved_query") and "SME" in resp["resolved_query"]


def test_ownership_404():
    _seed()
    conv = chat.create_conversation(OWNER, ChatMode.REGULATORY_ASSISTANT)
    for fn in (lambda: chat.get_conversation(OTHER, conv.id),
               lambda: chat.post_message(OTHER, OTHER, ROLE, conv.id, "hi"),
               lambda: chat.delete_conversation(OTHER, conv.id)):
        with pytest.raises(HTTPException) as e:
            fn()
        assert e.value.status_code == 404


def test_chat_messages_never_indexed(monkeypatch):
    _seed()
    calls = _spy_store_writes(monkeypatch)
    conv = chat.create_conversation(OWNER, ChatMode.REGULATORY_ASSISTANT)
    chat.add_attachment(OWNER, conv.id, "x.txt", "nội dung đính kèm")
    chat.post_message(OWNER, OWNER, ROLE, conv.id,
                      "Hạn mức tín dụng SME tối đa là bao nhiêu?")
    assert calls == []  # §9.3: messages/attachments never reach OpenSearch


def test_delete_conversation_expires_attachments():
    _seed()
    conv = chat.create_conversation(OWNER, ChatMode.REGULATORY_ASSISTANT)
    chat.add_attachment(OWNER, conv.id, "x.txt", "abc")
    chat.delete_conversation(OWNER, conv.id)
    with pytest.raises(HTTPException):
        chat.get_conversation(OWNER, conv.id)


def test_document_review_mode_requires_run():
    _seed()
    conv = chat.create_conversation(OWNER, ChatMode.DOCUMENT_REVIEW)
    with pytest.raises(HTTPException) as e:
        chat.post_message(OWNER, OWNER, ROLE, conv.id, "đánh giá giúp tôi")
    assert e.value.status_code == 409
    assert "REVIEW_RUN_REQUIRED" in str(e.value.detail)
