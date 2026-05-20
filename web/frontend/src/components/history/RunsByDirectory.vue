<script setup lang="ts">
// RunsByDirectory.vue — composer: holds filter state, groups Analysis[] by directory_path,
// renders DirectoryGroup list. Emits view/delete for parent to handle API calls.

import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { deleteAnalysis } from '@/api/analysis'
import RunsToolbar from './RunsToolbar.vue'
import DirectoryGroup from './DirectoryGroup.vue'
import type { AnalysisListItem } from '@/types'

type EnrichedItem = AnalysisListItem & {
  error_message?: string | null
  duration_seconds?: number | null
  avg_health?: number | null
  secrets_found?: number
  progress_pct?: number | null
  total_projects?: number
}

interface DirectoryGroupData {
  path: string
  runs: EnrichedItem[]
  latest: Date
}

const props = defineProps<{
  analyses: EnrichedItem[]
}>()

const emit = defineEmits<{
  refresh: []
}>()

const router = useRouter()

const search = ref('')
const statusFilter = ref('all')

// Live list (filtered on delete locally)
const localAnalyses = ref<EnrichedItem[]>([...props.analyses])

// Keep local in sync when parent refreshes the prop
// (parent replaces the array reference → watcher would be cleaner, but defineProps
//  re-initialisation is handled at mount; task 22 will wire live refresh)
// For this task the parent passes the initial list; deletions are handled locally.

const counts = computed(() => ({
  all:       localAnalyses.value.length,
  completed: localAnalyses.value.filter(a => a.status === 'completed').length,
  running:   localAnalyses.value.filter(a => a.status === 'running').length,
  failed:    localAnalyses.value.filter(a => a.status === 'failed').length,
}))

const groups = computed<DirectoryGroupData[]>(() => {
  const q = search.value.trim().toLowerCase()

  const filtered = localAnalyses.value.filter(a => {
    if (statusFilter.value !== 'all' && a.status !== statusFilter.value) return false
    if (q) return a.directory_path.toLowerCase().includes(q)
    return true
  })

  const map = new Map<string, EnrichedItem[]>()
  for (const a of filtered) {
    if (!map.has(a.directory_path)) map.set(a.directory_path, [])
    map.get(a.directory_path)!.push(a)
  }

  const out: DirectoryGroupData[] = []
  for (const [path, runs] of map.entries()) {
    // Sort runs within group: most-recent first
    runs.sort((a, b) => new Date(b.analyzed_at).getTime() - new Date(a.analyzed_at).getTime())
    out.push({ path, runs, latest: new Date(runs[0].analyzed_at) })
  }
  // Sort groups by most-recent analysis first
  out.sort((a, b) => b.latest.getTime() - a.latest.getTime())
  return out
})

async function handleView(id: number) {
  await router.push({ name: 'analysis', query: { id } })
}

async function handleDelete(id: number) {
  if (!confirm('Delete this analysis? This cannot be undone.')) return
  try {
    await deleteAnalysis(id)
    localAnalyses.value = localAnalyses.value.filter(a => a.id !== id)
  } catch (err) {
    alert(`Delete failed: ${(err as Error).message}`)
  }
}
</script>

<template>
  <section>
    <!-- Section header -->
    <div class="flex flex-wrap items-end justify-between gap-3 mb-3">
      <div>
        <h2 class="text-[15px] font-semibold text-slate-100">Runs by directory</h2>
        <p class="text-[12px] text-slate-500">
          Grouped by path so you can see growth over time. Click a row to expand.
        </p>
      </div>
      <button
        class="px-3 py-1.5 text-[12px] rounded-md border border-slate-800 bg-slate-900 text-slate-300 hover:text-slate-100 hover:border-slate-700 flex items-center gap-1.5"
        @click="emit('refresh')"
      >
        <svg width="13" height="13" viewBox="0 0 20 20" fill="none">
          <path
            d="M4 10a6 6 0 0110-4.5M16 10a6 6 0 01-10 4.5M16 4v3.5h-3.5M4 16v-3.5h3.5"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        Refresh
      </button>
    </div>

    <!-- Toolbar -->
    <RunsToolbar
      v-model:search="search"
      v-model:status-filter="statusFilter"
      :counts="counts"
      class="mb-3"
    />

    <!-- Groups -->
    <div v-if="groups.length > 0" class="space-y-3">
      <DirectoryGroup
        v-for="(group, i) in groups"
        :key="group.path"
        :path="group.path"
        :runs="group.runs"
        :default-open="i === 0"
        @view="handleView"
        @delete="handleDelete"
      />
    </div>

    <!-- Empty state -->
    <div
      v-else
      class="rounded-xl ring-1 ring-dashed ring-slate-800 px-6 py-12 text-center"
    >
      <div class="text-[13px] text-slate-400">No analyses match your filters.</div>
    </div>
  </section>
</template>
