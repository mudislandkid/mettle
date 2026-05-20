<script setup lang="ts">
import { computed } from 'vue'
import type { AnalysisListItem } from '@/types'

const props = defineProps<{
  analyses: AnalysisListItem[]
}>()

// Build 56-day (8-week) buckets — last 56 days including today
const buckets = computed(() => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const days = 56

  const raw = Array.from({ length: days }, (_, i) => {
    const d = new Date(today)
    d.setDate(today.getDate() - (days - 1 - i))
    return { date: d, count: 0, latest: null as AnalysisListItem | null }
  })

  for (const a of props.analyses) {
    const d = new Date(a.analyzed_at)
    d.setHours(0, 0, 0, 0)
    const diff = Math.floor((today.getTime() - d.getTime()) / 86_400_000)
    if (diff >= 0 && diff < days) {
      const b = raw[days - 1 - diff]
      b.count++
      if (!b.latest) b.latest = a
    }
  }

  return raw
})

const maxCount = computed(() => Math.max(1, ...buckets.value.map((b) => b.count)))
const totalRuns = computed(() => props.analyses.length)

// Intensity 0-3 → pre-built Tailwind classes (full strings so JIT picks them up)
const CELL_BG = [
  'bg-slate-800/60',   // 0 = no runs
  'bg-indigo-500/30',  // 1 = low
  'bg-indigo-500/55',  // 2 = medium
  'bg-indigo-400',     // 3 = high
] as const

function cellBg(count: number): string {
  if (count === 0) return CELL_BG[0]
  const intensity = Math.min(3, Math.ceil((count / maxCount.value) * 3)) as 0 | 1 | 2 | 3
  return CELL_BG[intensity]
}

function cellTitle(bucket: { date: Date; count: number }): string {
  const label = bucket.date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  const runs = bucket.count
  return `${label} · ${runs} run${runs === 1 ? '' : 's'}`
}
</script>

<template>
  <div class="rounded-xl ring-1 ring-slate-800 bg-slate-900/40 p-4 sm:p-5">
    <!-- Header row -->
    <div class="flex items-baseline justify-between mb-3">
      <div>
        <div class="text-[11px] uppercase tracking-[0.14em] text-slate-500 font-semibold">Activity</div>
        <div class="text-[12px] text-slate-400">{{ totalRuns }} runs over the last 56 days</div>
      </div>
      <!-- Legend -->
      <div class="flex items-center gap-1.5 text-[10px] text-slate-500">
        <span>less</span>
        <span class="w-2.5 h-2.5 rounded-sm bg-slate-800/60" />
        <span class="w-2.5 h-2.5 rounded-sm bg-indigo-500/30" />
        <span class="w-2.5 h-2.5 rounded-sm bg-indigo-500/55" />
        <span class="w-2.5 h-2.5 rounded-sm bg-indigo-400" />
        <span>more</span>
      </div>
    </div>

    <!-- 7-row × 8-col grid (col-flow so days flow down each column = Mon-Sun columns) -->
    <div class="grid grid-flow-col grid-rows-7 gap-[3px] auto-cols-min">
      <div
        v-for="(b, i) in buckets"
        :key="i"
        class="w-3 h-3 rounded-sm hover:ring-1 hover:ring-indigo-300 transition-shadow"
        :class="cellBg(b.count)"
        :title="cellTitle(b)"
      />
    </div>
  </div>
</template>
