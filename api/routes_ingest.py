from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from api._facade import call
from api.auth import CurrentUser, require_authenticated, require_employee
from packages.contracts.api_schemas import UploadResponse

router = APIRouter(tags=["ingestion"])


@router.post("/documents", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    type: str = Form("REGULATION"),
    user: CurrentUser = Depends(require_employee),
) -> UploadResponse:
    data = await file.read()
    return call("ingestion.service", "handle_upload", data, file.filename, type, user.username)


@router.get("/documents")
def list_documents(user: CurrentUser = Depends(require_authenticated)):
    return call("ingestion.service", "list_documents")


@router.post("/documents/{document_id}/activate")
def activate_document(document_id: str, user: CurrentUser = Depends(require_employee)):
    return call("ingestion.service", "activate_document", document_id, user.username)
