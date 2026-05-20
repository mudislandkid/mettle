<script setup lang="ts">
// AnalysisTimelineRow.vue — single analysis run within a directory group timeline.
// Shows: date, run id, status pill, duration, counts, delta, health dot, secrets, actions.

import { computed } from 'vue'
import { fmtNum, fmtCalendar, fmtDuration } from '@/lib/format'
import { TONE, healthBucket } from '@/lib/tone'
import type { AnalysisListItem } from '@/types'

const props = defineProps<{
  run: AnalysisListItem & {
    error_message?: string | null
    duration_seconds?: number | null
    avg_health?: number | null
    secrets_found?: number
    progress_pct?: number | null
    total_projects?: number
  }
  prevTotalLines: number | null
  isFirst: boolean
  isLast: boolean
  comparable: boolean
}>()

const emit = defineEmits<{
  view: []
  delete: []
}>()

const delta = computed<number | null>(() => {
  if (props.prevTotalLines == null || props.run.total_lines == null) return null
  return props.run.total_lines - props.prevTotalLines
})

const health = computed(() => {
  if (props.run.avg_health == null) return null
  return healthBucket(props.run.avg_health)
})

const healthBarClass = computed(() => {
  if (!health.value) return ''
  return TONE[health.value.tone].bar
})

const spineTopClass = computed(() => props.isFirst ? 'top-[14px]' : 'top-0')
const spineBottomClass = computed(() => props.isLast ? 'bottom-1/2' : 'bottom-0')

const spineDotClass = computed(() => {
  switch (props.run.status) {
    case 'completed': return 'bg-emerald-400 ring-2 ring-emerald-500/20'
    case 'running':   return 'bg-indigo-400 ring-2 ring-indigo-500/30 animate-pulse'
    default:          return 'bg-rose-400 ring-2 ring-rose-500/20'
  }
})
</script>

<template>
  <li class="relative group/run grid grid-cols-[auto_1fr_auto] items-center gap-4 px-4 py-2.5 hover:bg-slate-900/50 transition-colors">
    <!-- Spine -->
    <div class="relative flex flex-col items-center self-stretch w-3 shrink-0">
      <span
        class="absolute left-1/2 -translate-x-1/2 w-px bg-slate-800"
        :class="[spineTopClass, spineBottomClass]"
      />
      <span
        class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full"
        :class="spineDotClass"
      />
    </div>

    <!-- Main content -->
    <div class="min-w-0">
      <!-- Row 1: date, id, status, duration -->
      <div class="flex items-center gap-2 flex-wrap">
        <span class="text-[12.5px] text-slate-200 tabular-nums">
          {{ fmtCalendar(run.analyzed_at) }}
        </span>
        <span class="text-[10.5px] text-slate-500">· #{{ run.id }}</span>

        <!-- Status pill -->
        <span
          v-if="run.status === 'completed'"
          class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-[0.1em] bg-emerald-500/15 text-emerald-300 ring-1 ring-inset ring-emerald-500/25"
        >
          <span class="w-1 h-1 rounded-full bg-emerald-400"/>Completed
        </span>
        <span
          v-else-if="run.status === 'failed'"
          class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-[0.1em] bg-rose-500/15 text-rose-300 ring-1 ring-inset ring-rose-500/25"
        >
          <span class="w-1 h-1 rounded-full bg-rose-400"/>Failed
        </span>
        <span
          v-else-if="run.status === 'running'"
          class="inline-flex items-center gap-1.5 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-[0.1em] bg-indigo-500/15 text-indigo-300 ring-1 ring-inset ring-indigo-500/25"
        >
          <span class="w-1 h-1 rounded-full bg-indigo-400 animate-pulse"/>
          Running{{ run.progress_pct != null ? ` ${run.progress_pct}%` : '' }}
        </span>
        <span
          v-else
          class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-[0.1em] bg-slate-500/15 text-slate-400 ring-1 ring-inset ring-slate-500/25"
        >
          {{ run.status }}
        </span>

        <span
          v-if="run.status === 'completed' && run.duration_seconds != null"
          class="text-[10.5px] text-slate-500"
        >
          ran in {{ fmtDuration(run.duration_seconds) }}
        </span>
      </div>

      <!-- Row 2 (completed): counts + delta + health + secrets -->
      <div
        v-if="run.status === 'completed'"
        class="flex items-center gap-4 mt-1 text-[11.5px] text-slate-400"
      >
        <span v-if="run.total_projects != null">
          <span class="tabular-nums text-slate-200">{{ run.total_projects }}</span> projects
        </span>
        <span>
          <span class="tabular-nums text-slate-200">{{ fmtNum(run.total_files) }}</span> files
        </span>
        <span>
          <span class="tabular-nums text-slate-200">{{ fmtNum(run.total_lines) }}</span> lines
        </span>
        <span
          v-if="delta !== null && delta !== 0"
          class="tabular-nums"
          :class="delta > 0 ? 'text-emerald-300' : 'text-rose-300'"
        >
          {{ delta > 0 ? '+' : '' }}{{ fmtNum(Math.abs(delta)) }}
        </span>
        <span v-if="health" class="flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full" :class="healthBarClass"/>
          <span class="tabular-nums text-slate-200">{{ run.avg_health }}</span> health
        </span>
        <span v-if="(run.secrets_found ?? 0) > 0" class="text-rose-300 tabular-nums">
          {{ run.secrets_found }} secret{{ (run.secrets_found ?? 0) > 1 ? 's' : '' }}
        </span>
      </div>

      <!-- Row 2 (failed): error message -->
      <div
        v-if="run.status === 'failed'"
        class="flex items-center gap-2 mt-1 text-[11.5px] text-rose-300/90"
      >
        <svg width="11" height="11" viewBox="0 0 20 20" fill="none">
          <path d="M10 3l8 14H2L10 3z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
          <circle cx="10" cy="13" r=".75" fill="currentColor"/>
        </svg>
        <span class="truncate font-mono text-[11px]">{{ run.error_message || 'Analysis failed' }}</span>
      </div>

      <!-- Row 2 (running): progress bar -->
      <div v-if="run.status === 'running'" class="mt-1.5 h-1 w-48 rounded-full bg-slate-800 overflow-hidden">
        <div
          class="h-full bg-gradient-to-r from-indigo-500 to-sky-400 transition-[width]"
          :style="{ width: `${run.progress_pct || 0}%` }"
        />
      </div>
    </div>

    <!-- Actions (hover-revealed) -->
    <div class="flex items-center gap-1 opacity-0 group-hover/run:opacity-100 focus-within:opacity-100 transition-opacity">
      <!-- Diff: disabled, coming soon -->
      <button
        v-if="run.status === 'completed' && comparable"
        disabled
        title="Coming soon"
        class="px-2 py-1 text-[11px] rounded-md text-slate-600 cursor-not-allowed"
      >
        Diff
      </button>

      <!-- View -->
      <button
        v-if="run.status === 'completed'"
        class="px-2 py-1 text-[11px] rounded-md bg-indigo-500/20 text-indigo-200 ring-1 ring-inset ring-indigo-500/30 hover:bg-indigo-500/30"
        @click="emit('view')"
      >
        View
      </button>

      <!-- Delete -->
      <button
        title="Delete this analysis"
        class="px-2 py-1 text-[11px] rounded-md text-slate-500 hover:bg-rose-500/15 hover:text-rose-300"
        @click="emit('delete')"
      >
        <svg width="13" height="13" viewBox="0 0 20 20" fill="none">
          <path
            d="M5 6h10M8 6V4h4v2M6 6l1 11h6l1-11"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>
    </div>
  </li>
</template>
