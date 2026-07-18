/**
 * Typed endpoint wrappers — one function per row of spec §9.
 *
 * Each read endpoint declares the fixture to serve while the backend route does
 * not exist yet; writes never fall back, because pretending an approval
 * succeeded would be a lie the audit trail cannot back up.
 */
import { apiGet, apiPost } from '@/lib/apiClient'
import * as fx from '@/lib/fixtures'
import type {
  AuditEvent,
  ComplianceCheckStatusResponse,
  ComplianceReviewReport,
  DocumentSummary,
  EvidenceQueryResponse,
  HealthDetailsResponse,
  LoginResponse,
  OverviewStats,
  PolicyLinkSummary,
  RegulatoryImpactReport,
  RegulatorySourceStatusResponse,
  ReviewTaskSummary,
  SourceReviewPackage,
  ChangeEventSummary,
} from '@/types/api'
import type { ProposalDecision, ReviewerAction, UploadPurpose } from '@/types/domain'

export const api = {
  // ---- auth -------------------------------------------------------------- //
  /**
   * §9 specifies POST /auth/login. The backend currently still exposes the
   * pre-refactor POST /login, so we try the spec path first and fall back to the
   * legacy one on 404. Delete the second call once backend §9 lands — it is a
   * migration shim, not a contract.
   */
  login: async (username: string, password: string) => {
    const res = await apiPost<LoginResponse>('/auth/login', { json: { username, password } })
    if (res.ok || res.status !== 404) return res
    return apiPost<LoginResponse>('/login', { json: { username, password } })
  },

  // ---- overview (§10.2 nav #1) ------------------------------------------- //
  overview: () => apiGet<OverviewStats>('/overview', { fallback: fx.mockOverview }),

  documents: (params?: { upload_purpose?: UploadPurpose; trust_class?: string }) =>
    apiGet<DocumentSummary[]>('/documents', { params, fallback: fx.mockDocuments }),

  // ---- Workflow A: regulatory sources (§9) ------------------------------- //
  uploadRegulatorySource: (form: FormData) =>
    apiPost<{ document_id: string }>('/regulatory-sources', { body: form }),

  regulatorySource: (id: string) =>
    apiGet<RegulatorySourceStatusResponse>(`/regulatory-sources/${id}`, {
      fallback: () => fx.mockSourceStatus(id),
    }),

  reviewPackage: (id: string) =>
    apiGet<SourceReviewPackage>(`/regulatory-sources/${id}/review-package`, {
      fallback: () => fx.mockReviewPackage(id),
    }),

  decideProposal: (documentId: string, taskId: string, decision: ProposalDecision, payload?: unknown) =>
    apiPost<unknown>(`/regulatory-sources/${documentId}/reviews/${taskId}/decision`, {
      json: { decision, edited_payload: payload ?? null },
    }),

  /** Expected to 409 REVIEW_NOT_COMPLETED while critical reviews are pending (§11.2 T2). */
  activateSource: (documentId: string) => apiPost<unknown>(`/regulatory-sources/${documentId}/activate`),

  impactReport: (documentId: string) =>
    apiGet<RegulatoryImpactReport>(`/regulatory-sources/${documentId}/impact-report`, {
      fallback: () => fx.mockImpactReport(documentId),
    }),

  // ---- derived views over Workflow A ------------------------------------- //
  changeEvents: () => apiGet<ChangeEventSummary[]>('/regulatory-changes', { fallback: fx.mockChangeEvents }),

  policyLinks: () => apiGet<PolicyLinkSummary[]>('/policy-links', { fallback: fx.mockPolicyLinks }),

  impactReports: () => apiGet<RegulatoryImpactReport[]>('/impact-reports', { fallback: fx.mockImpactReports }),

  reviewTasks: () => apiGet<ReviewTaskSummary[]>('/review-tasks', { fallback: fx.mockReviewTasks }),

  // ---- Workflow B: compliance checks (§9) -------------------------------- //
  uploadComplianceCheck: (form: FormData) => apiPost<{ check_id: string }>('/compliance-checks', { body: form }),

  complianceCheck: (id: string) =>
    apiGet<ComplianceCheckStatusResponse>(`/compliance-checks/${id}`, {
      fallback: () => fx.mockCheckStatus(id),
    }),

  complianceReport: (id: string) =>
    apiGet<ComplianceReviewReport>(`/compliance-checks/${id}/report`, {
      fallback: () => fx.mockComplianceReport(id),
    }),

  decideAssessment: (checkId: string, taskId: string, action: ReviewerAction, note?: string) =>
    apiPost<unknown>(`/compliance-checks/${checkId}/reviews/${taskId}/decision`, {
      json: { decision: action, note: note ?? null },
    }),

  complianceReports: () =>
    apiGet<ComplianceReviewReport[]>('/compliance-reports', {
      fallback: () => [fx.mockComplianceReport(fx.MOCK_CHECK_ID)],
    }),

  // ---- supporting screens ------------------------------------------------ //
  evidenceQuery: (question: string, queryDate?: string | null, scope?: string[]) =>
    apiPost<EvidenceQueryResponse>('/evidence/query', {
      json: { question, query_date: queryDate ?? null, scope: scope ?? [] },
      fallback: () => fx.mockEvidenceQuery(question),
    }),

  audit: () => apiGet<AuditEvent[]>('/audit', { fallback: fx.mockAudit }),

  healthDetails: () => apiGet<HealthDetailsResponse>('/health/details', { fallback: fx.mockHealth }),
}
