/**
 * Vietnamese labels for every enum value the UI can show.
 *
 * Spec §10.5 has one hard rule encoded here: never use the words "AI kết luận"
 * for a status that is still NEEDS_HUMAN_REVIEW. All wording below is phrased as
 * a proposal, not a verdict.
 */
import {
  type AmendmentOperation,
  type BackendMode,
  type ComplianceStatus,
  type DocumentClass,
  type ResolutionStatus,
  type ReviewStatus,
  type ReviewTargetStatus,
  type Severity,
  type SourceStatus,
  type TrustClass,
  type UploadPurpose,
} from '@/types/domain'

export const TRUST_CLASS_LABEL: Record<TrustClass, string> = {
  AUTHORITY_SOURCE_CANDIDATE: 'Nguồn chờ xác minh',
  AUTHORITY_SOURCE: 'Nguồn pháp lý chính thức',
  INTERNAL_APPROVED: 'Nội bộ đã duyệt',
  REVIEW_TARGET: 'Tài liệu cần kiểm tra',
  UNVERIFIED: 'Chưa xác minh',
}

/** §2.1 — spelled out so the UI can state why a document may or may not be cited. */
export const TRUST_CLASS_HINT: Record<TrustClass, string> = {
  AUTHORITY_SOURCE_CANDIDATE: 'Chưa được duyệt — không dùng làm căn cứ pháp lý.',
  AUTHORITY_SOURCE: 'Đã approve và activate — được dùng làm căn cứ pháp lý.',
  INTERNAL_APPROVED: 'Policy nội bộ — là đối tượng mapping/impact, không phải căn cứ pháp lý.',
  REVIEW_TARGET: 'File upload để kiểm tra — không bao giờ vào kho pháp lý.',
  UNVERIFIED: 'Nguồn chưa xác định — không dùng làm căn cứ pháp lý.',
}

export const DOCUMENT_CLASS_LABEL: Record<DocumentClass, string> = {
  EXTERNAL_LEGAL: 'Văn bản pháp lý',
  INTERNAL_POLICY: 'Policy nội bộ',
  REVIEW_DOCUMENT: 'Tài liệu cần kiểm tra',
}

export const UPLOAD_PURPOSE_LABEL: Record<UploadPurpose, string> = {
  ADD_REGULATORY_SOURCE: 'Thêm nguồn pháp lý',
  CHECK_DOCUMENT_COMPLIANCE: 'Kiểm tra tuân thủ',
}

export const SOURCE_STATUS_LABEL: Record<SourceStatus, string> = {
  RECEIVED: 'Đã nhận',
  QUARANTINED: 'Cách ly & quét',
  EXTRACTED: 'Đã trích xuất',
  PARSED: 'Đã phân tích cấu trúc',
  REVIEW_REQUIRED: 'Chờ người rà soát',
  APPROVED: 'Đã duyệt',
  INDEX_SYNC_PENDING: 'Chờ đồng bộ chỉ mục tìm kiếm',
  GRAPH_SYNC_PENDING: 'Chờ đồng bộ graph',
  ACTIVE: 'Đang hiệu lực',
  REJECTED: 'Từ chối',
  NEEDS_CORRECTION: 'Cần chỉnh sửa',
  FAILED: 'Lỗi xử lý',
  ARCHIVED: 'Lưu trữ',
}

export const REVIEW_TARGET_STATUS_LABEL: Record<ReviewTargetStatus, string> = {
  RECEIVED: 'Đã nhận',
  QUARANTINED: 'Cách ly & quét',
  EXTRACTED: 'Đã trích xuất',
  CLAIMS_PARSED: 'Đã tách claim',
  CHECKING: 'Đang đối chiếu',
  REVIEW_REQUIRED: 'Chờ người rà soát',
  COMPLETED: 'Hoàn tất',
  NEEDS_CORRECTION: 'Cần chỉnh sửa',
  FAILED: 'Lỗi xử lý',
  REJECTED: 'Từ chối',
}

export const COMPLIANCE_STATUS_LABEL: Record<ComplianceStatus, string> = {
  COMPLIANT: 'Phù hợp',
  NON_COMPLIANT: 'Không phù hợp',
  PARTIALLY_COMPLIANT: 'Phù hợp một phần',
  OUTDATED_REFERENCE: 'Dùng phiên bản cũ',
  MISSING_EVIDENCE: 'Thiếu căn cứ',
  AMBIGUOUS: 'Chưa rõ ràng',
  NEEDS_HUMAN_REVIEW: 'Cần người xác nhận',
}

