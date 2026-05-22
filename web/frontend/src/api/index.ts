import { getToken, promptForToken } from '../lib/auth'
import { apiBase, wsBase } from '../lib/runtime'
import type { DigestReport } from '@/types'

// Resolved at call time so it picks up the Tauri sidecar port once
// initRuntime() has completed during app boot.
function apiUrl(endpoint: string): string {
  return `${apiBase()}/api${endpoint}`
}

function formatErrorDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    // FastAPI validation errors arrive as [{loc, msg, type}, ...]
    return detail
      .map((d) => {
        if (d && typeof d === 'object' && 'msg' in d) {
          const loc = Array.isArray((d as { loc?: unknown }).loc)
            ? ((d as { loc: unknown[] }).loc.join('.'))
            : ''
          return loc ? `${loc}: ${(d as { msg: string }).msg}` : (d as { msg: string }).msg
        }
        return JSON.stringify(d)
      })
      .join('; ')
  }
  if (detail && typeof detail === 'object') {
    return JSON.stringify(detail)
  }
  return 'Request failed'
}

export async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(apiUrl(endpoint), {
    ...options,
    headers,
  })

  if (response.status === 401) {
    // Clear and prompt; throw so callers see the failure.
    promptForToken()
    throw new Error('Authentication required.')
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: unknown } | null
    throw new Error(formatErrorDetail(body?.detail))
  }

  return response.json() as Promise<T>
}

export function getWebSocketUrl(path: string): string {
  return `${wsBase()}${path}`
}

export async function fetchDigest(params: {
  since?: string
  top?: number
  staleDays?: number
}): Promise<DigestReport> {
  const sp = new URLSearchParams()
  if (params.since) sp.set('since', params.since)
  if (params.top != null) sp.set('top', String(params.top))
  if (params.staleDays != null) sp.set('stale_days', String(params.staleDays))
  return fetchApi<DigestReport>(`/digest/?${sp.toString()}`)
}
