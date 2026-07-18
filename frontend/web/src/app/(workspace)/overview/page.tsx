'use client'

/** Nav #1 — Tổng quan. Counters for both workflows plus the two entry actions. */
import { useCallback } from 'react'
import Link from 'next/link'
import { DataSourceBanner, ApiErrorBanner } from '@/components/common/Banners'
import { DocumentClassBadge, LifecycleBadge, TrustClassBadge } from '@/components/common/StatusBadge'
import { EmptyState, LoadingState, PageHeader } from '@/components/layout/PageHeader'
import { useResource } from '@/hooks/useResource'
import { api } from '@/lib/api'
import { UPLOAD_PURPOSE_LABEL } from '@/lib/labels'
import type { DocumentSummary } from '@/types/api'

export default function OverviewPage() {
  const statsFetcher = useCallback(() => api.overview(), [])
  const docsFetcher = useCallback(() => api.documents(), [])
  const stats = useResource(statsFetcher)
  const docs = useResource(docsFetcher)

  return (
    <main className="page" data-testid="page-overview">
      <PageHeader
        navOrder={1}
        title="Tổng quan"
        subtitle="Trạng thái kho pháp lý đã xác minh và các việc đang chờ Compliance Officer xử lý."
      />

      <DataSourceBanner source={stats.source} />
      <ApiErrorBanner code={stats.code} message={stats.error} />

      <section className="page__section">
        <div className="landing__cards">
          <Link href="/regulatory-sources/new" className="landing__card" data-testid="card-add-regulatory-source">
            <h2>Add Regulatory Source</h2>
            <p>Thêm thông tư/quyết định/amendment — phải review và approve trước khi thành nguồn pháp lý.</p>
          </Link>
          <Link href="/compliance-checks/new" className="landing__card" data-testid="card-check-document-compliance">
            <h2>Check Document Compliance</h2>
            <p>Upload policy/báo cáo để kiểm tra — file không trở thành ground truth.</p>
          </Link>
        </div>
      </section>

      <section className="page__section">
        <h2 className="page__section-title">Chỉ số</h2>
        {stats.loading ? (
          <LoadingState />
        ) : (
          <div className="stat-grid">
            <Stat label="Nguồn pháp lý đang hiệu lực" value={stats.data?.authority_sources_active} />
            <Stat label="Nguồn chờ rà soát" value={stats.data?.sources_pending_review} href="/source-review-inbox" />
            <Stat label="Thay đổi gần đây" value={stats.data?.change_events_recent} href="/regulatory-changes" />
            <Stat label="Policy link chờ duyệt" value={stats.data?.policy_links_pending} href="/policy-mapping" />
            <Stat label="Compliance check đang mở" value={stats.data?.compliance_checks_open} href="/compliance-reports" />
            <Stat label="Claim cần xử lý" value={stats.data?.claims_needing_action} href="/compliance-reports" />
          </div>
        )}
      </section>

      <section className="page__section">
        <h2 className="page__section-title">Tài liệu trong hệ thống</h2>
        <DataSourceBanner source={docs.source} />
        <ApiErrorBanner code={docs.code} message={docs.error} />
        {docs.loading ? (
          <LoadingState />
        ) : !docs.data?.length ? (
          <EmptyState label="Chưa có tài liệu nào." />
        ) : (
          <table className="table" data-testid="documents-table">
            <thead>
              <tr>
                <th>Số hiệu / Tên</th>
                <th>Loại</th>
                <th>Mục đích upload</th>
                <th>Trust class</th>
                <th>Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {docs.data.map((d) => (
                <tr key={d.document_id}>
                  <td>
                    {(() => {
                      const href = detailHref(d)
                      const label = d.document_number ?? d.title ?? d.filename ?? d.document_id
                      return href ? <Link href={href}>{label}</Link> : label
                    })()}
                  </td>
                  <td>
                    <DocumentClassBadge value={d.document_class} />
                  </td>
                  <td>{d.upload_purpose ? (UPLOAD_PURPOSE_LABEL[d.upload_purpose] ?? d.upload_purpose) : '—'}</td>
                  <td>
                    <TrustClassBadge value={d.trust_class} />
                  </td>
                  <td>
                    <LifecycleBadge value={d.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  )
}

/**
 * Review targets and regulatory sources live in different detail screens (§2.4).
 *
 * A review target is addressed by its check_id, which is NOT its document_id —
 * so when the backend has not supplied one there is no link to build, and the
 * row stays plain text rather than pointing at a check that does not exist.
 */
function detailHref(doc: DocumentSummary): string | null {
  if (doc.document_class === 'REVIEW_DOCUMENT' || doc.upload_purpose === 'CHECK_DOCUMENT_COMPLIANCE') {
    return doc.check_id ? `/compliance-checks/${doc.check_id}` : null
  }
  return `/regulatory-sources/${doc.document_id}`
}

function Stat({ label, value, href }: { label: string; value?: number; href?: string }) {
  const body = (
    <>
      <span className="stat__value">{value ?? '—'}</span>
      <span className="stat__label">{label}</span>
    </>
  )
  return href ? (
    <Link href={href} className="stat">
      {body}
    </Link>
  ) : (
    <div className="stat">{body}</div>
  )
}
