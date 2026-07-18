'use client'

import { useSyncExternalStore } from 'react'
import { SESSION_EXPIRED_EVENT } from '@/lib/apiClient'
import { SESSION_CHANGED_EVENT, SESSION_KEY, parseSession, type Session } from '@/lib/session'

/**
 * Reads the session from localStorage the way React 19 wants external state read:
 * through useSyncExternalStore rather than setState-inside-an-effect.
 *
 * getSnapshot MUST return a stable reference for unchanged data, so the parsed
 * object is memoised against the raw string — returning a fresh object each call
 * makes React re-render forever.
 */
let cachedRaw: string | null = null
let cachedSession: Session | null = null

function getSnapshot(): Session | null {
  const raw = window.localStorage.getItem(SESSION_KEY)
  if (raw !== cachedRaw) {
    cachedRaw = raw
    cachedSession = parseSession(raw)
  }
  return cachedSession
}

/**
 * The server cannot read localStorage, so it reports `undefined` = "not known
 * yet" — deliberately NOT null. null means "checked, and there is no session",
 * and a guard that cannot tell the two apart redirects to /login during
 * hydration, before the client has had a chance to read storage.
 */
function getServerSnapshot(): Session | null | undefined {
  return undefined
}

function subscribe(onChange: () => void): () => void {
  // `storage` covers other tabs; the custom events cover this one, since
  // localStorage writes do not fire `storage` in the tab that made them.
  window.addEventListener('storage', onChange)
  window.addEventListener(SESSION_EXPIRED_EVENT, onChange)
  window.addEventListener(SESSION_CHANGED_EVENT, onChange)
  return () => {
    window.removeEventListener('storage', onChange)
    window.removeEventListener(SESSION_EXPIRED_EVENT, onChange)
    window.removeEventListener(SESSION_CHANGED_EVENT, onChange)
  }
}

/** `undefined` = chưa xác định (đang hydrate) · `null` = không có phiên. */
export function useSession(): Session | null | undefined {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}
