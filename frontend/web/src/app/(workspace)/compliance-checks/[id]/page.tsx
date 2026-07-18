'use client'

/**
 * Compliance Review Report — spec §10.4.
 *
 *   - "File này chỉ được dùng để kiểm tra"       -> <ReviewTargetBanner>
 *   - review date và scope/domain hiển thị rõ    -> header meta
 *   - claim list với filter theo status/severity -> <ClaimFilters>
 *   - mỗi claim: nội dung gốc, assessment, legal
 *     evidence, version/date, explanation,
 *     recommendation                             -> <ClaimAssessmentCard>
 *   - Confirm/Dismiss/Edit/Needs action          -> card actions
 *   - executive summary các nhóm status          -> <ExecutiveSummary>
 *
 * §10.5 also demands "Citation mở được đúng trang/evidence span", so clicking a
 * citation opens the cited legal source in the viewer panel — the evidence lives
 * in the regulation, not in the uploaded review target.
 */
import { use, useCallback, useMemo, useState } from 'react'
import { ApiErrorBanner, DataSourceBanner, ReviewTargetBanner } from '@/components/common/Banners'
import { PipelineSteps } from '@/components/common/PipelineSteps'
import { LifecycleBadge, TrustClassBadge } from '@/components/common/StatusBadge'
import { ClaimFilters, type ClaimFilterValue } from '@/components/compliance/ClaimFilters'
import { ClaimAssessmentCard } from '@/components/compliance/ClaimAssessmentCard'
import { ExecutiveSummary } from '@/components/compliance/ExecutiveSummary'
import { DocumentViewer } from '@/components/document/DocumentViewer'
import { EmptyState, LoadingState, PageHeader } from '@/components/layout/PageHeader'
import { useResource } from '@/hooks/useResource'
import { api } from '@/lib/api'
import { formatLocator, REVIEW_TARGET_STATUS_LABEL } from '@/lib/labels'
import { expandAssessments } from '@/lib/report'
import { REVIEW_TARGET_PIPELINE_STEPS, type ReviewerAction } from '@/types/domain'
import type { EvidenceSpan } from '@/types/api'

