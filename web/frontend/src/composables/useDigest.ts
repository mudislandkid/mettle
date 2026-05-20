import { ref } from 'vue'
import type { DigestReport } from '@/types'
import { fetchDigest } from '@/api'

export function useDigest(initial?: { since?: string; top?: number; staleDays?: number }) {
  const since = ref(initial?.since ?? '7d')
  const top = ref(initial?.top ?? 5)
  const staleDays = ref(initial?.staleDays ?? 30)
  const report = ref<DigestReport | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      report.value = await fetchDigest({
        since: since.value,
        top: top.value,
        staleDays: staleDays.value,
      })
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load digest'
      report.value = null
    } finally {
      loading.value = false
    }
  }

  return { since, top, staleDays, report, loading, error, load }
}
