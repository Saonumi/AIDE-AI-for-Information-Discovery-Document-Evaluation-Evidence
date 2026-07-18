/**
 * Report normalisation.
 *
 * Phụ lục B.3 serialises `assessments` as a list of claim IDs, but §10.4 needs
 * the expanded assessment on screen. Rather than trusting one shape and crashing
 * on the other, everything goes through here.
 */
import type { ClaimAssessment, ComplianceReviewReport } from '@/types/api'

export interface NormalisedAssessments {
  /** Fully expanded assessments the UI can render. */
  expanded: ClaimAssessment[]
  /** Claim IDs the backend referenced but did not expand. */
  unexpandedIds: string[]
}

export function expandAssessments(report?: ComplianceReviewReport): NormalisedAssessments {
  const raw = report?.assessments ?? []
  const expanded: ClaimAssessment[] = []
  const unexpandedIds: string[] = []

  for (const item of raw) {
    if (typeof item === 'string') unexpandedIds.push(item)
    else if (item && typeof item === 'object' && 'claim_id' in item) expanded.push(item)
  }

  return { expanded, unexpandedIds }
}
