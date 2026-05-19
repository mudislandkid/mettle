<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getProjectDiff } from '@/api/projects'
import type { ProjectDiff, ProjectDiffEntry } from '@/types'

const route = useRoute()
const router = useRouter()

const projectId = computed(() => Number(route.params.id))
const otherParam = computed(() => {
  const v = route.query.other
  return typeof v === 'string' && v ? Number(v) : undefined
})

const diff = ref<ProjectDiff | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function load() {
  if (!projectId.value) return
  loading.value = true
  error.value = null
  try {
    diff.value = await getProjectDiff(projectId.value, otherParam.value)
  } catch (e) {
    error.value = (e as Error).message
    diff.value = null
  } finally {
    loading.value = false
  }
}

watch([projectId, otherParam], load, { immediate: true })

function formatDelta(d: number): string {
  const sign = d > 0 ? '+' : d < 0 ? '−' : ''
  return `${sign}${Math.abs(d).toLocaleString()}`
}

function deltaPct(entry: ProjectDiffEntry): string {
  if (entry.delta_pct === null || entry.delta_pct === undefined) return '—'
  const sign = entry.delta_pct > 0 ? '+' : entry.delta_pct < 0 ? '−' : ''
  return `${sign}${Math.abs(entry.delta_pct).toFixed(1)}%`
}

function deltaClass(delta: number, metric: string): string {
  // Some metrics are "more is bad" (todos). Others are "more is good".
  const lowerIsBetter = metric === 'todos'
  if (delta === 0) return 'text-slate-500'
  const isGood = lowerIsBetter ? delta < 0 : delta > 0
  return isGood ? 'text-emerald-600' : 'text-rose-600'
}

const METRIC_LABELS: Record<string, string> = {
  total_files: 'Files',
  total_lines: 'Total lines',
  code_lines: 'Code lines',
  comment_lines: 'Comment lines',
  blank_lines: 'Blank lines',
  functions: 'Functions',
  classes: 'Classes',
  todos: 'TODOs',
  imports: 'Imports',
  test_files: 'Test files',
  test_total_lines: 'Test lines',
  test_code_lines: 'Test code lines',
  health_score: 'Health score',
}

function formatDate(s: string): string {
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? s : d.toLocaleString()
}

function back() {
  router.push({ name: 'project-detail', params: { id: projectId.value } })
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center gap-2 text-sm">
      <button
        @click="back"
        class="text-indigo-600 hover:text-indigo-700 font-medium flex items-center gap-1 dark:text-indigo-400 dark:text-indigo-300"
      >
        ← Back to Project
      </button>
    </div>

    <div v-if="loading" class="bg-white rounded-lg border border-slate-200 p-6 text-slate-500 dark:bg-slate-900 dark:border-slate-700 dark:text-slate-400">
      Loading diff…
    </div>

    <div v-else-if="error" class="bg-white rounded-lg border border-red-200 p-6 text-red-700 dark:bg-slate-900 dark:border-red-500/30 dark:text-red-300">
      {{ error }}
    </div>

    <template v-else-if="diff">
      <div class="bg-white rounded-lg border border-slate-200 p-6 space-y-2 dark:bg-slate-900 dark:border-slate-700">
        <h2 class="text-lg font-semibold text-slate-900 dark:text-slate-100">Diff</h2>
        <p class="text-sm text-slate-500 font-mono truncate dark:text-slate-400">{{ diff.project_path }}</p>
        <p class="text-sm text-slate-600 dark:text-slate-400">
          <strong>{{ formatDate(diff.before.analyzed_at) }}</strong>
          <span class="text-slate-400 mx-2 dark:text-slate-500">→</span>
          <strong>{{ formatDate(diff.after.analyzed_at) }}</strong>
          <span class="text-slate-400 ml-2 dark:text-slate-500">({{ diff.days_between.toFixed(1) }} days)</span>
        </p>
      </div>

      <div class="bg-white rounded-lg border border-slate-200 overflow-hidden dark:bg-slate-900 dark:border-slate-700">
        <table class="min-w-full divide-y divide-slate-200">
          <thead class="bg-slate-50 dark:bg-slate-900">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider dark:text-slate-300">Metric</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-700 uppercase tracking-wider dark:text-slate-300">Before</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-700 uppercase tracking-wider dark:text-slate-300">After</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-700 uppercase tracking-wider dark:text-slate-300">Δ</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-700 uppercase tracking-wider dark:text-slate-300">Δ %</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="entry in diff.entries" :key="entry.metric">
              <td class="px-4 py-2 text-sm text-slate-700 dark:text-slate-300">{{ METRIC_LABELS[entry.metric] || entry.metric }}</td>
              <td class="px-4 py-2 text-sm tabular-nums text-right text-slate-600 dark:text-slate-400">{{ entry.before.toLocaleString() }}</td>
              <td class="px-4 py-2 text-sm tabular-nums text-right text-slate-900 font-medium dark:text-slate-100">{{ entry.after.toLocaleString() }}</td>
              <td class="px-4 py-2 text-sm tabular-nums text-right font-semibold" :class="deltaClass(entry.delta, entry.metric)">
                {{ formatDelta(entry.delta) }}
              </td>
              <td class="px-4 py-2 text-sm tabular-nums text-right" :class="deltaClass(entry.delta, entry.metric)">
                {{ deltaPct(entry) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="diff.languages_added.length || diff.languages_removed.length"
           class="bg-white rounded-lg border border-slate-200 p-4 space-y-2 text-sm dark:bg-slate-900 dark:border-slate-700">
        <div v-if="diff.languages_added.length">
          <span class="text-slate-500 font-semibold mr-2 dark:text-slate-400">Languages added:</span>
          <span v-for="l in diff.languages_added" :key="l"
                class="inline-block mr-2 px-2 py-0.5 rounded bg-emerald-100 text-emerald-700">{{ l }}</span>
        </div>
        <div v-if="diff.languages_removed.length">
          <span class="text-slate-500 font-semibold mr-2 dark:text-slate-400">Languages removed:</span>
          <span v-for="l in diff.languages_removed" :key="l"
                class="inline-block mr-2 px-2 py-0.5 rounded bg-rose-100 text-rose-700">{{ l }}</span>
        </div>
      </div>
    </template>
  </div>
</template>
