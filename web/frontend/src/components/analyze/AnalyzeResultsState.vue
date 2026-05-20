<script setup lang="ts">
import { fmtCalendar, fmtDuration } from '@/lib/format'
import type { Analysis } from '@/types'
import SummaryHero from './SummaryHero.vue'
import ProjectTable from './ProjectTable.vue'

const props = defineProps<{
  analysis: Analysis
}>()

const emit = defineEmits<{
  (e: 'restart'): void
}>()

// Export URL helper: /api/export/{format}/{id}
function exportUrl(format: 'markdown' | 'json' | 'csv'): string {
  return `/api/export/${format}/${props.analysis.id}`
}

const exportItems: Array<{ label: string; format: 'markdown' | 'json' | 'csv' }> = [
  { label: 'Markdown', format: 'markdown' },
  { label: 'JSON',     format: 'json'     },
  { label: 'CSV',      format: 'csv'      },
]
</script>

<template>
  <div class="space-y-6">

    <!-- Header strip -->
    <div class="flex flex-wrap items-end justify-between gap-3">
      <!-- Left: path + meta -->
      <div class="min-w-0">
        <div class="flex items-center gap-2 mb-1">
          <span class="px-2 py-0.5 rounded text-[10px] font-semibold tracking-[0.18em] uppercase bg-emerald-500/15 text-emerald-300 ring-1 ring-inset ring-emerald-500/20">
            Complete
          </span>
          <span class="text-[11px] text-slate-500">Analysis #{{ analysis.id }}</span>
        </div>
        <h1 class="text-[24px] sm:text-[28px] font-semibold tracking-tight text-slate-100 truncate font-mono">
          {{ analysis.directory_path }}
        </h1>
        <p class="text-[12.5px] text-slate-400 mt-1">
          Finished {{ fmtCalendar(analysis.analyzed_at) }}
          <template v-if="analysis.duration_seconds != null">
            · ran in <span class="text-slate-200">{{ fmtDuration(analysis.duration_seconds) }}</span>
          </template>
        </p>
      </div>

      <!-- Right: export buttons + new analysis -->
      <div class="flex items-center gap-2">
        <!-- Segmented export button group -->
        <div class="inline-flex rounded-md ring-1 ring-inset ring-slate-800 bg-slate-900 overflow-hidden">
          <a
            v-for="(item, i) in exportItems"
            :key="item.format"
            :href="exportUrl(item.format)"
            target="_blank"
            rel="noopener noreferrer"
            class="px-3 py-1.5 text-[12px] text-slate-300 hover:text-slate-100 hover:bg-slate-800 transition-colors"
            :class="i > 0 ? 'border-l border-slate-800' : ''"
          >{{ item.label }}</a>
        </div>

        <!-- New analysis -->
        <button
          class="px-3 py-1.5 text-[12px] rounded-md bg-indigo-500/20 text-indigo-200 ring-1 ring-inset ring-indigo-500/30 hover:bg-indigo-500/30 transition-colors flex items-center gap-1.5"
          @click="emit('restart')"
        >
          <svg width="13" height="13" viewBox="0 0 20 20" fill="none">
            <path d="M10 4v12M4 10h12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
          </svg>
          New analysis
        </button>
      </div>
    </div>

    <!-- Summary hero -->
    <SummaryHero :analysis="analysis" />

    <!-- Project table -->
    <ProjectTable :projects="analysis.projects" />

  </div>
</template>
