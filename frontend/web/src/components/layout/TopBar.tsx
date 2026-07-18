'use client'

/**
 * Top bar: who is signed in, and which backends are really answering.
 *
 * §10.5 requires a backend real/mock/fallback badge to be visible; putting it in
 * the shell means every screen inherits it instead of each page remembering.
 */
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { BackendModeBadge } from '@/components/common/StatusBadge'
import { api } from '@/lib/api'
import { useSession } from '@/hooks/useSession'
import { clearSession } from '@/lib/session'
import type { BackendMode } from '@/types/domain'
import type { HealthDetailsResponse } from '@/types/api'

/**
 * Worst-case wins: one mocked component makes the whole system "not real".
 *
 * `components` is treated as possibly absent because a backend that only
 * implements the older flat /health payload returns no such field — and this
 * component sits in the workspace layout, so throwing here blanks every screen.
 */
function aggregateMode(health?: HealthDetailsResponse): BackendMode {
  const components = health?.components
  if (!components?.length) return 'FALLBACK'
  if (components.some((c) => c.mode === 'FALLBACK')) return 'FALLBACK'
  if (components.some((c) => c.mode === 'MOCK')) return 'MOCK'
  return 'REAL'
}

export function TopBar() {
  const router = useRouter()
  const session = useSession()
  const [health, setHealth] = useState<HealthDetailsResponse>()

  useEffect(() => {
    let alive = true
    void api.healthDetails().then((res) => {
      if (alive) setHealth(res.data)
    })
    return () => {
      alive = false
    }
  }, [])

  const mode = aggregateMode(health)
  const degraded = (health?.components ?? []).filter((c) => c.mode !== 'REAL').map((c) => c.name)

  return (
    <header className="topbar" data-testid="topbar">
      <div className="topbar__status">
        <BackendModeBadge
          value={mode}
          detail={degraded.length ? `Đang mock/fallback: ${degraded.join(', ')}` : 'Tất cả backend đang chạy thật'}
        />
        {degraded.length > 0 && (
          <span className="topbar__degraded" data-testid="topbar-degraded">
            {degraded.join(' · ')}
          </span>
        )}
      </div>

      <div className="topbar__user" data-testid="topbar-user">
        <span className="topbar__username">{session?.username ?? '—'}</span>
        <span className="topbar__role" data-role={session?.role}>
          {session?.role ?? ''}
        </span>
        <button
          type="button"
          onClick={() => {
            clearSession()
            router.push('/login')
          }}
        >
          Đăng xuất
        </button>
      </div>
    </header>
  )
}
