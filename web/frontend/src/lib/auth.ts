import { ref } from 'vue'
import { getRuntimeToken, isTauri } from './runtime'

/**
 * Single-token auth state for the Mettle frontend.
 *
 * The backend (when METTLE_TOKEN is set) requires every request to carry
 * `Authorization: Bearer <token>`. We store the token in localStorage so
 * it persists across reloads. The UI listens to `needsToken` and shows a
 * modal whenever the value becomes true.
 *
 * In the Tauri desktop build the sidecar generates a per-launch token,
 * which Rust hands to the frontend during `initRuntime()`. That token
 * always wins over the localStorage one — there's no token modal in
 * desktop mode because the user never types it.
 */

const TOKEN_KEY = 'mettle-token'

export const needsToken = ref(false)

export function getToken(): string | null {
  const runtime = getRuntimeToken()
  if (runtime) return runtime
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(t: string): void {
  localStorage.setItem(TOKEN_KEY, t)
  needsToken.value = false
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

/** Called on a 401 response. Clears the stored token and signals the modal. */
export function promptForToken(): void {
  // Desktop mode: the runtime token is correct by construction; a 401 here
  // is a real bug, not a missing-token UX. Don't fire the prompt modal.
  if (isTauri()) return
  clearToken()
  needsToken.value = true
}
