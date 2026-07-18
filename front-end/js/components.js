/* Render helpers + small DOM utilities. All HTML is escaped at the boundary. */
(function () {
  const L = APP.labels;

  function esc(s) {
    if (s === null || s === undefined) return "";
    return String(s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function el(html) {
    const t = document.createElement("template");
    t.innerHTML = html.trim();
    return t.content.firstElementChild;
  }

  function fmtHeading(path) {
    return path && path.length ? path.map(esc).join(" › ") : "—";
  }

  function fmtDate(d) {
    return d ? esc(d) : "—";
  }

  function statusBadge(status) {
    const s = L.status[status] || { icon: "•", text: status || "?", cls: "neutral" };
    return `<span class="badge ${s.cls}">${s.icon} ${esc(s.text)}</span>`;
  }

  /* ---- Answer card ---- */
  function renderAnswer(answer) {
    answer = answer || {};
    const parts = [];
    parts.push(`<div class="answer-status">${statusBadge(answer.status)}`);
    if (answer.query_date) parts.push(`<span class="badge neutral">📅 ${esc(answer.query_date)}</span>`);
    parts.push(`</div>`);

    const text = answer.text;
    parts.push(text
      ? `<div class="answer-text">${esc(text)}</div>`
      : `<div class="answer-text empty">(không có nội dung)</div>`);

    // citations
    const cits = answer.citations || [];
    if (cits.length) {
      parts.push(`<div class="section-label">Trích dẫn nguồn</div><ul class="citation-list">`);
      for (const c of cits) {
        const page = c.page != null ? `, trang ${esc(c.page)}` : "";
        parts.push(
          `<li class="citation"><span>📄</span><div>
             <span class="c-doc">${esc(c.document_number || c.source_id || "?")}</span>
             <span class="c-path"> — ${fmtHeading(c.heading_path)}${page}</span>
           </div></li>`);
      }
      parts.push(`</ul>`);
    }

    // timeline
    const tl = answer.timeline || [];
    if (tl.length) {
      parts.push(`<div class="section-label">Dòng thời gian thay đổi</div><ul class="timeline">`);
      for (const t of tl) {
        parts.push(
          `<li><div class="tl-op">${esc(t.operation || "CHANGE")}</div>
             <div class="tl-detail"><code>${esc(t.before_version_id || "—")}</code> → <code>${esc(t.after_version_id || "—")}</code></div>
           </li>`);
      }
      parts.push(`</ul>`);
    }

    // conflicts
    const conflicts = answer.conflict_candidates || [];
    if (conflicts.length) {
      parts.push(`<div class="callout warn"><div class="co-title">⚠️ Ứng viên xung đột (cần rà soát)</div>`);
      for (const c of conflicts) {
        const reason = L.conflict[c.reason] || c.reason;
        parts.push(
          `<div class="co-row">${esc(reason)}: <strong>${esc(c.value_a)}</strong> <span class="vs">↔</span> <strong>${esc(c.value_b)}</strong>
           <span class="muted"> (${esc(c.provision_a)} vs ${esc(c.provision_b)})</span></div>`);
      }
      parts.push(`</div>`);
    }

    // impacts
    const impacts = answer.impact_candidates || [];
    if (impacts.length) {
      parts.push(`<div class="callout bad"><div class="co-title">📌 Chính sách nội bộ có thể lỗi thời</div>`);
      for (const i of impacts) {
        parts.push(
          `<div class="co-row"><strong>${esc(i.artifact_title)}</strong>: nội bộ <strong>${esc(i.internal_policy_value)}</strong>
           <span class="vs">↔</span> quy định <strong>${esc(i.regulation_value)}</strong></div>`);
      }
      parts.push(`</div>`);
    }

    return parts.join("");
  }

  /* ---- "Why this answer" panel ---- */
  function renderWhyPanel(answer, evidence) {
    evidence = evidence || {};
    const parts = [];
    const valid = evidence.valid_evidence || [];
    parts.push(`<div class="section-label">✅ Nguồn hợp lệ được dùng</div>`);
    if (valid.length) {
      parts.push(`<div class="evidence-list">`);
      for (const e of valid) {
        const page = e.page != null ? `, tr.${esc(e.page)}` : "";
        const vt = `[${fmtDate(e.valid_from)} … ${e.valid_to_exclusive ? esc(e.valid_to_exclusive) : "∞"})`;
        parts.push(
          `<div class="evidence-item valid">
             <div class="evidence-head">
               <span class="e-doc">📄 ${esc(e.document_number || "?")} — ${fmtHeading(e.heading_path)}${page}</span>
               <span class="validity-tag">hiệu lực ${esc(vt)}</span>
             </div>
             ${e.content ? `<div class="evidence-body">${esc(e.content)}</div>` : ""}
           </div>`);
      }
      parts.push(`</div>`);
    } else {
      parts.push(`<p class="muted">Không có nguồn hợp lệ (hoặc backend chưa trả evidence).</p>`);
    }

    const excluded = evidence.excluded_evidence || answer.excluded_evidence || [];
    parts.push(`<div class="section-label">⛔ Nguồn bị loại (và lý do)</div>`);
    if (excluded.length) {
      parts.push(`<div class="evidence-list">`);
      for (const x of excluded) {
        const reason = L.exclusion[x.reason] || x.reason;
        parts.push(
          `<div class="evidence-item excluded">
             <div class="evidence-head">
               <span class="e-doc">${fmtHeading(x.heading_path)} <code>${esc(x.version_id)}</code></span>
               <span class="badge bad">${esc(reason)}</span>
             </div>
           </div>`);
      }
      parts.push(`</div>`);
    } else {
      parts.push(`<p class="muted">Không có nguồn nào bị loại.</p>`);
    }
    return parts.join("");
  }

  function empty(ico, title, sub) {
    return `<div class="empty"><div class="empty-ico">${ico}</div><h3>${esc(title)}</h3><p class="muted">${esc(sub || "")}</p></div>`;
  }

  function spinner() { return `<div class="spinner"></div>`; }

  function apiErrorCard(res) {
    return `<div class="card card-pad"><div class="alert alert-error">
      <strong>Không thể gọi API.</strong> Kiểm tra backend đang chạy và địa chỉ API đúng.
      ${res && res.error ? `<div class="muted" style="margin-top:6px;font-weight:400">${esc(res.error)}</div>` : ""}
    </div></div>`;
  }

  /* ---- toast ---- */
  function toast(msg, kind) {
    const host = document.getElementById("toast-host");
    const t = el(`<div class="toast ${kind || "info"}">${esc(msg)}</div>`);
    host.appendChild(t);
    setTimeout(() => { t.style.opacity = "0"; t.style.transition = "opacity .3s"; }, 2600);
    setTimeout(() => t.remove(), 3000);
  }

  APP.ui = { esc, el, fmtHeading, fmtDate, statusBadge, renderAnswer, renderWhyPanel, empty, spinner, apiErrorCard, toast };
})();
