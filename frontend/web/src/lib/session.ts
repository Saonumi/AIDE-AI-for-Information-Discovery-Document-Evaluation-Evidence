/**
 * Session state.
 *
 * §6.1 deletes USER and EMPLOYEE: the only product persona is COMPLIANCE_OFFICER,
 * with SYSTEM_ADMIN as a technical role. Nothing in this UI may branch on any
 * other role value.
 */
import { setToken } from '@/lib/apiClient'
import { ROLE, type Role } from '@/types/domain'

export const SESSION_KEY = 'vaic-session'

/** Fired after this tab writes or clears the session (storage events do not). */
export const SESSION_CHANGED_EVENT = 'vaic:session-changed'

export interface Session {
  username: string
  role: Role
}

/** Pure parse + validation, so useSession can memoise on the raw string. */
export function parseSession(raw: string | null): Session | null {
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as Session
    // reject anything carrying a retired role rather than rendering a ghost persona
    if (parsed.role !== ROLE.COMPLIANCE_OFFICER && parsed.role !== ROLE.SYSTEM_ADMIN) return null
    return parsed
  } catch {
    return null
  }
}

export function readSession(): Session | null {
  if (typeof window === 'undefined') return null
  return parseSession(window.localStorage.getItem(SESSION_KEY))
}

function notifyChanged(): void {
  window.dispatchEvent(new CustomEvent(SESSION_CHANGED_EVENT))
}

export function writeSession(session: Session, token: string): void {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session))
  setToken(token)
  notifyChanged()
}

export function clearSession(): void {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(SESSION_KEY)
  setToken(null)
  notifyChanged()
}

/** All business routes require COMPLIANCE_OFFICER (§7.1). */
export function canUseBusinessRoutes(session: Session | null): boolean {
  return session?.role === ROLE.COMPLIANCE_OFFICER
}