export default function ComplianceCheckReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)

  const statusFetcher = useCallback(() => api.complianceCheck(id), [id])
  const reportFetcher = useCallback(() => api.complianceReport(id), [id])
  const status = useResource(statusFetcher)
  const report = useResource(reportFetcher)

  const [filter, setFilter] = useState<ClaimFilterValue>({ status: '', severity: '' })
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState<{ code?: string; message?: string }>()
  const [openSpanId, setOpenSpanId] = useState<string | null>(null)
  const [viewerPage, setViewerPage] = useState(1)

  const { expanded, unexpandedIds } = useMemo(() => expandAssessments(report.data), [report.data])

  /**
   * Citations reference provisions in approved legal sources; turn them into
   * viewer spans so a click can open the exact page (§10.5).
   */
  const citedSpans: EvidenceSpan[] = useMemo(
    () =>
      expanded.flatMap((a) =>
        a.valid_evidence
          .filter((e) => e.evidence_span_id && e.page != null)
          .map((e) => ({
            evidence_span_id: e.evidence_span_id!,
            document_id: e.document_number ?? 'unknown',
            page: e.page!,
            text: e.text ?? formatLocator(e),
            extractor: 'citation',
          })),
      ),
    [expanded],
  )

  const openSpan = citedSpans.find((s) => s.evidence_span_id === openSpanId)

  const filtered = useMemo(
    () =>
      expanded.filter(
        (a) => (!filter.status || a.status === filter.status) && (!filter.severity || a.severity === filter.severity),
      ),
    [expanded, filter],
  )

  const openEvidence = useCallback((spanId: string, page: number) => {
    setOpenSpanId(spanId)
    setViewerPage(page)
  }, [])

  async function decide(taskOrClaimId: string, action: ReviewerAction, note?: string) {
    setBusy(true)
    setActionError(undefined)
    const res = await api.decideAssessment(id, taskOrClaimId, action, note)
    setBusy(false)
    if (!res.ok) {
      setActionError({ code: res.code, message: res.message })
      return
    }
    report.reload()
  }

  return (
    <main className="page page--wide" data-testid="page-compliance-report">
      <PageHeader title="Compliance Review Report" subtitle={report.data?.target_document_title ?? `Check ${id}`} />

      <ReviewTargetBanner />
      <DataSourceBanner source={report.source} />
      <ApiErrorBanner
        code={actionError?.code ?? report.code ?? status.code}
        message={actionError?.message ?? report.error ?? status.error}
      />

      <section className="page__section">
        <div className="page__meta-row">
          <TrustClassBadge value={status.data?.document.trust_class ?? 'REVIEW_TARGET'} />
          {status.data?.status && <LifecycleBadge value={status.data.status} />}
          <span data-testid="report-review-date">Ngày review: {report.data?.review_date ?? '—'}</span>
          <span data-testid="report-scope">
            Phạm vi: {report.data?.requested_scope?.length ? report.data.requested_scope.join(', ') : 'toàn bộ kho'}
          </span>
        </div>
        <PipelineSteps
          steps={REVIEW_TARGET_PIPELINE_STEPS}
          completed={status.data?.completed_steps ?? []}
          current={status.data?.status}
          labels={REVIEW_TARGET_STATUS_LABEL}
        />
      </section>

      {report.loading ? (
        <LoadingState />
      ) : !report.data ? (
        <EmptyState label="Chưa có báo cáo cho lần kiểm tra này." />
      ) : (
        <>
          <section className="page__section">
            <h2 className="page__section-title">Tổng hợp</h2>
            {report.data.summary ? (
              <ExecutiveSummary summary={report.data.summary} />
            ) : (
              <EmptyState label="Báo cáo không kèm phần tổng hợp (summary)." />
            )}
          </section>

          {unexpandedIds.length > 0 && (
            <div className="banner banner--info" role="status" data-testid="banner-unexpanded-claims">
              <strong>{unexpandedIds.length} claim chưa tải chi tiết.</strong>
              <span>
                Backend trả danh sách ID theo Phụ lục B.3 ({unexpandedIds.join(', ')}); cần gọi thêm endpoint chi tiết
                cho từng claim.
              </span>
            </div>
          )}

          {report.data.actions && report.data.actions.length > 0 && (
            <section className="page__section">
              <h2 className="page__section-title">Hành động theo dõi</h2>
              <table className="table" data-testid="report-actions">
                <thead>
                  <tr>
                    <th>Hành động</th>
                    <th>Claim</th>
                    <th>Chủ sở hữu</th>
                    <th>Hạn</th>
                    <th>Trạng thái</th>
                  </tr>
                </thead>
                <tbody>
                  {report.data.actions.map((a, i) => (
                    <tr key={a.action_id ?? i}>
                      <td>{a.action}</td>
                      <td>{a.claim_id ?? '—'}</td>
                      <td>{a.owner ?? '—'}</td>
                      <td>{a.due_date ?? '—'}</td>
                      <td>{a.status ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          <section className="page__section">
            <h2 className="page__section-title">Danh sách claim</h2>
            <ClaimFilters
              value={filter}
              onChange={setFilter}
              counts={{ shown: filtered.length, total: expanded.length }}
            />

            <div className="review-split">
              <div className="review-split__details">
                {filtered.length === 0 ? (
                  <EmptyState label="Không có claim nào khớp bộ lọc." />
                ) : (
                  filtered.map((a) => (
                    <ClaimAssessmentCard
                      key={a.claim_id}
                      assessment={a}
                      onDecide={decide}
                      onOpenEvidence={openEvidence}
                      busy={busy}
                    />
                  ))
                )}
              </div>

              {/* Citation target: the approved legal source the claim was judged against. */}
              <div className="review-split__viewer">
                {openSpan ? (
                  <DocumentViewer
                    documentId={openSpan.document_id}
                    filename={`Nguồn pháp lý: ${openSpan.document_id}`}
                    // page count and spans are scoped to the cited document —
                    // mixing documents would put another circular's highlight
                    // on this one's page
                    pageCount={Math.max(
                      1,
                      ...citedSpans.filter((s) => s.document_id === openSpan.document_id).map((s) => s.page),
                    )}
                    page={viewerPage}
                    onPageChange={setViewerPage}
                    spans={citedSpans.filter((s) => s.document_id === openSpan.document_id)}
                    activeSpanId={openSpanId}
                  />
                ) : (
                  <EmptyState label="Bấm “Mở evidence” ở một claim để xem đúng trang trong văn bản nguồn." />
                )}
              </div>
            </div>
          </section>
        </>
      )}
    </main>
  )
}
