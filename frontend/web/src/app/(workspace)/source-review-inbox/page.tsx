'use client'

/** Nav #3 — Source Review Inbox: every pending HITL unit across Workflow A. */
import { useCallback } from 'react'
import Link from 'next/link'
import { ApiErrorBanner, DataSourceBanner } from '@/components/common/Banners'
import { ReviewStatusBadge, SeverityBadge, TrustClassBadge } from '@/components/common/StatusBadge'
import { EmptyState, LoadingState, PageHeader } from '@/components/layout/PageHeader'
import { useResource } from '@/hooks/useResource'
import { api } from '@/lib/api'
import { formatDateTime } from '@/lib/labels'

export default function SourceReviewInboxPage() {
  const fetcher = useCallback(() => api.reviewTasks(), [])
  const tasks = useResource(fetcher)

  return (
    <main className="page" data-testid="page-source-review-inbox">
      <PageHeader
        navOrder={3}
        title="Source Review Inbox"
        subtitle="Hàng đợi Human-in-the-loop. Nguồn chỉ trở thành AUTHORITY_SOURCE khi mọi review bắt buộc được xử lý."
      />

      <DataSourceBanner source={tasks.source} />
      <ApiErrorBanner code={tasks.code} message={tasks.error} />

      {tasks.loading ? (
        <LoadingState />
      ) : !tasks.data?.length ? (
        <EmptyState label="Không có nhiệm vụ rà soát nào đang chờ." />
      ) : (
        <table className="table" data-testid="review-tasks-table">
          <thead>
            <tr>
              <th>Loại</th>
              <th>Đối tượng</th>
              <th>Rủi ro</th>
              <th>Bắt buộc</th>
              <th>Trạng thái</th>
              <th>Tạo lúc</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {tasks.data.map((t) => (
              <tr key={t.task_id} data-task-id={t.task_id} data-critical={t.is_critical ? 'true' : 'false'}>
                <td>{t.task_type}</td>
                <td>
                  {t.target_label ?? t.target_id}
                  {t.document_id && (
                    <>
                      {' '}
                      <TrustClassBadge value="AUTHORITY_SOURCE_CANDIDATE" />
                    </>
                  )}
                </td>
                <td>{t.risk ? <SeverityBadge value={t.risk} /> : '—'}</td>
                <td>{t.is_critical ? 'Có' : 'Không'}</td>
                <td>
                  <ReviewStatusBadge value={t.status} />
                </td>
                <td>{formatDateTime(t.created_at)}</td>
                <td>
                  {t.document_id ? (
                    <Link href={`/regulatory-sources/${t.document_id}`}>Mở review package →</Link>
                  ) : (
                    <Link href="/policy-mapping">Mở policy mapping →</Link>
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
