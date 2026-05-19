<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getProjectHighlights } from '@/api/projects'
import type { ProjectHighlight, ProjectHighlights } from '@/types'

const highlights = ref<ProjectHighlights | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    highlights.value = await getProjectHighlights(5)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

onMounted(load)

defineExpose({ reload: load })

const panels = computed(() => {
  if (!highlights.value) return []
  return [
    {
      key: 'biggest',
      title: 'Biggest projects',
      caption: 'Most total lines (latest snapshot per project)',
      items: highlights.value.biggest,
      column: 'lines',
    },
    {
      key: 'stalest',
      title: 'Stalest projects',
      caption: 'Oldest last-commit, excluding archived',
      items: highlights.value.stalest,
      column: 'last_commit',
    },
    {
      key: 'todo_heavy',
      title: 'Most TODOs',
      caption: 'Captured TODO / FIXME / XXX / HACK markers',
      items: highlights.value.todo_heavy,
      column: 'todos',
    },
    {
      key: 'lowest_health',
      title: 'Lowest health score',
      caption: 'Composite health score, ascending',
      items: highlights.value.lowest_health,
      column: 'health',
    },
  ] as const
})

function commitAge(p: ProjectHighlight): string {
  if (!p.last_commit_at) return 'never'
  const ms = Date.now() - new Date(p.last_commit_at).getTime()
  if (Number.isNaN(ms)) return '—'
  const days = Math.floor(ms / 86_400_000)
  if (days < 1) return 'today'
  if (days < 30) return `${days}d`
  if (days < 365) return `${Math.floor(days / 30)}mo`
  return `${Math.floor(days / 365)}y`
}

function healthClass(score: number): string {
  if (score >= 80) return 'text-emerald-600'
  if (score >= 60) return 'text-lime-600'
  if (score >= 40) return 'text-amber-600'
  if (score >= 20) return 'text-orange-600'
  return 'text-red-600'
}
</script>

<template>
  <section class="space-y-3">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-200">Highlights</h2>
        <p class="text-xs text-slate-500 dark:text-slate-400">Across every completed analysis, latest snapshot per project.</p>
      </div>
      <button
        @click="load"
        class="px-3 py-1.5 text-xs bg-slate-100 text-slate-700 rounded-md hover:bg-slate-200 transition-colors dark:bg-slate-800 dark:text-slate-300 dark:bg-slate-700"
      >
        Refresh
      </button>
    </div>

    <div v-if="loading" class="text-sm text-slate-500 dark:text-slate-400">Loading highlights…</div>
    <div v-else-if="error" class="text-sm text-red-600 dark:text-red-400">{{ error }}</div>

    <div v-else class="grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4">
      <div
        v-for="panel in panels"
        :key="panel.key"
        class="bg-white rounded-lg border border-slate-200 p-4 dark:bg-slate-900 dark:border-slate-700"
      >
        <div class="mb-2">
          <h3 class="text-sm font-semibold text-slate-900 dark:text-slate-100">{{ panel.title }}</h3>
          <p class="text-[11px] text-slate-500 dark:text-slate-400">{{ panel.caption }}</p>
        </div>

        <ol v-if="panel.items.length" class="space-y-1">
          <li
            v-for="p in panel.items"
            :key="p.id"
            class="flex items-center justify-between gap-2 text-sm"
          >
            <router-link
              :to="{ name: 'project-detail', params: { id: p.id } }"
              class="truncate text-indigo-600 hover:text-indigo-700 hover:underline dark:text-indigo-400 dark:text-indigo-300"
              :title="p.path"
            >
              {{ p.name }}
            </router-link>
            <span class="shrink-0 text-xs tabular-nums text-slate-700 font-semibold dark:text-slate-300">
              <template v-if="panel.column === 'lines'">{{ p.total_lines.toLocaleString() }}</template>
              <template v-else-if="panel.column === 'last_commit'">{{ commitAge(p) }}</template>
              <template v-else-if="panel.column === 'todos'">{{ p.todos }}</template>
              <template v-else-if="panel.column === 'health'">
                <span :class="healthClass(p.health_score)">{{ p.health_score.toFixed(0) }}</span>
              </template>
            </span>
          </li>
        </ol>
        <div v-else class="text-xs text-slate-400 dark:text-slate-500">No data yet.</div>
      </div>
    </div>
  </section>
</template>
