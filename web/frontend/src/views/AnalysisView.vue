<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAnalysis } from '@/composables/useAnalysis'
import AnalyzeEmptyState from '@/components/analyze/AnalyzeEmptyState.vue'
import AnalyzeRunningState from '@/components/analyze/AnalyzeRunningState.vue'
import AnalyzeResultsState from '@/components/analyze/AnalyzeResultsState.vue'
import type { AnalysisFilters } from '@/types'

const route = useRoute()

const {
  currentAnalysis,
  isAnalyzing,
  progress,
  startAnalysis,
  fetchAnalysis,
  clearAnalysis,
} = useAnalysis()

// Track the active directory path to show in the running state header
const activeDirectoryPath = ref('')

// ── State machine ─────────────────────────────────────────────────────────
// Three exclusive states: empty | running | results
// 'results' is shown when currentAnalysis is set; 'restart' clears it back to empty.
const viewState = computed<'empty' | 'running' | 'results'>(() => {
  if (isAnalyzing.value) return 'running'
  if (currentAnalysis.value) return 'results'
  return 'empty'
})

// ── Event handlers ────────────────────────────────────────────────────────

async function handleStart(payload: { directory_path: string; filters: AnalysisFilters }) {
  activeDirectoryPath.value = payload.directory_path
  await startAnalysis(payload.directory_path, payload.filters)
}

function handleCancel() {
  clearAnalysis()
  activeDirectoryPath.value = ''
}

function handleRestart() {
  clearAnalysis()
  activeDirectoryPath.value = ''
}

async function handleReanalyze() {
  const current = currentAnalysis.value
  if (!current) return
  const directory = current.directory_path
  const filters = (current.filters_applied ?? undefined) as AnalysisFilters | undefined
  activeDirectoryPath.value = directory
  clearAnalysis()
  await startAnalysis(directory, filters)
}

async function handleOpenAnalysis(id: number) {
  await fetchAnalysis(id)
}

// ── URL-based deep-link: ?id=N loads a past analysis on mount ────────────
onMounted(async () => {
  const analysisId = route.query.id
  if (analysisId) {
    await fetchAnalysis(Number(analysisId))
  }
})

</script>

<template>
  <div>
    <AnalyzeEmptyState
      v-if="viewState === 'empty'"
      @start="handleStart"
      @open-analysis="handleOpenAnalysis"
    />

    <AnalyzeRunningState
      v-else-if="viewState === 'running'"
      :progress="progress"
      :directory-path="activeDirectoryPath"
      @cancel="handleCancel"
    />

    <AnalyzeResultsState
      v-else-if="viewState === 'results' && currentAnalysis"
      :analysis="currentAnalysis"
      @restart="handleRestart"
      @reanalyze="handleReanalyze"
    />
  </div>
</template>
