import type { NextConfig } from 'next'

/**
 * /api/* is proxied to FastAPI so the browser stays same-origin — no CORS setup
 * and no backend host compiled into the bundle. Point it elsewhere with
 * API_PROXY_TARGET when the backend is not on :8000.
 */
const API_TARGET = process.env.API_PROXY_TARGET ?? 'http://localhost:8000'

const nextConfig: NextConfig = {
  // 'standalone' lets the Docker image ship a minimal server bundle instead of
  // the whole node_modules tree.
  output: 'standalone',
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${API_TARGET}/:path*` }]
  },
}

export default nextConfig
