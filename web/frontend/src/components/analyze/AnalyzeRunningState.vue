<script setup lang="ts">
import { computed } from 'vue'
import ProgressRing from './ProgressRing.vue'
import PhaseTracker from './PhaseTracker.vue'
import LiveCounterTile from './LiveCounterTile.vue'
import ConsolePanel from './ConsolePanel.vue'
import { fmtNum, fmtDuration } from '@/lib/format'
import type { Tone } from '@/lib/tone'
import type { AnalysisProgress } from '@/types'

const props = defineProps<{
  progress: AnalysisProgress
  directoryPath?: string
}>()

const emit = defineEmits<{
  (e: 'cancel'): void
}>()

// Derived values — optional fields default to 0/empty so the UI degrades
// gracefully when the backend hasn't emitted richer telemetry yet.
const pct = computed(() =>
  props.progress.total > 0
    ? Math.round((props.progress.current / props.progress.total) * 100)
    : 0,
)

// Phase derivation: prefer backend-supplied phase, otherwise infer from
// progress. discovering → counting → analyzing → finalizing.
const derivedPhase = computed<string>(() => {
  if (props.progress.phase) return props.progress.phase
  if (props.progress.total === 0) return 'discovering'
  if (pct.value < 100) return 'analyzing'
  return 'finalizing'
})

const elapsedSec = computed(() => {
  if (!props.progress.started_at) return 0
  return Math.max(0, Math.floor((Date.now() - new Date(props.progress.started_at).getTime()) / 1000))
})

const etaSec = computed<number | null>(() => {
  if (props.progress.current <= 0) return null
  return Math.round((elapsedSec.value / props.progress.current) * (props.progress.total - props.progress.current))
})

const secretsTone = computed<Tone>(() =>
  (props.progress.secrets_found ?? 0) > 0 ? 'rose' : 'slate',
)

const projectsValue = computed(() => props.progress.projects_discovered ?? props.progress.total ?? 0)
const filesValue = computed(() => fmtNum(props.progress.files_counted ?? 0))
const todosValue = computed(() => props.progress.todos_found ?? 0)
const secretsValue = computed(() => props.progress.secrets_found ?? 0)
const logsValue = computed<string[]>(() => props.progress.logs ?? [])
</script>

<template>
  <div class="space-y-6">

    <!-- ── Top bar ──────────────────────────────────────────────────── -->
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <div class="flex items-center gap-2 mb-1">
          <span class="px-2 py-0.5 rounded text-[10px] font-semibold tracking-[0.18em] uppercase bg-indigo-500/15 text-indigo-300 ring-1 ring-inset ring-indigo-500/20">
            Running
          </span>
          <span class="inline-flex items-center gap-1.5 text-[11px] text-slate-400">
            <span class="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
            live
          </span>
        </div>
        <h1 class="text-[24px] sm:text-[28px] font-semibold tracking-tight text-slate-100">
          Analyzing portfolio
        </h1>
        <p v-if="directoryPath" class="text-[13px] text-slate-400 mt-1 font-mono">
          {{ directoryPath }}
        </p>
      </div>

      <button
        class="px-3 py-1.5 text-[12px] rounded-md border border-slate-800 bg-slate-900 text-slate-300 hover:text-rose-300 hover:border-rose-500/40 transition-colors flex items-center gap-1.5"
        @click="emit('cancel')"
      >
        <svg width="13" height="13" viewBox="0 0 20 20" fill="none">
          <path d="M6 6l8 8M14 6l-8 8" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
        </svg>
        Cancel
      </button>
    </div>

    <!-- ── Ring + status card ───────────────────────────────────────── -->
    <div class="rounded-2xl ring-1 ring-slate-800 bg-slate-900/60 p-5 sm:p-6">
      <div class="flex flex-col sm:flex-row items-center gap-6">

        <!-- Progress ring -->
        <ProgressRing :percent="pct" />

        <!-- Status + progress bar + phase tracker -->
        <div class="flex-1 min-w-0 w-full">
          <div class="flex items-baseline justify-between gap-3 mb-1.5">
            <div class="min-w-0">
              <div class="text-[12px] text-slate-500">{{ progress.message }}</div>
              <div class="flex items-baseline gap-2 mt-1">
                <span
                  v-if="progress.project_name"
                  class="text-[18px] font-semibold text-slate-100 truncate font-mono"
                >{{ progress.project_name }}</span>
                <span class="text-[11px] text-slate-500 tabular-nums shrink-0">
                  {{ progress.current }} / {{ progress.total }}
                </span>
              </div>
            </div>
            <div class="text-right shrink-0">
              <div class="text-[11px] text-slate-500">Elapsed</div>
              <div class="text-[14px] tabular-nums text-slate-200">{{ fmtDuration(elapsedSec) }}</div>
              <div v-if="etaSec != null" class="text-[10.5px] text-slate-500 mt-0.5">
                ~{{ fmtDuration(etaSec) }} left
              </div>
            </div>
          </div>

          <!-- Progress bar -->
          <div class="h-2 w-full rounded-full bg-slate-800 overflow-hidden relative">
            <div
              class="h-full bg-gradient-to-r from-indigo-500 to-sky-400 transition-[width] duration-500"
              :style="{ width: `${pct}%` }"
            />
            <div class="absolute inset-y-0 left-0 w-12 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer-slide" />
          </div>

          <!-- Phase tracker -->
          <div class="mt-4">
            <PhaseTracker :phase="derivedPhase" />
          </div>
        </div>
      </div>
    </div>

    <!-- ── Live counters ────────────────────────────────────────────── -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <LiveCounterTile
        label="Projects"
        tone="indigo"
        :value="projectsValue"
      >
        <template #icon>
          <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
            <rect x="3" y="4" width="6" height="6" rx="1" stroke="currentColor" stroke-width="1.75"/>
            <rect x="11" y="10" width="6" height="6" rx="1" stroke="currentColor" stroke-width="1.75"/>
          </svg>
        </template>
      </LiveCounterTile>

      <LiveCounterTile
        label="Files counted"
        tone="sky"
        :value="filesValue"
      >
        <template #icon>
          <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
            <path d="M5 3h7l3 3v11a1 1 0 01-1 1H5a1 1 0 01-1-1V4a1 1 0 011-1z" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/>
          </svg>
        </template>
      </LiveCounterTile>

      <LiveCounterTile
        label="TODOs"
        tone="amber"
        :value="todosValue"
      >
        <template #icon>
          <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
            <path d="M4 5h12M4 10h12M4 15h7" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
          </svg>
        </template>
      </LiveCounterTile>

      <LiveCounterTile
        label="Secrets flagged"
        :tone="secretsTone"
        :value="secretsValue"
      >
        <template #icon>
          <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
            <path d="M10 3l8 14H2L10 3z" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/>
            <circle cx="10" cy="13" r="1" fill="currentColor"/>
          </svg>
        </template>
      </LiveCounterTile>
    </div>

    <!-- ── Console ──────────────────────────────────────────────────── -->
    <ConsolePanel :logs="logsValue" :shimmer="true" />

  </div>
</template>

<style scoped>
@keyframes shimmerSlide {
  0%   { transform: translateX(-100%) }
  100% { transform: translateX(900%)  }
}
.animate-shimmer-slide {
  animation: shimmerSlide 1.6s ease-in-out infinite;
}
</style>
