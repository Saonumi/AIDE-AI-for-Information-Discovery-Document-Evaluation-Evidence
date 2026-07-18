'use client'

/** §10.4 — "Claim list với filter theo status/severity." */
import { COMPLIANCE_STATUS_LABEL, SEVERITY_LABEL } from '@/lib/labels'
import { COMPLIANCE_STATUS, SEVERITY, type ComplianceStatus, type Severity } from '@/types/domain'

export interface ClaimFilterValue {
  status: ComplianceStatus | ''
  severity: Severity | ''
}

export function ClaimFilters({
  value,
  onChange,
  counts,
}: {
  value: ClaimFilterValue
  onChange: (next: ClaimFilterValue) => void
  counts?: { shown: number; total: number }
}) {
  return (
    <div className="filters" data-testid="claim-filters">
      <label className="filters__field">
        <span>Trạng thái</span>
        <select
          value={value.status}
          onChange={(e) => onChange({ ...value, status: e.target.value as ComplianceStatus | '' })}
          data-testid="filter-status"
        >
          <option value="">Tất cả</option>
          {Object.values(COMPLIANCE_STATUS).map((s) => (
            <option key={s} value={s}>
              {COMPLIANCE_STATUS_LABEL[s]}
            </option>
          ))}
        </select>
      </label>

      <label className="filters__field">
        <span>Mức độ</span>
        <select
          value={value.severity}
          onChange={(e) => onChange({ ...value, severity: e.target.value as Severity | '' })}
          data-testid="filter-severity"
        >
          <option value="">Tất cả</option>
          {Object.values(SEVERITY).map((s) => (
            <option key={s} value={s}>
              {SEVERITY_LABEL[s]}
            </option>
          ))}
        </select>
      </label>

      {counts && (
        <span className="filters__count">
          Hiển thị {counts.shown}/{counts.total} claim
        </span>
      )}
    </div>
  )
}
