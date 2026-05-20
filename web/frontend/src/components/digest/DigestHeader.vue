<script setup lang="ts">
import { computed } from 'vue'
import type { DigestReport } from '@/types'
import { fmtCalendarLong, fmtCalendarShort, fmtWindow } from '@/lib/format'

const props = defineProps<{
  report: DigestReport
  since: string
  top: number
  staleDays: number
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'update:since', value: string): void
  (e: 'update:top', value: number): void
  (e: 'update:staleDays', value: number): void
  (e: 'refresh'): void
}>()

const generatedStr = computed(() => fmtCalendarLong(props.report.generated_at))
const windowStr = computed(() => fmtWindow(props.report.window_days))

const SINCE_OPTIONS: Array<{ label: string; days: number }> = [
  { label: '1d', days: 1 },
  { label: '7d', days: 7 },
  { label: '14d', days: 14 },
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
]

// Parse the "since" string back to days for highlighting the active chip
const sinceDays = computed(() => {
  const s = props.since.trim().toLowerCase()
  if (s.endsWith('d') && /^\d+d$/.test(s)) return parseInt(s.slice(0, -1), 10)
  if (s.endsWith('w') && /^\d+w$/.test(s)) return parseInt(s.slice(0, -1), 10) * 7
  if (s.endsWith('m') && /^\d+m$/.test(s)) return parseInt(s.slice(0, -1), 10) * 30
  if (/^\d+$/.test(s)) return parseInt(s, 10)
  return props.report.window_days
})

function setSinceDays(days: number) {
  emit('update:since', `${days}d`)
}

function decTop() { emit('update:top', Math.max(1, props.top - 1)) }
function incTop() { emit('update:top', Math.min(50, props.top + 1)) }
function decStale() { emit('update:staleDays', Math.max(1, props.staleDays - 1)) }
function incStale() { emit('update:staleDays', Math.min(365, props.staleDays + 1)) }

function copyMarkdown() {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(`# Mettle digest — ${windowStr.value}`)
  }
}

const coverageSegs = computed(() => {
  const total = Math.max(1, props.report.total_projects)
  return [
    { key: 'with_baseline', label: 'With baseline', n: props.report.projects_with_baseline, bar: 'bg-indigo-500', dot: 'bg-indigo-400' },
    { key: 'new',           label: 'New in window', n: props.report.projects_new,           bar: 'bg-sky-500',    dot: 'bg-sky-400' },
    { key: 'no_recent',     label: 'No recent',     n: props.report.projects_no_recent,     bar: 'bg-slate-600',  dot: 'bg-slate-400' },
  ].map((s) => ({ ...s, pct: (s.n / total) * 100 }))
})
</script>

