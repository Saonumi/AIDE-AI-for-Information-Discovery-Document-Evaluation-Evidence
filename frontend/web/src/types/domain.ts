/**
 * Domain enums — mirror of spec §6 (Domain model và data contract).
 *
 * These are the ONLY vocabularies the UI is allowed to display. If a label
 * appears on screen it must come from here, so DB / API / graph / UI never drift.
 * Spec §6.2 is explicit: "DB, API, graph, OpenSearch mapping và UI phải dùng cùng enum".
 */

// --------------------------------------------------------------------------- //
// §6.1 Role — USER and EMPLOYEE are deleted by the spec
// --------------------------------------------------------------------------- //
export const ROLE = {
  COMPLIANCE_OFFICER: 'COMPLIANCE_OFFICER',
  SYSTEM_ADMIN: 'SYSTEM_ADMIN',
} as const
export type Role = (typeof ROLE)[keyof typeof ROLE]

// --------------------------------------------------------------------------- //
// §6.2 Document taxonomy
// --------------------------------------------------------------------------- //
export const DOCUMENT_CLASS = {
  EXTERNAL_LEGAL: 'EXTERNAL_LEGAL',
  INTERNAL_POLICY: 'INTERNAL_POLICY',
  REVIEW_DOCUMENT: 'REVIEW_DOCUMENT',
} as const
export type DocumentClass = (typeof DOCUMENT_CLASS)[keyof typeof DOCUMENT_CLASS]

/** Every upload must declare its purpose — the backend never guesses from filename. */
export const UPLOAD_PURPOSE = {
  ADD_REGULATORY_SOURCE: 'ADD_REGULATORY_SOURCE',
  CHECK_DOCUMENT_COMPLIANCE: 'CHECK_DOCUMENT_COMPLIANCE',
} as const
export type UploadPurpose = (typeof UPLOAD_PURPOSE)[keyof typeof UPLOAD_PURPOSE]

export const TRUST_CLASS = {
  AUTHORITY_SOURCE_CANDIDATE: 'AUTHORITY_SOURCE_CANDIDATE',
  AUTHORITY_SOURCE: 'AUTHORITY_SOURCE',
  INTERNAL_APPROVED: 'INTERNAL_APPROVED',
  REVIEW_TARGET: 'REVIEW_TARGET',
  UNVERIFIED: 'UNVERIFIED',
} as const
export type TrustClass = (typeof TRUST_CLASS)[keyof typeof TRUST_CLASS]

/** §2.1 — only AUTHORITY_SOURCE may ever back a legal conclusion. */
export const TRUST_CLASS_IS_LEGAL_GROUND_TRUTH: Record<TrustClass, boolean> = {
  AUTHORITY_SOURCE_CANDIDATE: false,
  AUTHORITY_SOURCE: true,
  INTERNAL_APPROVED: false,
  REVIEW_TARGET: false,
  UNVERIFIED: false,
}

// --------------------------------------------------------------------------- //
// §2.4 State machines — regulatory source and review target are separate
// --------------------------------------------------------------------------- //
export const SOURCE_STATUS = {
  RECEIVED: 'RECEIVED',
  QUARANTINED: 'QUARANTINED',
  EXTRACTED: 'EXTRACTED',
  PARSED: 'PARSED',
  REVIEW_REQUIRED: 'REVIEW_REQUIRED',
  APPROVED: 'APPROVED',
  // §7.6/§8.1: PostgreSQL is committed but the search index / graph sync has not
  // caught up. The officer must see this rather than assume full propagation.
  INDEX_SYNC_PENDING: 'INDEX_SYNC_PENDING',
  GRAPH_SYNC_PENDING: 'GRAPH_SYNC_PENDING',
  ACTIVE: 'ACTIVE',
  REJECTED: 'REJECTED',
  NEEDS_CORRECTION: 'NEEDS_CORRECTION',
  FAILED: 'FAILED',
  ARCHIVED: 'ARCHIVED',
} as const
export type SourceStatus = (typeof SOURCE_STATUS)[keyof typeof SOURCE_STATUS]

/** The happy path, in order — drives the pipeline stepper (spec §10.3). */
export const SOURCE_PIPELINE_STEPS: SourceStatus[] = [
  'RECEIVED',
  'QUARANTINED',
  'EXTRACTED',
  'PARSED',
  'REVIEW_REQUIRED',
  'APPROVED',
  'ACTIVE',
]

export const REVIEW_TARGET_STATUS = {
  RECEIVED: 'RECEIVED',
  QUARANTINED: 'QUARANTINED',
  EXTRACTED: 'EXTRACTED',
  CLAIMS_PARSED: 'CLAIMS_PARSED',
  CHECKING: 'CHECKING',
  REVIEW_REQUIRED: 'REVIEW_REQUIRED',
  COMPLETED: 'COMPLETED',
  NEEDS_CORRECTION: 'NEEDS_CORRECTION',
  FAILED: 'FAILED',
  REJECTED: 'REJECTED',
} as const
export type ReviewTargetStatus = (typeof REVIEW_TARGET_STATUS)[keyof typeof REVIEW_TARGET_STATUS]

