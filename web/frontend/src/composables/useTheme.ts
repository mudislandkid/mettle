import { onMounted, ref, watch } from 'vue'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'code-counter-theme'

// Module-level so every call to `useTheme()` shares the same source of truth.
const current = ref<Theme>(initialTheme())

function initialTheme(): Theme {
  if (typeof window === 'undefined') return 'light'
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') return stored
  } catch {
    // localStorage can throw in privacy modes; fall through to media query.
  }
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

function apply(theme: Theme) {
  if (typeof document === 'undefined') return
  document.documentElement.classList.toggle('dark', theme === 'dark')
  document.documentElement.style.colorScheme = theme
}

// Apply once at module load so the very first render is already correct.
apply(current.value)

export function useTheme() {
  function setTheme(next: Theme) {
    current.value = next
  }
  function toggle() {
    setTheme(current.value === 'dark' ? 'light' : 'dark')
  }

  // Keep the DOM + localStorage in sync whenever the value changes.
  watch(current, (next) => {
    apply(next)
    try {
      window.localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Ignore — non-fatal.
    }
  })

  // Listen to system preference changes, but only when the user hasn't set
  // an explicit preference yet. Mounted (rather than module-load) so we
  // don't double-attach during SSR / hot-reload.
  onMounted(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (event: MediaQueryListEvent) => {
      try {
        const stored = window.localStorage.getItem(STORAGE_KEY)
        if (stored === 'light' || stored === 'dark') return  // user override wins
      } catch {
        // No localStorage — system-follows behavior is the only sensible default.
      }
      setTheme(event.matches ? 'dark' : 'light')
    }
    // `addEventListener` not supported on every Safari ≤14; guard.
    if (typeof media.addEventListener === 'function') {
      media.addEventListener('change', handler)
    } else if (typeof (media as MediaQueryList & { addListener?: (fn: typeof handler) => void }).addListener === 'function') {
      ;(media as MediaQueryList & { addListener: (fn: typeof handler) => void }).addListener(handler)
    }
  })

  return { theme: current, setTheme, toggle }
}
