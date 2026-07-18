/* Bootstrap + router + page controllers for the SHB1 front-end SPA. */
(function () {
  const api = APP.api, ui = APP.ui, L = APP.labels;
  const $ = (sel, root) => (root || document).querySelector(sel);

  // --------------------------------------------------------------------- //
  // Navigation registry (role-aware)
  // --------------------------------------------------------------------- //
  const PAGES = {
    query:    { title: "Hỏi đáp quy định", sub: "Trả lời có trích dẫn, đúng theo hiệu lực thời gian", ico: "💬", roles: ["USER", "EMPLOYEE"], render: pageQuery },
    compare:  { title: "So sánh hệ thống", sub: "Standard RAG vs Hệ thống Temporal/Graph", ico: "⚖️", roles: ["USER", "EMPLOYEE"], render: pageCompare },
    graph:    { title: "Đồ thị tri thức", sub: "Trực quan hoá điều khoản, phiên bản & sửa đổi", ico: "🕸️", roles: ["USER", "EMPLOYEE"], render: pageGraph },
    review:   { title: "Hộp thư rà soát", sub: "Duyệt bóc tách, sửa đổi, xung đột trước khi kích hoạt", ico: "📥", roles: ["EMPLOYEE"], render: pageReview },
    documents:{ title: "Tài liệu & Nạp dữ liệu", sub: "Tải lên, theo dõi trạng thái, kích hoạt tài liệu", ico: "📚", roles: ["EMPLOYEE"], render: pageDocuments },
    audit:    { title: "Nhật ký kiểm toán", sub: "Truy vết mọi câu trả lời & nguồn đã dùng", ico: "🧾", roles: ["EMPLOYEE"], render: pageAudit },
  };
  const NAV_ORDER = ["query", "compare", "graph", "review", "documents", "audit"];

  let current = "query";

  // --------------------------------------------------------------------- //
  // Boot
  // --------------------------------------------------------------------- //
  function boot() {
    // prefill api base
    $("#login-apibase").value = api.getApiBase();
    wireLogin();
    checkHealth();

    const s = api.session();
    if (s.token && s.role) enterApp();
    else showLogin();
  }

  function showLogin() {
    $("#login-view").classList.remove("hidden");
    $("#app-view").classList.add("hidden");
  }

  async function checkHealth() {
    const pill = $("#health-pill"), dot = $(".hp-dot", pill), txt = $(".hp-text", pill);
    const res = await api.health();
    pill.className = "health-pill " + (res.ok ? "health-ok" : "health-down");
    txt.textContent = res.ok
      ? `API sẵn sàng${res.data && res.data.demo_mode ? " · demo_mode" : ""}`
      : "API chưa phản hồi";
  }

  // --------------------------------------------------------------------- //
  // Login
  // --------------------------------------------------------------------- //
  function wireLogin() {
    const form = $("#login-form");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = $(".btn-primary", form);
      const errBox = $("#login-error");
      errBox.classList.add("hidden");
      api.setApiBase($("#login-apibase").value);
      btn.classList.add("loading"); btn.disabled = true;
      const res = await api.login($("#login-username").value.trim(), $("#login-password").value);
      btn.classList.remove("loading"); btn.disabled = false;
      if (res.ok) {
        enterApp();
        ui.toast(`Xin chào ${res.data.username} (${res.data.role})`, "ok");
      } else {
        errBox.textContent = res.error || "Đăng nhập thất bại";
        errBox.classList.remove("hidden");
      }
    });

    document.querySelectorAll(".demo-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        $("#login-username").value = chip.dataset.user;
        $("#login-password").value = chip.dataset.pass;
      });
    });
  }

  // --------------------------------------------------------------------- //
  // App shell
  // --------------------------------------------------------------------- //
  function enterApp() {
    const s = api.session();
    $("#login-view").classList.add("hidden");
    $("#app-view").classList.remove("hidden");

    $("#user-name").textContent = s.username || "—";
    $("#user-role").textContent = s.role === "EMPLOYEE" ? "Nhân viên" : "Người dùng";
    $("#user-avatar").textContent = (s.username || "?").slice(0, 1).toUpperCase();
    $("#api-badge").textContent = "🔗 " + api.getApiBase();

    buildNav(s.role);
    $("#logout-btn").onclick = () => {
      api.logout();
      location.reload();
    };
    $("#menu-toggle").onclick = () => $(".sidebar").classList.toggle("open");

    // default page valid for role
    if (!PAGES[current] || !PAGES[current].roles.includes(s.role)) current = "query";
    navigate(current);
  }

  function buildNav(role) {
    const nav = $("#nav");
    nav.innerHTML = "";
    for (const key of NAV_ORDER) {
      const p = PAGES[key];
      if (!p.roles.includes(role)) continue;
      const item = ui.el(
        `<div class="nav-item" data-page="${key}">
           <span class="nav-ico">${p.ico}</span><span>${p.title}</span>
         </div>`);
      item.addEventListener("click", () => { navigate(key); $(".sidebar").classList.remove("open"); });
      nav.appendChild(item);
    }
  }

  function navigate(key) {
    current = key;
    const p = PAGES[key];
    document.querySelectorAll(".nav-item").forEach((n) => n.classList.toggle("active", n.dataset.page === key));
    $("#page-title").textContent = p.title;
    $("#page-subtitle").textContent = p.sub;
    const c = $("#page-container");
    c.innerHTML = "";
    p.render(c);
  }

  // ===================================================================== //
  //  PAGE: Query
  // ===================================================================== //
  function pageQuery(root) {
    const form = ui.el(`
      <div class="card card-pad">
        <div class="card-head"><h3>Đặt câu hỏi về quy định</h3>
          <span class="sub">Để trống ngày = hôm nay</span></div>
        <div class="row">
          <div class="grow"><label class="field"><span>Câu hỏi</span>
            <input id="q-text" type="text" value="Hạn mức tín dụng SME hiện tại là bao nhiêu?" /></label></div>
          <label class="field"><span>Ngày truy vấn</span>
            <input id="q-date" type="date" /></label>
          <button id="q-submit" class="btn btn-primary"><span class="btn-label">Hỏi</span></button>
        </div>
        <div class="q-chips" id="q-chips"></div>
      </div>`);
    root.appendChild(form);

    const result = ui.el(`<div id="q-result"></div>`);
    root.appendChild(result);

    // sample chips
    const chips = $("#q-chips", form);
    APP.sampleQuestions.forEach((sq) => {
      const chip = ui.el(`<span class="q-chip">${ui.esc(sq.q.length > 60 ? sq.q.slice(0, 58) + "…" : sq.q)}</span>`);
      chip.title = sq.q;
      chip.addEventListener("click", () => {
        $("#q-text", form).value = sq.q;
        $("#q-date", form).value = sq.d || "";
        runQuery();
      });
      chips.appendChild(chip);
    });

    async function runQuery() {
      const text = $("#q-text", form).value.trim();
      if (!text) return;
      const date = $("#q-date", form).value;
      const btn = $("#q-submit", form);
      btn.classList.add("loading"); btn.disabled = true;
      result.innerHTML = `<div class="card card-pad">${ui.spinner()}</div>`;
      const res = await api.query(text, date || null);
      btn.classList.remove("loading"); btn.disabled = false;

      if (!res.ok) { result.innerHTML = ui.apiErrorCard(res); return; }
      const data = res.data || {};
      const answer = data.answer || data;
      const evidence = data.evidence;
      result.innerHTML = "";
      const ansCard = ui.el(`<div class="card card-pad"><div class="card-head"><h3>Câu trả lời</h3></div><div id="ans"></div></div>`);
      $("#ans", ansCard).innerHTML = ui.renderAnswer(answer);
      result.appendChild(ansCard);

      const whyCard = ui.el(`<div class="card card-pad"><div class="card-head"><h3>🔎 Vì sao câu trả lời này</h3><span class="sub">Nguồn hợp lệ & nguồn bị loại</span></div><div id="why"></div></div>`);
      $("#why", whyCard).innerHTML = ui.renderWhyPanel(answer, evidence);
      result.appendChild(whyCard);
    }

    $("#q-submit", form).addEventListener("click", runQuery);
    $("#q-text", form).addEventListener("keydown", (e) => { if (e.key === "Enter") runQuery(); });
    runQuery();
  }

  // ===================================================================== //
  //  PAGE: Compare
  // ===================================================================== //
  function pageCompare(root) {
    const form = ui.el(`
      <div class="card card-pad">
        <div class="card-head"><h3>So sánh head-to-head</h3>
          <span class="sub">Chứng minh giá trị: Standard RAG trả lời sai theo thời gian</span></div>
        <div class="row">
          <div class="grow"><label class="field"><span>Câu hỏi</span>
            <input id="c-text" type="text" value="Hạn mức tín dụng SME hiện tại là bao nhiêu?" /></label></div>
          <label class="field"><span>Ngày truy vấn</span><input id="c-date" type="date" /></label>
          <button id="c-submit" class="btn btn-primary"><span class="btn-label">So sánh</span></button>
        </div>
      </div>`);
    root.appendChild(form);
    const result = ui.el(`<div id="c-result"></div>`);
    root.appendChild(result);

    async function run() {
      const text = $("#c-text", form).value.trim();
      if (!text) return;
      const date = $("#c-date", form).value;
      const btn = $("#c-submit", form);
      btn.classList.add("loading"); btn.disabled = true;
      result.innerHTML = `<div class="card card-pad">${ui.spinner()}</div>`;
      const res = await api.compare(text, date || null);
      btn.classList.remove("loading"); btn.disabled = false;
      if (!res.ok) { result.innerHTML = ui.apiErrorCard(res); return; }
      const d = res.data || {};
      result.innerHTML = `
        <div class="compare-grid">
          <div class="card card-pad compare-col baseline">
            <div class="compare-head"><span class="badge tag-baseline">Standard RAG</span><h3>Chỉ vector, không temporal</h3></div>
            <div id="cmp-std"></div>
          </div>
          <div class="card card-pad compare-col ours">
            <div class="compare-head"><span class="badge tag-ours">Hệ thống của chúng tôi</span><h3>Temporal + Graph + kiểm tra</h3></div>
            <div id="cmp-ours"></div>
          </div>
        </div>`;
      $("#cmp-std", result).innerHTML = ui.renderAnswer(d.standard_rag || {});
      $("#cmp-ours", result).innerHTML = ui.renderAnswer(d.our_system || {});
    }
    $("#c-submit", form).addEventListener("click", run);
    run();
  }

  // ===================================================================== //
  //  PAGE: Graph
  // ===================================================================== //
  function pageGraph(root) {
    const form = ui.el(`
      <div class="card card-pad">
        <div class="card-head"><h3>Đồ thị tri thức theo điều khoản</h3>
          <span class="sub">Nhập provision_id để xem subgraph</span></div>
        <div class="row">
          <div class="grow"><label class="field"><span>provision_id</span>
            <input id="g-id" type="text" value="${ui.esc(APP.demoProvisionId)}" /></label></div>
          <button id="g-submit" class="btn btn-primary"><span class="btn-label">Tải đồ thị</span></button>
        </div>
        <div class="q-chips"><span class="q-chip" data-id="prov-qd01-d7k2">prov-qd01-d7k2 (hạn mức SME)</span>
          <span class="q-chip" data-id="prov-qd01-d7k3">prov-qd01-d7k3 (tham chiếu)</span>
          <span class="q-chip" data-id="prov-qd03-d5">prov-qd03-d5 (xung đột)</span></div>
      </div>`);
    root.appendChild(form);
    const holder = ui.el(`<div class="card card-pad"><div id="g-holder"></div></div>`);
    root.appendChild(holder);

    form.querySelectorAll(".q-chip").forEach((c) =>
      c.addEventListener("click", () => { $("#g-id", form).value = c.dataset.id; run(); }));

    async function run() {
      const id = $("#g-id", form).value.trim();
      if (!id) return;
      const btn = $("#g-submit", form);
      btn.classList.add("loading"); btn.disabled = true;
      const holderEl = $("#g-holder", holder);
      holderEl.innerHTML = ui.spinner();
      const res = await api.graphProvision(id);
      btn.classList.remove("loading"); btn.disabled = false;
      if (!res.ok) { holderEl.innerHTML = ui.apiErrorCard(res).replace(/^<div class="card card-pad">|<\/div>$/g, ""); return; }
      APP.graph.render(holderEl, res.data || {});
    }
    $("#g-submit", form).addEventListener("click", run);
    run();
  }

  // ===================================================================== //
  //  PAGE: Review inbox
  // ===================================================================== //
  function pageReview(root) {
    const bar = ui.el(`
      <div class="card card-pad">
        <div class="spread">
          <div class="card-head" style="margin:0"><h3>Nhiệm vụ chờ rà soát</h3></div>
          <label class="field inline"><span>Trạng thái</span>
            <select id="rv-status" style="width:auto">
              <option value="PENDING">Chờ duyệt</option>
              <option value="">Tất cả</option>
              <option value="APPROVED">Đã duyệt</option>
              <option value="REJECTED">Từ chối</option>
            </select></label>
        </div>
      </div>`);
    root.appendChild(bar);
    const list = ui.el(`<div id="rv-list"></div>`);
    root.appendChild(list);

    $("#rv-status", bar).addEventListener("change", load);

    async function load() {
      list.innerHTML = `<div class="card card-pad">${ui.spinner()}</div>`;
      const res = await api.listReviewTasks($("#rv-status", bar).value || null);
      if (!res.ok) { list.innerHTML = ui.apiErrorCard(res); return; }
      const tasks = (res.data && res.data.tasks) || (Array.isArray(res.data) ? res.data : []) || [];
      if (!tasks.length) { list.innerHTML = `<div class="card card-pad">${ui.empty("✅", "Không có nhiệm vụ rà soát", "Hộp thư đang trống.")}</div>`; return; }
      list.innerHTML = "";
      tasks.forEach((t) => list.appendChild(renderTask(t)));
    }

    function renderTask(t) {
      const typeLabel = L.reviewType[t.task_type] || t.task_type;
      const stLabel = L.reviewStatus[t.status] || t.status;
      const stCls = t.status === "APPROVED" ? "ok" : t.status === "REJECTED" ? "bad" : "warn";
      const node = ui.el(`
        <div class="review-task">
          <div class="rt-head">
            <div class="rt-title">
              <span class="badge info">${ui.esc(typeLabel)}</span>
              <strong>${ui.esc(t.source_ref || t.task_id)}</strong>
              <span class="badge neutral">conf ${ui.esc((t.confidence ?? 1).toFixed ? (t.confidence).toFixed(2) : t.confidence)}</span>
            </div>
            <span class="badge ${stCls}">${ui.esc(stLabel)}</span>
          </div>
          <div class="rt-body hidden"></div>
        </div>`);
      const head = $(".rt-head", node), body = $(".rt-body", node);
      head.addEventListener("click", () => {
        body.classList.toggle("hidden");
        if (!body.dataset.filled) { fillBody(body, t); body.dataset.filled = "1"; }
      });
      return node;
    }

    function fillBody(body, t) {
      const parts = [];
      if (t.document_id) parts.push(`<div class="muted" style="margin-top:12px">Tài liệu: <code>${ui.esc(t.document_id)}</code></div>`);
      if (t.diff_before || t.diff_after) {
        parts.push(`<div class="diff-grid">
          <div class="diff-box diff-before"><div class="diff-label">Trước</div><pre>${ui.esc(t.diff_before || "—")}</pre></div>
          <div class="diff-box diff-after"><div class="diff-label">Sau</div><pre>${ui.esc(t.diff_after || "—")}</pre></div>
        </div>`);
      }
      parts.push(`<div class="section-label">Dữ liệu bóc tách</div>`);
      parts.push(`<pre class="json-view" id="jv-${ui.esc(t.task_id)}">${ui.esc(JSON.stringify(t.extracted || {}, null, 2))}</pre>`);
      body.innerHTML = parts.join("");

      if (t.status === "PENDING") {
        const actions = ui.el(`<div class="rt-actions">
          <button class="btn btn-ok btn-sm" data-a="APPROVE">✔ Duyệt</button>
          <button class="btn btn-ghost btn-sm" data-a="EDIT">✎ Sửa & duyệt</button>
          <button class="btn btn-danger btn-sm" data-a="REJECT">✕ Từ chối</button>
        </div>`);
        actions.querySelectorAll("button").forEach((b) =>
          b.addEventListener("click", () => decide(t, b.dataset.a, body)));
        body.appendChild(actions);
      }
    }

    async function decide(t, decision, body) {
      let edited = null;
      if (decision === "EDIT") {
        const raw = $(`#jv-${CSS.escape(t.task_id)}`, body)?.textContent;
        try { edited = JSON.parse(raw); } catch (_) { ui.toast("JSON không hợp lệ", "bad"); return; }
      }
      const res = await api.decideReviewTask(t.task_id, decision, edited);
      if (res.ok) { ui.toast(`Đã ${decision} ${t.task_id}`, "ok"); load(); }
      else ui.toast(res.error || "Thao tác thất bại", "bad");
    }

    load();
  }

  // ===================================================================== //
  //  PAGE: Documents / dashboard
  // ===================================================================== //
  function pageDocuments(root) {
    const metrics = ui.el(`<div class="grid grid-4" id="doc-metrics"></div>`);
    root.appendChild(metrics);

    const upload = ui.el(`
      <div class="card card-pad">
        <div class="card-head"><h3>Tải lên tài liệu</h3><span class="sub">Tài liệu vào trạng thái cách ly, chờ rà soát</span></div>
        <div class="row">
          <label class="field" style="width:auto"><span>Loại tài liệu</span>
            <select id="up-type" style="width:auto">
              <option value="REGULATION">Văn bản quy định</option>
              <option value="AMENDMENT">Văn bản sửa đổi</option>
              <option value="INTERNAL_POLICY">Chính sách nội bộ</option>
            </select></label>
        </div>
        <div class="dropzone" id="dropzone" style="margin-top:12px">
          <div class="dz-ico">📤</div>
          <div><strong>Kéo thả tệp vào đây</strong> hoặc bấm để chọn</div>
          <div class="muted" id="dz-file">Hỗ trợ PDF / văn bản quy định</div>
        </div>
        <input type="file" id="up-file" class="hidden" />
        <div style="margin-top:12px"><button id="up-submit" class="btn btn-primary" disabled><span class="btn-label">Tải lên & bóc tách</span></button></div>
      </div>`);
    root.appendChild(upload);

    const docsCard = ui.el(`<div class="card card-pad"><div class="card-head"><h3>Danh sách tài liệu</h3></div><div id="docs-body">${ui.spinner()}</div></div>`);
    root.appendChild(docsCard);

    // upload wiring
    const dz = $("#dropzone", upload), fileInput = $("#up-file", upload), submit = $("#up-submit", upload);
    let picked = null;
    function setFile(f) { picked = f; $("#dz-file", dz).textContent = f ? `Đã chọn: ${f.name}` : "Hỗ trợ PDF / văn bản quy định"; submit.disabled = !f; }
    dz.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
    dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("drag"); });
    dz.addEventListener("dragleave", () => dz.classList.remove("drag"));
    dz.addEventListener("drop", (e) => { e.preventDefault(); dz.classList.remove("drag"); if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); });
    submit.addEventListener("click", async () => {
      if (!picked) return;
      submit.classList.add("loading"); submit.disabled = true;
      const res = await api.uploadDocument(picked, $("#up-type", upload).value);
      submit.classList.remove("loading");
      if (res.ok) {
        ui.toast("Đã tải lên: " + (res.data.filename || picked.name), "ok");
        if (res.data.injection_suspected) ui.toast("⚠️ Nghi ngờ prompt-injection!", "bad");
        setFile(null); fileInput.value = ""; loadDocs();
      } else { ui.toast(res.error || "Tải lên thất bại", "bad"); submit.disabled = false; }
    });

    async function loadDocs() {
      const res = await api.listDocuments();
      const body = $("#docs-body", docsCard);
      if (!res.ok) { body.innerHTML = ui.apiErrorCard(res).replace(/^<div class="card card-pad">|<\/div>$/g, ""); metrics.innerHTML = ""; return; }
      let docs = Array.isArray(res.data) ? res.data : (res.data && res.data.documents) || [];

      const pending = docs.filter((d) => d.approval_status === "PENDING");
      const injections = docs.filter((d) => d.injection_suspected);
      const active = docs.filter((d) => d.approval_status === "APPROVED");
      metrics.innerHTML = `
        ${metric("Tổng tài liệu", docs.length, "")}
        ${metric("Đang hiệu lực", active.length, "accent")}
        ${metric("Chờ duyệt", pending.length, "warn")}
        ${metric("Nghi injection", injections.length, injections.length ? "bad" : "")}`;

      if (!docs.length) { body.innerHTML = ui.empty("📭", "Chưa có tài liệu", "Hãy tải lên tài liệu đầu tiên."); return; }

      const rows = docs.map((d) => {
        const appr = L.approval[d.approval_status] || d.approval_status;
        const apprCls = d.approval_status === "APPROVED" ? "ok" : d.approval_status === "REJECTED" ? "bad" : "warn";
        const proc = L.processing[d.processing_status] || d.processing_status || "—";
        const canActivate = d.approval_status !== "APPROVED";
        return `<tr>
          <td><strong>${ui.esc(d.document_number || d.filename || "—")}</strong>
            ${d.injection_suspected ? `<span class="badge bad" style="margin-left:6px">⚠️ injection</span>` : ""}
            <div class="muted mono">${ui.esc(d.document_id || "")}</div></td>
          <td><span class="badge neutral">${ui.esc(L.docType[d.type] || d.type || "—")}</span></td>
          <td>${ui.esc(proc)}</td>
          <td><span class="badge ${apprCls}">${ui.esc(appr)}</span></td>
          <td>${canActivate ? `<button class="btn btn-ghost btn-sm" data-activate="${ui.esc(d.document_id)}">Kích hoạt</button>` : `<span class="muted">—</span>`}</td>
        </tr>`;
      }).join("");

      body.innerHTML = `
        ${injections.length ? `<div class="alert alert-error" style="margin-bottom:14px"><strong>⚠️ Cảnh báo prompt-injection</strong> ở ${injections.length} tài liệu — cần rà soát trước khi kích hoạt.</div>` : ""}
        <div class="table-wrap"><table class="data">
          <thead><tr><th>Tài liệu</th><th>Loại</th><th>Xử lý</th><th>Phê duyệt</th><th>Hành động</th></tr></thead>
          <tbody>${rows}</tbody></table></div>`;

      body.querySelectorAll("[data-activate]").forEach((b) =>
        b.addEventListener("click", async () => {
          b.classList.add("loading"); b.disabled = true;
          const r = await api.activateDocument(b.dataset.activate);
          if (r.ok) { ui.toast("Đã kích hoạt tài liệu", "ok"); loadDocs(); }
          else { ui.toast(r.error || "Kích hoạt thất bại", "bad"); b.classList.remove("loading"); b.disabled = false; }
        }));
    }

    loadDocs();
  }

  function metric(label, value, cls) {
    return `<div class="metric"><div class="m-label">${label}</div><div class="m-value ${cls || ""}">${value}</div></div>`;
  }

  // ===================================================================== //
  //  PAGE: Audit
  // ===================================================================== //
  function pageAudit(root) {
    const card = ui.el(`<div class="card card-pad"><div class="card-head"><h3>Nhật ký kiểm toán</h3><span class="sub">Mỗi truy vấn được ghi lại đầy đủ nguồn</span></div><div id="au-body">${ui.spinner()}</div></div>`);
    root.appendChild(card);

    (async () => {
      const res = await api.audit();
      const body = $("#au-body", card);
      if (!res.ok) { body.innerHTML = ui.apiErrorCard(res).replace(/^<div class="card card-pad">|<\/div>$/g, ""); return; }
      const rows = Array.isArray(res.data) ? res.data : (res.data && res.data.records) || [];
      if (!rows.length) { body.innerHTML = ui.empty("🗒️", "Chưa có bản ghi audit", "Hãy thực hiện vài truy vấn ở trang Hỏi đáp."); return; }

      const trs = rows.map((r) => {
        const st = r.status ? ui.statusBadge(r.status) : "—";
        const used = (r.used_versions || []).map((v) => `<code>${ui.esc(v)}</code>`).join(" ") || "—";
        const excl = (r.excluded_versions || []).length;
        return `<tr>
          <td>${ui.esc(r.created_at || "—")}</td>
          <td><strong>${ui.esc(r.user_id || "—")}</strong><div class="muted">${ui.esc(r.role || "")}</div></td>
          <td>${ui.esc(r.query || "—")}<div class="muted">📅 ${ui.esc(r.query_date || "—")}</div></td>
          <td>${st}</td>
          <td>${used}${excl ? `<div class="muted">${excl} nguồn bị loại</div>` : ""}</td>
          <td>${r.latency_ms != null ? ui.esc(r.latency_ms) + " ms" : "—"}</td>
        </tr>`;
      }).join("");
      body.innerHTML = `<div class="table-wrap"><table class="data">
        <thead><tr><th>Thời điểm</th><th>Người dùng</th><th>Truy vấn</th><th>Trạng thái</th><th>Nguồn đã dùng</th><th>Độ trễ</th></tr></thead>
        <tbody>${trs}</tbody></table></div>`;
    })();
  }

  // --------------------------------------------------------------------- //
  document.addEventListener("DOMContentLoaded", boot);
})();