<template>
  <div class="space-y-5">
    <!-- Title + meta -->
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div class="min-w-0">
        <div class="flex items-center gap-2 mb-1">
          <span class="px-2 py-0.5 rounded text-[10px] font-semibold tracking-[0.18em] uppercase bg-indigo-500/15 text-indigo-300 ring-1 ring-inset ring-indigo-500/20">Digest</span>
          <span class="text-[11px] text-slate-500 font-mono">v1 · cross-project</span>
        </div>
        <h1 class="text-[28px] sm:text-[32px] font-semibold tracking-tight text-slate-100 leading-tight">
          What changed across your portfolio
          <span class="text-slate-500 font-normal"> — {{ windowStr }}</span>
        </h1>
        <p class="text-[13px] text-slate-400 mt-1">
          Generated {{ generatedStr }}.
          Window <span class="font-mono text-slate-300">{{ fmtCalendarShort(report.window_start) }}</span>
          <span class="px-1.5 text-slate-600">→</span>
          <span class="font-mono text-slate-300">{{ fmtCalendarShort(report.generated_at) }}</span>.
          Stale threshold <span class="text-slate-300">{{ report.stale_days }}d</span>.
        </p>
      </div>

      <div class="flex items-center gap-2">
        <button
          @click="copyMarkdown"
          class="px-3 py-1.5 text-[12px] rounded-md border border-slate-800 bg-slate-900 text-slate-300 hover:text-slate-100 hover:border-slate-700 transition-colors flex items-center gap-1.5"
          title="Copy the report as Markdown (Slack / email / gh issue)"
        >
          <svg width="13" height="13" viewBox="0 0 20 20" fill="none"><rect x="5" y="5" width="11" height="11" rx="1.5" stroke="currentColor" stroke-width="1.5"/><path d="M4 13V4a1 1 0 011-1h9" stroke="currentColor" stroke-width="1.5"/></svg>
          Copy Markdown
        </button>
        <button
          @click="emit('refresh')"
          :disabled="loading"
          class="px-3 py-1.5 text-[12px] rounded-md bg-indigo-500/20 text-indigo-200 ring-1 ring-inset ring-indigo-500/30 hover:bg-indigo-500/30 disabled:opacity-50 transition-colors flex items-center gap-1.5"
        >
          <svg width="13" height="13" viewBox="0 0 20 20" fill="none" :class="loading ? 'animate-spin' : ''"><path d="M4 10a6 6 0 0110-4.5M16 10a6 6 0 01-10 4.5M16 4v3.5h-3.5M4 16v-3.5h3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          {{ loading ? 'Refreshing…' : 'Refresh' }}
        </button>
      </div>
    </div>

    <!-- Controls row -->
    <div class="flex flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3 rounded-lg border border-slate-800 bg-slate-900/50">
      <!-- Since (chip group) -->
      <div class="flex items-center gap-2">
        <label class="text-[11px] uppercase tracking-[0.12em] text-slate-500 font-semibold">Since</label>
        <div class="flex items-center rounded-md ring-1 ring-inset ring-slate-800 bg-slate-950/60 p-0.5">
          <button v-for="o in SINCE_OPTIONS" :key="o.days"
            @click="setSinceDays(o.days)"
            :class="`px-2.5 py-1 text-[12px] rounded font-medium tabular-nums transition-colors ${
              sinceDays === o.days
                ? 'bg-indigo-500/25 text-indigo-200 ring-1 ring-inset ring-indigo-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`"
          >{{ o.label }}</button>
        </div>
      </div>

      <!-- Top stepper -->
      <div class="flex items-center gap-2">
        <label class="text-[11px] uppercase tracking-[0.12em] text-slate-500 font-semibold">Top per section</label>
        <div class="flex items-center rounded-md ring-1 ring-inset ring-slate-800 bg-slate-950/60">
          <button @click="decTop" class="w-7 h-7 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-l">−</button>
          <span class="px-2 text-[12px] tabular-nums text-slate-200 min-w-[2.5rem] text-center">{{ top }}</span>
          <button @click="incTop" class="w-7 h-7 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-r">+</button>
        </div>
      </div>

      <!-- Stale after stepper -->
      <div class="flex items-center gap-2">
        <label class="text-[11px] uppercase tracking-[0.12em] text-slate-500 font-semibold">Stale after</label>
        <div class="flex items-center rounded-md ring-1 ring-inset ring-slate-800 bg-slate-950/60">
          <button @click="decStale" class="w-7 h-7 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-l">−</button>
          <span class="px-2 text-[12px] tabular-nums text-slate-200 min-w-[2.5rem] text-center">{{ staleDays }}d</span>
          <button @click="incStale" class="w-7 h-7 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-r">+</button>
        </div>
      </div>

      <!-- Coverage shortcut -->
      <div class="ml-auto text-[11px] text-slate-500">
        <span class="hidden sm:inline">URL: </span>
        <code class="font-mono text-slate-400">GET /api/digest/?since={{ since }}&amp;top={{ top }}&amp;stale_days={{ staleDays }}</code>
      </div>
    </div>

    <!-- Coverage bar -->
    <div class="flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-6 px-4 py-3 rounded-lg border border-slate-800 bg-slate-900/30">
      <div class="flex-1 min-w-0">
        <div class="flex items-baseline justify-between mb-1.5">
          <span class="text-[11px] uppercase tracking-[0.14em] text-slate-500 font-semibold">Coverage</span>
          <span class="text-[11px] text-slate-500 tabular-nums">{{ report.total_projects }} projects analyzed</span>
        </div>
        <div class="h-1.5 w-full flex rounded-full overflow-hidden bg-slate-800/80">
          <div v-for="s in coverageSegs" :key="s.key"
               :class="s.bar"
               :style="`width: ${s.pct}%`"
               :title="`${s.label}: ${s.n}`"/>
        </div>
      </div>
      <div class="grid grid-cols-3 gap-x-5 sm:flex sm:items-center sm:gap-5 shrink-0">
        <div v-for="s in coverageSegs" :key="s.key" class="flex items-center gap-2">
          <span :class="`w-1.5 h-3 rounded-sm ${s.dot}`" aria-hidden="true"/>
          <div class="flex flex-col leading-tight">
            <span class="text-[15px] font-semibold tabular-nums text-slate-100">{{ s.n }}</span>
            <span class="text-[10.5px] uppercase tracking-[0.08em] text-slate-500">{{ s.label }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
