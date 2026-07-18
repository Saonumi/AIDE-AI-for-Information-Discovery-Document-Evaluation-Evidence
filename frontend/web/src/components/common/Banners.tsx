/**
 * Trust banners — the loudest UX signals in the spec.
 *
 * §10.3: 'Banner "Chưa phải nguồn pháp lý" cho tới khi ACTIVE'.
 * §10.4: 'Hiển thị rõ "File này chỉ được dùng để kiểm tra, không thêm vào legal
 *         knowledge base"'.
 * §10.5: mock/fallback data must be announced, never silently rendered.
 */
import { BackendModeBadge } from '@/components/common/StatusBadge'
import { ERROR_CODE_LABEL } from '@/lib/labels'
import { SOURCE_STATUS, TRUST_CLASS_IS_LEGAL_GROUND_TRUTH, type BackendMode, type TrustClass } from '@/types/domain'

/**
 * Shown on every regulatory-source screen until the document is genuinely usable
 * as legal ground truth.
 *
 * §10.3 says the banner stays "cho tới khi ACTIVE", and §2.2's predicate needs
 * BOTH the trust class AND the lifecycle status — a document can be APPROVED but
 * not yet ACTIVE, and citing it then would be wrong. Both conditions are checked.
 */
export function NotLegalSourceBanner({ trustClass, status }: { trustClass: TrustClass; status?: string }) {
  const isGroundTruth = TRUST_CLASS_IS_LEGAL_GROUND_TRUTH[trustClass] && status === SOURCE_STATUS.ACTIVE
  if (isGroundTruth) return null
  return (
    <div className="banner banner--warning" role="status" data-testid="banner-not-legal-source">
      <strong>Chưa phải nguồn pháp lý.</strong> Tài liệu này chưa được duyệt và activate, nên không được dùng làm căn cứ
      pháp lý trong retrieval, impact analysis hay compliance checking.
    </div>
  )
}

/** Shown on every compliance-check screen (§10.4). */
export function ReviewTargetBanner() {
  return (
    <div className="banner banner--info" role="status" data-testid="banner-review-target">
      <strong>File này chỉ được dùng để kiểm tra.</strong> Tài liệu không được thêm vào legal knowledge base và không
      bao giờ trở thành căn cứ pháp lý.
    </div>
  )
}

/** Rendered whenever a screen is showing fixture data instead of backend data. */
export function DataSourceBanner({ source, note }: { source: BackendMode; note?: string }) {
  if (source === 'REAL') return null
  return (
    <div className="banner banner--mock" role="status" data-testid="banner-mock-data">
      <BackendModeBadge value={source} />
      <span>
        {note ??
          'Endpoint tương ứng chưa có trên backend — màn hình đang hiển thị dữ liệu mẫu theo JSON contract của spec.'}
      </span>
    </div>
  )
}

/** Renders a §9.1 error by its stable code; free-text message is shown as detail only. */
export function ApiErrorBanner({ code, message }: { code?: string; message?: string }) {
  if (!code && !message) return null
  return (
    <div className="banner banner--error" role="alert" data-testid="banner-api-error" data-code={code}>
      <strong>{code ?? 'ERROR'}</strong>
      <span>{(code && ERROR_CODE_LABEL[code]) ?? message}</span>
      {code && message && <small className="banner__detail">{message}</small>}
    </div>
  )
}

/**
 * §10.5 — never present a machine proposal as a conclusion while a human still
 * has to decide. Any screen showing NEEDS_HUMAN_REVIEW renders this.
 */
export function AwaitingHumanDecisionNote() {
  return (
    <p className="note note--awaiting-human" data-testid="note-awaiting-human">
      Hệ thống chỉ đề xuất. Kết luận pháp lý cuối cùng thuộc về Compliance Officer.
    </p>
  )
}
