// Thin client for the FastAPI backend (VAIC2026 SHB1).
// Surface = đúng hai tab của UI: Add Source (ingestion + HITL review + activate)
// và RAG (conversations, review runs, batch reviews). CORS mở, browser gọi thẳng.

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

// fetch() chỉ ném TypeError khi request KHÔNG chạm được server (CORS chặn, backend
// chưa chạy, sai URL, mất mạng) — trình duyệt che nguyên nhân thật vì lý do bảo
// mật. Bọc lại để báo lỗi tiếng Việt, nêu rõ nguyên nhân thường gặp cho khâu dev.
async function safeFetch(url: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init)
  } catch {
    const origin = typeof window !== "undefined" ? window.location.origin : "(server)"
    throw new Error(
      `Không gọi được API: ${init.method ?? "GET"} ${url}.\n` +
      `Nguyên nhân thường gặp:\n` +
      `• CORS — backend chưa cho phép origin ${origin} ` +
      `(sửa: đặt env CORS_ORIGINS ở backend và deploy lại).\n` +
      `• Backend chưa chạy hoặc sai NEXT_PUBLIC_API_URL (đang trỏ: ${BASE}).\n` +
      `• Mất mạng.\n` +
      `Mở DevTools → Network để xem chi tiết.`,
    )
  }
}

// Phiên đăng nhập nội bộ: tài khoản do quản trị viên cấp, backend /login trả
// {token, role, username}. Lưu localStorage; 401 → xóa phiên, quay về màn đăng nhập.
export interface Session {
  token: string
  username: string
  role: string
}

const SESSION_KEY = "shb-session"

export function getSession(): Session | null {
  if (typeof window === "undefined") return null
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    return raw ? (JSON.parse(raw) as Session) : null
  } catch {
    return null
  }
}

