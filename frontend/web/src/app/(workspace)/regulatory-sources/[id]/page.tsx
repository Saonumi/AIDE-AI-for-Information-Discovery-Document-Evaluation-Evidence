'use client'

/**
 * Source Review screen — spec §10.3, the densest requirement in the document:
 *
 *   - pipeline state theo bước                    -> <PipelineSteps>
 *   - PDF viewer bên trái; metadata/provisions/
 *     change proposals bên phải                   -> .review-split
 *   - mỗi proposal mở đúng trang và highlight     -> openEvidence()
 *   - before/after, effective date, target
 *     resolution, warnings                        -> <ChangeProposalCard>
 *   - approve/edit/reject từng proposal           -> per-card actions
 *   - banner "Chưa phải nguồn pháp lý" tới ACTIVE -> <NotLegalSourceBanner>
 *
 * Activation deliberately surfaces HTTP 409 REVIEW_NOT_COMPLETED (§11.2 T2)
 * instead of hiding the button while reviews are pending: the officer must see
 * the gate reject them, which is the demo step in Phụ lục D #5.
 */
import { useCallback, useMemo, useState } from 'react'
import Link from 'next/link'
import { use } from 'react'
import { ApiErrorBanner, DataSourceBanner, NotLegalSourceBanner } from '@/components/common/Banners'
import { PipelineSteps } from '@/components/common/PipelineSteps'
import { LifecycleBadge, ResolutionBadge, TrustClassBadge } from '@/components/common/StatusBadge'
import { DocumentViewer } from '@/components/document/DocumentViewer'
import { EvidenceLink } from '@/components/document/EvidenceHighlight'
import { LoadingState, PageHeader } from '@/components/layout/PageHeader'
import { ChangeProposalCard } from '@/components/review/ChangeProposalCard'
import { useResource } from '@/hooks/useResource'
import { api } from '@/lib/api'
import { SOURCE_STATUS_LABEL, formatConfidence } from '@/lib/labels'
import { SOURCE_PIPELINE_STEPS, type ProposalDecision } from '@/types/domain'

