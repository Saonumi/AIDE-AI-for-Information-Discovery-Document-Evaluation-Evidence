from __future__ import annotations

from fastapi import APIRouter, Depends

from api._facade import call
from api.auth import CurrentUser, require_authenticated, require_employee
from packages.contracts.api_schemas import GraphResponse

router = APIRouter(tags=["graph"])


@router.get("/graph/provision/{provision_id}", response_model=GraphResponse)
def graph_provision(provision_id: str, user: CurrentUser = Depends(require_authenticated)) -> GraphResponse:
    return call("query.service", "graph_subgraph", provision_id)


@router.get("/audit")
def audit(user: CurrentUser = Depends(require_employee)):
    return call("query.service", "list_audit")
