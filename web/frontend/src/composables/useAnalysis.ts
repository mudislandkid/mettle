import { ref, computed, onScopeDispose } from 'vue'
import { useWebSocket } from './useWebSocket'
import * as api from '@/api/analysis'
import type { Analysis, AnalysisFilters, AnalysisProgress } from '@/types'

const INITIAL_PROGRESS: AnalysisProgress = {
  status: 'idle',
  current: 0,
  total: 0,
  project_name: '',
  message: '',
  logs: [],
}

export function useAnalysis() {
  const currentAnalysis = ref<Analysis | null>(null)
  const isAnalyzing = ref(false)
  const progress = ref<AnalysisProgress>({ ...INITIAL_PROGRESS })
  const error = ref<string | null>(null)

  let activeSocket: ReturnType<typeof useWebSocket<AnalysisProgress>> | null = null
  let pollFallbackTimer: ReturnType<typeof setTimeout> | null = null

  function stopPollFallback() {
    if (pollFallbackTimer !== null) {
      clearTimeout(pollFallbackTimer)
      pollFallbackTimer = null
    }
  }

  function tearDown() {
    stopPollFallback()
    activeSocket?.disconnect()
    activeSocket = null
  }

  async function startAnalysis(directory: string, filters?: AnalysisFilters) {
    tearDown()
    isAnalyzing.value = true
    error.value = null
    progress.value = { ...INITIAL_PROGRESS, status: 'pending', message: 'Starting analysis...' }

    let id: number
    try {
      ;({ id } = await api.startAnalysis(directory, filters))
    } catch (e) {
      error.value = (e as Error).message
      isAnalyzing.value = false
      return
    }

    const socket = useWebSocket<AnalysisProgress>(`/api/analysis/ws/${id}`, {
      autoReconnect: true,
      onMessage(data) {
        progress.value = data
        if (data.status === 'completed') {
          isAnalyzing.value = false
          fetchAnalysis(id)
          tearDown()
        } else if (data.status === 'failed') {
          isAnalyzing.value = false
          error.value = data.error || 'Analysis failed'
          tearDown()
        }
      },
    })
    activeSocket = socket
    socket.connect()

    // One-shot fallback poll after 10 min — only triggers if the websocket
    // never delivered a terminal state (e.g. backend crashed silently). Avoids
    // the previous double-fetch race where both the WS and a 2s setInterval
    // would refresh state in parallel.
    pollFallbackTimer = setTimeout(async () => {
      try {
        const status = await api.getAnalysisStatus(id)
        if (status.status === 'completed') {
          isAnalyzing.value = false
          await fetchAnalysis(id)
        } else if (status.status === 'failed') {
          isAnalyzing.value = false
          error.value = status.message || 'Analysis failed'
        } else {
          error.value = 'Analysis did not finish within 10 minutes'
          isAnalyzing.value = false
        }
      } catch (e) {
        error.value = (e as Error).message
        isAnalyzing.value = false
      } finally {
        tearDown()
      }
    }, 10 * 60 * 1000)
  }

  async function fetchAnalysis(id: number) {
    try {
      currentAnalysis.value = await api.getAnalysis(id)
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  function clearAnalysis() {
    tearDown()
    currentAnalysis.value = null
    error.value = null
    progress.value = { ...INITIAL_PROGRESS }
    isAnalyzing.value = false
  }

  const progressPercentage = computed(() => {
    if (progress.value.total === 0) return 0
    return Math.round((progress.value.current / progress.value.total) * 100)
  })

  onScopeDispose(tearDown)

  return {
    currentAnalysis,
    isAnalyzing,
    progress,
    progressPercentage,
    error,
    startAnalysis,
    fetchAnalysis,
    clearAnalysis,
  }
}
