'use client'

/**
 * document_viewer (spec §10.6) — the left pane of the source review screen.
 *
 * §10.3 requires: "PDF viewer bên trái" and "Mỗi proposal mở đúng trang và
 * highlight evidence". This component owns page navigation and renders the
 * highlight overlay; the actual PDF raster is not wired yet, so the page frame
 * is a labelled placeholder that still proves the page/highlight plumbing works.
 */
import { EvidenceHighlight } from '@/components/document/EvidenceHighlight'
import type { EvidenceSpan } from '@/types/api'

interface DocumentViewerProps {
  documentId: string
  filename?: string
  pageCount?: number
  /** Page currently displayed — controlled by the parent so proposals can jump. */
  page: number
  onPageChange: (page: number) => void
  /** Spans on the current page; the active one is emphasised. */
  spans: EvidenceSpan[]
  activeSpanId?: string | null
}

export function DocumentViewer({
  documentId,
  filename,
  pageCount = 1,
  page,
  onPageChange,
  spans,
  activeSpanId,
}: DocumentViewerProps) {
  // Filter by document as well as page: a caller may hold spans from several
  // documents (a compliance report cites many regulations), and page numbers
  // collide across them — page 3 of one circular is not page 3 of another.
  const spansOnPage = spans.filter((s) => s.page === page && s.document_id === documentId)

  return (
    <section className="doc-viewer" data-testid="document-viewer" aria-label="Trình xem tài liệu">
      <header className="doc-viewer__toolbar">
        <span className="doc-viewer__filename">{filename ?? documentId}</span>
        <span className="doc-viewer__pager">
          <button type="button" onClick={() => onPageChange(Math.max(1, page - 1))} disabled={page <= 1}>
            ‹ Trang trước
          </button>
          <span className="doc-viewer__page-indicator" data-testid="viewer-page">
            Trang {page} / {pageCount}
          </span>
          <button type="button" onClick={() => onPageChange(Math.min(pageCount, page + 1))} disabled={page >= pageCount}>
            Trang sau ›
          </button>
        </span>
      </header>

      <div className="doc-viewer__canvas" data-page={page}>
        {/* PDF raster goes here once the file-serving endpoint exists. */}
        <div className="doc-viewer__placeholder">
          <p>Khung hiển thị trang PDF (trang {page})</p>
          <p className="doc-viewer__placeholder-hint">
            Chưa gắn PDF renderer — vị trí và cơ chế highlight theo trang đã sẵn sàng.
          </p>
        </div>

        <div className="doc-viewer__overlay">
          {spansOnPage.map((span) => (
            <EvidenceHighlight key={span.evidence_span_id} span={span} active={span.evidence_span_id === activeSpanId} />
          ))}
        </div>
      </div>

      <footer className="doc-viewer__footer">
        {spansOnPage.length === 0 ? (
          <span className="doc-viewer__empty">Không có evidence span nào trên trang này.</span>
        ) : (
          <span>{spansOnPage.length} evidence span trên trang {page}</span>
        )}
      </footer>
    </section>
  )
}
