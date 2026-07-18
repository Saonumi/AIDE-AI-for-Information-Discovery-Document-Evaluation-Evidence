"""VAIC2026 SHB1 — Streamlit UI (Track C): ChatGPT-style regulatory assistant.

Layout
    sidebar : new chat · chat history · employee tools · user card
    main    : message stream, 3 mode buttons above the composer, chat input

Modes (the 3 buttons above the input)
    💬 Hỏi đáp     → POST /query    — one grounded answer
    ⚖️ So sánh RAG → POST /compare  — Standard RAG vs our system, side by side
    🔎 Vì sao      → toggle: show valid + excluded evidence for every answer

Run:  streamlit run frontend/streamlit_app/app.py
Env:  API_BASE_URL (default http://localhost:8000)

The module imports without streamlit installed (guarded) so CI's import smoke test
passes; main() requires streamlit to actually run.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Dict, List, Optional

try:  # installed as a package (docker) or run as a script (dev)
    from frontend.streamlit_app.api_client import ApiClient, DEFAULT_BASE_URL
    from frontend.streamlit_app import theme
except Exception:  # pragma: no cover - path fallback
    from api_client import ApiClient, DEFAULT_BASE_URL  # type: ignore
    import theme  # type: ignore

try:
    import streamlit as st
    _HAS_ST = True
except Exception:  # pragma: no cover - streamlit optional for import
    st = None  # type: ignore
    _HAS_ST = False


APP_TITLE = "SHB Regulatory Assistant"
APP_SUBTITLE = "Trợ lý tra cứu quy định theo thời điểm hiệu lực"

MODES = [
    ("ask", "💬 Hỏi đáp"),
    ("compare", "⚖️ So sánh RAG"),
    ("why", "🔎 Vì sao"),
]

SUGGESTIONS = [
    "Hạn mức tín dụng SME hiện tại là bao nhiêu?",
    "Tỷ lệ dự trữ bắt buộc áp dụng từ 01/01/2025?",
    "Quy định về xác thực sinh trắc học khi chuyển tiền?",
    "Điều kiện cho vay tiêu dùng không tài sản bảo đảm?",
]

_EXCLUSION_VI = {
    "NOT_VALID_AT_QUERY_DATE": "Không hiệu lực tại ngày truy vấn",
    "SUPERSEDED": "Đã bị thay thế (bản cũ)",
    "NOT_APPROVED": "Chưa được phê duyệt",
    "OUT_OF_SCOPE": "Ngoài phạm vi câu hỏi",
}


# --------------------------------------------------------------------------- #
# formatting helpers (pure — unit-testable without streamlit)
# --------------------------------------------------------------------------- #
def fmt_heading(heading_path: Optional[List[str]]) -> str:
    return " › ".join(heading_path) if heading_path else "—"


def status_badge_html(status: Optional[str]) -> str:
    colour, icon, label = theme.status_parts(status)
    return f'<span class="shb-badge" style="color:{colour}">{icon} {label}</span>'


def conversation_title(text: str, limit: int = 38) -> str:
    """First line of the question, trimmed — used as the history entry label."""
    clean = " ".join((text or "").split())
    if not clean:
        return "Cuộc trò chuyện mới"
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"


def initials(name: Optional[str]) -> str:
    parts = [p for p in (name or "?").replace("_", " ").split() if p]
    if not parts:
        return "?"
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


# --------------------------------------------------------------------------- #
# session / conversation state
# --------------------------------------------------------------------------- #
def _rerun() -> None:
    (getattr(st, "rerun", None) or getattr(st, "experimental_rerun", lambda: None))()


def _client() -> ApiClient:
    return ApiClient(
        base_url=st.session_state.get("base_url", DEFAULT_BASE_URL),
        token=st.session_state.get("token"),
    )


def _api_down(res: Any) -> None:
    st.error("Không gọi được API. Kiểm tra backend đang chạy và API_BASE_URL đúng.")
    if getattr(res, "error", None):
        st.caption(res.error)


def bootstrap_state() -> None:
    ss = st.session_state
    ss.setdefault("base_url", DEFAULT_BASE_URL)
    ss.setdefault("conversations", {})   # cid -> {title, messages: [...]}
    ss.setdefault("order", [])           # cid list, most recent first
    ss.setdefault("active_cid", None)
    ss.setdefault("mode", "ask")
    ss.setdefault("show_why", False)
    ss.setdefault("query_date", "")
    ss.setdefault("tool_page", None)
    ss.setdefault("pending", None)       # question queued from a suggestion chip
    if ss["active_cid"] is None:
        new_conversation()


def new_conversation() -> str:
    cid = uuid.uuid4().hex[:12]
    st.session_state["conversations"][cid] = {"title": "Cuộc trò chuyện mới", "messages": []}
    st.session_state["order"].insert(0, cid)
    st.session_state["active_cid"] = cid
    st.session_state["tool_page"] = None
    return cid


def active_conversation() -> Dict[str, Any]:
    ss = st.session_state
    cid = ss.get("active_cid")
    if cid not in ss["conversations"]:
        cid = new_conversation()
    return ss["conversations"][cid]


def append_message(role: str, content: str, **meta: Any) -> None:
    convo = active_conversation()
    convo["messages"].append({"role": role, "content": content, **meta})
    if role == "user" and convo["title"] == "Cuộc trò chuyện mới":
        convo["title"] = conversation_title(content)


# --------------------------------------------------------------------------- #
# answer rendering
# --------------------------------------------------------------------------- #
def render_answer(answer: Dict[str, Any], *, compact: bool = False) -> None:
    """One assistant answer: status badge, text, citations, timeline, warnings."""
    st.markdown(
        f'<div class="shb-card">{status_badge_html(answer.get("status"))}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(answer.get("text") or "_(không có nội dung)_")

    citations = answer.get("citations") or []
    if citations:
        st.markdown('<div class="shb-sec">Trích dẫn</div>', unsafe_allow_html=True)
        for c in citations:
            page = c.get("page")
            page_s = f" · trang {page}" if page is not None else ""
            st.markdown(
                f'<div class="shb-cite"><b>{c.get("document_number") or "?"}</b> — '
                f'{fmt_heading(c.get("heading_path"))}<small>{page_s}</small></div>',
                unsafe_allow_html=True,
            )

    timeline = answer.get("timeline") or []
    if timeline and not compact:
        st.markdown('<div class="shb-sec">Dòng thời gian hiệu lực</div>', unsafe_allow_html=True)
        for t in timeline:
            st.markdown(
                f'<span class="shb-chip">{t.get("operation") or "CHANGE"}</span> '
                f'`{t.get("before_version_id")}` → `{t.get("after_version_id")}`',
                unsafe_allow_html=True,
            )

    for c in answer.get("conflict_candidates") or []:
        st.warning(
            f"⚠️ Xung đột: {c.get('reason')} — {c.get('value_a')} ↔ {c.get('value_b')} "
            f"({c.get('provision_a')} vs {c.get('provision_b')})"
        )
    for i in answer.get("impact_candidates") or []:
        st.warning(
            f"⚠️ Chính sách nội bộ có thể lỗi thời — {i.get('artifact_title')}: "
            f"nội bộ {i.get('internal_policy_value')} vs quy định {i.get('regulation_value')}"
        )


def render_why_panel(answer: Dict[str, Any], evidence: Optional[Dict[str, Any]]) -> None:
    """Valid sources used AND excluded sources with the reason they were dropped."""
    with st.expander("🔎 Vì sao câu trả lời này", expanded=False):
        valid = (evidence or {}).get("valid_evidence") or []
        st.markdown('<div class="shb-sec">Nguồn hợp lệ được dùng</div>', unsafe_allow_html=True)
        if valid:
            for e in valid:
                page = e.get("page")
                page_s = f" · trang {page}" if page is not None else ""
                st.markdown(
                    f'<div class="shb-cite">✅ <b>{e.get("document_number")}</b> '
                    f'{fmt_heading(e.get("heading_path"))}<small>{page_s} · hiệu lực '
                    f'[{e.get("valid_from")} … {e.get("valid_to_exclusive") or "∞"})</small></div>',
                    unsafe_allow_html=True,
                )
                if e.get("content"):
                    st.caption(e["content"])
        else:
            st.caption("Không có nguồn hợp lệ (hoặc backend chưa trả evidence).")

        excluded = (evidence or {}).get("excluded_evidence") or answer.get("excluded_evidence") or []
        st.markdown('<div class="shb-sec">Nguồn bị loại &amp; lý do</div>', unsafe_allow_html=True)
        if excluded:
            for x in excluded:
                reason = _EXCLUSION_VI.get(x.get("reason"), x.get("reason"))
                st.markdown(
                    f'<div class="shb-cite" style="border-left-color:{theme.SHB_RED}">⛔ '
                    f'{fmt_heading(x.get("heading_path"))} <small>({x.get("version_id")}) — '
                    f'{reason}</small></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Không có nguồn nào bị loại.")


def render_assistant_message(msg: Dict[str, Any]) -> None:
    """Replay a stored assistant turn (answer, compare pair, or a failed call)."""
    if msg.get("kind") == "error":
        st.error("Không gọi được API. Kiểm tra backend đang chạy và API_BASE_URL đúng.")
        if msg.get("error"):
            st.caption(msg["error"])
        return
    if msg.get("kind") == "compare":
        left, right = st.columns(2)
        with left:
            st.markdown("**Standard RAG** (đối chứng)")
            render_answer(msg.get("standard_rag") or {}, compact=True)
        with right:
            st.markdown("**Hệ thống của chúng tôi**")
            render_answer(msg.get("our_system") or {}, compact=True)
        return
    answer = msg.get("answer") or {}
    render_answer(answer)
    if st.session_state.get("show_why"):
        render_why_panel(answer, msg.get("evidence"))


# --------------------------------------------------------------------------- #
# sidebar
# --------------------------------------------------------------------------- #
def render_sidebar() -> None:
    ss = st.session_state
    with st.sidebar:
        st.markdown(
            '<div class="shb-brand">'
            '<div class="shb-brand-mark">SHB</div>'
            f'<div class="shb-brand-text"><b>{APP_TITLE}</b><br>'
            '<span>Temporal Regulatory RAG</span></div></div>',
            unsafe_allow_html=True,
        )

        if st.button("＋  Cuộc trò chuyện mới", key="new_chat", type="primary"):
            new_conversation()
            _rerun()

        # ---- chat history -------------------------------------------------
        st.markdown('<div class="shb-side-label">Lịch sử đoạn chat</div>', unsafe_allow_html=True)
        visible = [c for c in ss["order"] if (ss["conversations"].get(c) or {}).get("messages")]
        if not visible:
            st.caption("Chưa có cuộc trò chuyện nào.")
        for cid in visible:
            convo = ss["conversations"][cid]
            marker = "•  " if cid == ss["active_cid"] and not ss["tool_page"] else "　"
            if st.button(f"{marker}{convo['title']}", key=f"conv-{cid}"):
                ss["active_cid"] = cid
                ss["tool_page"] = None
                _rerun()

        # ---- employee tools ------------------------------------------------
        role = ss.get("role", "USER")
        tools = {"Đồ thị tri thức": "graph"}
        if role == "EMPLOYEE":
            tools = {
                "Hộp thư rà soát": "review",
                "Bảng điều khiển": "dashboard",
                "Đồ thị tri thức": "graph",
                "Nhật ký kiểm toán": "audit",
            }
        st.markdown('<div class="shb-side-label">Công cụ</div>', unsafe_allow_html=True)
        for label, key in tools.items():
            if st.button(label, key=f"tool-{key}"):
                ss["tool_page"] = key
                _rerun()

        # ---- profile: identity + settings + logout in one account menu ------
        st.markdown('<div class="shb-side-label">Thông tin người dùng</div>', unsafe_allow_html=True)
        render_profile()


def render_profile() -> None:
    """The account menu: click the user row to reveal settings and logout.

    Settings live here (not in a separate panel) so the sidebar has exactly one
    place for "everything about me": who I am, how I query, how I disconnect.
    """
    ss = st.session_state
    username = ss.get("username", "khách")
    role = ss.get("role", "USER")

    with st.expander(f"{username}  ·  {role}", expanded=False):
        st.markdown(
            f'<div class="shb-user"><div class="shb-avatar">{initials(username)}</div>'
            f'<div class="shb-user-meta"><b>{username}</b><br><span>{role}</span></div></div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="shb-side-label">Tuỳ chọn truy vấn</div>', unsafe_allow_html=True)
        ss["query_date"] = st.text_input(
            "Ngày truy vấn (YYYY-MM-DD)",
            value=ss["query_date"],
            placeholder=str(date.today()),
            help="Để trống = hôm nay. Bộ lọc thời gian chạy TRƯỚC khi truy hồi top-k.",
        )
        # "Vì sao" is owned by the 🔎 button above the composer — shown here read-only
        # so two widgets never fight over the same session_state key.
        st.caption(f"Panel 'Vì sao': {'đang bật' if ss['show_why'] else 'đang tắt'} "
                   "(đổi bằng nút 🔎 phía trên ô chat)")

        st.markdown('<div class="shb-side-label">Kết nối</div>', unsafe_allow_html=True)
        ss["base_url"] = st.text_input("API_BASE_URL", value=ss["base_url"])
        health = _client().health()
        if health.ok:
            st.caption(f"✅ API sẵn sàng · demo_mode={(health.data or {}).get('demo_mode')}")
        else:
            st.caption("⛔ Không kết nối được API")

        if st.button("Đăng xuất", key="logout"):
            for k in ("token", "role", "username"):
                ss.pop(k, None)
            _rerun()


# --------------------------------------------------------------------------- #
# composer: the 3 mode buttons + the chat input
# --------------------------------------------------------------------------- #
def render_composer() -> Optional[str]:
    """Draw the mode toolbar, then the chat input. Returns the submitted text."""
    ss = st.session_state
    st.markdown('<div class="shb-modes">', unsafe_allow_html=True)
    cols = st.columns(len(MODES))
    for col, (key, label) in zip(cols, MODES):
        selected = ss["show_why"] if key == "why" else ss["mode"] == key
        if col.button(label, key=f"mode-{key}", type="primary" if selected else "secondary"):
            if key == "why":
                ss["show_why"] = not ss["show_why"]
            else:
                ss["mode"] = key
            _rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    placeholder = (
        "Nhập câu hỏi để so sánh 2 hệ thống…"
        if ss["mode"] == "compare"
        else "Hỏi về quy định, hạn mức, điều kiện…"
    )
    typed = st.chat_input(placeholder)
    qdate = ss["query_date"] or "hôm nay"
    st.markdown(
        f'<div class="shb-disclaimer">Ngày truy vấn: <b>{qdate}</b> · '
        "Mọi câu trả lời đều kèm trích dẫn truy vết được về văn bản gốc.</div>",
        unsafe_allow_html=True,
    )
    return typed


def render_hero() -> None:
    st.markdown(
        '<div class="shb-hero"><div class="shb-hero-mark">SHB</div>'
        f"<h1>{APP_TITLE}</h1><p>{APP_SUBTITLE}</p></div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, s in enumerate(SUGGESTIONS):
        if cols[i % 2].button(s, key=f"sug-{i}"):
            st.session_state["pending"] = s
            _rerun()


# --------------------------------------------------------------------------- #
# chat page
# --------------------------------------------------------------------------- #
def page_chat() -> None:
    convo = active_conversation()
    messages: List[Dict[str, Any]] = convo["messages"]

    if not messages:
        render_hero()
    for msg in messages:
        with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🏦"):
            if msg["role"] == "user":
                st.markdown(msg["content"])
            else:
                render_assistant_message(msg)

    typed = render_composer()
    question = st.session_state.pop("pending", None) or typed
    if not question:
        return

    append_message("user", question)
    with st.chat_message("user", avatar="🧑"):
        st.markdown(question)

    mode = st.session_state["mode"]
    qdate = st.session_state["query_date"] or None
    api = _client()
    with st.spinner("Đang truy hồi và kiểm tra hiệu lực…"):
        res = api.compare(question, qdate) if mode == "compare" else api.query(question, qdate)

    if not res.ok:
        # keep the failure in the thread so the user sees what went wrong on replay
        convo["messages"].append(
            {"role": "assistant", "content": "", "kind": "error", "error": res.error}
        )
    elif mode == "compare":
        data = res.data or {}
        convo["messages"].append({
            "role": "assistant", "content": "", "kind": "compare",
            "standard_rag": data.get("standard_rag") or {},
            "our_system": data.get("our_system") or {},
        })
    else:
        data = res.data or {}
        convo["messages"].append({
            "role": "assistant", "content": "", "kind": "answer",
            "answer": data.get("answer", data), "evidence": data.get("evidence"),
        })

    # rerun so the sidebar title and the full thread re-render in one consistent pass
    _rerun()


# --------------------------------------------------------------------------- #
# employee tool pages
# --------------------------------------------------------------------------- #
def _tool_header(title: str, subtitle: str) -> None:
    st.markdown(f"### {title}")
    st.caption(subtitle)
    if st.button("← Quay lại trò chuyện", key="back-to-chat"):
        st.session_state["tool_page"] = None
        _rerun()


def page_review() -> None:
    _tool_header("📥 Hộp thư rà soát", "Không tài liệu nào vào truy hồi trước khi nhân viên duyệt.")
    status = st.selectbox("Trạng thái", ["PENDING", "APPROVED", "REJECTED", ""], index=0)
    res = _client().list_review_tasks(status or None)
    if not res.ok:
        return _api_down(res)
    tasks = res.data.get("tasks") if isinstance(res.data, dict) else res.data
    if not tasks:
        st.info("Không có nhiệm vụ rà soát.")
        return
    for t in tasks:
        with st.expander(f"{t.get('task_type')} — {t.get('task_id')} (conf={t.get('confidence')})"):
            st.write("Nguồn:", t.get("source_ref"))
            if t.get("diff_before") or t.get("diff_after"):
                c1, c2 = st.columns(2)
                c1.markdown("**Trước**")
                c1.code(t.get("diff_before") or "")
                c2.markdown("**Sau**")
                c2.code(t.get("diff_after") or "")
            st.json(t.get("extracted") or {})
            b1, b2, b3 = st.columns(3)
            if b1.button("Duyệt", key=f"ap-{t['task_id']}", type="primary"):
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
    _tool_header("📊 Bảng điều khiển", "Tình trạng kho tài liệu và các cảnh báo cần xử lý.")
    res = _client().list_documents()
    if not res.ok:
        return _api_down(res)
    docs = res.data if isinstance(res.data, list) else (res.data or {}).get("documents", [])
    docs = docs or []
    pending = [d for d in docs if d.get("approval_status") == "PENDING"]
    injections = [d for d in docs if d.get("injection_suspected")]
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng tài liệu", len(docs))
    c2.metric("Chờ duyệt", len(pending))
    c3.metric("Nghi prompt-injection", len(injections))
    if injections:
        st.error("⚠️ Cảnh báo prompt-injection:")
        for d in injections:
            st.markdown(f"- `{d.get('document_number') or d.get('filename')}`")
    st.markdown('<div class="shb-sec">Tài liệu</div>', unsafe_allow_html=True)
    st.dataframe(docs, use_container_width=True)


def page_graph() -> None:
    _tool_header("🕸️ Đồ thị tri thức", "Điều khoản, phiên bản và các sự kiện sửa đổi liên quan.")
    pid = st.text_input("provision_id", value="prov-qd01-d7k2")
    if not st.button("Tải đồ thị", type="primary"):
        return
    res = _client().graph_provision(pid)
    if not res.ok:
        return _api_down(res)
    data = res.data or {}
    _render_graph(data.get("nodes") or [], data.get("edges") or [])


def _render_graph(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> None:
    try:
        from streamlit_agraph import agraph, Node, Edge, Config  # type: ignore
    except Exception:
        st.info("streamlit-agraph chưa cài — hiển thị dạng bảng.")
        st.write(nodes or "—")
        st.write(edges or "—")
        return
    colour = {
        "Document": theme.SHB_NAVY, "Provision": theme.SHB_ORANGE,
        "ProvisionVersion": "#F6BD16", "ChangeEvent": theme.SHB_RED,
        "InternalArtifact": "#9270CA",
    }
    ag_nodes = [Node(id=n["id"], label=n.get("title", n["id"]),
                     color=colour.get(n.get("label"), "#999")) for n in nodes]
    ag_edges = [Edge(source=e["source"], target=e["target"], label=e.get("label", ""))
                for e in edges]
    agraph(nodes=ag_nodes, edges=ag_edges,
           config=Config(width=800, height=520, directed=True, physics=True))


def page_audit() -> None:
    _tool_header("🧾 Nhật ký kiểm toán", "Mọi truy vấn và quyết định duyệt đều được ghi lại.")
    res = _client().audit()
    if not res.ok:
        return _api_down(res)
    rows = res.data if isinstance(res.data, list) else (res.data or {}).get("records", [])
    if not rows:
        st.info("Chưa có bản ghi audit.")
        return
    st.dataframe(rows, use_container_width=True)


_TOOL_PAGES = {
    "review": page_review, "dashboard": page_dashboard,
    "graph": page_graph, "audit": page_audit,
}


# --------------------------------------------------------------------------- #
# login
# --------------------------------------------------------------------------- #
def page_login() -> None:
    st.markdown(
        '<div class="shb-hero"><div class="shb-hero-mark">SHB</div>'
        f"<h1>{APP_TITLE}</h1><p>{APP_SUBTITLE}</p></div>",
        unsafe_allow_html=True,
    )
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        api = ApiClient(base_url=st.session_state.get("base_url", DEFAULT_BASE_URL))
        h = api.health()
        if h.ok:
            st.success(f"API sẵn sàng (demo_mode={h.data.get('demo_mode')}).")
        else:
            st.warning("API chưa phản hồi — vẫn có thể thử đăng nhập.")

        with st.form("login"):
            username = st.text_input("Tài khoản", value="employee")
            password = st.text_input("Mật khẩu", value="employee123", type="password")
            st.caption("Demo: employee / employee123 (EMPLOYEE) · user / user123 (USER)")
            submitted = st.form_submit_button("Đăng nhập", type="primary", use_container_width=True)
        if submitted:
            res = api.login(username, password)
            if res.ok:
                st.session_state["token"] = res.data.get("token")
                st.session_state["role"] = res.data.get("role")
                st.session_state["username"] = res.data.get("username")
                _rerun()
            else:
                st.error(res.error or "Đăng nhập thất bại")


# --------------------------------------------------------------------------- #
# shell
# --------------------------------------------------------------------------- #
def main() -> None:
    if not _HAS_ST:
        raise RuntimeError("streamlit is not installed: pip install streamlit")
    st.set_page_config(page_title=APP_TITLE, page_icon="🏦", layout="wide",
                       initial_sidebar_state="expanded")
    st.markdown(theme.css(), unsafe_allow_html=True)
    bootstrap_state()

    if not st.session_state.get("token"):
        page_login()
        return

    render_sidebar()
    tool = st.session_state.get("tool_page")
    (_TOOL_PAGES[tool] if tool in _TOOL_PAGES else page_chat)()


if __name__ == "__main__":  # pragma: no cover
    main()
