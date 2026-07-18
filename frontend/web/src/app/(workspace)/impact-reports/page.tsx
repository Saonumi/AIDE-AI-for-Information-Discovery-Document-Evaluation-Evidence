'use client'

/** Nav #6 — Regulatory Impact Reports (list). */
import { useCallback } from 'react'
import Link from 'next/link'
import { ApiErrorBanner, DataSourceBanner } from '@/components/common/Banners'
import { LifecycleBadge } from '@/components/common/StatusBadge'
import { EmptyState, LoadingState, PageHeader } from '@/components/layout/PageHeader'
import { useResource } from '@/hooks/useResource'
import { api } from '@/lib/api'
import { formatDateTime } from '@/lib/labels'

export default function ImpactReportsPage() {
  const fetcher = useCallback(() => api.impactReports(), [])
  const reports = useResource(fetcher)

  return (
    <main className="page" data-testid="page-impact-reports">
      <PageHeader
        navOrder={6}
        title="Regulatory Impact Reports"
        subtitle="Sinh ra sau khi một nguồn pháp lý được approve và activate: thay đổi nào ảnh hưởng policy nội bộ nào."
      />

      <DataSourceBanner source={reports.source} />
      <ApiErrorBanner code={reports.code} message={reports.error} />

      {reports.loading ? (
        <LoadingState />
      ) : !reports.data?.length ? (
        <EmptyState label="Chưa có báo cáo tác động nào." />
      ) : (
        <table className="table" data-testid="impact-reports-table">
          <thead>
            <tr>
              <th>Văn bản nguồn</th>
              <th>Số ChangeEvent</th>
              <th>Policy bị ảnh hưởng</th>
              <th>Trạng thái</th>
              <th>Tạo lúc</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {reports.data.map((r) => (
              <tr key={r.report_id} data-report-id={r.report_id}>
                <td>{r.source_document_number ?? r.source_document_id}</td>
                <td>{r.change_event_ids?.length ?? 0}</td>
                <td>{r.impacted_policy_clauses?.length ?? r.impacted_policy_ids?.length ?? 0}</td>
                <td>
                  <LifecycleBadge value={r.status} />
                </td>
                <td>{formatDateTime(r.generated_at)}</td>
                <td>
                  <Link href={`/impact-reports/${r.source_document_id}`}>Mở báo cáo →</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  )
}
