'use client'

/**
 * One ChangeProposal with its own decision controls.
 *
 * §10.3 is explicit: "Approve/Edit/Reject từng proposal; không chỉ approve cả
 * file mù." So the decision buttons live here, per proposal — there is
 * deliberately no bulk-approve control anywhere in this UI.
 */
import { useState } from 'react'
import { BeforeAfterDiff } from '@/components/review/BeforeAfterDiff'
import { EvidenceLink } from '@/components/document/EvidenceHighlight'
import { ResolutionBadge, ReviewStatusBadge } from '@/components/common/StatusBadge'
import { AMENDMENT_OPERATION_LABEL, formatConfidence, formatLocator } from '@/lib/labels'
import type { ChangeProposal, EvidenceSpan } from '@/types/api'
import type { ProposalDecision } from '@/types/domain'

interface Props {
  proposal: ChangeProposal
  evidenceSpan?: EvidenceSpan
  onOpenEvidence?: (spanId: string, page: number) => void
  onDecide: (taskOrProposalId: string, decision: ProposalDecision, editedAfterText?: string) => void
  busy?: boolean
}

export function ChangeProposalCard({ proposal, evidenceSpan, onOpenEvidence, onDecide, busy }: Props) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(proposal.after_text ?? '')

  const decided = proposal.review_status !== 'PENDING'
  // §9's decision route is keyed by task_id; fall back to proposal_id only when
  // the backend has not linked a ReviewTask yet.
  const decisionId = proposal.review_task_id ?? proposal.proposal_id

  return (
    <article
      className="proposal"
      data-testid="change-proposal"
      data-proposal-id={proposal.proposal_id}
      data-critical={proposal.is_critical ? 'true' : 'false'}
      data-review-status={proposal.review_status}
    >
      <header className="proposal__header">
        <div className="proposal__identity">
          <h4 className="proposal__operation">
            {AMENDMENT_OPERATION_LABEL[proposal.operation] ?? proposal.operation}
          </h4>
          <p className="proposal__target">{formatLocator(proposal.target)}</p>
        </div>
        <div className="proposal__badges">
          <ResolutionBadge value={proposal.resolution_status} />
          <ReviewStatusBadge value={proposal.review_status} />
          {proposal.is_critical && (
            <span className="badge badge--critical" data-value="CRITICAL">
              Bắt buộc duyệt trước khi activate
            </span>
          )}
        </div>
      </header>

      <BeforeAfterDiff
        before={proposal.before_text}
        after={editing ? draft : proposal.after_text}
        effectiveDate={proposal.effective_date}
        operation={proposal.operation}
      />

      <div className="proposal__provenance">
        <EvidenceLink
          spanId={proposal.evidence_span_id}
          page={evidenceSpan?.page ?? null}
          label="Xem evidence trong tài liệu"
          onOpen={onOpenEvidence}
        />
        <span className="proposal__confidence">Confidence: {formatConfidence(proposal.confidence)}</span>
      </div>

      {proposal.warnings && proposal.warnings.length > 0 && (
        <ul className="proposal__warnings" data-testid="proposal-warnings">
          {proposal.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}

      {editing && (
        <div className="proposal__editor">
          <label htmlFor={`edit-${proposal.proposal_id}`}>Sửa nội dung sau sửa đổi</label>
          <textarea
            id={`edit-${proposal.proposal_id}`}
            value={draft}
            rows={4}
            onChange={(e) => setDraft(e.target.value)}
          />
        </div>
      )}

      <footer className="proposal__actions">
        {decided ? (
          <span className="proposal__decided">Đã xử lý — {proposal.review_status}</span>
        ) : editing ? (
          <>
            <button type="button" disabled={busy} onClick={() => onDecide(decisionId, 'EDIT', draft)}>
              Lưu &amp; duyệt
            </button>
            <button type="button" onClick={() => setEditing(false)}>
              Huỷ
            </button>
          </>
        ) : (
          <>
            <button type="button" disabled={busy} onClick={() => onDecide(decisionId, 'APPROVE')}>
              Approve
            </button>
            <button type="button" disabled={busy} onClick={() => setEditing(true)}>
              Edit
            </button>
            <button type="button" disabled={busy} onClick={() => onDecide(decisionId, 'REJECT')}>
              Reject
            </button>
          </>
        )}
      </footer>
    </article>
  )
}
