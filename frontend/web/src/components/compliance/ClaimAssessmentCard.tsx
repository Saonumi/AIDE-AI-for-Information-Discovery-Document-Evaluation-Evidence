'use client'

/**
 * claim_assessment_card (spec §10.6), built to §10.4's checklist.
 *
 * One card must show: claim gốc, assessment, legal evidence (with version/date),
 * explanation, recommendation — plus excluded evidence and its reason (§10.5) —
 * and offer Confirm / Dismiss / Edit / Needs action.
 */
import { useState } from 'react'
import { AwaitingHumanDecisionNote } from '@/components/common/Banners'
import { ComplianceStatusBadge, ReviewStatusBadge, SeverityBadge, TrustClassBadge } from '@/components/common/StatusBadge'
import { EvidenceLink } from '@/components/document/EvidenceHighlight'
import { COMPLIANCE_STATUS_HINT, formatConfidence, formatLocator, formatValidity } from '@/lib/labels'
import type { ClaimAssessment } from '@/types/api'
import type { ReviewerAction } from '@/types/domain'

interface Props {
  assessment: ClaimAssessment
  /** Decisions are keyed by ReviewTask id when the backend supplies one (§9). */
  onDecide: (taskOrClaimId: string, action: ReviewerAction, note?: string) => void
  onOpenEvidence?: (spanId: string, page: number) => void
  busy?: boolean
}

export function ClaimAssessmentCard({ assessment, onDecide, onOpenEvidence, busy }: Props) {
  const [noteOpen, setNoteOpen] = useState(false)
  const [note, setNote] = useState('')

  const decided = assessment.review_status !== 'PENDING'
  const decisionId = assessment.review_task_id ?? assessment.claim_id

  const decide = (action: ReviewerAction) => onDecide(decisionId, action, note || undefined)

  return (
    <article
      className="claim"
      data-testid="claim-assessment-card"
      data-claim-id={assessment.claim_id}
      data-status={assessment.status}
      data-review-status={assessment.review_status}
    >
      <header className="claim__header">
        <div className="claim__identity">
          <span className="claim__section">{assessment.section ?? 'Không rõ mục'}</span>
          <h4 className="claim__source-text">{assessment.source_text}</h4>
        </div>
        <div className="claim__badges">
          <ComplianceStatusBadge value={assessment.status} />
          {assessment.severity && <SeverityBadge value={assessment.severity} />}
          <ReviewStatusBadge value={assessment.review_status} />
        </div>
      </header>

      <p className="claim__status-hint">{COMPLIANCE_STATUS_HINT[assessment.status]}</p>

      {assessment.structured_facts && Object.keys(assessment.structured_facts).length > 0 && (
        <dl className="claim__facts" data-testid="claim-structured-facts">
          {Object.entries(assessment.structured_facts).map(([k, v]) => (
            <div key={k} className="claim__fact">
              <dt>{k}</dt>
              <dd>{String(v)}</dd>
            </div>
          ))}
        </dl>
      )}

      <section className="claim__evidence">
        <h5 className="claim__subtitle">Căn cứ pháp lý được dùng</h5>
        {assessment.valid_evidence.length === 0 ? (
          <p className="claim__empty">Không có căn cứ nào trong kho nguồn đã duyệt.</p>
        ) : (
          <ul className="claim__evidence-list">
            {assessment.valid_evidence.map((e, i) => (
              <li key={e.evidence_id ?? `${e.document_number}-${i}`} className="claim__evidence-item">
                <div className="claim__evidence-head">
                  <strong>{formatLocator(e)}</strong>
                  {e.trust_class && <TrustClassBadge value={e.trust_class} />}
                </div>
                <div className="claim__evidence-meta">
                  <span>Version {e.version ?? '—'}</span>
                  <span>Hiệu lực {formatValidity(e.effective_from, e.effective_to_exclusive)}</span>
                  <EvidenceLink
                    spanId={e.evidence_span_id}
                    page={e.page}
                    label="Mở evidence"
                    onOpen={onOpenEvidence}
                  />
                </div>
                {e.text && <blockquote className="claim__evidence-text">{e.text}</blockquote>}
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* §10.5 — excluded evidence and the reason it was dropped must be visible. */}
      <section className="claim__excluded">
        <h5 className="claim__subtitle">Bằng chứng bị loại &amp; lý do</h5>
        {assessment.excluded_evidence.length === 0 ? (
          <p className="claim__empty">Không có bằng chứng nào bị loại.</p>
        ) : (
          <ul className="claim__excluded-list" data-testid="claim-excluded-evidence">
            {assessment.excluded_evidence.map((x, i) => (
              <li key={x.evidence_id ?? `${x.reason}-${i}`}>
                <span>
                  {x.document_number ?? 'Không rõ văn bản'}
                  {x.version ? ` · ${x.version}` : ''}
                </span>
                <code className="claim__excluded-reason" data-reason={x.reason}>
                  {x.reason}
                </code>
              </li>
            ))}
          </ul>
        )}
      </section>

      {assessment.explanation && (
        <section className="claim__explanation">
          <h5 className="claim__subtitle">Giải thích</h5>
          <p>{assessment.explanation}</p>
        </section>
      )}

      {assessment.recommendation && (
        <section className="claim__recommendation">
          <h5 className="claim__subtitle">Đề xuất chỉnh sửa</h5>
          <p>{assessment.recommendation}</p>
        </section>
      )}

      <p className="claim__confidence">Confidence: {formatConfidence(assessment.confidence)}</p>

      {assessment.status === 'NEEDS_HUMAN_REVIEW' && <AwaitingHumanDecisionNote />}

      {noteOpen && (
        <div className="claim__note-editor">
          <label htmlFor={`note-${assessment.claim_id}`}>Ghi chú / nội dung sửa của reviewer</label>
          <textarea id={`note-${assessment.claim_id}`} rows={3} value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
      )}

      <footer className="claim__actions">
        {decided ? (
          <span className="claim__decided">
            Reviewer đã xử lý{assessment.reviewer_action ? ` — ${assessment.reviewer_action}` : ''}
          </span>
        ) : noteOpen ? (
          // Edit mode needs its own submit, otherwise the typed note is never
          // sent and REVIEWER_ACTION.EDIT is never dispatched at all.
          <>
            <button type="button" disabled={busy} onClick={() => decide('EDIT')} data-testid="claim-submit-edit">
              Lưu chỉnh sửa
            </button>
            <button type="button" onClick={() => setNoteOpen(false)}>
              Huỷ
            </button>
          </>
        ) : (
          <>
            <button type="button" disabled={busy} onClick={() => decide('CONFIRM')}>
              Confirm
            </button>
            <button type="button" disabled={busy} onClick={() => decide('DISMISS')}>
              Dismiss
            </button>
            <button type="button" disabled={busy} onClick={() => setNoteOpen(true)}>
              Edit
            </button>
            <button type="button" disabled={busy} onClick={() => decide('NEEDS_ACTION')}>
              Needs action
            </button>
          </>
        )}
      </footer>
    </article>
  )
}
