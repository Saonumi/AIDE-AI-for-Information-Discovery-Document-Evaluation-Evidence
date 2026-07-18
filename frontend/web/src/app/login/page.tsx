'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ApiErrorBanner } from '@/components/common/Banners'
import { api } from '@/lib/api'
import { writeSession } from '@/lib/session'
import { ERROR_CODE, ROLE } from '@/types/domain'

/** POST /auth/login (§9). Only COMPLIANCE_OFFICER / SYSTEM_ADMIN exist (§6.1). */
export default function LoginPage() {
  const router = useRouter()
  const [username, setUsername] = useState('officer')
  const [password, setPassword] = useState('officer123')
  const [error, setError] = useState<{ code?: string; message?: string }>()
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(undefined)
    const res = await api.login(username, password)
    setBusy(false)

    if (!res.ok || !res.data) {
      setError({ code: res.code, message: res.message ?? 'Đăng nhập thất bại' })
      return
    }

    // §6.1 deleted USER and EMPLOYEE. A backend still issuing one of them would
    // otherwise be silently rejected by readSession() and bounce the officer
    // back here forever, so the mismatch is named explicitly.
    const role = res.data.role
    if (role !== ROLE.COMPLIANCE_OFFICER && role !== ROLE.SYSTEM_ADMIN) {
      setError({
        code: ERROR_CODE.ROLE_NOT_SUPPORTED,
        message: `Backend trả role "${role}", nhưng spec §6.1 chỉ còn COMPLIANCE_OFFICER và SYSTEM_ADMIN. Cần cập nhật enum Role ở backend trước khi đăng nhập được.`,
      })
      return
    }

    writeSession({ username: res.data.username, role }, res.data.token)
    router.push('/overview')
  }

  return (
    <main className="login" data-testid="login">
      <h1 className="page__title">Đăng nhập</h1>
      <p className="page__subtitle">Compliance Officer</p>

      <form onSubmit={submit} className="form">
        <label className="form__field">
          <span>Tài khoản</span>
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
        </label>
        <label className="form__field">
          <span>Mật khẩu</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>

        <ApiErrorBanner code={error?.code} message={error?.message} />

        <div className="form__actions">
          <button type="submit" disabled={busy}>
            {busy ? 'Đang đăng nhập…' : 'Đăng nhập'}
          </button>
        </div>
      </form>
    </main>
  )
}
