<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { compareProjects } from '@/api/projects'
import type { ProjectCompareEntry, ProjectCompareResponse } from '@/types'

const route = useRoute()
const router = useRouter()

const projectIds = computed<number[]>(() => {
  const raw = route.query.ids
  if (typeof raw !== 'string') return []
  return raw.split(',').map((s) => Number(s.trim())).filter((n) => Number.isFinite(n) && n > 0)
})

const data = ref<ProjectCompareResponse | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function load() {
  if (projectIds.value.length === 0) {
    data.value = null
    return
  }
  loading.value = true
  error.value = null
  try {
    data.value = await compareProjects(projectIds.value)
  } catch (e) {
    error.value = (e as Error).message
    data.value = null
  } finally {
    loading.value = false
  }
}

watch(projectIds, load, { immediate: true })

// Rows: each entry is one metric. `pick` extracts the comparable value.
type Row = {
  label: string
  pick: (p: ProjectCompareEntry) => number | string
  format?: (v: number | string) => string
  highlight?: 'max' | 'min'  // visually bold the winner across the row
  tooltip?: string
}

function fmtInt(v: number | string): string {
  return typeof v === 'number' ? v.toLocaleString() : String(v)
}

function commitAge(p: ProjectCompareEntry): string {
  if (!p.last_commit_at) return 'never'
  const ms = Date.now() - new Date(p.last_commit_at).getTime()
  if (Number.isNaN(ms)) return '—'
  const days = Math.floor(ms / 86_400_000)
  if (days < 1) return 'today'
  if (days < 30) return `${days}d`
  if (days < 365) return `${Math.floor(days / 30)}mo`
  return `${Math.floor(days / 365)}y`
}

const rows: Row[] = [
  { label: 'Files', pick: (p) => p.total_files, format: fmtInt },
  { label: 'Total lines', pick: (p) => p.total_lines, format: fmtInt, highlight: 'max' },
  { label: 'Code lines', pick: (p) => p.code_lines, format: fmtInt },
  { label: 'Comment lines', pick: (p) => p.comment_lines, format: fmtInt },
  { label: 'Blank lines', pick: (p) => p.blank_lines, format: fmtInt },
  { label: 'Functions', pick: (p) => p.functions, format: fmtInt },
  { label: 'Classes', pick: (p) => p.classes, format: fmtInt },
  { label: 'Imports', pick: (p) => p.imports, format: fmtInt },
  { label: 'TODOs', pick: (p) => p.todos, format: fmtInt, highlight: 'min', tooltip: 'Lower is better' },
  { label: 'Test files', pick: (p) => p.test_files, format: fmtInt, highlight: 'max' },
  { label: 'Test lines', pick: (p) => p.test_total_lines, format: fmtInt, highlight: 'max' },
  {
    label: 'Avg lines / file',
    pick: (p) => Math.round(p.avg_lines_per_file),
    format: fmtInt,
    highlight: 'min',
    tooltip: 'Smaller files = healthier separation of concerns',
  },
  {
    label: 'Health score',
    pick: (p) => p.health_score,
    format: (v) => (typeof v === 'number' ? v.toFixed(1) : String(v)),
    highlight: 'max',
  },
  { label: 'Last commit', pick: (p) => commitAge(p) },
  {
    label: 'Languages',
    pick: (p) => p.languages.slice(0, 4).join(', ') + (p.languages.length > 4 ? '…' : ''),
  },
]

function winnerIndex(row: Row): number | null {
  if (!row.highlight || !data.value) return null
  const values = data.value.projects.map((p) => {
    const v = row.pick(p)
    return typeof v === 'number' ? v : Number.NaN
  })
  if (values.some(Number.isNaN)) return null
  const target = row.highlight === 'max' ? Math.max(...values) : Math.min(...values)
  // If they're all equal there's no winner worth highlighting.
  if (values.every((v) => v === target)) return null
  return values.indexOf(target)
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-100">Compare projects</h2>
        <p class="text-xs text-slate-500 dark:text-slate-400">
          Side-by-side snapshot from each project's most recent analysis.
        </p>
      </div>
      <button
        @click="router.back()"
        class="px-3 py-1.5 text-sm bg-slate-100 text-slate-700 rounded-md hover:bg-slate-200 transition-colors dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
      >
        Back
      </button>
    </div>

    <div v-if="projectIds.length === 0"
         class="bg-white rounded-lg border border-slate-200 p-8 text-center text-slate-500 dark:bg-slate-900 dark:border-slate-700 dark:text-slate-400">
      No projects to compare. Add <code class="font-mono">?ids=1,2,3</code> to the URL, or pick projects from a table and click "Compare selected".
    </div>

    <div v-else-if="loading"
         class="bg-white rounded-lg border border-slate-200 p-6 text-slate-500 dark:bg-slate-900 dark:border-slate-700 dark:text-slate-400">
      Loading…
    </div>

    <div v-else-if="error"
         class="bg-white rounded-lg border border-red-200 p-6 text-red-700 dark:bg-slate-900 dark:border-red-500/30 dark:text-red-300">
      {{ error }}
    </div>

    <div v-else-if="data" class="overflow-x-auto bg-white rounded-lg border border-slate-200 dark:bg-slate-900 dark:border-slate-700">
      <table class="min-w-full text-sm">
        <thead class="bg-slate-50 dark:bg-slate-900">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider sticky left-0 bg-slate-50 dark:bg-slate-900 dark:text-slate-300">Metric</th>
            <th
              v-for="p in data.projects"
              :key="p.id"
              class="px-4 py-3 text-right text-xs font-semibold text-slate-700 uppercase tracking-wider dark:text-slate-300"
            >
              <router-link
                :to="{ name: 'project-detail', params: { id: p.id } }"
                class="text-indigo-600 hover:text-indigo-700 hover:underline dark:text-indigo-400"
                :title="p.path"
              >
                {{ p.name }}
              </router-link>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100 dark:divide-slate-800">
          <tr v-for="row in rows" :key="row.label">
            <th
              class="px-4 py-2 text-left text-xs font-medium text-slate-600 sticky left-0 bg-white dark:bg-slate-900 dark:text-slate-400"
              :title="row.tooltip"
            >
              {{ row.label }}
              <span v-if="row.tooltip" class="text-slate-400 dark:text-slate-500"> ⓘ</span>
            </th>
            <td
              v-for="(p, idx) in data.projects"
              :key="p.id"
              :class="[
                'px-4 py-2 text-right tabular-nums',
                winnerIndex(row) === idx
                  ? 'text-emerald-600 font-semibold dark:text-emerald-400'
                  : 'text-slate-700 dark:text-slate-300',
              ]"
            >
              {{ row.format ? row.format(row.pick(p)) : row.pick(p) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
