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
  error,
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

function dismissError() {
  // Clearing the analysis state also clears `error`; cheaper than a separate ref.
  clearAnalysis()
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
    <!-- Surface API errors instead of flickering back to empty state silently. -->
    <div
      v-if="error && viewState === 'empty'"
      class="mb-4 rounded-lg ring-1 ring-rose-500/30 bg-rose-500/10 px-4 py-3 flex items-start gap-3"
    >
      <svg width="16" height="16" viewBox="0 0 20 20" fill="none" class="mt-0.5 text-rose-300 shrink-0">
        <path d="M10 6v5m0 3v.01M3 10a7 7 0 1014 0 7 7 0 00-14 0z"
              stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
      </svg>
      <div class="flex-1 min-w-0">
        <div class="text-[12px] uppercase tracking-[0.12em] text-rose-300 font-semibold">
          Analysis couldn't start
        </div>
        <div class="text-[13px] text-rose-100 mt-0.5 break-words">{{ error }}</div>
      </div>
      <button
        @click="dismissError"
        class="shrink-0 text-rose-300 hover:text-rose-100 text-[11px] underline underline-offset-2"
      >Dismiss</button>
    </div>

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
