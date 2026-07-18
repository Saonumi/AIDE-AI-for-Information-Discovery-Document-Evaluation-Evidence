/**
 * HTTP client for the VAIC2026 backend.
 *
 * Two rules that come straight from the spec:
 *
 *  1. Never throw. Every call resolves to an ApiResult so a page renders a
 *     degraded state instead of a blank error boundary.
 *  2. Never hide a fallback. When the real endpoint is missing the client serves
 *     a fixture from Phụ lục B and stamps `source: 'MOCK'`, which the UI must
 *     surface as a badge (spec §10.5: "Badge backend thật/mock/fallback").
 *
 * Paths follow spec §9 exactly. Requests go to /api/* and next.config.ts rewrites
 * them to FastAPI, so the browser stays same-origin.
 */
import { ERROR_CODE, type BackendMode } from '@/types/domain'
import type { ApiErrorBody } from '@/types/api'

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api'
const TIMEOUT_MS = Number(process.env.NEXT_PUBLIC_API_TIMEOUT_MS ?? 60_000)
const TOKEN_KEY = 'vaic-token'

/**
 * Fired once when a request carrying a token is rejected as unauthenticated.
 * The workspace shell listens and performs the logout + redirect.
 */
export const SESSION_EXPIRED_EVENT = 'vaic:session-expired'

export interface ApiResult<T> {
  ok: boolean
  status: number
  data?: T
  /** Where the payload actually came from — REAL backend or a local fixture. */
  source: BackendMode
  /** Stable machine code from §9.1; the UI switches on this, never on `message`. */
  code?: string
  message?: string
  details?: Record<string, unknown>
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null): void {
  if (typeof window === 'undefined') return
  if (token) window.localStorage.setItem(TOKEN_KEY, token)
  else window.localStorage.removeItem(TOKEN_KEY)
}

interface RequestOptions<T> {
  json?: unknown
  body?: BodyInit
  params?: Record<string, string | undefined>
  /** Fixture used when the endpoint is missing or unreachable. */
  fallback?: () => T
}

function parseError(status: number, payload: unknown): { code?: string; message: string; details?: Record<string, unknown> } {
  // §9.1 envelope: {"error": {"code", "message", "details"}}
  if (payload && typeof payload === 'object' && 'error' in payload) {
    const err = (payload as ApiErrorBody).error
    if (err && typeof err === 'object') {
      return { code: err.code, message: err.message ?? `HTTP ${status}`, details: err.details }
    }
  }
  // FastAPI's default {"detail": ...}
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail: unknown }).detail
    return { message: typeof detail === 'string' ? detail : JSON.stringify(detail) }
  }
  return { message: typeof payload === 'string' && payload ? payload : `HTTP ${status}` }
}

async function request<T>(method: string, path: string, options: RequestOptions<T> = {}): Promise<ApiResult<T>> {
  const query = new URLSearchParams()
  for (const [k, v] of Object.entries(options.params ?? {})) {
    if (v !== undefined && v !== '') query.set(k, v)
  }
  const url = `${BASE_URL}${path}${query.toString() ? `?${query}` : ''}`

  const headers: Record<string, string> = { Accept: 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (options.json !== undefined) headers['Content-Type'] = 'application/json'

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)

  let response: Response
  try {
    response = await fetch(url, {
      method,
      headers,
      body: options.json !== undefined ? JSON.stringify(options.json) : options.body,
      signal: controller.signal,
    })
  } catch {
    clearTimeout(timer)
    // Backend unreachable. Degrade to the fixture, but `source: 'MOCK'` makes the
    // banner appear — the degraded state is announced, never silent. No error
    // code here: a served fixture is not a failed request, and passing one would
    // light up the error banner on a screen that rendered fine.
    if (options.fallback) {
      return { ok: true, status: 0, data: options.fallback(), source: 'MOCK' }
    }
    return { ok: false, status: 0, source: 'FALLBACK', code: ERROR_CODE.BACKEND_DEGRADED, message: `Không kết nối được API (${path})` }
  }
  clearTimeout(timer)

  let payload: unknown = null
  const text = await response.text()
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = text
    }
  }

  if (!response.ok) {
    const parsed = parseError(response.status, payload)

    // An expired or missing token must never look like "no data": without a
    // stable code here the screen renders an empty table and implies the store
    // is genuinely empty.
    // 401 while we were actually carrying a token means the session died. The
    // `token` check matters: a failed login also returns 401, and treating that
    // as an expiry would destroy a perfectly good session in another tab.
    //
    // 403 is authorization, not authentication (§7.1 — SYSTEM_ADMIN is refused
    // business routes), so it must NOT log anyone out.
    //
    // This layer only reports. Clearing the session and redirecting is the
    // shell's job — a transport function silently mutating storage is how the
    // UI ends up in a state no component knows about.
    if (response.status === 401 && token && !parsed.code) {
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT))
      }
      return {
        ok: false,
        status: response.status,
        source: 'REAL',
        code: ERROR_CODE.UNAUTHENTICATED,
        message: parsed.message,
      }
    }
    if (response.status === 403 && !parsed.code) {
      return { ok: false, status: response.status, source: 'REAL', code: ERROR_CODE.FORBIDDEN, message: parsed.message }
    }
    // "Endpoint not built yet" / "backend not reachable" is what the fixture is
    // for: 404 and 501 say the route is missing, and 5xx covers both a crashed
    // backend and Next's rewrite proxy, which answers 502/500 — not a network
    // error — when nothing is listening upstream.
    //
    // 4xx below 500 (except 404) is a real backend answer and must reach the UI
    // intact, notably 409 REVIEW_NOT_COMPLETED which the activation gate needs.
    const endpointMissing = response.status === 404 || response.status === 501 || response.status >= 500
    // `!parsed.code` matters: a 5xx that still carries a §9.1 code is a business
    // answer, not a missing route. Substituting a fixture there would replace a
    // real "NOT_LEGAL_GROUND_TRUTH" with invented evidence.
    if (endpointMissing && options.fallback && !parsed.code) {
      return { ok: true, status: response.status, data: options.fallback(), source: 'MOCK' }
    }
    // A write has no fixture to fall back on. When the failure is infrastructure
    // rather than a business rule, label it with the stable BACKEND_DEGRADED code
    // — §9.1 says the UI must not put a raw upstream message in front of the user.
    if (endpointMissing && !parsed.code) {
      return {
        ok: false,
        status: response.status,
        source: 'FALLBACK',
        code: ERROR_CODE.BACKEND_DEGRADED,
        message: `${path} — HTTP ${response.status}`,
      }
    }
    return { ok: false, status: response.status, source: 'REAL', ...parsed }
  }

  return { ok: true, status: response.status, data: payload as T, source: 'REAL' }
}

export const apiGet = <T>(path: string, options?: RequestOptions<T>) => request<T>('GET', path, options)
export const apiPost = <T>(path: string, options?: RequestOptions<T>) => request<T>('POST', path, options)
