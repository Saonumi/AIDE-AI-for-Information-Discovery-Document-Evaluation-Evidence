'use client'

/**
 * Nav #5 — Policy Mapping: which internal policy clause implements/references
 * which provision, with the evidence and review status behind that link.
 *
 * Phụ lục C: the reviewer must check "policy clause thực sự dựa trên provision
 * nào, evidence và scope có phù hợp không" — so confidence and review status are
 * first-class columns, not tooltips.
 */
import { useCallback, useState } from 'react'
import { ApiErrorBanner, DataSourceBanner } from '@/components/common/Banners'
import { ReviewStatusBadge, TrustClassBadge } from '@/components/common/StatusBadge'
import { EmptyState, LoadingState, PageHeader } from '@/components/layout/PageHeader'
import { useResource } from '@/hooks/useResource'
import { api } from '@/lib/api'
import { formatConfidence, REVIEW_STATUS_LABEL } from '@/lib/labels'
import { REVIEW_STATUS, type ReviewStatus } from '@/types/domain'

export default function PolicyMappingPage() {
  const fetcher = useCallback(() => api.policyLinks(), [])
  const links = useResource(fetcher)
  const [filter, setFilter] = useState<ReviewStatus | ''>('')

  const rows = (links.data ?? []).filter((l) => !filter || l.review_status === filter)

  return (
    <main className="page" data-testid="page-policy-mapping">
      <PageHeader
        navOrder={5}
        title="Policy Mapping"
        subtitle="Liên kết giữa điều khoản policy nội bộ và provision pháp lý — nền tảng cho phân tích tác động."
      />

      <DataSourceBanner source={links.source} />
      <ApiErrorBanner code={links.code} message={links.error} />

      <div className="filters">
        <label className="filters__field">
          <span>Trạng thái duyệt</span>
          <select value={filter} onChange={(e) => setFilter(e.target.value as ReviewStatus | '')} data-testid="filter-review-status">
            <option value="">Tất cả</option>
            {Object.values(REVIEW_STATUS).map((s) => (
              <option key={s} value={s}>
                {REVIEW_STATUS_LABEL[s]}
              </option>
            ))}
          </select>
        </label>
        <span className="filters__count">
          Hiển thị {rows.length}/{links.data?.length ?? 0} liên kết
        </span>
      </div>

      {links.loading ? (
        <LoadingState />
      ) : rows.length === 0 ? (
        <EmptyState label="Không có policy link nào khớp bộ lọc." />
      ) : (
        <table className="table" data-testid="policy-links-table">
          <thead>
            <tr>
              <th>Điều khoản policy</th>
              <th>Quan hệ</th>
              <th>Provision pháp lý</th>
              <th>Chủ sở hữu</th>
              <th>Confidence</th>
              <th>Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((l) => (
              <tr key={l.policy_link_id} data-link-id={l.policy_link_id}>
                <td>
                  {l.policy_document_title}
                  {l.policy_locator ? ` › ${l.policy_locator}` : ''}{' '}
                  {/* §10.5: state plainly that an internal policy is not legal ground truth */}
                  <TrustClassBadge value="INTERNAL_APPROVED" />
                </td>
                <td>
                  <code>{l.relation}</code>
                </td>
                <td>
                  {l.provision_locator ?? l.provision_id} <TrustClassBadge value="AUTHORITY_SOURCE" />
                </td>
                <td>{l.owner ?? '—'}</td>
                <td>{formatConfidence(l.confidence)}</td>
                <td>
                  <ReviewStatusBadge value={l.review_status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  )
}
