'use client'

/**
 * Workspace shell — everything behind the landing page.
 *
 * Guards on session: §7.1 requires business routes to demand COMPLIANCE_OFFICER.
 * This is a UX guard only; the backend remains the enforcement point.
 */
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { SideNav } from '@/components/layout/SideNav'
import { TopBar } from '@/components/layout/TopBar'
import { useSession } from '@/hooks/useSession'
import { canUseBusinessRoutes, clearSession } from '@/lib/session'
import { SESSION_EXPIRED_EVENT } from '@/lib/apiClient'

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const session = useSession()

  // `undefined` means the client has not read storage yet (hydration); only a
  // definite `null` may trigger the redirect, otherwise every load bounces to
  // /login before the session is known.
  useEffect(() => {
    if (session === null) router.replace('/login')
  }, [session, router])

  useEffect(() => {
    function onExpired() {
      clearSession()
      router.replace('/login')
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired)
  }, [router])

  if (!session) return <div className="state">Đang kiểm tra phiên đăng nhập…</div>

  return (
    <div className="app-shell">
      <SideNav />
      <div className="app-shell__main">
        <TopBar />
        {canUseBusinessRoutes(session) ? (
          children
        ) : (
          <div className="page">
            <div className="banner banner--error" role="alert">
              <strong>Không đủ quyền.</strong> Các màn hình nghiệp vụ yêu cầu vai trò COMPLIANCE_OFFICER. Vai trò hiện
              tại: {session.role}.
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
