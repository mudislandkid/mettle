/**
 * Runtime detection + API base URL resolution.
 *
 * In a browser, the frontend talks to a same-origin `/api/...` (Vite proxies
 * to uvicorn in dev; FastAPI serves the dist in prod). In the Tauri desktop
 * shell, the Vue bundle is loaded from `tauri://localhost` and the Python
 * sidecar listens on a random localhost port — so we ask the Rust side
 * "where is the sidecar?" before any API call goes out, then use that base
 * for the lifetime of the session.
 *
 * Boot order: `initRuntime()` runs before `app.mount()` in main.ts. Once
 * resolved, `apiBase()` / `wsBase()` / `getRuntimeToken()` are synchronous.
 */

interface SidecarHandshake {
  port: number
  token: string
}

let runtimeReady = false
let sidecar: SidecarHandshake | null = null

export function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window
}

/**
 * Resolve the API base. In Tauri this is `http://127.0.0.1:<sidecarPort>`;
 * in the browser it's a relative `''` (so fetch hits the same origin under
 * `/api`).
 */
export function apiBase(): string {
  if (sidecar) return `http://127.0.0.1:${sidecar.port}`
  return ''
}

export function wsBase(): string {
  if (sidecar) return `ws://127.0.0.1:${sidecar.port}`
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}`
}

/**
 * The token Tauri injected for this sidecar process. In browser mode this
 * returns null and the caller falls back to localStorage.
 */
export function getRuntimeToken(): string | null {
  return sidecar?.token ?? null
}

export function isRuntimeReady(): boolean {
  return runtimeReady
}

/**
 * Negotiate with the Rust host. Called once during app boot. Throws if the
 * sidecar handshake hasn't completed yet — Rust waits for the "MettleReady"
 * stdout line before resolving this command, so the await is bounded by
 * sidecar startup (typically <2s, generous timeout in Rust ~30s).
 */
export async function initRuntime(): Promise<void> {
  if (runtimeReady) return
  if (!isTauri()) {
    runtimeReady = true
    return
  }
  const { invoke } = await import('@tauri-apps/api/core')
  sidecar = await invoke<SidecarHandshake>('get_sidecar')
  runtimeReady = true
}
