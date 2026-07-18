'use client'

/**
 * Regulatory change detail — the `regulatory_change_detail` screen from §10.6.
 * Shows one ChangeEvent's before/after, its effective date, and its lineage back
 * to the source document and evidence.
 */
import { use, useCallback } from 'react'
import Link from 'next/link'
import { ApiErrorBanner, DataSourceBanner } from '@/components/common/Banners'
import { LoadingState, PageHeader } from '@/components/layout/PageHeader'
import { BeforeAfterDiff } from '@/components/review/BeforeAfterDiff'
import { LineageGraph, type LineageEdge, type LineageNode } from '@/components/graph/LineageGraph'
import { useResource } from '@/hooks/useResource'
import { api } from '@/lib/api'
import { AMENDMENT_OPERATION_LABEL } from '@/lib/labels'

export default function RegulatoryChangeDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const fetcher = useCallback(() => api.changeEvents(), [])
  const changes = useResource(fetcher)

  const change = changes.data?.find((c) => c.change_event_id === id)

  const nodes: LineageNode[] = change
    ? [
        { id: 'src', kind: 'Document', label: change.source_document_number ?? 'Văn bản sửa đổi' },
        { id: 'chg', kind: 'ChangeEvent', label: `${change.operation} · ${change.provision_locator}` },
        { id: 'before', kind: 'ProvisionVersion', label: change.before_version_id ?? 'version trước' },
        { id: 'after', kind: 'ProvisionVersion', label: change.after_version_id ?? 'đóng hiệu lực' },
      ]
    : []

  const edges: LineageEdge[] = change
    ? [
        { from: 'src', to: 'chg', relation: 'DECLARES' },
        { from: 'chg', to: 'before', relation: 'SUPERSEDES' },
        { from: 'chg', to: 'after', relation: 'PRODUCES' },
      ]
    : []

  return (
    <main className="page" data-testid="page-regulatory-change-detail">
      <PageHeader title="Chi tiết thay đổi" subtitle={id} />

      <DataSourceBanner source={changes.source} />
      <ApiErrorBanner code={changes.code} message={changes.error} />

      {changes.loading ? (
        <LoadingState />
      ) : !change ? (
        <div className="state">Không tìm thấy ChangeEvent {id}.</div>
      ) : (
        <>
          <section className="page__section">
            <h2 className="page__section-title">
              {AMENDMENT_OPERATION_LABEL[change.operation] ?? change.operation} ·{' '}
              {change.target_document_number} › {change.provision_locator}
            </h2>
            <BeforeAfterDiff
              before={change.before_text ?? `Version ${change.before_version_id ?? '—'}`}
              after={change.after_text ?? null}
              effectiveDate={change.effective_date}
              operation={change.operation}
            />
            <p className="form__hint">
              Version: <code>{change.before_version_id ?? '—'}</code> →{' '}
              <code>{change.after_version_id ?? 'đóng hiệu lực'}</code> · trạng thái {change.status ?? '—'}
            </p>
          </section>

          <section className="page__section">
            <h2 className="page__section-title">Evidence lineage</h2>
            <LineageGraph nodes={nodes} edges={edges} />
          </section>

          <p className="page__section">
            <Link href="/regulatory-changes">← Danh sách thay đổi</Link>
          </p>
        </>
      )}
    </main>
  )
}
