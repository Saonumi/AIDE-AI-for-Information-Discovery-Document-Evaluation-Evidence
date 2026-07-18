from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.auth import authenticate, create_token
from packages.contracts.api_schemas import LoginRequest, LoginResponse

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest) -> LoginResponse:
    user = authenticate(req.username, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")
    return LoginResponse(token=create_token(user.username, user.role.value),
                         role=user.role, username=user.username)
