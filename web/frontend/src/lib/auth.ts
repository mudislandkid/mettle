import { ref } from 'vue'

/**
 * Single-token auth state for the Mettle frontend.
 *
 * The backend (when METTLE_TOKEN is set) requires every request to carry
 * `Authorization: Bearer <token>`. We store the token in localStorage so
 * it persists across reloads. The UI listens to `needsToken` and shows a
 * modal whenever the value becomes true.
 */

const TOKEN_KEY = 'mettle-token'

export const needsToken = ref(false)

export function getToken(): string | null {
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
  clearToken()
  needsToken.value = true
}
