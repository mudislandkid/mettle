import { ref, watch, computed, type Ref } from 'vue'
import { getProjectGitStats } from '@/api/git'
import type { GitStatsResponse } from '@/types'

export function useGitStats(projectId: Ref<number>) {
  const stats = ref<GitStatsResponse | null>(null)
  const loading = ref(false)
  // `error` is reserved for actual fetch failures. "Not a git repo" is a
  // legitimate state that the UI should render distinctly, not as an error.
  const error = ref<string | null>(null)
  const isGitRepo = computed(() => stats.value?.is_git_repo ?? false)

  async function fetchStats() {
    if (!projectId.value) return

    loading.value = true
    error.value = null

    try {
      stats.value = await getProjectGitStats(projectId.value)
    } catch (e) {
      error.value = (e as Error).message || 'Failed to load Git statistics'
      stats.value = null
    } finally {
      loading.value = false
    }
  }

  function refresh() {
    return fetchStats()
  }

  watch(projectId, fetchStats, { immediate: true })

  return {
    stats,
    loading,
    error,
    isGitRepo,
    refresh,
  }
}
