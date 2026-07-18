// Thin client for the FastAPI backend (VAIC2026 SHB1).
// Shapes mirror the live /query, /compliance-checks, /impact-report responses.
// CORS is open on the backend, so the browser calls it directly.

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

// ponytail: demo auto-login. No login screen for the hackathon demo — first call
// grabs a COMPLIANCE_OFFICER token and caches it. Swap to a real login form later.
const DEMO_CREDS = { username: "compliance", password: "compliance123" }

let _token: string | null = null

async function getToken(): Promise<string> {
  if (_token) return _token
  const r = await fetch(`${BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(DEMO_CREDS),
  })
  if (!r.ok) throw new Error(`login failed (${r.status})`)
  _token = (await r.json()).token as string
  return _token
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const token = await getToken()
  const r = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (r.status === 401) {
    _token = null // token expired — retry once with a fresh login
    return req<T>(method, path, body)
  }
  if (!r.ok) {
    let detail: unknown
    try { detail = await r.json() } catch { detail = await r.text() }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail))
  }
  return r.json() as Promise<T>
}

// ─── Types (subset of the real payloads that the UI renders) ──────────────────

export interface Citation {
  source_id: string
  document_number: string
  heading_path: string[]
  page: number
}

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

export interface ConflictCandidate {
  provision_a: string
  provision_b: string
  reason: string
  value_a: string
  value_b: string
  temporal_overlap: boolean
  scope_overlap: boolean
  human_review: string
}

export interface Answer {
  text: string
  citations: Citation[]
  status: string
  query_date: string
  timeline: unknown[]
  conflict_candidates: ConflictCandidate[]
  impact_candidates: unknown[]
  excluded_evidence: ExcludedEvidence[]
  check_failures: unknown[]
}

export interface QueryResponse {
  answer: Answer
  evidence: {
    query: string
    query_date: string
    intent: string
    valid_evidence: EvidenceItem[]
    excluded_evidence: ExcludedEvidence[]
    reference_paths: unknown[]
    change_paths: unknown[]
    conflict_candidates: ConflictCandidate[]
    impact_candidates: unknown[]
  }
}

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

export interface HealthDetails {
  demo_mode: boolean
  postgres: string
  opensearch: string
  neo4j: string
  embedding: string
  llm: string
  status: string
}

export interface CheckSummary {
  compliant: number
  non_compliant: number
  partially_compliant: number
  outdated_reference: number
  missing_evidence: number
  ambiguous: number
  needs_human_review: number
  total_claims: number
}

export interface Assessment {
  claim_id: string
  source_text: string
  status: string
  valid_evidence: EvidenceItem[]
  excluded_evidence: ExcludedEvidence[]
  findings: string[]
  explanation: string | null
  recommendation: string | null
  confidence: number
  review_status: string
}

export interface ComplianceReport {
  report_id: string
  target_document_id: string
  review_date: string
  summary: CheckSummary
  assessments: Assessment[]
  status: string
}

export interface ImpactReport {
  report_id: string
  document_id: string
  document_number: string
  executive_summary: string
  changes: {
    change_event_id: string
    operation: string
    target_document_number: string
    target_locator: string
    before_text: string
    after_text: string
    effective_date: string
    review_status: string
  }[]
  impacted_policies: {
    artifact_id: string
    title: string
    reason: string
    severity: string
    regulation_value: string
    internal_policy_value: string
    review_status: string
  }[]
  max_severity: string
  status: string
}

// ─── Endpoints ────────────────────────────────────────────────────────────────

// ─── Mode-based chat + Review Runs (Mode spec §12.2) ─────────────────────────

export type ChatMode = "REGULATORY_ASSISTANT" | "DOCUMENT_REVIEW"

export interface Conversation {
  id: string
  mode: ChatMode
  title: string | null
  active_review_run_id: string | null
  active_batch_review_id: string | null
  last_activity_at: string
}

export interface ChatTurnT {
  id: string
  role: string
  content: string
  citations: { source_id: string; document_number?: string | null }[]
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
  citations: { source_id: string; document_number?: string | null }[]
  action?: string
  result_locked?: boolean
  claim_id?: string
}

export const api = {
  query: (text: string, query_date?: string) =>
    req<QueryResponse>("POST", "/query", { text, query_date }),
  // chat modes
  createConversation: (mode: ChatMode, title?: string) =>
    req<Conversation>("POST", "/conversations", { mode, title }),
  listConversations: () => req<Conversation[]>("GET", "/conversations"),
  getConversation: (id: string) =>
    req<{ conversation: Conversation; turns: ChatTurnT[]; attachments: { id: string; filename: string }[] }>(
      "GET", `/conversations/${id}`),
  postMessage: (id: string, text: string, query_date?: string) =>
    req<{ answer: string; citations: ChatTurnT["citations"]; mode: string; resolved_query?: string | null; action?: string; result_locked?: boolean }>(
      "POST", `/conversations/${id}/messages`, { text, query_date }),
  addAttachment: (id: string, filename: string, text: string) =>
    req<{ attachment_id: string; notice: string }>(
      "POST", `/conversations/${id}/attachments`, { filename, text }),
  deleteConversation: (id: string) => req<unknown>("DELETE", `/conversations/${id}`),
  // review runs
  createReviewRun: (filename: string, text: string, assessment_date?: string, conversation_id?: string) =>
    req<ReviewRunResult>("POST", "/review-runs", { filename, text, assessment_date, conversation_id }),
  getReviewRun: (id: string) => req<ReviewRunResult>("GET", `/review-runs/${id}`),
  askReviewRun: (id: string, question: string, claim_id?: string) =>
    req<ExplainerAnswer>("POST", `/review-runs/${id}/questions`, { question, claim_id }),
  rerunReviewRun: (id: string, assessment_date?: string) =>
    req<ReviewRunResult>("POST", `/review-runs/${id}/rerun`, { assessment_date }),
  // batch reviews
  createBatchReview: (files: { filename: string; text: string }[], assessment_date?: string, conversation_id?: string) =>
    req<BatchReview>("POST", "/batch-reviews", { files, assessment_date, conversation_id }),
  getBatchReview: (id: string) => req<BatchReview>("GET", `/batch-reviews/${id}`),
  askBatch: (id: string, question: string, scope = "ENTIRE_BATCH", review_run_id?: string, claim_ids?: string[]) =>
    req<ExplainerAnswer>("POST", `/batch-reviews/${id}/questions`, { question, scope, review_run_id, claim_ids }),
  rerunBatch: (id: string, full = false, item_id?: string) =>
    req<BatchReview>("POST", `/batch-reviews/${id}/rerun`, { full, item_id }),
  documents: () => req<DocumentRow[]>("GET", "/documents"),
  reviewTasks: () => req<unknown[]>("GET", "/review-tasks"),
  health: () => req<HealthDetails>("GET", "/health/details"),
  createCheck: (text: string, review_date?: string) =>
    req<{ check_id: string; status: string; summary: CheckSummary }>(
      "POST", "/compliance-checks", { text, review_date },
    ),
  checkReport: (id: string) =>
    req<ComplianceReport>("GET", `/compliance-checks/${id}/report`),
  impactReport: (documentId: string) =>
    req<ImpactReport>("GET", `/regulatory-sources/${documentId}/impact-report`),
}