export default function RegulatorySourceDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)

  const statusFetcher = useCallback(() => api.regulatorySource(id), [id])
  const packageFetcher = useCallback(() => api.reviewPackage(id), [id])
  const status = useResource(statusFetcher)
  const pkg = useResource(packageFetcher)

  const [page, setPage] = useState(1)
  const [activeSpanId, setActiveSpanId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState<{ code?: string; message?: string }>()
  const [activated, setActivated] = useState(false)

  // memoised so the two derived memos below do not recompute on every render
  const spans = useMemo(() => pkg.data?.evidence_spans ?? [], [pkg.data])
  const spanById = useMemo(() => new Map(spans.map((s) => [s.evidence_span_id, s])), [spans])
  const pageCount = useMemo(() => Math.max(1, ...spans.map((s) => s.page)), [spans])

  const openEvidence = useCallback((spanId: string, targetPage: number) => {
    setPage(targetPage)
    setActiveSpanId(spanId)
  }, [])

  async function decide(proposalId: string, decision: ProposalDecision, editedAfterText?: string) {
    setBusy(true)
    setActionError(undefined)
    const res = await api.decideProposal(id, proposalId, decision, editedAfterText ? { after_text: editedAfterText } : undefined)
    setBusy(false)
    if (!res.ok) {
      setActionError({ code: res.code, message: res.message })
      return
    }
    pkg.reload()
    status.reload()
  }

  async function activate() {
    setBusy(true)
    setActionError(undefined)
    const res = await api.activateSource(id)
    setBusy(false)
    if (!res.ok) {
      // 409 REVIEW_NOT_COMPLETED lands here and is shown verbatim by code
      setActionError({ code: res.code, message: res.message })
      return
    }
    setActivated(true)
    pkg.reload()
    status.reload()
  }

  const trustClass = pkg.data?.trust_class ?? status.data?.trust_class ?? 'AUTHORITY_SOURCE_CANDIDATE'
  const pendingCritical =
    pkg.data?.pending_critical_reviews ??
    pkg.data?.change_proposals.filter((p) => p.is_critical && p.review_status === 'PENDING').length ??
    0

  return (
    <main className="page page--wide" data-testid="page-source-review">
      <PageHeader
        title="Source Review Package"
        subtitle={`Xác nhận hệ thống đã hiểu đúng văn bản trước khi nó trở thành nguồn pháp lý · ${id}`}
      />

      <NotLegalSourceBanner trustClass={trustClass} status={status.data?.status} />
      <DataSourceBanner source={pkg.source} />
      {/* action failures first, then whichever fetch failed — never fail silently */}
      <ApiErrorBanner
        code={actionError?.code ?? pkg.code ?? status.code}
        message={actionError?.message ?? pkg.error ?? status.error}
      />

      {activated && (
        <div className="banner banner--info" role="status" data-testid="banner-activated">
          <strong>Đã activate.</strong> Nguồn trở thành AUTHORITY_SOURCE và được dùng trong retrieval chính thức.
        </div>
      )}

      <section className="page__section">
        <div className="page__meta-row">
          <TrustClassBadge value={trustClass} />
          {status.data?.status && <LifecycleBadge value={status.data.status} />}
        </div>
        <PipelineSteps
          steps={SOURCE_PIPELINE_STEPS}
          completed={status.data?.completed_steps ?? []}
          current={status.data?.status}
          labels={SOURCE_STATUS_LABEL}
        />
      </section>

      {pkg.loading ? (
        <LoadingState />
      ) : (
        <div className="review-split page__section">
          {/* ---------------------------------------------- left: PDF viewer */}
          <div className="review-split__viewer">
            <DocumentViewer
              documentId={id}
              filename={status.data?.document.filename}
              pageCount={pageCount}
              page={page}
              onPageChange={setPage}
              spans={spans}
              activeSpanId={activeSpanId}
            />
          </div>

          {/* ------------------------ right: metadata + proposals + warnings */}
          <div className="review-split__details">
            <section>
              <h2 className="page__section-title">Metadata trích xuất</h2>
              <table className="table" data-testid="metadata-table">
                <thead>
                  <tr>
                    <th>Trường</th>
                    <th>Giá trị</th>
                    <th>Evidence</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(pkg.data?.metadata ?? {}).map(([key, field]) =>
                    field ? (
                      <tr key={key} data-field={key}>
                        <td>{key}</td>
                        <td>{field.value}</td>
                        <td>
                          <EvidenceLink
                            spanId={`meta-${key}`}
                            page={field.page ?? null}
                            label={field.evidence_text ? `“${field.evidence_text.slice(0, 40)}…”` : 'Xem trang'}
                            onOpen={(_, p) => {
                              setPage(p)
                              setActiveSpanId(null)
                            }}
                          />
                        </td>
                        <td>{formatConfidence(field.confidence)}</td>
                      </tr>
                    ) : null,
                  )}
                </tbody>
              </table>
            </section>

            {/* §10.3 requires provisions alongside metadata and proposals. */}
            <section className="page__section">
              <h2 className="page__section-title">Điều khoản đã phân tích ({pkg.data?.provisions?.length ?? 0})</h2>
              {!pkg.data?.provisions?.length ? (
                <p className="claim__empty">Chưa tách được điều khoản nào từ tài liệu.</p>
              ) : (
                <table className="table" data-testid="provisions-table">
                  <thead>
                    <tr>
                      <th>Locator</th>
                      <th>Tiêu đề</th>
                      <th>Nội dung</th>
                      <th>Trang</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pkg.data.provisions.map((p) => (
                      <tr key={p.provision_id} data-provision-id={p.provision_id}>
                        <td>{p.locator}</td>
                        <td>{p.heading ?? '—'}</td>
                        <td>{p.content ?? '—'}</td>
                        <td>
                          <EvidenceLink
                            spanId={p.evidence_span_id ?? `prov-${p.provision_id}`}
                            page={p.page ?? null}
                            label={p.page != null ? `Trang ${p.page}` : '—'}
                            onOpen={openEvidence}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>

            {/* §3.1.1 "Danh sách phát hiện … hoặc dẫn chiếu" */}
            <section className="page__section">
              <h2 className="page__section-title">Dẫn chiếu phát hiện ({pkg.data?.references?.length ?? 0})</h2>
              {!pkg.data?.references?.length ? (
                <p className="claim__empty">Không phát hiện dẫn chiếu nào.</p>
              ) : (
                <table className="table" data-testid="references-table">
                  <thead>
                    <tr>
                      <th>Trích dẫn trong văn bản</th>
                      <th>Văn bản đích</th>
                      <th>Điều khoản đích</th>
                      <th>Kết quả resolve</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pkg.data.references.map((r) => (
                      <tr key={r.reference_id} data-reference-id={r.reference_id}>
                        <td>{r.raw_text}</td>
                        <td>{r.target_document_number ?? '—'}</td>
                        <td>{r.target_locator ?? '—'}</td>
                        <td>
                          <ResolutionBadge value={r.resolution_status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>

            {pkg.data?.warnings && pkg.data.warnings.length > 0 && (
              <section className="page__section">
                <h2 className="page__section-title">Cảnh báo</h2>
                <ul data-testid="package-warnings">
                  {pkg.data.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </section>
            )}

            <section className="page__section">
              <h2 className="page__section-title">
                Change proposals ({pkg.data?.change_proposals.length ?? 0})
              </h2>
              {pkg.data?.change_proposals.map((proposal) => (
                <ChangeProposalCard
                  key={proposal.proposal_id}
                  proposal={proposal}
                  evidenceSpan={proposal.evidence_span_id ? spanById.get(proposal.evidence_span_id) : undefined}
                  onOpenEvidence={openEvidence}
                  onDecide={decide}
                  busy={busy}
                />
              ))}
            </section>

            <section className="page__section">
              <h2 className="page__section-title">Activation gate</h2>
              <p className="form__hint" data-testid="pending-critical">
                Còn <strong>{pendingCritical}</strong> review bắt buộc chưa xử lý. Activation chỉ thành công khi con số
                này bằng 0.
              </p>
              <div className="form__actions">
                <button type="button" onClick={activate} disabled={busy} data-testid="btn-activate">
                  Activate nguồn pháp lý
                </button>
                <Link href={`/impact-reports/${id}`}>Xem Regulatory Impact Report →</Link>
              </div>
            </section>
          </div>
        </div>
      )}
    </main>
  )
}
