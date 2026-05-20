<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import PathInput from './PathInput.vue'
import RecentPathChips from './RecentPathChips.vue'
import AdvancedFiltersDisclosure from './AdvancedFiltersDisclosure.vue'
import RecentAnalysesRail from './RecentAnalysesRail.vue'
import { getRecentPaths } from '@/api/analysis'
import type { AnalysisFilters, RecentPath } from '@/types'

const emit = defineEmits<{
  (e: 'start', payload: { directory_path: string; filters: AnalysisFilters }): void
  (e: 'open-analysis', id: number): void
}>()

const directoryPath = ref('')
const recentPaths = ref<RecentPath[]>([])
const filters = ref<AnalysisFilters>({
  github_user: null,
  skip_public_sdks: true,
  max_files: 0,
  include_internal: false,
})

const canStart = computed(() => directoryPath.value.trim().length > 0)

onMounted(async () => {
  try {
    recentPaths.value = await getRecentPaths()
  } catch {
    // Non-fatal — proceed without recent paths
  }
})

function handleStart() {
  if (!canStart.value) return
  emit('start', {
    directory_path: directoryPath.value.trim(),
    filters: filters.value,
  })
}

const BULLETS = [
  'All completed analyses feed the Digest view',
  'Re-running keeps history — compare snapshots over time',
  'Read-only · runs locally · zero telemetry',
]
</script>

<template>
  <div class="space-y-10">
    <!-- Hero + Form grid -->
    <div class="grid grid-cols-1 lg:grid-cols-[1.1fr_1fr] gap-8 items-start">
      <!-- Left: hero pitch -->
      <div class="pt-2">
        <div class="flex items-center gap-2 mb-3">
          <span class="px-2 py-0.5 rounded text-[10px] font-semibold tracking-[0.18em] uppercase bg-indigo-500/15 text-indigo-300 ring-1 ring-inset ring-indigo-500/20">
            Analyze
          </span>
          <span class="text-[11px] text-slate-500 font-mono">point at a directory</span>
        </div>
        <h1 class="text-[34px] sm:text-[40px] font-semibold tracking-tight text-slate-100 leading-[1.05]">
          See what's actually<br/>
          <span class="text-slate-500">going on in your code.</span>
        </h1>
        <p class="text-[14px] text-slate-400 mt-3 max-w-md leading-relaxed">
          Mettle scans every project under one path: counting lines, mapping languages,
          finding TODOs, sniffing out secrets, and grading health. No agents, no upload — it
          reads from your filesystem and your git history.
        </p>

        <ul class="mt-6 space-y-2 text-[13px] text-slate-300">
          <li
            v-for="bullet in BULLETS"
            :key="bullet"
            class="flex items-start gap-2.5"
          >
            <svg width="14" height="14" viewBox="0 0 20 20" fill="none" class="mt-1 text-emerald-400 shrink-0">
              <path d="M4 11l4 4 8-10" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>{{ bullet }}</span>
          </li>
        </ul>
      </div>

      <!-- Right: form card -->
      <div class="rounded-2xl ring-1 ring-slate-800 bg-slate-900/70 backdrop-blur-[2px] p-5 sm:p-6 shadow-[0_10px_60px_-20px_rgba(99,102,241,0.25)]">
        <div class="space-y-4">
          <PathInput
            v-model="directoryPath"
            :recent-paths="recentPaths"
            :disabled="false"
          />

          <RecentPathChips
            :recent-paths="recentPaths"
            :active-path="directoryPath"
            @select="directoryPath = $event"
          />

          <AdvancedFiltersDisclosure
            v-model="filters"
            :disabled="false"
          />

          <button
            type="button"
            @click="handleStart"
            :disabled="!canStart"
            class="w-full mt-1 px-4 py-3 rounded-lg bg-indigo-500 hover:bg-indigo-400 text-slate-950 font-semibold text-[14px] flex items-center justify-center gap-2 disabled:bg-slate-800 disabled:text-slate-600 disabled:cursor-not-allowed transition-colors shadow-[0_8px_30px_-10px_rgba(99,102,241,0.6)]"
          >
            <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
              <path d="M5 4l11 6-11 6V4z" fill="currentColor"/>
            </svg>
            Start analysis
          </button>
          <p class="text-[11px] text-slate-500 text-center">
            Tip: a 50-project run takes about 30–60s.
          </p>
        </div>
      </div>
    </div>

    <!-- Recent analyses rail -->
    <RecentAnalysesRail @open="emit('open-analysis', $event.id)" />
  </div>
</template>
