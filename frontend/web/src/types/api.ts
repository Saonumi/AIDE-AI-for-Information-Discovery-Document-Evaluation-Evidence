/**
 * API payload shapes — mirror of spec §9 (API contract) and Phụ lục B (JSON contract mẫu).
 *
 * Hand-maintained: when backend/app/domain/contracts.py changes, change this too.
 */
import type {
  AmendmentOperation,
  BackendMode,
  ComplianceStatus,
  DocumentClass,
  ErrorCode,
  ResolutionStatus,
  ReviewStatus,
  ReviewTargetStatus,
  ReviewerAction,
  Role,
  Severity,
  SourceStatus,
  TrustClass,
  UploadPurpose,
} from '@/types/domain'

// --------------------------------------------------------------------------- //
// §9.1 error envelope
// --------------------------------------------------------------------------- //
export interface ApiErrorBody {
  error: {
    code: ErrorCode | string
    message: string
    details?: Record<string, unknown>
  }
}

// --------------------------------------------------------------------------- //
// auth
// --------------------------------------------------------------------------- //
export interface LoginResponse {
  token: string
  username: string
  role: Role
}

// --------------------------------------------------------------------------- //
// provenance — §2.3: every extracted field carries its evidence
// --------------------------------------------------------------------------- //
export interface EvidenceSpan {
  evidence_span_id: string
  document_id: string
  page: number
  text: string
  /** [x0, y0, x1, y1] in PDF points — drives the viewer highlight. */
  bbox?: [number, number, number, number]
  extractor?: string
  confidence?: number
}

/** A metadata value that knows where it came from (Phụ lục B.1). */
export interface ProvenancedField<T = string> {
  value: T
  page?: number
  evidence_text?: string
  extractor?: string
  confidence?: number
  validation_status?: string
}

// --------------------------------------------------------------------------- //
// documents
// --------------------------------------------------------------------------- //
export interface DocumentSummary {
  document_id: string
  filename?: string
  document_number?: string | null
  title?: string | null
  issuer?: string | null
  document_class: DocumentClass
  subtype?: string | null
  /**
   * Null for documents that did not arrive through either upload flow — e.g. a
   * seeded INTERNAL_APPROVED policy (§2.4 requires a separate workflow for that
   * promotion, so neither UploadPurpose value would be truthful).
   */
  upload_purpose?: UploadPurpose | null
  trust_class: TrustClass
  /** Set on REVIEW_DOCUMENTs so the UI can link to the check without guessing. */
  check_id?: string | null
  status: SourceStatus | ReviewTargetStatus
  issued_date?: string | null
  effective_date?: string | null
  valid_from?: string | null
  valid_to_exclusive?: string | null
  uploaded_at?: string | null
}

// --------------------------------------------------------------------------- //
// Workflow A — regulatory sources (§3.1, Phụ lục B.1)
// --------------------------------------------------------------------------- //
export interface ChangeProposalTarget {
  document_number?: string
  article?: string
  clause?: string
  point?: string
}

export interface ChangeProposal {
  proposal_id: string
  /**
   * The ReviewTask this proposal is decided through. §9's decision route is
   * keyed by task_id, NOT by proposal_id — they are different identifiers
   * (see ReviewTaskSummary.task_id vs .target_id).
   */
  review_task_id?: string
  operation: AmendmentOperation
  target: ChangeProposalTarget
  resolution_status: ResolutionStatus
  before_text?: string | null
  after_text?: string | null
  effective_date?: string | null
  evidence_span_id?: string | null
  review_status: ReviewStatus
  /** Blocking proposals must be decided before activation (§7.6). */
  is_critical?: boolean
  warnings?: string[]
  confidence?: number
}

/** One Điều/Khoản/Điểm parsed out of the uploaded source (§10.3 "provisions"). */
export interface ParsedProvision {
  provision_id: string
  locator: string
  heading?: string | null
  content?: string | null
  page?: number | null
  evidence_span_id?: string | null
  parent_id?: string | null
}

/** §3.1.1 — a reference this document makes to another document/provision. */
export interface DetectedReference {
  reference_id: string
  raw_text: string
  target_document_number?: string | null
  target_locator?: string | null
  resolution_status: ResolutionStatus
  evidence_span_id?: string | null
}

export interface SourceReviewPackage {
  document_id: string
  trust_class: TrustClass
  status: SourceStatus
  metadata: {
    document_number?: ProvenancedField
    title?: ProvenancedField
    issuer?: ProvenancedField
    issued_date?: ProvenancedField
    effective_date?: ProvenancedField
  }
  /** §10.3 requires metadata, provisions AND change proposals in the right pane. */
  provisions: ParsedProvision[]
  references: DetectedReference[]
  change_proposals: ChangeProposal[]
  evidence_spans: EvidenceSpan[]
  /** §3.1.1 — OCR thấp, target mơ hồ, date conflict, unresolved reference... */
  warnings: string[]
  pending_critical_reviews: number
}

export interface RegulatorySourceStatusResponse {
  document_id: string
  status: SourceStatus
  trust_class: TrustClass
  /** Steps already completed, in pipeline order. */
  completed_steps: SourceStatus[]
  document: DocumentSummary
}

// --------------------------------------------------------------------------- //
// Regulatory changes & impact (§1.5)
// --------------------------------------------------------------------------- //
export interface ChangeEventSummary {
  change_event_id: string
  operation: AmendmentOperation
  provision_locator: string
  target_document_number?: string
  source_document_number?: string
  before_version_id?: string | null
  after_version_id?: string | null
  effective_date?: string | null
  status?: string
  /** Provenance: the span in the amending document that declared this change. */
  evidence_span_id?: string | null
  before_text?: string | null
  after_text?: string | null
}

