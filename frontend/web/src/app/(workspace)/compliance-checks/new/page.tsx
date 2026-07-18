'use client'

/**
 * Nav #7 — Check Document Compliance (Workflow B intake).
 *
 * §10.4 requires this screen to say plainly that the file is not added to the
 * legal knowledge base, and to let the officer choose a review date and a
 * scope/domain before the check runs.
 */
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ApiErrorBanner, ReviewTargetBanner } from '@/components/common/Banners'
import { PageHeader } from '@/components/layout/PageHeader'
import { api } from '@/lib/api'
import { UPLOAD_PURPOSE } from '@/types/domain'

/** Scope choices narrow retrieval to a domain; free text stays possible. */
const SCOPE_OPTIONS = ['Tín dụng SME', 'Thanh toán & chuyển tiền', 'Phòng chống rửa tiền', 'Báo cáo & thống kê']

export default function NewComplianceCheckPage() {
  const router = useRouter()
  const [file, setFile] = useState<File | null>(null)
  const [reviewDate, setReviewDate] = useState('')
  const [scope, setScope] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<{ code?: string; message?: string }>()

  function toggleScope(value: string) {
    setScope((prev) => (prev.includes(value) ? prev.filter((s) => s !== value) : [...prev, value]))
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    setError(undefined)

    const form = new FormData()
    form.append('file', file)
    form.append('upload_purpose', UPLOAD_PURPOSE.CHECK_DOCUMENT_COMPLIANCE)
    if (reviewDate) form.append('review_date', reviewDate)
    scope.forEach((s) => form.append('requested_scope', s))

    const res = await api.uploadComplianceCheck(form)
    setBusy(false)

    if (!res.ok || !res.data) {
      setError({ code: res.code, message: res.message ?? 'Upload thất bại' })
      return
    }
    router.push(`/compliance-checks/${res.data.check_id}`)
  }

  return (
    <main className="page" data-testid="page-new-compliance-check">
      <PageHeader
        navOrder={7}
        title="Check Document Compliance"
        subtitle="Upload policy, báo cáo hoặc tài liệu nội bộ để đối chiếu với kho quy định đã được duyệt."
      />

      <ReviewTargetBanner />

      <form className="form" onSubmit={submit}>
        <label className="form__field">
          <span>Tệp cần kiểm tra *</span>
          <input
            type="file"
            accept="application/pdf,.doc,.docx"
            data-testid="input-file"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>

        <label className="form__field">
          <span>Ngày review</span>
          <input
            type="date"
            value={reviewDate}
            data-testid="input-review-date"
            onChange={(e) => setReviewDate(e.target.value)}
          />
          <p className="form__hint">
            Quyết định phiên bản quy định nào được coi là đang hiệu lực. Để trống = hôm nay.
          </p>
        </label>

        <fieldset className="form__field" data-testid="scope-options">
          <legend>Phạm vi / domain</legend>
          {SCOPE_OPTIONS.map((s) => (
            <label key={s} className="form__checkbox">
              <input type="checkbox" checked={scope.includes(s)} onChange={() => toggleScope(s)} />
              <span>{s}</span>
            </label>
          ))}
          <p className="form__hint">Không chọn = tìm trên toàn bộ kho nguồn đã duyệt.</p>
        </fieldset>

        <p className="form__hint" data-testid="upload-purpose-note">
          upload_purpose = <code>{UPLOAD_PURPOSE.CHECK_DOCUMENT_COMPLIANCE}</code>
        </p>

        <ApiErrorBanner code={error?.code} message={error?.message} />

        <div className="form__actions">
          <button type="submit" disabled={!file || busy}>
            {busy ? 'Đang tải lên…' : 'Upload & chạy kiểm tra'}
          </button>
        </div>
      </form>
    </main>
  )
}
