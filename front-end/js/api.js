/* Resilient HTTP client — mirrors ui/api_client.py.
 * Every method returns { ok, status, data, error }; never throws on network errors.
 */
(function () {
  const S = APP.config.storageKeys;

  function getApiBase() {
    return localStorage.getItem(S.apiBase) || APP.config.defaultApiBase;
  }
  function setApiBase(url) {
    localStorage.setItem(S.apiBase, (url || "").trim() || APP.config.defaultApiBase);
  }
  function getToken() {
    return localStorage.getItem(S.token);
  }

  function headers(extra) {
    const h = { Accept: "application/json" };
    const t = getToken();
    if (t) h["Authorization"] = "Bearer " + t;
    return Object.assign(h, extra || {});
  }

  async function request(method, path, opts) {
    opts = opts || {};
    const url = getApiBase().replace(/\/$/, "") + path;
    const init = { method, headers: headers(opts.headers) };
    if (opts.json !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(opts.json);
    }
    if (opts.form) init.body = opts.form; // FormData: browser sets content-type

    let resp;
    try {
      resp = await fetch(url + (opts.query ? "?" + opts.query : ""), init);
    } catch (e) {
      return { ok: false, status: 0, data: null, error: `Không kết nối được API (${url}): ${e.message}` };
    }
    let payload;
    const text = await resp.text();
    try { payload = text ? JSON.parse(text) : null; } catch (_) { payload = text; }

    if (!resp.ok) {
      const detail = payload && typeof payload === "object" ? payload.detail : payload;
      return { ok: false, status: resp.status, data: payload, error: `HTTP ${resp.status}: ${detail || resp.statusText}` };
    }
    return { ok: true, status: resp.status, data: payload, error: null };
  }

  const api = {
    getApiBase,
    setApiBase,
    getToken,

    health: () => request("GET", "/health"),

    async login(username, password) {
      const res = await request("POST", "/login", { json: { username, password } });
      if (res.ok && res.data) {
        localStorage.setItem(S.token, res.data.token);
        localStorage.setItem(S.role, res.data.role);
        localStorage.setItem(S.username, res.data.username);
      }
      return res;
    },

    logout() {
      localStorage.removeItem(S.token);
      localStorage.removeItem(S.role);
      localStorage.removeItem(S.username);
    },

    session() {
      return {
        token: localStorage.getItem(S.token),
        role: localStorage.getItem(S.role),
        username: localStorage.getItem(S.username),
      };
    },

    query(text, queryDate, mode) {
      const body = { text };
      if (queryDate) body.query_date = queryDate;
      if (mode) body.mode = mode;
      return request("POST", "/query", { json: body });
    },

    compare(text, queryDate) {
      const body = { text };
      if (queryDate) body.query_date = queryDate;
      return request("POST", "/compare", { json: body });
    },

    listReviewTasks(status) {
      return request("GET", "/review-tasks", { query: status ? "status=" + encodeURIComponent(status) : "" });
    },

    decideReviewTask(taskId, decision, editedPayload, note) {
      const body = { decision };
      if (editedPayload !== undefined && editedPayload !== null) body.edited_payload = editedPayload;
      if (note) body.note = note;
      return request("POST", `/review-tasks/${encodeURIComponent(taskId)}/decision`, { json: body });
    },

    listDocuments: () => request("GET", "/documents"),

    uploadDocument(file, docType) {
      const fd = new FormData();
      fd.append("file", file, file.name);
      fd.append("type", docType || "REGULATION");
      return request("POST", "/documents", { form: fd });
    },

    activateDocument: (id) => request("POST", `/documents/${encodeURIComponent(id)}/activate`),

    graphProvision: (id) => request("GET", `/graph/provision/${encodeURIComponent(id)}`),

    audit: () => request("GET", "/audit"),
  };

  APP.api = api;
})();
