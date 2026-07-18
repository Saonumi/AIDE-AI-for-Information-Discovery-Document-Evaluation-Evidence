'use client'

/** Nav #8 — Compliance Review Reports (list of past and open checks). */
import { useCallback } from 'react'
import Link from 'next/link'
import { ApiErrorBanner, DataSourceBanner } from '@/components/common/Banners'
import { LifecycleBadge, TrustClassBadge } from '@/components/common/StatusBadge'
import { EmptyState, LoadingState, PageHeader } from '@/components/layout/PageHeader'
import { useResource } from '@/hooks/useResource'
import { api } from '@/lib/api'

export default function ComplianceReportsPage() {
  const fetcher = useCallback(() => api.complianceReports(), [])
  const reports = useResource(fetcher)

  return (
    <main className="page" data-testid="page-compliance-reports">
      <PageHeader
        navOrder={8}
        title="Compliance Review Reports"
        subtitle="Kết quả kiểm tra các policy, báo cáo và tài liệu nội bộ đã upload."
      />

      <DataSourceBanner source={reports.source} />
      <ApiErrorBanner code={reports.code} message={reports.error} />

      {reports.loading ? (
        <LoadingState />
      ) : !reports.data?.length ? (
        <EmptyState label="Chưa có báo cáo kiểm tra nào." />
      ) : (
        <table className="table" data-testid="compliance-reports-table">
          <thead>
            <tr>
              <th>Tài liệu</th>
              <th>Ngày review</th>
              <th>Tổng claim</th>
              <th>Không phù hợp</th>
              <th>Dùng bản cũ</th>
              <th>Cần người xác nhận</th>
              <th>Trạng thái</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {reports.data.map((r) => (
              <tr key={r.report_id ?? r.target_document_id}>
                <td>
                  {r.target_document_title ?? r.target_document_id}{' '}
                  <TrustClassBadge value="REVIEW_TARGET" />
                </td>
                <td>{r.review_date}</td>
                <td>{r.summary?.total_claims ?? '—'}</td>
                <td>{r.summary?.non_compliant ?? '—'}</td>
                <td>{r.summary?.outdated_reference ?? '—'}</td>
                <td>{r.summary?.needs_human_review ?? '—'}</td>
                <td>
                  <LifecycleBadge value={r.status} />
                </td>
                <td>
                  {/* A report is opened by its check_id. Deriving one by trimming
                      a prefix off report_id only works for fixture naming, so a
                      report without check_id gets no link rather than a wrong one. */}
                  {r.check_id ? (
                    <Link href={`/compliance-checks/${r.check_id}`}>Mở báo cáo →</Link>
                  ) : (
                    <span className="claim__empty">Thiếu check_id</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  )
}
