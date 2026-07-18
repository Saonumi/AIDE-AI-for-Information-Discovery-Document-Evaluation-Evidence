'use client'

/**
 * Nav #10 — Audit & System Health.
 *
 * Phụ lục D #12 requires the officer to be able to see exactly which backend is
 * serving PostgreSQL / OpenSearch / Neo4j / LLM / embedding, and §4.2 forbids a
 * silent fallback — so every component's mode is listed, not summarised away.
 */
import { useCallback } from 'react'
import { ApiErrorBanner, DataSourceBanner } from '@/components/common/Banners'
import { BackendModeBadge } from '@/components/common/StatusBadge'
import { EmptyState, LoadingState, PageHeader } from '@/components/layout/PageHeader'
import { useResource } from '@/hooks/useResource'
import { api } from '@/lib/api'
import { formatDateTime } from '@/lib/labels'

export default function AuditHealthPage() {
  const healthFetcher = useCallback(() => api.healthDetails(), [])
  const auditFetcher = useCallback(() => api.audit(), [])
  const health = useResource(healthFetcher)
  const audit = useResource(auditFetcher)

  return (
    <main className="page" data-testid="page-audit-health">
      <PageHeader
        navOrder={10}
        title="Audit & System Health"
        subtitle="Mọi thay đổi trạng thái đều ghi AuditEvent với actor, thời điểm và before/after."
      />

      <section className="page__section">
        <h2 className="page__section-title">Backend đang dùng</h2>
        <DataSourceBanner source={health.source} />
        <ApiErrorBanner code={health.code} message={health.error} />

        {health.loading ? (
          <LoadingState />
        ) : (
          <table className="table" data-testid="health-table">
            <thead>
              <tr>
                <th>Thành phần</th>
                <th>Chế độ</th>
                <th>Tình trạng</th>
                <th>Chi tiết</th>
              </tr>
            </thead>
            <tbody>
              {(health.data?.components ?? []).map((c) => (
                <tr key={c.name} data-component={c.name} data-mode={c.mode}>
                  <td>{c.name}</td>
                  <td>
                    <BackendModeBadge value={c.mode} />
                  </td>
                  <td>{c.healthy ? 'OK' : 'Suy giảm'}</td>
                  <td>{c.detail ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {health.data && (
          <p className="form__hint">
            demo_mode = <code>{String(health.data.demo_mode)}</code> · status = <code>{health.data.status}</code>
          </p>
        )}
      </section>

      <section className="page__section">
        <h2 className="page__section-title">Audit trail</h2>
        <DataSourceBanner source={audit.source} />
        <ApiErrorBanner code={audit.code} message={audit.error} />

        {audit.loading ? (
          <LoadingState />
        ) : !audit.data?.length ? (
          <EmptyState label="Chưa có bản ghi audit." />
        ) : (
          <table className="table" data-testid="audit-table">
            <thead>
              <tr>
                <th>Thời điểm</th>
                <th>Actor</th>
                <th>Hành động</th>
                <th>Đối tượng</th>
                <th>Before → After</th>
              </tr>
            </thead>
            <tbody>
              {audit.data.map((e, i) => (
                <tr key={e.audit_id ?? i}>
                  <td>{formatDateTime(e.timestamp)}</td>
                  <td>{e.actor}</td>
                  <td>{e.action}</td>
                  <td>
                    {e.entity} {e.entity_id ? <code>{e.entity_id}</code> : null}
                  </td>
                  <td>
                    <code>{JSON.stringify(e.before)}</code> → <code>{JSON.stringify(e.after)}</code>
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
