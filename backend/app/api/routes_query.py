from __future__ import annotations

from fastapi import APIRouter, Depends

from api._facade import call
from api.auth import CurrentUser, require_authenticated
from packages.contracts.api_schemas import CompareResponse, QueryRequest, QueryResponse

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, user: CurrentUser = Depends(require_authenticated)) -> QueryResponse:
    return call("query.service", "answer_query", req.text, req.query_date, user.username, user.role.value)


@router.post("/compare", response_model=CompareResponse)
def compare(req: QueryRequest, user: CurrentUser = Depends(require_authenticated)) -> CompareResponse:
    return call("query.service", "compare", req.text, req.query_date, user.username, user.role.value)
