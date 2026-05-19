<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { getProjectHealth } from '@/api/projects'
import type { HealthBreakdown } from '@/types'

const props = defineProps<{
  projectId: number
}>()

const breakdown = ref<HealthBreakdown | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function load(id: number) {
  loading.value = true
  error.value = null
  try {
    breakdown.value = await getProjectHealth(id)
  } catch (e) {
    error.value = (e as Error).message
    breakdown.value = null
  } finally {
    loading.value = false
  }
}

watch(() => props.projectId, (id) => { if (id) load(id) }, { immediate: true })

const headlineScore = computed(() => breakdown.value?.score ?? 0)
const headlineColor = computed(() => {
  const s = headlineScore.value
  if (s >= 80) return 'text-emerald-600'
  if (s >= 60) return 'text-lime-600'
  if (s >= 40) return 'text-amber-600'
  if (s >= 20) return 'text-orange-600'
  return 'text-red-600'
})

const COMPONENT_LABELS: Record<string, string> = {
  comment_ratio: 'Comment ratio',
  test_ratio: 'Test coverage',
  commit_recency: 'Commit recency',
  todo_density: 'TODO density',
  file_size: 'File size',
  metadata: 'Metadata',
}

function barClass(score: number): string {
  if (score >= 80) return 'bg-emerald-500'
  if (score >= 60) return 'bg-lime-500'
  if (score >= 40) return 'bg-amber-500'
  if (score >= 20) return 'bg-orange-500'
  return 'bg-red-500'
}
</script>

<template>
  <div class="bg-white rounded-lg border border-slate-200 p-6 space-y-4 dark:bg-slate-900 dark:border-slate-700">
    <div class="flex items-baseline justify-between">
      <div>
        <h3 class="text-sm font-semibold text-slate-900 uppercase tracking-wide dark:text-slate-100">Health Score</h3>
        <p class="text-xs text-slate-500 dark:text-slate-400">Composite 0-100 score with explanations.</p>
      </div>
      <div :class="['text-4xl font-bold tabular-nums', headlineColor]">
        {{ headlineScore.toFixed(1) }}
      </div>
    </div>

    <div v-if="loading" class="text-sm text-slate-500 dark:text-slate-400">Loading…</div>
    <div v-else-if="error" class="text-sm text-red-600 dark:text-red-400">{{ error }}</div>
    <div v-else-if="breakdown" class="space-y-2">
      <div
        v-for="c in breakdown.components"
        :key="c.name"
        class="flex items-center gap-3"
      >
        <div class="w-32 shrink-0 text-xs text-slate-600 dark:text-slate-400">
          {{ COMPONENT_LABELS[c.name] || c.name }}
          <span class="text-slate-400 dark:text-slate-500">({{ Math.round(c.weight * 100) }}%)</span>
        </div>
        <div class="flex-1 h-2 bg-slate-100 rounded overflow-hidden dark:bg-slate-800">
          <div
            :class="['h-full transition-all', barClass(c.score)]"
            :style="{ width: `${c.score}%` }"
          ></div>
        </div>
        <div class="w-12 shrink-0 text-right text-xs tabular-nums text-slate-700 font-semibold dark:text-slate-300">
          {{ c.score.toFixed(0) }}
        </div>
        <div class="w-56 shrink-0 text-xs text-slate-500 truncate dark:text-slate-400" :title="c.detail">
          {{ c.detail }}
        </div>
      </div>
    </div>
  </div>
</template>
