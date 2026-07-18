'use client'

import { useCallback, useEffect, useState } from 'react'
import type { ApiResult } from '@/lib/apiClient'
import type { BackendMode } from '@/types/domain'

interface Resource<T> {
  data?: T
  /** Whether this payload came from the backend or a fixture (§10.5 badge). */
  source: BackendMode
  code?: string
  error?: string
  loading: boolean
  reload: () => void
}

/**
 * Fetch-on-mount for page data.
 *
 * `fetcher` must be stable — wrap it in useCallback at the call site, otherwise
 * this refetches on every render.
 */
export function useResource<T>(fetcher: () => Promise<ApiResult<T>>): Resource<T> {
  const [state, setState] = useState<{ data?: T; source: BackendMode; code?: string; error?: string }>({
    source: 'REAL',
  })
  const [loading, setLoading] = useState(true)
  const [nonce, setNonce] = useState(0)

  const reload = useCallback(() => setNonce((n) => n + 1), [])

  useEffect(() => {
    let alive = true
    // setState lives inside the async callback, never in the effect body — a
    // synchronous setState here would cascade a render on every mount.
    void fetcher().then((res) => {
      if (!alive) return
      setLoading(false)
      setState(
        res.ok
          ? { data: res.data, source: res.source, code: res.code }
          : { source: res.source, code: res.code, error: res.message },
      )
    })
    return () => {
      alive = false
    }
  }, [fetcher, nonce])

  return { ...state, loading, reload }
}
