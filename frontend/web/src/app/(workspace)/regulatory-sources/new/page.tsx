'use client'

/**
 * Nav #2 — Add Regulatory Source (Workflow A intake).
 *
 * The upload_purpose is sent explicitly (§7.1: "backend không suy đoán bằng
 * filename") and the screen states up front that the file will NOT be legal
 * ground truth until it is reviewed and activated (§2, §10.3).
 */
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ApiErrorBanner } from '@/components/common/Banners'
import { PageHeader } from '@/components/layout/PageHeader'
import { api } from '@/lib/api'
import { TRUST_CLASS_HINT } from '@/lib/labels'
import { UPLOAD_PURPOSE } from '@/types/domain'

export default function AddRegulatorySourcePage() {
  const router = useRouter()
  const [file, setFile] = useState<File | null>(null)
  const [documentNumber, setDocumentNumber] = useState('')
  const [issuer, setIssuer] = useState('')
  const [effectiveDate, setEffectiveDate] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<{ code?: string; message?: string }>()

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    setError(undefined)

    const form = new FormData()
    form.append('file', file)
    form.append('upload_purpose', UPLOAD_PURPOSE.ADD_REGULATORY_SOURCE)
    if (documentNumber) form.append('document_number', documentNumber)
    if (issuer) form.append('issuer', issuer)
    if (effectiveDate) form.append('effective_date', effectiveDate)

    const res = await api.uploadRegulatorySource(form)
    setBusy(false)

    if (!res.ok || !res.data) {
      setError({ code: res.code, message: res.message ?? 'Upload thất bại' })
      return
    }
    router.push(`/regulatory-sources/${res.data.document_id}`)
  }

  return (
    <main className="page" data-testid="page-add-regulatory-source">
      <PageHeader
        navOrder={2}
        title="Add Regulatory Source"
        subtitle="Thêm thông tư, quyết định, văn bản sửa đổi hoặc văn bản hợp nhất vào kho pháp lý."
      />

      <div className="banner banner--warning" role="status" data-testid="banner-not-ground-truth">
        <strong>File upload không mặc định là nguồn pháp lý.</strong>
        <span>{TRUST_CLASS_HINT.AUTHORITY_SOURCE_CANDIDATE} Sau khi upload, tài liệu ở trạng thái chờ xác minh.</span>
      </div>

      <form className="form" onSubmit={submit}>
        <label className="form__field">
          <span>Tệp PDF *</span>
          <input
            type="file"
            accept="application/pdf"
            data-testid="input-file"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>

        <label className="form__field">
          <span>Số hiệu văn bản</span>
          <input
            value={documentNumber}
            placeholder="06/2025/TT-NHNN"
            onChange={(e) => setDocumentNumber(e.target.value)}
          />
          <p className="form__hint">Để trống nếu muốn hệ thống tự trích xuất và bạn xác nhận ở bước review.</p>
        </label>

        <label className="form__field">
          <span>Cơ quan ban hành</span>
          <input value={issuer} placeholder="Ngân hàng Nhà nước Việt Nam" onChange={(e) => setIssuer(e.target.value)} />
        </label>

        <label className="form__field">
          <span>Ngày hiệu lực dự kiến</span>
          <input type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} />
        </label>

        <input type="hidden" name="upload_purpose" value={UPLOAD_PURPOSE.ADD_REGULATORY_SOURCE} readOnly />
        <p className="form__hint" data-testid="upload-purpose-note">
          upload_purpose = <code>{UPLOAD_PURPOSE.ADD_REGULATORY_SOURCE}</code>
        </p>

        <ApiErrorBanner code={error?.code} message={error?.message} />

        <div className="form__actions">
          <button type="submit" disabled={!file || busy}>
            {busy ? 'Đang tải lên…' : 'Upload & bắt đầu pipeline'}
          </button>
        </div>
      </form>
    </main>
  )
}
