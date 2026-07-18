/**
 * status_badge (spec §10.6) — one badge component for every vocabulary.
 *
 * Styling hooks are semantic and stable: `.badge` plus `.badge--<kind>` plus
 * `data-value="<ENUM_VALUE>"`. The CSS owner can target any exact state, e.g.
 *   .badge--compliance[data-value="NON_COMPLIANT"] { ... }
 * without this file needing to know a single colour.
 */
import {
  BACKEND_MODE_LABEL,
  COMPLIANCE_STATUS_LABEL,
  DOCUMENT_CLASS_LABEL,
  RESOLUTION_STATUS_LABEL,
  REVIEW_STATUS_LABEL,
  REVIEW_TARGET_STATUS_LABEL,
  SEVERITY_LABEL,
  SOURCE_STATUS_LABEL,
  TRUST_CLASS_HINT,
  TRUST_CLASS_LABEL,
} from '@/lib/labels'
import type {
  BackendMode,
  ComplianceStatus,
  DocumentClass,
  ResolutionStatus,
  ReviewStatus,
  ReviewTargetStatus,
  Severity,
  SourceStatus,
  TrustClass,
} from '@/types/domain'

type BadgeKind =
  | 'trust'
  | 'lifecycle'
  | 'compliance'
  | 'severity'
  | 'review'
  | 'resolution'
  | 'backend'
  | 'class'

function Badge({ kind, value, label, title }: { kind: BadgeKind; value: string; label: string; title?: string }) {
  return (
    <span className={`badge badge--${kind}`} data-value={value} title={title}>
      {label}
    </span>
  )
}

/** §10.5 — trust class must appear on every document. */
export function TrustClassBadge({ value }: { value: TrustClass }) {
  return <Badge kind="trust" value={value} label={TRUST_CLASS_LABEL[value] ?? value} title={TRUST_CLASS_HINT[value]} />
}

/** §10.5 — lifecycle status must appear next to trust class. */
export function LifecycleBadge({ value }: { value: SourceStatus | ReviewTargetStatus | string }) {
  const label =
    SOURCE_STATUS_LABEL[value as SourceStatus] ?? REVIEW_TARGET_STATUS_LABEL[value as ReviewTargetStatus] ?? value
  return <Badge kind="lifecycle" value={value} label={label} />
}

export function ComplianceStatusBadge({ value }: { value: ComplianceStatus }) {
  return <Badge kind="compliance" value={value} label={COMPLIANCE_STATUS_LABEL[value] ?? value} />
}

export function SeverityBadge({ value }: { value: Severity }) {
  return <Badge kind="severity" value={value} label={`Mức độ: ${SEVERITY_LABEL[value] ?? value}`} />
}

export function ReviewStatusBadge({ value }: { value: ReviewStatus }) {
  return <Badge kind="review" value={value} label={REVIEW_STATUS_LABEL[value] ?? value} />
}

export function ResolutionBadge({ value }: { value: ResolutionStatus }) {
  return <Badge kind="resolution" value={value} label={RESOLUTION_STATUS_LABEL[value] ?? value} />
}

export function DocumentClassBadge({ value }: { value: DocumentClass }) {
  return <Badge kind="class" value={value} label={DOCUMENT_CLASS_LABEL[value] ?? value} />
}

/** §10.5 — "Badge backend thật/mock/fallback". Never hide a degraded backend. */
export function BackendModeBadge({ value, detail }: { value: BackendMode; detail?: string }) {
  return <Badge kind="backend" value={value} label={BACKEND_MODE_LABEL[value] ?? value} title={detail} />
}
