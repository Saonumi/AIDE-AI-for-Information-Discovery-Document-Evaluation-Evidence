/**
 * evidence_highlight (spec §10.6).
 *
 * One highlighted evidence span drawn over the page canvas. Position comes from
 * the bbox in PDF points; when the backend has no bbox the span still renders as
 * a listed quote so provenance is never lost (§2.3 requires page + evidence_text
 * on every extracted field).
 */
import { formatConfidence } from '@/lib/labels'
import type { EvidenceSpan } from '@/types/api'

/** Points-per-page used to turn PDF coordinates into percentages (A4 default). */
const PAGE_WIDTH_PT = 595
const PAGE_HEIGHT_PT = 842

export function EvidenceHighlight({ span, active }: { span: EvidenceSpan; active?: boolean }) {
  const style = span.bbox
    ? {
        left: `${(span.bbox[0] / PAGE_WIDTH_PT) * 100}%`,
        top: `${(span.bbox[1] / PAGE_HEIGHT_PT) * 100}%`,
        width: `${((span.bbox[2] - span.bbox[0]) / PAGE_WIDTH_PT) * 100}%`,
        height: `${((span.bbox[3] - span.bbox[1]) / PAGE_HEIGHT_PT) * 100}%`,
      }
    : undefined

  return (
    <mark
      className={`evidence-highlight${active ? ' evidence-highlight--active' : ''}${span.bbox ? '' : ' evidence-highlight--no-bbox'}`}
      style={style}
      data-testid="evidence-highlight"
      data-span-id={span.evidence_span_id}
      data-page={span.page}
      title={span.text}
    >
      <span className="evidence-highlight__meta">
        trang {span.page} · {span.extractor ?? 'unknown'} · {formatConfidence(span.confidence)}
      </span>
      {!span.bbox && <span className="evidence-highlight__text">{span.text}</span>}
    </mark>
  )
}

/** Inline citation that jumps the viewer to the right page/span (§10.5). */
export function EvidenceLink({
  spanId,
  page,
  label,
  onOpen,
}: {
  spanId?: string | null
  page?: number | null
  label: string
  onOpen?: (spanId: string, page: number) => void
}) {
  const canOpen = Boolean(spanId && page && onOpen)
  return (
    <button
      type="button"
      className="evidence-link"
      data-testid="evidence-link"
      data-span-id={spanId ?? undefined}
      disabled={!canOpen}
      title={canOpen ? `Mở trang ${page} và highlight evidence` : 'Chưa có evidence span để mở'}
      onClick={() => canOpen && onOpen!(spanId!, page!)}
    >
      {label}
      {page != null && <span className="evidence-link__page"> (trang {page})</span>}
    </button>
  )
}
