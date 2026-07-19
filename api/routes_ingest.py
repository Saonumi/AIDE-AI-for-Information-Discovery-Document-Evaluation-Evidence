from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

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
    try:
        return call("ingestion.service", "activate_document", document_id, user.username)
    except Exception as e:
        # Hard gate (Final spec T2): pending critical review -> HTTP 409, stable code
        if type(e).__name__ == "ReviewNotCompletedError":
            raise HTTPException(
                status_code=409,
                detail={"error": {"code": "REVIEW_NOT_COMPLETED", "message": str(e),
                                  "details": {"reasons": getattr(e, "reasons", [])}}},
            )
        raise


@router.delete("/documents/{document_id}")
def delete_document(document_id: str, user: CurrentUser = Depends(require_employee)):
    return call("ingestion.service", "delete_document", document_id, user.username)


@router.get("/documents/{document_id}/provisions")
def list_document_provisions(document_id: str, user: CurrentUser = Depends(require_authenticated)):
    return call("ingestion.service", "list_document_provisions", document_id)
