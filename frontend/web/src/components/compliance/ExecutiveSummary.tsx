/**
 * Executive summary — §10.4 requires the counts of compliant, non-compliant,
 * outdated, missing evidence and ambiguous claims on the report screen.
 */
import { COMPLIANCE_STATUS_LABEL } from '@/lib/labels'
import type { ComplianceReportSummary } from '@/types/api'
import type { ComplianceStatus } from '@/types/domain'

/** Order shown to the officer: problems first, compliant last. */
const ROWS: Array<{ key: keyof ComplianceReportSummary; status: ComplianceStatus }> = [
  { key: 'non_compliant', status: 'NON_COMPLIANT' },
  { key: 'outdated_reference', status: 'OUTDATED_REFERENCE' },
  { key: 'partially_compliant', status: 'PARTIALLY_COMPLIANT' },
  { key: 'missing_evidence', status: 'MISSING_EVIDENCE' },
  { key: 'ambiguous', status: 'AMBIGUOUS' },
  { key: 'needs_human_review', status: 'NEEDS_HUMAN_REVIEW' },
  { key: 'compliant', status: 'COMPLIANT' },
]

export function ExecutiveSummary({ summary }: { summary: ComplianceReportSummary }) {
  return (
    <section className="summary" data-testid="executive-summary" aria-label="Tổng hợp kết quả">
      <div className="summary__total">
        <span className="summary__total-label">Tổng số claim</span>
        <strong className="summary__total-value" data-testid="summary-total">
          {summary.total_claims}
        </strong>
      </div>

      <ul className="summary__breakdown">
        {ROWS.map(({ key, status }) => (
          <li key={key} className="summary__item" data-status={status}>
            <span className="summary__item-label">{COMPLIANCE_STATUS_LABEL[status]}</span>
            <strong className="summary__item-value" data-testid={`summary-${status}`}>
              {summary[key] ?? 0}
            </strong>
          </li>
        ))}
      </ul>
    </section>
  )
}
