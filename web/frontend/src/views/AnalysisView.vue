<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import DirectoryInput from '@/components/DirectoryInput.vue'
import FilterControls from '@/components/FilterControls.vue'
import SummaryStats from '@/components/SummaryStats.vue'
import ProjectTableNative from '@/components/ProjectTableNative.vue'
import ExportButtons from '@/components/ExportButtons.vue'
import AnalysisProgress from '@/components/AnalysisProgress.vue'
import { useAnalysis } from '@/composables/useAnalysis'
import type { AnalysisFilters } from '@/types'

const route = useRoute()
const {
  currentAnalysis,
  isAnalyzing,
  progress,
  progressPercentage,
  error,
  startAnalysis,
  fetchAnalysis,
  clearAnalysis,
} = useAnalysis()

const directoryPath = ref('')
const filters = ref<AnalysisFilters>({
  github_user: null,
  skip_public_sdks: true,
  max_files: 0,
  include_internal: false,
})

async function handleAnalyze() {
  if (!directoryPath.value) return
  await startAnalysis(directoryPath.value, filters.value)
}

function handleNewAnalysis() {
  clearAnalysis()
  directoryPath.value = ''
}

onMounted(async () => {
  const analysisId = route.query.id
  if (analysisId) {
    await fetchAnalysis(Number(analysisId))
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- Analysis form -->
    <div v-if="!currentAnalysis" class="bg-white rounded-lg shadow-sm border border-slate-200 p-6 dark:bg-slate-900 dark:border-slate-700">
      <h2 class="text-lg font-semibold text-slate-800 mb-4 dark:text-slate-200">Analyze Projects</h2>

      <div class="space-y-4">
        <DirectoryInput
          v-model="directoryPath"
          :disabled="isAnalyzing"
        />

        <FilterControls
          v-model="filters"
          :disabled="isAnalyzing"
        />

        <div class="flex items-center gap-4">
          <button
            @click="handleAnalyze"
            :disabled="!directoryPath || isAnalyzing"
            class="px-4 py-2 bg-indigo-600 text-white rounded-md font-medium hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors dark:hover:bg-indigo-600 dark:bg-slate-600"
          >
            {{ isAnalyzing ? 'Analyzing...' : 'Start Analysis' }}
          </button>

          <span v-if="error" class="text-red-600 text-sm dark:text-red-400">
            {{ error }}
          </span>
        </div>
      </div>

      <!-- Progress -->
      <AnalysisProgress
        v-if="isAnalyzing"
        :progress="progress"
        :percentage="progressPercentage"
        class="mt-6"
      />
    </div>

    <!-- Results -->
    <template v-if="currentAnalysis">
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-200">
            {{ currentAnalysis.directory_path }}
          </h2>
          <p class="text-sm text-slate-500 dark:text-slate-400">
            Analyzed {{ new Date(currentAnalysis.analyzed_at).toLocaleString() }}
          </p>
        </div>
        <div class="flex gap-2">
          <ExportButtons :analysisId="currentAnalysis.id" />
          <button
            @click="handleNewAnalysis"
            class="px-4 py-2 bg-slate-100 text-slate-700 rounded-md font-medium hover:bg-slate-200 transition-colors dark:bg-slate-800 dark:text-slate-300 dark:bg-slate-700"
          >
            New Analysis
          </button>
        </div>
      </div>

      <SummaryStats :analysis="currentAnalysis" />

      <ProjectTableNative
        :projects="currentAnalysis.projects"
        @projects-changed="fetchAnalysis(currentAnalysis.id)"
      />
    </template>
  </div>
</template>