export async function login(username: string, password: string): Promise<Session> {
  const r = await safeFetch(`${BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  })
  if (!r.ok) {
    throw new Error(r.status === 401
      ? "Sai tên đăng nhập hoặc mật khẩu."
      : `Không đăng nhập được (mã lỗi ${r.status}). Vui lòng thử lại.`)
  }
  const data = await r.json()
  const session: Session = { token: data.token, username: data.username, role: data.role }
  localStorage.setItem(SESSION_KEY, JSON.stringify(session))
  return session
}

export function logout(): void {
  localStorage.removeItem(SESSION_KEY)
}

export class ApiError extends Error {
  status: number
  detail: unknown
  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail))
    this.status = status
    this.detail = detail
  }
}

function authHeader(): Record<string, string> {
  const session = getSession()
  if (!session) throw new Error("Chưa đăng nhập.")
  return { Authorization: `Bearer ${session.token}` }
}

async function handle<T>(r: Response): Promise<T> {
  if (r.status === 401) {
    logout() // phiên hết hạn — về màn đăng nhập
    window.location.reload()
    throw new Error("Phiên đăng nhập đã hết hạn.")
  }
  if (!r.ok) {
    let detail: unknown
    try { detail = await r.json() } catch { detail = await r.text() }
    throw new ApiError(r.status, detail)
  }
  return r.json() as Promise<T>
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const r = await safeFetch(`${BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  return handle<T>(r)
}

// multipart — không set Content-Type để browser tự thêm boundary
async function reqForm<T>(path: string, form: FormData): Promise<T> {
  const r = await safeFetch(`${BASE}${path}`, { method: "POST", headers: authHeader(), body: form })
  return handle<T>(r)
}

// ─── Types (subset of the real payloads that the UI renders) ──────────────────

export interface EvidenceItem {
  source_id: string
  provision_id: string
  version_id: string
  document_number: string
  heading_path: string[]
  content: string
  page: number
  valid_from: string
  valid_to_exclusive: string | null
  score: number
}

export interface ExcludedEvidence {
  version_id: string
  provision_id: string
  heading_path: string[]
  reason: string
}

// ─── Add Source: documents + HITL review tasks ────────────────────────────────

export interface DocumentRow {
  document_id: string
  filename: string
  type: string
  document_number: string
  processing_status: string
  approval_status: string
  injection_suspected: boolean
  created_at: string
}

export interface UploadResponse {
  document_id: string
  filename: string
  file_hash: string
  processing_status: string
  approval_status: string
  injection_suspected: boolean
}

export interface ReviewTask {
  task_id: string
  task_type: string
  document_id: string | null
  source_ref: string | null
  extracted: Record<string, unknown>
  diff_before: string | null
  diff_after: string | null
  confidence: number
  valid_from: string | null
  status: string
  decision: string | null
  decided_by: string | null
  created_at: string | null
}

export type ReviewDecision = "APPROVE" | "EDIT" | "REJECT"

// ─── RAG: mode-based chat + Review Runs (Mode spec §12.2) ────────────────────

export type ChatMode = "REGULATORY_ASSISTANT" | "DOCUMENT_REVIEW"

export interface Conversation {
  id: string
  mode: ChatMode
  title: string | null
  active_review_run_id: string | null
  active_batch_review_id: string | null
  last_activity_at: string
}

export interface ChatCitation {
  source_id: string
  document_number?: string | null
  heading_path?: string[]
  page?: number
  valid_from?: string
  valid_to_exclusive?: string | null
  content?: string | null
}

export interface ChatTurnT {
  id: string
  role: string
  content: string
  citations: ChatCitation[]
}

export interface ReviewRunAssessment {
  claim_id: string
  source_text: string
  status: string
  findings: string[]
  explanation: string
  recommendation: string | null
  confidence: number
  requires_human_review: boolean
  valid_evidence: EvidenceItem[]
  excluded_evidence: ExcludedEvidence[]
}

export interface ReviewRunReport {
  review_run_id: string
  assessment_date: string
  knowledge_snapshot_id: string
  target_document: { id: string; filename: string | null; trust_class: string }
  versions: { parser: string; prompt: string; schema: string }
  summary: Record<string, number>
  assessments: ReviewRunAssessment[]
}

export interface ReviewRunResult {
  review_run_id: string
  state: string
  knowledge_snapshot_id: string
  report: ReviewRunReport | null
}

export interface BatchItem {
  item_id: string
  filename: string
  status: string
  review_run_id: string | null
  error: string | null
}

export interface BatchReview {
  batch_review_id: string
  assessment_date: string
  knowledge_snapshot_id: string
  total_documents: number
  completed_documents: number
  failed_documents: number
  summary: Record<string, number>
  recurring_issues: {
    finding_type: string
    regulatory_provision_id: string | null
    shared_value: string | null
    occurrence_count: number
    affected_document_ids: string[]
  }[]
  items: BatchItem[]
}

export interface ExplainerAnswer {
  answer: string
  citations: ChatCitation[]
  action?: string
  result_locked?: boolean
  claim_id?: string
}

export interface PostMessageResponse {
  answer: string
  citations: ChatCitation[]
  mode: string
  resolved_query?: string | null
  action?: string
  result_locked?: boolean
}

// ─── Endpoints ────────────────────────────────────────────────────────────────

export const api = {
  // Add Source — nguồn pháp lý (AUTHORITY_SOURCE_CANDIDATE → APPROVED + ACTIVE)
  uploadDocument: (file: File, type: string) => {
    const form = new FormData()
    form.append("file", file)
    form.append("type", type)
    return reqForm<UploadResponse>("/documents", form)
  },
  documents: () => req<DocumentRow[]>("GET", "/documents"),
  activateDocument: (documentId: string) =>
    req<Record<string, unknown>>("POST", `/documents/${documentId}/activate`),
  reviewTasks: (status?: string) =>
    req<ReviewTask[]>("GET", `/review-tasks${status ? `?status=${status}` : ""}`),
  decideReviewTask: (taskId: string, decision: ReviewDecision, edited_payload?: Record<string, unknown>) =>
    req<ReviewTask>("POST", `/review-tasks/${taskId}/decision`, { decision, edited_payload }),

  // RAG — chat modes
  createConversation: (mode: ChatMode, title?: string) =>
    req<Conversation>("POST", "/conversations", { mode, title }),
  listConversations: () => req<Conversation[]>("GET", "/conversations"),
  getConversation: (id: string) =>
    req<{ conversation: Conversation; turns: ChatTurnT[]; attachments: { id: string; filename: string }[] }>(
      "GET", `/conversations/${id}`),
  postMessage: (id: string, text: string, query_date?: string) =>
    req<PostMessageResponse>("POST", `/conversations/${id}/messages`, { text, query_date }),
  addAttachment: (id: string, filename: string, text: string) =>
    req<{ attachment_id: string; notice: string }>(
      "POST", `/conversations/${id}/attachments`, { filename, text }),
  deleteConversation: (id: string) => req<unknown>("DELETE", `/conversations/${id}`),

  // Trích xuất text từ file (PDF/DOCX/TXT) qua backend PyMuPDF — dùng trước khi review.
  extractText: (file: File) => {
    const form = new FormData()
    form.append("file", file)
    return reqForm<{ filename: string; text: string }>("/extract-text", form)
  },

  // RAG — review runs (Nhận xét tài liệu)
  createReviewRun: (filename: string, text: string, assessment_date?: string, conversation_id?: string) =>
    req<ReviewRunResult>("POST", "/review-runs", { filename, text, assessment_date, conversation_id }),
  getReviewRun: (id: string) => req<ReviewRunResult>("GET", `/review-runs/${id}`),
  askReviewRun: (id: string, question: string, claim_id?: string) =>
    req<ExplainerAnswer>("POST", `/review-runs/${id}/questions`, { question, claim_id }),
  rerunReviewRun: (id: string, assessment_date?: string) =>
    req<ReviewRunResult>("POST", `/review-runs/${id}/rerun`, { assessment_date }),

  // RAG — batch reviews (tối đa ~5 file, mỗi file một Review Run độc lập)
  createBatchReview: (files: { filename: string; text: string }[], assessment_date?: string, conversation_id?: string) =>
    req<BatchReview>("POST", "/batch-reviews", { files, assessment_date, conversation_id }),
  getBatchReview: (id: string) => req<BatchReview>("GET", `/batch-reviews/${id}`),
  askBatch: (id: string, question: string, scope = "ENTIRE_BATCH", review_run_id?: string, claim_ids?: string[]) =>
    req<ExplainerAnswer>("POST", `/batch-reviews/${id}/questions`, { question, scope, review_run_id, claim_ids }),
  rerunBatch: (id: string, full = false, item_id?: string) =>
    req<BatchReview>("POST", `/batch-reviews/${id}/rerun`, { full, item_id }),
}
