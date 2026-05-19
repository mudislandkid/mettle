const API_BASE = '/api'

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
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: unknown } | null
    throw new Error(formatErrorDetail(body?.detail))
  }

  return response.json() as Promise<T>
}

export function getWebSocketUrl(path: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${path}`
}
