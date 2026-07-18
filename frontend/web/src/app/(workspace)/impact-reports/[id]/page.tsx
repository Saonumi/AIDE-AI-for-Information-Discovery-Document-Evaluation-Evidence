'use client'

/**
 * Regulatory Impact Report detail — Phụ lục D #7: "xem policy clause bị ảnh
 * hưởng cùng evidence lineage".
 *
 * §1.5 fixes the required content: ChangeEvent, before/after, effective date,
 * impacted policy clauses, severity, evidence lineage.
 */
import { use, useCallback } from 'react'
import { ApiErrorBanner, DataSourceBanner } from '@/components/common/Banners'
import { SeverityBadge } from '@/components/common/StatusBadge'
import { LoadingState, PageHeader } from '@/components/layout/PageHeader'
import { LineageGraph, type LineageEdge, type LineageNode } from '@/components/graph/LineageGraph'
import { useResource } from '@/hooks/useResource'
import { api } from '@/lib/api'
import { AMENDMENT_OPERATION_LABEL, formatDateTime } from '@/lib/labels'

export default function ImpactReportDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const fetcher = useCallback(() => api.impactReport(id), [id])
  const report = useResource(fetcher)

  const data = report.data
  // §6.3 makes only the ID arrays mandatory; default the expanded collections so
  // a spec-minimal payload renders a "chưa mở rộng" notice instead of crashing.
  const changeEvents = data?.change_events ?? []
  const clauses = data?.impacted_policy_clauses ?? []
  const changesUnexpanded = !data?.change_events && (data?.change_event_ids?.length ?? 0) > 0
  const clausesUnexpanded = !data?.impacted_policy_clauses && (data?.impacted_policy_ids?.length ?? 0) > 0
  const unexpanded = changesUnexpanded || clausesUnexpanded

  // lineage: source document -> change event -> impacted policy clause -> evidence
  const nodes: LineageNode[] = data
    ? [
        { id: 'source', kind: 'Document', label: data.source_document_number ?? data.source_document_id },
        ...changeEvents.map((c) => ({
          id: c.change_event_id,
          kind: 'ChangeEvent' as const,
          label: `${c.operation} · ${c.provision_locator}`,
        })),
        ...clauses.map((p) => ({
          id: p.policy_clause_id,
          kind: 'PolicyClause' as const,
          label: `${p.policy_document_title ?? ''} ${p.locator ?? ''}`.trim(),
        })),
      ]
    : []

  /**
   * Link each policy clause to the change events it actually shares evidence
   * with. Joining every clause to every change event would draw edges the data
   * does not support — on the fixture that asserts a repeal of Điều 15 impacts
   * the SME credit-limit clause, which is false. A clause with no shared
   * evidence gets no edge rather than a guessed one.
   */
  const edges: LineageEdge[] = data
    ? [
        ...changeEvents.map((c) => ({ from: 'source', to: c.change_event_id, relation: 'DECLARES' })),
        ...clauses.flatMap((p) => {
          const spanIds = new Set(p.evidence_span_ids ?? [])
          return changeEvents
            .filter((c) => (c.evidence_span_id ? spanIds.has(c.evidence_span_id) : false))
            .map((c) => ({ from: c.change_event_id, to: p.policy_clause_id, relation: 'IMPACTS' }))
        }),
      ]
    : []

  return (
    <main className="page" data-testid="page-impact-report-detail">
      <PageHeader title="Regulatory Impact Report" subtitle={`Nguồn: ${id}`} />

      <DataSourceBanner source={report.source} />
      <ApiErrorBanner code={report.code} message={report.error} />

      {report.loading ? (
        <LoadingState />
      ) : !data ? (
        <div className="state">Không có báo cáo cho tài liệu này.</div>
      ) : (
        <>
          <section className="page__section">
            <p>{data.summary}</p>
            <p className="form__hint">
              Trạng thái: {data.status} · Tạo lúc: {formatDateTime(data.generated_at)}
            </p>
          </section>

          {unexpanded && (
            <div className="banner banner--info" role="status" data-testid="banner-unexpanded-changes">
              <strong>Báo cáo chỉ trả về ID.</strong>
              <span>
                {changesUnexpanded && `${data.change_event_ids.length} ChangeEvent chưa mở rộng chi tiết. `}
                {clausesUnexpanded &&
                  `${data.impacted_policy_ids?.length} điều khoản policy bị ảnh hưởng chưa mở rộng chi tiết. `}
                Cần gọi thêm endpoint chi tiết cho từng mục.
              </span>
            </div>
          )}

          <section className="page__section">
            <h2 className="page__section-title">ChangeEvent ({changeEvents.length})</h2>
            <table className="table" data-testid="impact-change-events">
              <thead>
                <tr>
                  <th>Thao tác</th>
                  <th>Điều khoản</th>
                  <th>Version trước → sau</th>
                  <th>Ngày hiệu lực</th>
                </tr>
              </thead>
              <tbody>
                {changeEvents.map((c) => (
                  <tr key={c.change_event_id}>
                    <td>{AMENDMENT_OPERATION_LABEL[c.operation] ?? c.operation}</td>
                    <td>
                      {c.target_document_number} › {c.provision_locator}
                    </td>
                    <td>
                      <code>{c.before_version_id ?? '—'}</code> → <code>{c.after_version_id ?? 'đóng hiệu lực'}</code>
                    </td>
                    <td>{c.effective_date ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="page__section">
            <h2 className="page__section-title">
              Điều khoản policy bị ảnh hưởng ({clauses.length})
            </h2>
            {clauses.map((p) => (
              <article key={p.policy_clause_id} className="proposal" data-policy-clause-id={p.policy_clause_id}>
                <header className="proposal__header">
                  <div className="proposal__identity">
                    <h4 className="proposal__operation">
                      {p.policy_document_title} {p.locator ? `› ${p.locator}` : ''}
                    </h4>
                    <p className="proposal__target">Chủ sở hữu: {p.owner ?? '—'}</p>
                  </div>
                  <div className="proposal__badges">
                    <SeverityBadge value={p.severity} />
                  </div>
                </header>
                {p.content && <p>{p.content}</p>}
                {p.recommended_action && (
                  <p>
                    <strong>Đề xuất hành động:</strong> {p.recommended_action}
                  </p>
                )}
              </article>
            ))}
          </section>

          <section className="page__section">
            <h2 className="page__section-title">Evidence lineage</h2>
            <LineageGraph nodes={nodes} edges={edges} />
          </section>
        </>
      )}
    </main>
  )
}
