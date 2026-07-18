"""HTTP client for the VAIC2026 backend — resilient by design.

Every method returns an `ApiResult` (ok / status / data / error) and NEVER raises on
a network problem, so the Streamlit app can render a friendly "API is down" message
instead of crashing. The endpoint shapes mirror packages.contracts.api_schemas.

API_BASE_URL comes from the env (default http://localhost:8000).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

try:
    import requests
except Exception:  # pragma: no cover - requests should be present, but stay import-safe
    requests = None  # type: ignore


DEFAULT_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
_TIMEOUT = float(os.environ.get("API_TIMEOUT", "30"))


@dataclass
class ApiResult:
    ok: bool
    status: int = 0
    data: Any = None
    error: Optional[str] = None

    def __bool__(self) -> bool:  # allow `if result:` idiom
        return self.ok


@dataclass
class ApiClient:
    base_url: str = DEFAULT_BASE_URL
    token: Optional[str] = None
    timeout: float = _TIMEOUT
    _session: Any = field(default=None, repr=False)

    def __post_init__(self):
        if requests is not None and self._session is None:
            self._session = requests.Session()

    # ----------------------------------------------------------------- #
    # low-level request (never raises)
    # ----------------------------------------------------------------- #
    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if extra:
            h.update(extra)
        return h

    def _request(self, method: str, path: str, *, json: Any = None,
                 params: Any = None, files: Any = None, data: Any = None) -> ApiResult:
        if requests is None:
            return ApiResult(False, error="The 'requests' package is not installed.")
        url = f"{self.base_url.rstrip('/')}{path}"
        try:
            resp = self._session.request(
                method, url, headers=self._headers(), json=json, params=params,
                files=files, data=data, timeout=self.timeout,
            )
        except Exception as e:  # connection refused, DNS, timeout, ...
            return ApiResult(False, error=f"Không kết nối được API ({url}): {e}")
        payload: Any
        try:
            payload = resp.json()
        except Exception:
            payload = resp.text
        if not resp.ok:
            detail = payload.get("detail") if isinstance(payload, dict) else payload
            return ApiResult(False, status=resp.status_code, data=payload,
                             error=f"HTTP {resp.status_code}: {detail}")
        return ApiResult(True, status=resp.status_code, data=payload)

    def get(self, path: str, **kw) -> ApiResult:
        return self._request("GET", path, **kw)

    def post(self, path: str, **kw) -> ApiResult:
        return self._request("POST", path, **kw)

    # ----------------------------------------------------------------- #
    # typed endpoints (mirror api/routes_*.py)
    # ----------------------------------------------------------------- #
    def health(self) -> ApiResult:
        return self.get("/health")

    def login(self, username: str, password: str) -> ApiResult:
        res = self.post("/login", json={"username": username, "password": password})
        if res.ok and isinstance(res.data, dict):
            self.token = res.data.get("token")
        return res

    def query(self, text: str, query_date: Optional[str] = None,
              mode: Optional[str] = None) -> ApiResult:
        body: Dict[str, Any] = {"text": text}
        if query_date:
            body["query_date"] = query_date
        if mode:
            body["mode"] = mode
        return self.post("/query", json=body)

    def compare(self, text: str, query_date: Optional[str] = None) -> ApiResult:
        body: Dict[str, Any] = {"text": text}
        if query_date:
            body["query_date"] = query_date
        return self.post("/compare", json=body)

    def compliance_check(self, text: str, review_date: Optional[str] = None,
                         filename: Optional[str] = None) -> ApiResult:
        body: Dict[str, Any] = {"text": text}
        if review_date:
            body["review_date"] = review_date
        if filename:
            body["filename"] = filename
        return self.post("/compliance-checks", json=body)

    def compliance_report(self, check_id: str) -> ApiResult:
        return self.get(f"/compliance-checks/{check_id}/report")

    def list_review_tasks(self, status: Optional[str] = None) -> ApiResult:
        params = {"status": status} if status else None
        return self.get("/review-tasks", params=params)

    def decide_review_task(self, task_id: str, decision: str,
                           edited_payload: Optional[dict] = None,
                           note: Optional[str] = None) -> ApiResult:
        body: Dict[str, Any] = {"decision": decision}
        if edited_payload is not None:
            body["edited_payload"] = edited_payload
        if note:
            body["note"] = note
        return self.post(f"/review-tasks/{task_id}/decision", json=body)

    def list_documents(self) -> ApiResult:
        return self.get("/documents")

    def upload_document(self, filename: str, content: bytes,
                        doc_type: str = "REGULATION") -> ApiResult:
        files = {"file": (filename, content)}
        return self.post("/documents", files=files, data={"type": doc_type})

    def activate_document(self, document_id: str) -> ApiResult:
        return self.post(f"/documents/{document_id}/activate")

    def graph_provision(self, provision_id: str) -> ApiResult:
        return self.get(f"/graph/provision/{provision_id}")

    def audit(self) -> ApiResult:
        return self.get("/audit")
