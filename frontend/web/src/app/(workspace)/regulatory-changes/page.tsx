'use client'

/** Nav #4 — Regulatory Changes: every ChangeEvent produced by activated sources. */
import { useCallback } from 'react'
import Link from 'next/link'
import { ApiErrorBanner, DataSourceBanner } from '@/components/common/Banners'
import { LifecycleBadge } from '@/components/common/StatusBadge'
import { EmptyState, LoadingState, PageHeader } from '@/components/layout/PageHeader'
import { useResource } from '@/hooks/useResource'
import { api } from '@/lib/api'
import { AMENDMENT_OPERATION_LABEL } from '@/lib/labels'

export default function RegulatoryChangesPage() {
  const fetcher = useCallback(() => api.changeEvents(), [])
  const changes = useResource(fetcher)

  return (
    <main className="page" data-testid="page-regulatory-changes">
      <PageHeader
        navOrder={4}
        title="Regulatory Changes"
        subtitle="Điều/Khoản/Điểm nào bị sửa, bởi văn bản nào, có hiệu lực từ khi nào."
      />

      <DataSourceBanner source={changes.source} />
      <ApiErrorBanner code={changes.code} message={changes.error} />

      {changes.loading ? (
        <LoadingState />
      ) : !changes.data?.length ? (
        <EmptyState label="Chưa có ChangeEvent nào." />
      ) : (
        <table className="table" data-testid="change-events-table">
          <thead>
            <tr>
              <th>Thao tác</th>
              <th>Điều khoản bị tác động</th>
              <th>Văn bản sửa đổi</th>
              <th>Version trước → sau</th>
              <th>Ngày hiệu lực</th>
              <th>Trạng thái</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {changes.data.map((c) => (
              <tr key={c.change_event_id} data-change-id={c.change_event_id}>
                <td>{AMENDMENT_OPERATION_LABEL[c.operation] ?? c.operation}</td>
                <td>
                  {c.target_document_number} › {c.provision_locator}
                </td>
                <td>{c.source_document_number ?? '—'}</td>
                <td>
                  <code>{c.before_version_id ?? '—'}</code> → <code>{c.after_version_id ?? 'đóng hiệu lực'}</code>
                </td>
                <td>{c.effective_date ?? '—'}</td>
                <td>{c.status ? <LifecycleBadge value={c.status} /> : '—'}</td>
                <td>
                  <Link href={`/regulatory-changes/${c.change_event_id}`}>Chi tiết →</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  )
}
