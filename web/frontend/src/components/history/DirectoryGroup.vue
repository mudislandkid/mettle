<script setup lang="ts">
// DirectoryGroup.vue — collapsible group header (path + count + latest + trend + sparkline)
// plus a timeline body of AnalysisTimelineRow entries.

import { ref, computed } from 'vue'
import { fmtNum, fmtRelative } from '@/lib/format'
import GrowthSparkline from './GrowthSparkline.vue'
import AnalysisTimelineRow from './AnalysisTimelineRow.vue'
import type { AnalysisListItem } from '@/types'

type EnrichedItem = AnalysisListItem & {
  error_message?: string | null
  duration_seconds?: number | null
  avg_health?: number | null
  secrets_found?: number
  progress_pct?: number | null
  total_projects?: number
}

const props = defineProps<{
  path: string
  runs: EnrichedItem[]
  defaultOpen: boolean
}>()

const emit = defineEmits<{
  view: [id: number]
  delete: [id: number]
}>()

const open = ref(props.defaultOpen)

// Ascending completed runs for sparkline (oldest first)
const completedAsc = computed(() =>
  [...props.runs].filter(r => r.status === 'completed').reverse()
)

const lineSeries = computed(() => completedAsc.value.map(r => r.total_lines || 0))

const latest = computed(() => props.runs[0] ?? null)

const failedCount = computed(() => props.runs.filter(r => r.status === 'failed').length)
const runningRun = computed(() => props.runs.find(r => r.status === 'running') ?? null)

const trend = computed<number | null>(() => {
  const asc = completedAsc.value
  if (asc.length < 2) return null
  const a = asc[asc.length - 2].total_lines || 0
  const b = asc[asc.length - 1].total_lines || 0
  if (a === 0) return null
  return ((b - a) / a) * 100
})

const trendClass = computed(() => {
  if (trend.value === null) return 'text-slate-400'
  return trend.value > 0 ? 'text-emerald-300' : trend.value < 0 ? 'text-rose-300' : 'text-slate-400'
})

const trendArrow = computed(() => {
  if (trend.value === null) return '→'
  return trend.value > 0 ? '↑' : trend.value < 0 ? '↓' : '→'
})

const shortPath = computed(() => props.path.replace(/^\/Users\/[^/]+/, '~'))

// For delta calculation: within completed runs, each run's prev is the next older completed run
function prevLinesFor(run: EnrichedItem): number | null {
  const completed = props.runs.filter(r => r.status === 'completed')
  const idx = completed.findIndex(r => r.id === run.id)
  if (idx < 0) return null
  return completed[idx + 1]?.total_lines ?? null
}

const comparable = computed(() => props.runs.filter(r => r.status === 'completed').length >= 2)
</script>

<template>
  <section class="rounded-xl ring-1 ring-slate-800 bg-slate-900/40 overflow-hidden">
    <!-- Header (toggle) -->
    <button
      class="w-full grid grid-cols-[auto_1fr_auto] items-center gap-4 px-4 sm:px-5 py-4 text-left hover:bg-slate-900/60 transition-colors"
      @click="open = !open"
    >
      <!-- Chevron icon -->
      <span
        class="shrink-0 w-7 h-7 rounded-md bg-slate-800 ring-1 ring-inset ring-slate-700 flex items-center justify-center text-slate-400 transition-transform"
        :class="open ? 'rotate-90' : ''"
      >
        <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
          <path d="M7 5l5 5-5 5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </span>

      <!-- Path + meta -->
      <div class="min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="font-mono text-[14px] text-slate-100 truncate">{{ shortPath }}</span>
          <span class="text-[10.5px] uppercase tracking-[0.12em] text-slate-500 font-semibold">
            {{ runs.length }} run{{ runs.length === 1 ? '' : 's' }}
          </span>
          <!-- Running pill -->
          <span
            v-if="runningRun"
            class="inline-flex items-center gap-1.5 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-[0.1em] bg-indigo-500/15 text-indigo-300 ring-1 ring-inset ring-indigo-500/25"
          >
            <span class="w-1 h-1 rounded-full bg-indigo-400 animate-pulse"/>
            Running{{ runningRun.progress_pct != null ? ` ${runningRun.progress_pct}%` : '' }}
          </span>
          <span v-else-if="failedCount > 0" class="text-[10.5px] text-rose-300/80">
            {{ failedCount }} failed
          </span>
        </div>
        <!-- Latest summary -->
        <div
          v-if="latest && latest.status === 'completed'"
          class="flex items-center gap-4 mt-1 text-[11.5px] text-slate-500"
        >
          <span>Latest <span class="text-slate-300">{{ fmtRelative(latest.analyzed_at) }}</span></span>
          <span v-if="latest.total_projects != null">· <span class="tabular-nums text-slate-300">{{ latest.total_projects }}</span> projects</span>
          <span>· <span class="tabular-nums text-slate-300">{{ fmtNum(latest.total_lines) }}</span> lines</span>
          <span v-if="trend !== null" class="tabular-nums" :class="trendClass">
            {{ trendArrow }} {{ Math.abs(trend).toFixed(1) }}% vs prior
          </span>
        </div>
      </div>

      <!-- Sparkline -->
      <div class="hidden sm:block shrink-0">
        <GrowthSparkline
          v-if="lineSeries.length >= 2"
          :values="lineSeries"
          :width="110"
          :height="32"
        />
      </div>
    </button>

    <!-- Timeline body -->
    <ul v-if="open" class="border-t border-slate-800/70 divide-y divide-slate-800/40">
      <AnalysisTimelineRow
        v-for="(run, i) in runs"
        :key="run.id"
        :run="run"
        :prev-total-lines="prevLinesFor(run)"
        :is-first="i === 0"
        :is-last="i === runs.length - 1"
        :comparable="comparable"
        @view="emit('view', run.id)"
        @delete="emit('delete', run.id)"
      />
    </ul>
  </section>
</template>