export const COMPLIANCE_STATUS_HINT: Record<ComplianceStatus, string> = {
  COMPLIANT: 'Được bằng chứng hiện hành hỗ trợ đầy đủ.',
  NON_COMPLIANT: 'Mâu thuẫn với một hoặc nhiều quy định hiện hành.',
  PARTIALLY_COMPLIANT: 'Đúng một phần nhưng thiếu điều kiện, ngoại lệ hoặc phạm vi.',
  OUTDATED_REFERENCE: 'Dùng version hoặc văn bản đã bị thay thế.',
  MISSING_EVIDENCE: 'Không tìm thấy căn cứ đủ mạnh trong kho đã duyệt.',
  AMBIGUOUS: 'Có nhiều quy định có thể áp dụng hoặc evidence xung đột.',
  // deliberately NOT "AI kết luận ..." — §10.5
  NEEDS_HUMAN_REVIEW: 'Hệ thống chưa đủ cơ sở kết luận; chờ Compliance Officer quyết định.',
}

export const AMENDMENT_OPERATION_LABEL: Record<AmendmentOperation, string> = {
  REPLACE_TEXT: 'Thay cụm từ',
  REPLACE_PROVISION: 'Thay nội dung điều khoản',
  INSERT_AFTER: 'Bổ sung sau',
  DELETE_TEXT: 'Xoá cụm từ',
  REPEAL_PROVISION: 'Bãi bỏ điều khoản',
}

export const RESOLUTION_STATUS_LABEL: Record<ResolutionStatus, string> = {
  EXACT: 'Xác định chính xác',
  AMBIGUOUS: 'Mơ hồ — cần xác nhận',
  UNRESOLVED: 'Chưa xác định được',
}

export const REVIEW_STATUS_LABEL: Record<ReviewStatus, string> = {
  PENDING: 'Chờ duyệt',
  APPROVED: 'Đã duyệt',
  EDITED: 'Đã sửa & duyệt',
  REJECTED: 'Đã từ chối',
}

export const SEVERITY_LABEL: Record<Severity, string> = {
  HIGH: 'Cao',
  MEDIUM: 'Trung bình',
  LOW: 'Thấp',
}

export const BACKEND_MODE_LABEL: Record<BackendMode, string> = {
  REAL: 'Backend thật',
  MOCK: 'Dữ liệu mẫu',
  FALLBACK: 'Fallback',
}

/** §9.1 error codes — the UI explains the code, it does not parse the message. */
export const ERROR_CODE_LABEL: Record<string, string> = {
  INVALID_UPLOAD_PURPOSE: 'Mục đích upload không hợp lệ.',
  REVIEW_NOT_COMPLETED: 'Không thể activate khi còn review bắt buộc chưa xử lý.',
  EVIDENCE_NOT_VALID: 'Bằng chứng không hợp lệ tại ngày áp dụng.',
  TARGET_NOT_RESOLVED: 'Chưa xác định được điều khoản đích của sửa đổi.',
  NOT_LEGAL_GROUND_TRUTH: 'Tài liệu này không phải nguồn pháp lý được phép trích dẫn.',
  BACKEND_DEGRADED: 'Một số backend đang chạy ở chế độ suy giảm.',
  // not in the spec's minimum list, but the spec calls that list a minimum and
  // an empty screen caused by an expired token must not read as "no data"
  UNAUTHENTICATED: 'Phiên đăng nhập không hợp lệ hoặc đã hết hạn — cần đăng nhập lại.',
  FORBIDDEN: 'Tài khoản không có quyền thực hiện thao tác này.',
  ROLE_NOT_SUPPORTED: 'Vai trò tài khoản không nằm trong mô hình role hiện hành.',
}

/** "Điều 7 › Khoản 7" from the structured target. */
export function formatLocator(target: {
  document_number?: string
  article?: string
  clause?: string
  point?: string
}): string {
  const parts: string[] = []
  if (target.document_number) parts.push(target.document_number)
  if (target.article) parts.push(`Điều ${target.article}`)
  if (target.clause) parts.push(`Khoản ${target.clause}`)
  if (target.point) parts.push(`Điểm ${target.point}`)
  return parts.length ? parts.join(' › ') : '—'
}

/** Half-open validity interval, matching the temporal model. */
export function formatValidity(from?: string | null, toExclusive?: string | null): string {
  return `[${from ?? '?'} … ${toExclusive ?? '∞'})`
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return '—'
  // keep it lexical: no locale surprises between server and client render
  return iso.replace('T', ' ').replace('Z', '').slice(0, 19)
}

export function formatConfidence(value?: number | null): string {
  return value == null ? '—' : `${Math.round(value * 100)}%`
}
