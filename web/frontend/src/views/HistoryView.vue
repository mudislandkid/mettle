<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listAnalyses } from '@/api/analysis'
import type { AnalysisListItem, Analysis } from '@/types'
import HistoryHero from '@/components/history/HistoryHero.vue'
import PortfolioHighlights from '@/components/history/PortfolioHighlights.vue'
import RunsByDirectory from '@/components/history/RunsByDirectory.vue'

const analyses = ref<AnalysisListItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

async function loadAnalyses() {
  loading.value = true
  error.value = null
  try {
    analyses.value = await listAnalyses(200, 0)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

onMounted(loadAnalyses)
</script>

<template>
  <div class="space-y-10 px-4 sm:px-6 lg:px-8 py-6">

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-24">
      <div class="w-8 h-8 rounded-full border-4 border-indigo-500 border-t-transparent animate-spin" />
    </div>

    <!-- Error -->
    <div
      v-else-if="error"
      class="rounded-xl ring-1 ring-rose-500/30 bg-rose-500/10 px-6 py-10 text-center text-[13px] text-rose-300"
    >
      {{ error }}
    </div>

    <!-- Content -->
    <template v-else>
      <!-- 1. Hero + Activity Heatmap -->
      <HistoryHero :analyses="(analyses as unknown as Analysis[])" />

      <!-- 2. Portfolio Highlights (4-card grid, self-loading) -->
      <PortfolioHighlights />

      <!-- 3. Runs by Directory (toolbar + groups + timelines) -->
      <RunsByDirectory :analyses="analyses" @refresh="loadAnalyses" />
    </template>

  </div>
</template>
