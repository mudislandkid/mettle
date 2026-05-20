<script setup lang="ts">
import { computed } from 'vue'
import { fmtNum, fmtRelative } from '@/lib/format'
import type { Analysis } from '@/types'
import ActivityHeatmap from './ActivityHeatmap.vue'

const props = defineProps<{
  analyses: Analysis[]
}>()

const stats = computed(() => {
  const completed = props.analyses.filter((a) => a.status === 'completed')
  const directories = new Set(props.analyses.map((a) => a.directory_path)).size
  // analyses are returned newest-first from the API
  const latest = completed[0] ?? null
  const totalLines = completed.reduce((acc, a) => acc + (a.total_lines ?? 0), 0)
  return { runs: completed.length, directories, latest, totalLines }
})

// Shorten home prefix — e.g. /Users/greg/code → ~/code
function shortenPath(p: string): string {
  return p.replace(/^\/Users\/[^/]+/, '~')
}
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-[1fr_auto] gap-6 items-start">

    <!-- Left: title + counter tiles -->
    <div>
      <!-- Badge + subtitle -->
      <div class="flex items-center gap-2 mb-1">
        <span class="px-2 py-0.5 rounded text-[10px] font-semibold tracking-[0.18em] uppercase
                     bg-indigo-500/15 text-indigo-300 ring-1 ring-inset ring-indigo-500/20">
          History
        </span>
        <span class="text-[11px] text-slate-500 font-mono">
          all completed runs feed the Digest
        </span>
      </div>

      <!-- Headline -->
      <h1 class="text-[28px] sm:text-[32px] font-semibold tracking-tight text-slate-100 leading-tight">
        Every run, every snapshot
      </h1>
      <p class="text-[13px] text-slate-400 mt-1.5 max-w-xl">
        Each analysis is preserved so you can compare snapshots over time. Re-running keeps
        history; deleting an analysis removes it permanently.
      </p>

      <!-- Counter tiles -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-4 mt-5 max-w-2xl">

        <!-- Total runs -->
        <div>
          <div class="text-[24px] font-semibold tabular-nums leading-none text-slate-100">
            {{ stats.runs }}
          </div>
          <div class="text-[10.5px] uppercase tracking-[0.14em] text-slate-500 mt-1.5">Total runs</div>
        </div>

        <!-- Directories -->
        <div>
          <div class="text-[24px] font-semibold tabular-nums leading-none text-slate-100">
            {{ stats.directories }}
          </div>
          <div class="text-[10.5px] uppercase tracking-[0.14em] text-slate-500 mt-1.5">Directories</div>
        </div>

        <!-- Lines counted -->
        <div>
          <div class="text-[24px] font-semibold tabular-nums leading-none text-slate-100">
            {{ fmtNum(stats.totalLines) }}
          </div>
          <div class="text-[10.5px] uppercase tracking-[0.14em] text-slate-500 mt-1.5">Lines counted</div>
        </div>

        <!-- Latest run -->
        <div>
          <div class="text-[24px] font-semibold tabular-nums leading-none text-slate-100">
            {{ stats.latest ? fmtRelative(stats.latest.analyzed_at) : '—' }}
          </div>
          <div class="text-[10.5px] uppercase tracking-[0.14em] text-slate-500 mt-1.5">Latest run</div>
          <div
            v-if="stats.latest"
            class="text-[11px] font-mono text-slate-500 mt-0.5 truncate"
            :title="stats.latest.directory_path"
          >
            {{ shortenPath(stats.latest.directory_path) }}
          </div>
        </div>

      </div>
    </div>

    <!-- Right: 8-week activity heatmap -->
    <div class="lg:min-w-[420px]">
      <ActivityHeatmap :analyses="analyses" />
    </div>

  </div>
</template>
