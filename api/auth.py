"""Auth: password hashing + signed token + role dependencies.

Uses stdlib only (hmac/hashlib/base64) so the whole backend imports with zero extra
deps. Two roles enforced (USER/EMPLOYEE). require_employee gates every write/approve
route — a USER can never upload, approve, or reach admin endpoints (security invariant).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from infra.db_models import User
from infra.postgres import session_scope
from packages.common.config import get_settings
from packages.common.ids import new_id
from packages.contracts.enums import Role

_bearer = HTTPBearer(auto_error=False)

# -------- password hashing (pbkdf2, stdlib) --------
def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or base64.b16encode(hashlib.sha256(password.encode()).digest()[:8]).decode()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${base64.b16encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


# -------- token (HMAC-signed, stdlib) --------
def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def create_token(username: str, role: str) -> str:
    s = get_settings()
    payload = {"sub": username, "role": role, "exp": int(time.time()) + s.jwt_expire_minutes * 60}
    body = _b64e(json.dumps(payload).encode())
    sig = _b64e(hmac.new(s.jwt_secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def decode_token(token: str) -> dict:
    s = get_settings()
    try:
        body, sig = token.split(".")
    except ValueError:
        raise _unauth()
    expected = _b64e(hmac.new(s.jwt_secret.encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        raise _unauth()
    payload = json.loads(_b64d(body))
    if payload.get("exp", 0) < time.time():
        raise _unauth("Token expired")
    return payload


def _unauth(msg: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)


# -------- dependencies --------
class CurrentUser:
    def __init__(self, username: str, role: str):
        self.username = username
        self.role = Role(role)


def require_authenticated(creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)) -> CurrentUser:
    if creds is None:
        raise _unauth()
    payload = decode_token(creds.credentials)
    return CurrentUser(payload["sub"], payload["role"])


def require_employee(user: CurrentUser = Depends(require_authenticated)) -> CurrentUser:
    # Final spec §6.1: COMPLIANCE_OFFICER is the business persona; EMPLOYEE is its
    # deprecated alias kept until the legacy tree is retired.
    if user.role not in (Role.EMPLOYEE, Role.COMPLIANCE_OFFICER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Compliance Officer role required")
    return user


require_compliance_officer = require_employee  # canonical name (Final spec §6.1)


# -------- login + seeding --------
def authenticate(username: str, password: str) -> Optional[CurrentUser]:
    with session_scope() as ses:
        u = ses.query(User).filter(User.username == username).one_or_none()
        if u and verify_password(password, u.password_hash):
            return CurrentUser(u.username, u.role)
    return None


def seed_users() -> None:
    """Idempotent: create demo employee + user accounts if missing."""
    demo = [("employee", "employee123", Role.EMPLOYEE), ("user", "user123", Role.USER),
            ("compliance", "compliance123", Role.COMPLIANCE_OFFICER)]
    with session_scope() as ses:
        for username, pw, role in demo:
            if not ses.query(User).filter(User.username == username).one_or_none():
                ses.add(User(id=new_id("usr"), username=username,
                             password_hash=hash_password(pw), role=role.value))
