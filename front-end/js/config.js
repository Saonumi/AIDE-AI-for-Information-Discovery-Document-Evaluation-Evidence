/* Global config + tiny shared helpers for the SHB1 front-end.
 * No build step — plain browser globals under window.APP.
 */
window.APP = window.APP || {};

APP.config = {
  // Default backend base URL. Overridable at login and persisted in localStorage.
  defaultApiBase: "http://localhost:8000",
  storageKeys: {
    token: "shb1.token",
    role: "shb1.role",
    username: "shb1.username",
    apiBase: "shb1.apiBase",
  },
};

/* ---- Vietnamese label maps (mirror ui/app.py) ---- */
APP.labels = {
  status: {
    SOURCE_GROUNDED: { icon: "✅", text: "Có nguồn dẫn", cls: "ok" },
    DETERMINISTIC_CHECKS_PASSED: { icon: "✅", text: "Qua kiểm tra xác định", cls: "ok" },
    HUMAN_REVIEWED: { icon: "✅", text: "Đã người duyệt", cls: "ok" },
    NEEDS_REVIEW: { icon: "⚠️", text: "Cần rà soát", cls: "warn" },
    INSUFFICIENT_EVIDENCE: { icon: "⛔", text: "Không đủ bằng chứng", cls: "bad" },
  },
  exclusion: {
    NOT_VALID_AT_QUERY_DATE: "Không hiệu lực tại ngày truy vấn",
    SUPERSEDED: "Đã bị thay thế (bản cũ)",
    NOT_APPROVED: "Chưa được phê duyệt",
    OUT_OF_SCOPE: "Ngoài phạm vi câu hỏi",
  },
  conflict: {
    THRESHOLD_MISMATCH: "Lệch ngưỡng giá trị",
    MODALITY_CONFLICT: "Xung đột nghĩa vụ/cấm/phép",
    DEADLINE_MISMATCH: "Lệch thời hạn",
    SCOPE_OVERLAP_VALUE_DIFF: "Trùng phạm vi, khác giá trị",
  },
  reviewType: {
    PARSING_REVIEW: "Rà soát bóc tách",
    CHANGE_EVENT_REVIEW: "Rà soát sửa đổi",
    REFERENCE_REVIEW: "Rà soát tham chiếu",
    CONFLICT_REVIEW: "Rà soát xung đột",
    IMPACT_REVIEW: "Rà soát ảnh hưởng",
    INJECTION_REVIEW: "Rà soát prompt-injection",
  },
  reviewStatus: {
    PENDING: "Chờ duyệt",
    APPROVED: "Đã duyệt",
    REJECTED: "Từ chối",
  },
  approval: {
    PENDING: "Chờ duyệt",
    APPROVED: "Đã duyệt",
    REJECTED: "Từ chối",
    ARCHIVED: "Lưu trữ",
  },
  processing: {
    QUARANTINED: "Cách ly",
    PROCESSING: "Đang xử lý",
    PARSED: "Đã bóc tách",
    INDEXED: "Đã lập chỉ mục",
    FAILED: "Lỗi",
  },
  docType: {
    REGULATION: "Văn bản quy định",
    AMENDMENT: "Văn bản sửa đổi",
    INTERNAL_POLICY: "Chính sách nội bộ",
  },
};

/* Curated demo questions surfaced as quick chips on the query page. */
APP.sampleQuestions = [
  { q: "Hạn mức tín dụng SME hiện tại là bao nhiêu?", d: "" },
  { q: "Hạn mức tín dụng SME tại ngày 01/03/2026 là bao nhiêu?", d: "2026-03-01" },
  { q: "Hạn mức tín dụng SME đã thay đổi như thế nào trong năm 2026?", d: "2026-08-15" },
  { q: "Có mâu thuẫn nào về hạn mức tín dụng cho nhóm khách hàng SME đang cùng hiệu lực không?", d: "2026-08-15" },
  { q: "Chính sách nội bộ nào cần cập nhật sau khi hạn mức SME tăng lên 700 triệu?", d: "2026-08-15" },
  { q: "Ai chịu trách nhiệm thẩm định hồ sơ tín dụng SME trước khi phê duyệt?", d: "2026-08-15" },
  { q: "Lãi suất cho vay mua nhà ở đối với khách hàng cá nhân là bao nhiêu?", d: "2026-08-15" },
];

APP.demoProvisionId = "prov-qd01-d7k2";
