/* Lightweight self-contained force-directed graph (SVG). No external libs.
 * APP.graph.render(container, {nodes, edges}) where node = {id,label,title,props}.
 */
(function () {
  const NODE_COLORS = {
    Document: "#5B8FF9",
    Provision: "#5AD8A6",
    ProvisionVersion: "#F6BD16",
    ChangeEvent: "#E8684A",
    InternalArtifact: "#9270CA",
  };
  const NODE_LABEL_VI = {
    Document: "Tài liệu",
    Provision: "Điều khoản",
    ProvisionVersion: "Phiên bản",
    ChangeEvent: "Sự kiện sửa đổi",
    InternalArtifact: "Chính sách nội bộ",
  };
  const R = 22;

  function svgEl(name, attrs) {
    const e = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }

  function render(container, data) {
    const nodes = (data.nodes || []).map((n) => Object.assign({}, n));
    const edges = data.edges || [];
    container.innerHTML = "";

    if (!nodes.length) {
      container.innerHTML = APP.ui.empty("🕸️", "Không có dữ liệu đồ thị", "Thử một provision_id khác.");
      return;
    }

    const wrap = document.createElement("div");
    wrap.className = "graph-wrap";
    const W = container.clientWidth || 900, H = 520;
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "xMidYMid meet" });

    // legend
    const usedLabels = [...new Set(nodes.map((n) => n.label))];
    const legend = document.createElement("div");
    legend.className = "graph-legend";
    legend.innerHTML = usedLabels.map((lb) =>
      `<div class="lg-row"><span class="lg-dot" style="background:${NODE_COLORS[lb] || "#999"}"></span>${NODE_LABEL_VI[lb] || lb}</div>`
    ).join("");

    // --- init positions on a circle ---
    const cx = W / 2, cy = H / 2;
    nodes.forEach((n, i) => {
      const a = (i / nodes.length) * Math.PI * 2;
      n.x = cx + Math.cos(a) * Math.min(W, H) * 0.3;
      n.y = cy + Math.sin(a) * Math.min(W, H) * 0.3;
      n.vx = 0; n.vy = 0;
    });
    const byId = {};
    nodes.forEach((n) => (byId[n.id] = n));
    const links = edges.filter((e) => byId[e.source] && byId[e.target]);

    // --- deterministic force simulation (fixed iterations) ---
    const K = 130; // ideal edge length
    for (let iter = 0; iter < 320; iter++) {
      // repulsion
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j];
          let dx = a.x - b.x, dy = a.y - b.y;
          let dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
          const rep = (K * K) / dist * 0.9;
          const fx = (dx / dist) * rep, fy = (dy / dist) * rep;
          a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
        }
      }
      // attraction along edges
      for (const e of links) {
        const a = byId[e.source], b = byId[e.target];
        let dx = b.x - a.x, dy = b.y - a.y;
        let dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const att = ((dist - K) / dist) * 0.12 * dist;
        const fx = (dx / dist) * att, fy = (dy / dist) * att;
        a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
      }
      // center gravity + integrate
      const cool = 1 - iter / 400;
      for (const n of nodes) {
        n.vx += (cx - n.x) * 0.008;
        n.vy += (cy - n.y) * 0.008;
        n.x += Math.max(-18, Math.min(18, n.vx)) * cool;
        n.y += Math.max(-18, Math.min(18, n.vy)) * cool;
        n.vx *= 0.85; n.vy *= 0.85;
        n.x = Math.max(R + 6, Math.min(W - R - 6, n.x));
        n.y = Math.max(R + 6, Math.min(H - R - 6, n.y));
      }
    }

    // --- arrow marker ---
    const defs = svgEl("defs", {});
    const marker = svgEl("marker", { id: "arrow", viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse" });
    marker.appendChild(svgEl("path", { d: "M 0 0 L 10 5 L 0 10 z", fill: "#b9c4d2" }));
    defs.appendChild(marker);
    svg.appendChild(defs);

    // --- edges ---
    for (const e of links) {
      const a = byId[e.source], b = byId[e.target];
      const dx = b.x - a.x, dy = b.y - a.y, len = Math.sqrt(dx * dx + dy * dy) || 1;
      const ex = b.x - (dx / len) * (R + 6), ey = b.y - (dy / len) * (R + 6);
      svg.appendChild(svgEl("line", { class: "gedge", x1: a.x, y1: a.y, x2: ex, y2: ey, "marker-end": "url(#arrow)" }));
      if (e.label) {
        const t = svgEl("text", { class: "gedge-label", x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 - 3, "text-anchor": "middle" });
        t.textContent = e.label;
        svg.appendChild(t);
      }
    }

    // --- detail panel ---
    const detail = document.createElement("div");
    detail.className = "node-detail hidden";

    // --- nodes ---
    for (const n of nodes) {
      const g = svgEl("g", { class: "gnode", transform: `translate(${n.x},${n.y})` });
      g.appendChild(svgEl("circle", { r: R, fill: NODE_COLORS[n.label] || "#999", stroke: "#fff", "stroke-width": "2.5" }));
      const label = svgEl("text", { "text-anchor": "middle", y: R + 14 });
      const title = (n.title || n.id || "").toString();
      label.textContent = title.length > 22 ? title.slice(0, 21) + "…" : title;
      g.appendChild(label);

      g.addEventListener("click", () => {
        const props = n.props || {};
        const rows = Object.keys(props).length
          ? Object.entries(props).map(([k, v]) =>
              `<div class="nd-prop"><span>${APP.ui.esc(k)}</span><span>${APP.ui.esc(String(v))}</span></div>`).join("")
          : `<p class="muted">Không có thuộc tính.</p>`;
        detail.innerHTML =
          `<h4>${APP.ui.esc(n.title || n.id)}</h4>
           <span class="badge neutral">${NODE_LABEL_VI[n.label] || APP.ui.esc(n.label)}</span>
           <div class="nd-prop" style="margin-top:8px"><span>id</span><span class="mono">${APP.ui.esc(n.id)}</span></div>
           ${rows}`;
        detail.classList.remove("hidden");
      });
      svg.appendChild(g);
    }

    wrap.appendChild(svg);
    wrap.appendChild(legend);
    wrap.appendChild(detail);
    container.appendChild(wrap);
  }

  APP.graph = { render };
})();
