'use client'

/**
 * Nav #9 — Tra cứu bằng chứng.
 *
 * §3.3: "Tra cứu bằng chứng vẫn được giữ nhưng không phải màn hình trung tâm."
 * So this is a lookup form with an evidence table, NOT a chat thread: no message
 * history, no conversational framing. It answers questions about provision,
 * version, change history, source evidence and why an assessment was produced.
 *
 * §2.2 — only APPROVED + ACTIVE AUTHORITY_SOURCE may appear as valid evidence,
 * and excluded evidence is shown with its reason (§10.5).
 */
import { useState } from 'react'
import { ApiErrorBanner, AwaitingHumanDecisionNote, DataSourceBanner } from '@/components/common/Banners'
import { TrustClassBadge } from '@/components/common/StatusBadge'
import { DocumentViewer } from '@/components/document/DocumentViewer'
import { EvidenceLink } from '@/components/document/EvidenceHighlight'
import { EmptyState, PageHeader } from '@/components/layout/PageHeader'
import { api } from '@/lib/api'
import { AMENDMENT_OPERATION_LABEL, formatLocator, formatValidity } from '@/lib/labels'
import type { EvidenceQueryResponse, EvidenceSpan } from '@/types/api'
import type { BackendMode } from '@/types/domain'

export default function EvidenceQueryPage() {
  const [question, setQuestion] = useState('')
  const [queryDate, setQueryDate] = useState('')
  const [result, setResult] = useState<EvidenceQueryResponse>()
  const [source, setSource] = useState<BackendMode>('REAL')
  const [error, setError] = useState<{ code?: string; message?: string }>()
  const [busy, setBusy] = useState(false)
  const [openSpanId, setOpenSpanId] = useState<string | null>(null)
  const [viewerPage, setViewerPage] = useState(1)

  // §10.5 "Citation mở được đúng trang/evidence span" applies here too, not only
  // on the compliance report screen.
  const spans: EvidenceSpan[] = (result?.valid_evidence ?? [])
    .filter((e) => e.evidence_span_id && e.page != null)
    .map((e) => ({
      evidence_span_id: e.evidence_span_id!,
      document_id: e.document_number ?? 'unknown',
      page: e.page!,
      text: e.text ?? '',
      extractor: 'citation',
    }))
  const openSpan = spans.find((s) => s.evidence_span_id === openSpanId)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!question.trim()) return
    setBusy(true)
    setError(undefined)
    const res = await api.evidenceQuery(question.trim(), queryDate || null)
    setBusy(false)
    setSource(res.source)
    if (!res.ok || !res.data) {
      setError({ code: res.code, message: res.message })
      setResult(undefined)
      return
    }
    setResult(res.data)
  }

  return (
    <main className="page" data-testid="page-evidence-query">
      <PageHeader
        navOrder={9}
        title="Tra cứu bằng chứng"
        subtitle="Chức năng hỗ trợ: tra cứu provision, version, lịch sử thay đổi và nguồn evidence. Không phải màn hình trung tâm của sản phẩm."
      />

      <form className="form" onSubmit={submit}>
        <label className="form__field">
          <span>Câu hỏi</span>
          <textarea
            rows={3}
            value={question}
            data-testid="input-question"
            placeholder="Hạn mức cấp tín dụng SME hiện tại là bao nhiêu?"
            onChange={(e) => setQuestion(e.target.value)}
          />
        </label>

        <label className="form__field">
          <span>Ngày truy vấn</span>
          <input type="date" value={queryDate} onChange={(e) => setQueryDate(e.target.value)} />
          <p className="form__hint">Bộ lọc thời gian chạy TRƯỚC khi truy hồi top-k. Để trống = hôm nay.</p>
        </label>

        <div className="form__actions">
          <button type="submit" disabled={busy || !question.trim()}>
            {busy ? 'Đang tra cứu…' : 'Tra cứu'}
          </button>
        </div>
      </form>

      <DataSourceBanner source={source} />
      <ApiErrorBanner code={error?.code} message={error?.message} />

      {result && (
        <>
          {result.answer && (
            <section className="page__section">
              <h2 className="page__section-title">Tóm tắt từ bằng chứng</h2>
              <p>{result.answer}</p>
              {result.needs_human_review && <AwaitingHumanDecisionNote />}
            </section>
          )}

          <section className="page__section">
            <h2 className="page__section-title">Bằng chứng hợp lệ ({result.valid_evidence.length})</h2>
            {result.valid_evidence.length === 0 ? (
              <EmptyState label="Không có bằng chứng hợp lệ tại ngày truy vấn." />
            ) : (
              <table className="table" data-testid="valid-evidence-table">
                <thead>
                  <tr>
                    <th>Điều khoản</th>
                    <th>Version</th>
                    <th>Hiệu lực</th>
                    <th>Trang</th>
                    <th>Trust class</th>
                    <th>Nội dung</th>
                  </tr>
                </thead>
                <tbody>
                  {result.valid_evidence.map((e, i) => (
                    <tr key={e.evidence_id ?? i}>
                      <td>{formatLocator(e)}</td>
                      <td>{e.version ?? '—'}</td>
                      <td>{formatValidity(e.effective_from, e.effective_to_exclusive)}</td>
                      <td>
                        <EvidenceLink
                          spanId={e.evidence_span_id}
                          page={e.page}
                          label={e.page != null ? `Trang ${e.page}` : '—'}
                          onOpen={(spanId, p) => {
                            setOpenSpanId(spanId)
                            setViewerPage(p)
                          }}
                        />
                      </td>
                      <td>{e.trust_class && <TrustClassBadge value={e.trust_class} />}</td>
                      <td>{e.text}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          {openSpan && (
            <section className="page__section">
              <h2 className="page__section-title">Evidence trong văn bản nguồn</h2>
              <DocumentViewer
                documentId={openSpan.document_id}
                filename={`Nguồn pháp lý: ${openSpan.document_id}`}
                pageCount={Math.max(1, ...spans.filter((s) => s.document_id === openSpan.document_id).map((s) => s.page))}
                page={viewerPage}
                onPageChange={setViewerPage}
                spans={spans.filter((s) => s.document_id === openSpan.document_id)}
                activeSpanId={openSpanId}
              />
            </section>
          )}

          <section className="page__section">
            <h2 className="page__section-title">Bằng chứng bị loại ({result.excluded_evidence.length})</h2>
            {result.excluded_evidence.length === 0 ? (
              <p className="claim__empty">Không có bằng chứng nào bị loại.</p>
            ) : (
              <table className="table" data-testid="excluded-evidence-table">
                <thead>
                  <tr>
                    <th>Văn bản</th>
                    <th>Version</th>
                    <th>Lý do loại</th>
                  </tr>
                </thead>
                <tbody>
                  {result.excluded_evidence.map((x, i) => (
                    <tr key={x.evidence_id ?? i}>
                      <td>{x.document_number ?? '—'}</td>
                      <td>{x.version ?? '—'}</td>
                      <td>
                        <code data-reason={x.reason}>{x.reason}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          {result.change_history && result.change_history.length > 0 && (
            <section className="page__section">
              <h2 className="page__section-title">Lịch sử thay đổi</h2>
              <ul data-testid="change-history">
                {result.change_history.map((c) => (
                  <li key={c.change_event_id}>
                    {AMENDMENT_OPERATION_LABEL[c.operation] ?? c.operation} · {c.provision_locator} · hiệu lực{' '}
                    {c.effective_date ?? '—'}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </main>
  )
}
