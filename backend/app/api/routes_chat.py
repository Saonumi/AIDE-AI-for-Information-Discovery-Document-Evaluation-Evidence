"""API — Mode-based chat (Mode spec §12.2).

POST   /conversations                  create (mode = REGULATORY_ASSISTANT | DOCUMENT_REVIEW)
GET    /conversations                  list mine
GET    /conversations/{id}             conversation + turns + attachments
POST   /conversations/{id}/messages    send a message (mode contract enforced)
POST   /conversations/{id}/attachments local CONVERSATION_ATTACHMENT (never legal evidence)
DELETE /conversations/{id}             delete + expire local attachments

owner_id is ALWAYS derived from the auth token (spec §12.3) — never from the body.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.auth import CurrentUser, require_authenticated

from backend.app.chat import service
from backend.app.chat.domain import ChatMode

router = APIRouter(tags=["chat"])


class CreateConversationRequest(BaseModel):
    mode: ChatMode = ChatMode.REGULATORY_ASSISTANT
    title: Optional[str] = None


class MessageRequest(BaseModel):
    text: str
    query_date: Optional[date] = None


class AttachmentRequest(BaseModel):
    filename: str
    text: str


@router.post("/conversations")
def create_conversation(
    req: CreateConversationRequest, user: CurrentUser = Depends(require_authenticated)
) -> dict:
    return service.create_conversation(user.username, req.mode, req.title).model_dump(mode="json")


@router.get("/conversations")
def list_conversations(user: CurrentUser = Depends(require_authenticated)) -> list:
    return [c.model_dump(mode="json") for c in service.list_conversations(user.username)]


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str, user: CurrentUser = Depends(require_authenticated)
) -> dict:
    return service.get_conversation(user.username, conversation_id)


@router.post("/conversations/{conversation_id}/messages")
def post_message(
    conversation_id: str,
    req: MessageRequest,
    user: CurrentUser = Depends(require_authenticated),
) -> dict:
    return service.post_message(
        user.username, user.username, user.role.value, conversation_id,
        req.text, req.query_date,
    )


@router.post("/conversations/{conversation_id}/attachments")
def add_attachment(
    conversation_id: str,
    req: AttachmentRequest,
    user: CurrentUser = Depends(require_authenticated),
) -> dict:
    return service.add_attachment(user.username, conversation_id, req.filename, req.text)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str, user: CurrentUser = Depends(require_authenticated)
) -> dict:
    return service.delete_conversation(user.username, conversation_id)