export interface PolicyLinkSummary {
  policy_link_id: string
  policy_clause_id: string
  policy_document_title?: string
  policy_locator?: string
  provision_id: string
  provision_locator?: string
  relation: string
  confidence?: number
  review_status: ReviewStatus
  owner?: string | null
}

export interface ImpactedPolicyClause {
  policy_clause_id: string
  policy_document_title?: string
  locator?: string
  content?: string
  severity: Severity
  owner?: string | null
  recommended_action?: string | null
  evidence_span_ids?: string[]
}

export interface RegulatoryImpactReport {
  report_id: string
  source_document_id: string
  source_document_number?: string
  generated_at?: string
  /**
   * §6.3 lists only the ID arrays as required fields. The expanded objects are
   * what the screen renders, so they are optional here and every consumer must
   * default them — a spec-minimal backend payload must not blank the page.
   */
  change_event_ids: string[]
  impacted_policy_ids?: string[]
  change_events?: ChangeEventSummary[]
  impacted_policy_clauses?: ImpactedPolicyClause[]
  summary: string
  status: string
}

// --------------------------------------------------------------------------- //
// Workflow B — compliance checks (§3.2, Phụ lục B.2 / B.3)
// --------------------------------------------------------------------------- //
export interface ClaimEvidence {
  evidence_id?: string
  document_number: string
  article?: string
  clause?: string
  point?: string
  version?: string
  effective_from?: string
  effective_to_exclusive?: string | null
  page?: number
  text?: string
  evidence_span_id?: string
  trust_class?: TrustClass
}

export interface ExcludedEvidence {
  evidence_id?: string
  document_number?: string
  version?: string
  reason: string
}

export interface ClaimAssessment {
  claim_id: string
  /** ReviewTask id used by the §9 decision route (distinct from claim_id). */
  review_task_id?: string
  section?: string | null
  source_text: string
  status: ComplianceStatus
  structured_facts?: Record<string, unknown>
  valid_evidence: ClaimEvidence[]
  excluded_evidence: ExcludedEvidence[]
  explanation?: string
  recommendation?: string | null
  confidence?: number
  severity?: Severity
  review_status: ReviewStatus
  reviewer_action?: ReviewerAction | null
}

export interface ComplianceReportSummary {
  total_claims: number
  compliant: number
  non_compliant: number
  partially_compliant?: number
  outdated_reference: number
  missing_evidence: number
  ambiguous?: number
  needs_human_review: number
}

/** One follow-up item the officer marked — §6.3 lists `actions` on the report. */
export interface ReportAction {
  action_id?: string
  claim_id?: string
  action: string
  owner?: string | null
  due_date?: string | null
  status?: string
}

export interface ComplianceReviewReport {
  report_id?: string
  /** Needed to link back to /compliance-checks/{check_id} without guessing. */
  check_id?: string
  target_document_id: string
  target_document_title?: string
  review_date: string
  requested_scope?: string[]
  summary: ComplianceReportSummary
  /**
   * Phụ lục B.3 serialises this as a list of claim IDs (`["claim-001", ...]`),
   * while the UI needs the expanded objects. Both shapes are accepted and
   * normalised by `expandAssessments()` in lib/report.ts — a bare ID list
   * renders as "chưa tải chi tiết" instead of crashing the report screen.
   */
  assessments: Array<ClaimAssessment | string>
  actions?: ReportAction[]
  status: ReviewTargetStatus | string
}

export interface ComplianceCheckStatusResponse {
  check_id: string
  target_document_id: string
  status: ReviewTargetStatus
  completed_steps: ReviewTargetStatus[]
  document: DocumentSummary
  review_date?: string
  requested_scope?: string[]
}

// --------------------------------------------------------------------------- //
// Evidence query (§3.3 — supporting screen, not the centre of the product)
// --------------------------------------------------------------------------- //
export interface EvidenceQueryResponse {
  question: string
  query_date: string
  answer?: string
  /** Only AUTHORITY_SOURCE + APPROVED + ACTIVE may appear here (§2.2). */
  valid_evidence: ClaimEvidence[]
  excluded_evidence: ExcludedEvidence[]
  change_history?: ChangeEventSummary[]
  needs_human_review?: boolean
}

// --------------------------------------------------------------------------- //
// Review inbox (§7.6) — one queue for both workflows
// --------------------------------------------------------------------------- //
export interface ReviewTaskSummary {
  task_id: string
  task_type: string
  target_id: string
  target_label?: string
  document_id?: string
  risk?: Severity
  status: ReviewStatus
  created_at?: string
  is_critical?: boolean
}

// --------------------------------------------------------------------------- //
// Audit & health (§10.5, §11.2 T11)
// --------------------------------------------------------------------------- //
export interface AuditEvent {
  audit_id?: string
  actor: string
  action: string
  entity?: string
  entity_id?: string
  before?: unknown
  after?: unknown
  timestamp: string
}

export interface BackendComponentHealth {
  name: string
  mode: BackendMode
  detail?: string
  healthy: boolean
}

export interface HealthDetailsResponse {
  status: string
  demo_mode: boolean
  components: BackendComponentHealth[]
}

// --------------------------------------------------------------------------- //
// Overview (§10.2 nav #1) — aggregate counters for the dashboard
// --------------------------------------------------------------------------- //
export interface OverviewStats {
  authority_sources_active: number
  sources_pending_review: number
  change_events_recent: number
  policy_links_pending: number
  compliance_checks_open: number
  claims_needing_action: number
}