export const REVIEW_TARGET_PIPELINE_STEPS: ReviewTargetStatus[] = [
  'RECEIVED',
  'QUARANTINED',
  'EXTRACTED',
  'CLAIMS_PARSED',
  'CHECKING',
  'REVIEW_REQUIRED',
  'COMPLETED',
]

// --------------------------------------------------------------------------- //
// §6.4 Amendment operations
// --------------------------------------------------------------------------- //
export const AMENDMENT_OPERATION = {
  REPLACE_TEXT: 'REPLACE_TEXT',
  REPLACE_PROVISION: 'REPLACE_PROVISION',
  INSERT_AFTER: 'INSERT_AFTER',
  DELETE_TEXT: 'DELETE_TEXT',
  REPEAL_PROVISION: 'REPEAL_PROVISION',
} as const
export type AmendmentOperation = (typeof AMENDMENT_OPERATION)[keyof typeof AMENDMENT_OPERATION]

// --------------------------------------------------------------------------- //
// §6.5 Compliance assessment
// --------------------------------------------------------------------------- //
export const COMPLIANCE_STATUS = {
  COMPLIANT: 'COMPLIANT',
  NON_COMPLIANT: 'NON_COMPLIANT',
  PARTIALLY_COMPLIANT: 'PARTIALLY_COMPLIANT',
  OUTDATED_REFERENCE: 'OUTDATED_REFERENCE',
  MISSING_EVIDENCE: 'MISSING_EVIDENCE',
  AMBIGUOUS: 'AMBIGUOUS',
  NEEDS_HUMAN_REVIEW: 'NEEDS_HUMAN_REVIEW',
} as const
export type ComplianceStatus = (typeof COMPLIANCE_STATUS)[keyof typeof COMPLIANCE_STATUS]

/** Human decision on one assessment (spec §10.4). */
export const REVIEWER_ACTION = {
  CONFIRM: 'CONFIRM',
  DISMISS: 'DISMISS',
  EDIT: 'EDIT',
  NEEDS_ACTION: 'NEEDS_ACTION',
} as const
export type ReviewerAction = (typeof REVIEWER_ACTION)[keyof typeof REVIEWER_ACTION]

/** Human decision on one change proposal (spec §3.1.1). */
export const PROPOSAL_DECISION = {
  APPROVE: 'APPROVE',
  EDIT: 'EDIT',
  REJECT: 'REJECT',
} as const
export type ProposalDecision = (typeof PROPOSAL_DECISION)[keyof typeof PROPOSAL_DECISION]

export const REVIEW_STATUS = {
  PENDING: 'PENDING',
  APPROVED: 'APPROVED',
  EDITED: 'EDITED',
  REJECTED: 'REJECTED',
} as const
export type ReviewStatus = (typeof REVIEW_STATUS)[keyof typeof REVIEW_STATUS]

/** How confidently an amendment's target was resolved (spec §10.3). */
export const RESOLUTION_STATUS = {
  EXACT: 'EXACT',
  AMBIGUOUS: 'AMBIGUOUS',
  UNRESOLVED: 'UNRESOLVED',
} as const
export type ResolutionStatus = (typeof RESOLUTION_STATUS)[keyof typeof RESOLUTION_STATUS]

export const SEVERITY = {
  HIGH: 'HIGH',
  MEDIUM: 'MEDIUM',
  LOW: 'LOW',
} as const
export type Severity = (typeof SEVERITY)[keyof typeof SEVERITY]

// --------------------------------------------------------------------------- //
// §9.1 Error contract — the UI switches on the code, never on the message
// --------------------------------------------------------------------------- //
export const ERROR_CODE = {
  INVALID_UPLOAD_PURPOSE: 'INVALID_UPLOAD_PURPOSE',
  REVIEW_NOT_COMPLETED: 'REVIEW_NOT_COMPLETED',
  EVIDENCE_NOT_VALID: 'EVIDENCE_NOT_VALID',
  TARGET_NOT_RESOLVED: 'TARGET_NOT_RESOLVED',
  NOT_LEGAL_GROUND_TRUTH: 'NOT_LEGAL_GROUND_TRUTH',
  BACKEND_DEGRADED: 'BACKEND_DEGRADED',
  // beyond the spec's minimum list, but an expired session must be nameable —
  // otherwise an empty screen reads as "there is no data"
  UNAUTHENTICATED: 'UNAUTHENTICATED',
  FORBIDDEN: 'FORBIDDEN',
  ROLE_NOT_SUPPORTED: 'ROLE_NOT_SUPPORTED',
} as const
export type ErrorCode = (typeof ERROR_CODE)[keyof typeof ERROR_CODE]

/** §10.5 — the UI must say which backend is really answering. */
export const BACKEND_MODE = {
  REAL: 'REAL',
  MOCK: 'MOCK',
  FALLBACK: 'FALLBACK',
} as const
export type BackendMode = (typeof BACKEND_MODE)[keyof typeof BACKEND_MODE]
