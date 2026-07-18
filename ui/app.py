"""VAIC2026 SHB1 — Streamlit demo UI (Track C).

Talks to the FastAPI backend over HTTP via ui.api_client. Resilient: if the API is
down every page shows a friendly message instead of crashing.

Run:  streamlit run ui/app.py
Env:  API_BASE_URL (default http://localhost:8000)

Sections:
  - Login (role USER / EMPLOYEE)
  - Chat: /query — answer, citations, status badge, timeline, "Vì sao câu trả lời này"
  - So sánh (head-to-head): /compare — Standard RAG vs Our System
  - Review inbox (EMPLOYEE): /review-tasks
  - Dashboard (EMPLOYEE): docs, change events, conflict/stale/injection candidates
  - KG visualization: /graph/provision/{id} (streamlit-agraph, table fallback)
  - Audit (EMPLOYEE): /audit

The module imports without streamlit installed (guarded) so an import smoke test in
CI passes; main() requires streamlit to actually run.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ui.api_client import ApiClient, DEFAULT_BASE_URL

try:
    import streamlit as st
    _HAS_ST = True
except Exception:  # pragma: no cover - streamlit optional for import
    st = None  # type: ignore
    _HAS_ST = False


# --------------------------------------------------------------------------- #
# small render helpers (pure enough to reason about; guarded on st)
# --------------------------------------------------------------------------- #
_STATUS_STYLE = {
    "SOURCE_GROUNDED": ("✅", "Có nguồn dẫn"),
    "DETERMINISTIC_CHECKS_PASSED": ("✅", "Qua kiểm tra xác định"),
    "HUMAN_REVIEWED": ("✅", "Đã người duyệt"),
    "NEEDS_REVIEW": ("⚠️", "Cần rà soát"),
    "INSUFFICIENT_EVIDENCE": ("⛔", "Không đủ bằng chứng"),
}

_EXCLUSION_VI = {
    "NOT_VALID_AT_QUERY_DATE": "Không hiệu lực tại ngày truy vấn",
    "SUPERSEDED": "Đã bị thay thế (bản cũ)",
    "NOT_APPROVED": "Chưa được phê duyệt",
    "OUT_OF_SCOPE": "Ngoài phạm vi câu hỏi",
}


def _fmt_heading(heading_path: Optional[List[str]]) -> str:
    return " › ".join(heading_path) if heading_path else "—"


def status_badge(status: Optional[str]) -> str:
    icon, label = _STATUS_STYLE.get(status or "", ("•", status or "?"))
    return f"{icon} {label}"


def _client() -> ApiClient:
    base = st.session_state.get("base_url", DEFAULT_BASE_URL)
    token = st.session_state.get("token")
    return ApiClient(base_url=base, token=token)


def _api_down(res) -> None:
    st.error("Không thể gọi API. Kiểm tra backend đang chạy và API_BASE_URL đúng.")
    if res is not None and getattr(res, "error", None):
        st.caption(res.error)


# --------------------------------------------------------------------------- #
# rendering blocks
# --------------------------------------------------------------------------- #
def render_answer(answer: Dict[str, Any]) -> None:
    st.markdown(f"**Trạng thái:** {status_badge(answer.get('status'))}")
    st.markdown(answer.get("text") or "_(không có nội dung)_")

    citations = answer.get("citations") or []
    if citations:
        st.markdown("**Trích dẫn:**")
        for c in citations:
            doc = c.get("document_number") or "?"
            page = c.get("page")
            page_s = f", trang {page}" if page is not None else ""
            st.markdown(f"- `{doc}` — {_fmt_heading(c.get('heading_path'))}{page_s}")

    timeline = answer.get("timeline") or []
    if timeline:
        st.markdown("**Dòng thời gian (timeline):**")
        for t in timeline:
            op = t.get("operation") or "CHANGE"
            st.markdown(
                f"- {op}: `{t.get('before_version_id')}` → `{t.get('after_version_id')}`"
            )

    conflicts = answer.get("conflict_candidates") or []
    if conflicts:
        st.warning("Phát hiện ứng viên xung đột (cần rà soát):")
        for c in conflicts:
            st.markdown(
                f"- {c.get('reason')}: {c.get('value_a')} ↔ {c.get('value_b')} "
                f"({c.get('provision_a')} vs {c.get('provision_b')})"
            )

    impacts = answer.get("impact_candidates") or []
    if impacts:
        st.warning("Chính sách nội bộ có thể lỗi thời (stale):")
        for i in impacts:
            st.markdown(
                f"- {i.get('artifact_title')}: nội bộ {i.get('internal_policy_value')} "
                f"vs quy định {i.get('regulation_value')}"
            )


def render_why_panel(answer: Dict[str, Any], evidence: Optional[Dict[str, Any]]) -> None:
    """The 'Vì sao câu trả lời này' panel: valid sources AND excluded sources+reason."""
    with st.expander("🔎 Vì sao câu trả lời này", expanded=True):
        valid = (evidence or {}).get("valid_evidence") or []
        st.markdown("**Nguồn hợp lệ được dùng:**")
        if valid:
            for e in valid:
                page = e.get("page")
                page_s = f", trang {page}" if page is not None else ""
                st.markdown(
                    f"- ✅ `{e.get('document_number')}` {_fmt_heading(e.get('heading_path'))}"
                    f"{page_s} — hiệu lực [{e.get('valid_from')} … "
                    f"{e.get('valid_to_exclusive') or '∞'})"
                )
                if e.get("content"):
                    st.caption(e["content"])
        else:
            st.caption("Không có nguồn hợp lệ (hoặc backend chưa trả evidence).")

        excluded = (evidence or {}).get("excluded_evidence") or answer.get("excluded_evidence") or []
        st.markdown("**Nguồn bị loại (và lý do):**")
        if excluded:
            for x in excluded:
                reason = _EXCLUSION_VI.get(x.get("reason"), x.get("reason"))
                st.markdown(
                    f"- ⛔ {_fmt_heading(x.get('heading_path'))} "
                    f"(`{x.get('version_id')}`) — {reason}"
                )
        else:
            st.caption("Không có nguồn nào bị loại.")


# --------------------------------------------------------------------------- #
# pages
# --------------------------------------------------------------------------- #
def page_login() -> None:
    st.header("Đăng nhập")
    api = ApiClient(base_url=st.session_state.get("base_url", DEFAULT_BASE_URL))
    h = api.health()
    if h.ok:
        st.success(f"API sẵn sàng (demo_mode={h.data.get('demo_mode')}).")
    else:
        st.warning("API chưa phản hồi. Bạn vẫn có thể nhập thông tin; sẽ thử lại khi đăng nhập.")
        st.caption(h.error or "")

    with st.form("login"):
        col1, col2 = st.columns(2)
        username = col1.text_input("Tài khoản", value="employee")
        password = col2.text_input("Mật khẩu", value="employee123", type="password")
        submitted = st.form_submit_button("Đăng nhập")
    if submitted:
        res = api.login(username, password)
        if res.ok:
            st.session_state["token"] = res.data.get("token")
            st.session_state["role"] = res.data.get("role")
            st.session_state["username"] = res.data.get("username")
            st.success(f"Xin chào {res.data.get('username')} ({res.data.get('role')})")
            _rerun()
        else:
            st.error(res.error or "Đăng nhập thất bại")


def page_chat() -> None:
    st.header("💬 Hỏi đáp quy định")
    with st.form("chat"):
        text = st.text_input("Câu hỏi", value="Hạn mức tín dụng SME hiện tại là bao nhiêu?")
        qdate = st.text_input("Ngày truy vấn (YYYY-MM-DD, để trống = hôm nay)", value="")
        submitted = st.form_submit_button("Hỏi")
    if not submitted:
        return
    res = _client().query(text, qdate or None)
    if not res.ok:
        _api_down(res)
        return
    data = res.data or {}
    answer = data.get("answer", data)  # QueryResponse{answer, evidence} or bare Answer
    evidence = data.get("evidence")
    render_answer(answer)
    render_why_panel(answer, evidence)


def page_compare() -> None:
    st.header("⚖️ So sánh: Standard RAG vs Hệ thống của chúng tôi")
    with st.form("compare"):
        text = st.text_input("Câu hỏi", value="Hạn mức tín dụng SME hiện tại là bao nhiêu?")
        qdate = st.text_input("Ngày truy vấn (YYYY-MM-DD, để trống = hôm nay)", value="")
        submitted = st.form_submit_button("So sánh")
    if not submitted:
        return
    res = _client().compare(text, qdate or None)
    if not res.ok:
        _api_down(res)
        return
    data = res.data or {}
    left, right = st.columns(2)
    with left:
        st.subheader("Standard RAG")
        render_answer(data.get("standard_rag") or {})
    with right:
        st.subheader("Hệ thống của chúng tôi")
        render_answer(data.get("our_system") or {})


def page_overview() -> None:
    st.header("🏛️ Compliance Regulatory Knowledge & Document Review")
    st.markdown("Hai luồng nghiệp vụ — không file nào mặc định là ground truth:")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📥 Add Regulatory Source")
        st.markdown(
            "Thêm thông tư/quyết định/amendment vào kho pháp lý.\n\n"
            "Tài liệu phải qua **Human Review + Activate** mới trở thành "
            "nguồn pháp lý (AUTHORITY_SOURCE).\n\n"
            "→ Dùng trang **Review inbox** / **Dashboard**."
        )
    with c2:
        st.subheader("🛡️ Check Document Compliance")
        st.markdown(
            "Upload policy/báo cáo nội bộ để kiểm tra với kho quy định **đã duyệt**.\n\n"
            "File chỉ là REVIEW_TARGET — **không** được thêm vào knowledge base.\n\n"
            "→ Dùng trang **Kiểm tra tuân thủ**."
        )


def page_add_source() -> None:
    st.header("📥 Thêm nguồn pháp lý (Add Regulatory Source)")
    st.warning(
        "Tài liệu upload chỉ là ỨNG VIÊN (AUTHORITY_SOURCE_CANDIDATE) — "
        "chưa được dùng làm căn cứ pháp lý. Phải qua Human Review và Activate."
    )
    up = st.file_uploader("Chọn văn bản (.pdf/.txt)", type=["pdf", "txt"])
    dtype = st.selectbox("Loại văn bản", ["REGULATION", "AMENDMENT", "INTERNAL_POLICY"])
    if up is not None and st.button("Upload"):
        res = _client().upload_document(up.name, up.getvalue(), dtype)
        if res.ok:
            doc_id = (res.data or {}).get("document_id", "")
            st.session_state["last_doc_id"] = doc_id
            st.success(f"Đã nhận `{doc_id}` — chờ review (xem Review inbox).")
            st.json(res.data)
        else:
            _api_down(res)
    st.divider() if hasattr(st, "divider") else st.markdown("---")
    doc_id = st.text_input("Document ID cần kích hoạt",
                           value=st.session_state.get("last_doc_id", ""))
    if doc_id and st.button("Activate (qua hard gate)"):
        res = _client().activate_document(doc_id)
        if res.ok:
            st.success("✅ ACTIVE — versioning đã áp dụng, tài liệu vào kho pháp lý.")
            st.json(res.data)
        elif res.status == 409:
            st.error("⛔ HTTP 409 REVIEW_NOT_COMPLETED — còn critical review chưa duyệt. "
                     "Mở Review inbox để Approve trước.")
            st.json(res.data)
        else:
            _api_down(res)


_COMPLIANCE_STYLE = {
    "COMPLIANT": ("✅", "Phù hợp"),
    "NON_COMPLIANT": ("❌", "Không phù hợp"),
    "PARTIALLY_COMPLIANT": ("🟡", "Phù hợp một phần"),
    "OUTDATED_REFERENCE": ("⏳", "Dùng phiên bản đã bị thay thế"),
    "MISSING_EVIDENCE": ("⛔", "Thiếu căn cứ"),
    "AMBIGUOUS": ("❓", "Nhiều quy định có thể áp dụng"),
    "NEEDS_HUMAN_REVIEW": ("👤", "Cần người review"),
}


def page_compliance() -> None:
    st.header("🛡️ Kiểm tra tuân thủ tài liệu (Check Document Compliance)")
    st.info(
        "File này CHỈ được dùng để kiểm tra với kho quy định đã duyệt — "
        "KHÔNG được thêm vào kho tri thức pháp lý (trust class: REVIEW_TARGET)."
    )
    uploaded = st.file_uploader("Tải lên policy/báo cáo (.txt)", type=["txt"])
    default_text = ""
    if uploaded is not None:
        default_text = uploaded.read().decode("utf-8", errors="replace")
    with st.form("compliance"):
        text = st.text_area("Nội dung tài liệu cần kiểm tra", value=default_text, height=200)
        rdate = st.text_input("Ngày review (YYYY-MM-DD, để trống = hôm nay)", value="")
        submitted = st.form_submit_button("Kiểm tra tuân thủ")
    if not submitted or not text.strip():
        return
    res = _client().compliance_check(text, rdate or None,
                                     uploaded.name if uploaded else None)
    if not res.ok:
        _api_down(res)
        return
    check_id = (res.data or {}).get("check_id")
    rep = _client().compliance_report(check_id)
    if not rep.ok:
        _api_down(rep)
        return
    _render_compliance_report(rep.data or {})


def _render_compliance_report(report: Dict[str, Any]) -> None:
    summary = report.get("summary") or {}
    st.subheader("Tổng quan")
    cols = st.columns(4)
    cols[0].metric("Tổng claim", summary.get("total_claims", 0))
    cols[1].metric("✅ Phù hợp", summary.get("compliant", 0))
    cols[2].metric("❌ Không phù hợp / lỗi thời",
                   summary.get("non_compliant", 0) + summary.get("outdated_reference", 0))
    cols[3].metric("⛔ Thiếu căn cứ / cần review",
                   summary.get("missing_evidence", 0) + summary.get("needs_human_review", 0))

    for a in report.get("assessments") or []:
        icon, label = _COMPLIANCE_STYLE.get(a.get("status"), ("•", a.get("status")))
        with st.expander(f"{icon} {label} — {a.get('source_text', '')[:80]}"):
            st.markdown(f"**Claim:** {a.get('source_text')}")
            st.markdown(f"**Giải thích:** {a.get('explanation')}")
            for f in a.get("findings") or []:
                st.markdown(f"- {f}")
            if a.get("recommendation"):
                st.warning(f"Đề xuất sửa: {a['recommendation']}")
            valid = a.get("valid_evidence") or []
            if valid:
                st.markdown("**Căn cứ pháp lý hiện hành:**")
                for e in valid:
                    st.markdown(
                        f"- ✅ `{e.get('document_number')}` {_fmt_heading(e.get('heading_path'))}"
                        f" — hiệu lực [{e.get('valid_from')} … {e.get('valid_to_exclusive') or '∞'})"
                    )
                    if e.get("content"):
                        st.caption(e["content"])
            excluded = a.get("excluded_evidence") or []
            if excluded:
                st.markdown("**Phiên bản bị loại (và lý do):**")
                for x in excluded:
                    reason = _EXCLUSION_VI.get(x.get("reason"), x.get("reason"))
                    st.markdown(f"- ⛔ `{x.get('version_id')}` — {reason}")
            st.caption(f"Confidence: {a.get('confidence')}")


def page_review() -> None:
    st.header("📥 Hộp thư rà soát (Review inbox)")
    status = st.selectbox("Lọc theo trạng thái", ["", "PENDING", "APPROVED", "REJECTED"], index=1)
    res = _client().list_review_tasks(status or None)
    if not res.ok:
        _api_down(res)
        return
    tasks = res.data.get("tasks") if isinstance(res.data, dict) else res.data
    tasks = tasks or []
    if not tasks:
        st.info("Không có nhiệm vụ rà soát.")
        return
    for t in tasks:
        with st.expander(f"{t.get('task_type')} — {t.get('task_id')} "
                         f"(conf={t.get('confidence')})"):
            st.write("Nguồn:", t.get("source_ref"))
            if t.get("diff_before") or t.get("diff_after"):
                c1, c2 = st.columns(2)
                c1.markdown("**Trước:**")
                c1.code(t.get("diff_before") or "")
                c2.markdown("**Sau:**")
                c2.code(t.get("diff_after") or "")
            st.json(t.get("extracted") or {})
            b1, b2, b3 = st.columns(3)
            if b1.button("Duyệt", key=f"ap-{t['task_id']}"):
                _decide(t["task_id"], "APPROVE")
            if b2.button("Sửa & duyệt", key=f"ed-{t['task_id']}"):
                _decide(t["task_id"], "EDIT", edited=t.get("extracted") or {})
            if b3.button("Từ chối", key=f"rj-{t['task_id']}"):
                _decide(t["task_id"], "REJECT")


def _decide(task_id: str, decision: str, edited: Optional[dict] = None) -> None:
    res = _client().decide_review_task(task_id, decision, edited)
    if res.ok:
        st.success(f"Đã {decision} {task_id}")
        _rerun()
    else:
        _api_down(res)


def page_dashboard() -> None:
    st.header("📊 Bảng điều khiển (Dashboard)")
    docs_res = _client().list_documents()
    if not docs_res.ok:
        _api_down(docs_res)
        return
    docs = docs_res.data if isinstance(docs_res.data, list) else (docs_res.data or {}).get("documents", [])
    docs = docs or []

    pending = [d for d in docs if d.get("approval_status") == "PENDING"]
    injections = [d for d in docs if d.get("injection_suspected")]
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng tài liệu", len(docs))
    c2.metric("Chờ duyệt", len(pending))
    c3.metric("Nghi injection", len(injections))

    if injections:
        st.error("⚠️ Cảnh báo prompt-injection ở các tài liệu:")
        for d in injections:
            st.markdown(f"- `{d.get('document_number') or d.get('filename')}`")

    st.subheader("Tài liệu")
    st.dataframe(docs, use_container_width=True) if hasattr(st, "dataframe") else st.write(docs)

    # change events / conflict / stale candidates come through review tasks
    st.subheader("Ứng viên (ChangeEvent / Conflict / Stale)")
    rt = _client().list_review_tasks()
    if rt.ok:
        tasks = rt.data.get("tasks") if isinstance(rt.data, dict) else rt.data
        st.write(tasks or "Không có.")
    else:
        st.caption("Không tải được review tasks.")


def page_graph() -> None:
    st.header("🕸️ Đồ thị tri thức (Knowledge Graph)")
    pid = st.text_input("provision_id", value="prov-qd01-d7k2")
    if not st.button("Tải đồ thị"):
        return
    res = _client().graph_provision(pid)
    if not res.ok:
        _api_down(res)
        return
    data = res.data or {}
    nodes = data.get("nodes") or []
    edges = data.get("edges") or []
    _render_graph(nodes, edges)


def _render_graph(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> None:
    try:
        from streamlit_agraph import agraph, Node, Edge, Config  # type: ignore
    except Exception:
        st.info("streamlit-agraph chưa cài — hiển thị dạng bảng.")
        st.subheader("Nút (nodes)")
        st.write(nodes or "—")
        st.subheader("Cạnh (edges)")
        st.write(edges or "—")
        return
    color = {
        "Document": "#5B8FF9", "Provision": "#5AD8A6", "ProvisionVersion": "#F6BD16",
        "ChangeEvent": "#E8684A", "InternalArtifact": "#9270CA",
    }
    ag_nodes = [Node(id=n["id"], label=n.get("title", n["id"]),
                     color=color.get(n.get("label"), "#999")) for n in nodes]
    ag_edges = [Edge(source=e["source"], target=e["target"], label=e.get("label", ""))
                for e in edges]
    agraph(nodes=ag_nodes, edges=ag_edges,
           config=Config(width=800, height=500, directed=True, physics=True))


def page_audit() -> None:
    st.header("🧾 Nhật ký kiểm toán (Audit)")
    res = _client().audit()
    if not res.ok:
        _api_down(res)
        return
    rows = res.data if isinstance(res.data, list) else (res.data or {}).get("records", [])
    if not rows:
        st.info("Chưa có bản ghi audit.")
        return
    st.dataframe(rows, use_container_width=True) if hasattr(st, "dataframe") else st.write(rows)


# --------------------------------------------------------------------------- #
# shell
# --------------------------------------------------------------------------- #
def _rerun() -> None:
    (getattr(st, "rerun", None) or getattr(st, "experimental_rerun", lambda: None))()


def page_impact_report() -> None:
    st.header("📊 Regulatory Impact Report")
    st.caption("Báo cáo tác động sau khi một nguồn pháp lý được approve + activate (spec §7.8).")
    doc_id = st.text_input("Document ID của văn bản sửa đổi",
                           value=st.session_state.get("last_doc_id", ""))
    if doc_id and st.button("Xem báo cáo"):
        res = _client().impact_report(doc_id)
        if not res.ok:
            _api_down(res)
            return
        rep = res.data or {}
        st.subheader(rep.get("document_number") or doc_id)
        st.info(rep.get("executive_summary", ""))
        if rep.get("max_severity"):
            st.warning(f"Mức ảnh hưởng cao nhất: {rep['max_severity']}")
        for c in rep.get("changes", []):
            with st.expander(
                f"{c.get('operation')} → {c.get('target_document_number')} "
                f"{c.get('target_locator') or ''} (hiệu lực {c.get('effective_date')})"
            ):
                col1, col2 = st.columns(2)
                col1.markdown(f"**Trước:**\n\n{c.get('before_text') or '_—_'}")
                col2.markdown(f"**Sau:**\n\n{c.get('after_text') or '_—_'}")
                st.caption(f"ChangeEvent `{c.get('change_event_id')}` · review: {c.get('review_status')}")
        pols = rep.get("impacted_policies", [])
        if pols:
            st.subheader("Policy nội bộ bị ảnh hưởng")
            for p in pols:
                st.markdown(
                    f"- **{p.get('title')}** — {p.get('reason')} (severity {p.get('severity')}): "
                    f"quy định `{p.get('regulation_value')}` vs policy `{p.get('internal_policy_value')}`"
                )
        else:
            st.success("Không phát hiện policy nội bộ bị ảnh hưởng.")


def page_system_health() -> None:
    st.header("🩺 System Health")
    res = _client().health_details()
    if not res.ok:
        _api_down(res)
        return
    d = res.data or {}
    badge = "🟢" if d.get("status") == "ok" else "🟠"
    st.markdown(f"{badge} **{d.get('status', '?').upper()}** — demo_mode: `{d.get('demo_mode')}`")
    if d.get("error_code"):
        st.error(f"Mã lỗi: {d['error_code']} — backend fallback khi DEMO_MODE=false.")
    for k in ("postgres", "opensearch", "neo4j", "embedding", "llm"):
        st.markdown(f"- **{k}**: `{d.get(k)}`")


_USER_PAGES = {"Hỏi đáp": page_chat, "So sánh": page_compare, "Đồ thị KG": page_graph}
_EMPLOYEE_PAGES = {
    "Tổng quan": page_overview,
    "Thêm nguồn pháp lý": page_add_source,
    "Hỏi đáp": page_chat, "So sánh": page_compare,
    "Kiểm tra tuân thủ": page_compliance, "Review inbox": page_review,
    "Impact Report": page_impact_report,
    "Dashboard": page_dashboard, "Đồ thị KG": page_graph, "Audit": page_audit,
    "System Health": page_system_health,
}


def main() -> None:
    if not _HAS_ST:
        raise RuntimeError("streamlit is not installed: pip install streamlit")
    st.set_page_config(page_title="VAIC2026 SHB1 — Temporal Regulatory RAG", layout="wide")
    st.sidebar.title("VAIC2026 SHB1")
    st.session_state.setdefault("base_url", DEFAULT_BASE_URL)
    st.session_state["base_url"] = st.sidebar.text_input(
        "API_BASE_URL", value=st.session_state["base_url"])

    if not st.session_state.get("token"):
        page_login()
        return

    role = st.session_state.get("role", "EMPLOYEE")
    st.sidebar.success(f"{st.session_state.get('username')} · {role}")
    if st.sidebar.button("Đăng xuất"):
        for k in ("token", "role", "username"):
            st.session_state.pop(k, None)
        _rerun()
        return

    pages = _EMPLOYEE_PAGES if role == "EMPLOYEE" else _USER_PAGES
    choice = st.sidebar.radio("Trang", list(pages.keys()))
    pages[choice]()


if __name__ == "__main__":  # pragma: no cover
    main()
