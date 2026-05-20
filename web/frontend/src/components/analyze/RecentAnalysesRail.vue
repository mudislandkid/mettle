<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listAnalyses } from '@/api/analysis'
import { fmtNum, fmtRelative, fmtDuration } from '@/lib/format'
import { TONE, healthBucket } from '@/lib/tone'
import type { AnalysisListItem } from '@/types'

// The /api/analysis/ list endpoint returns AnalysisListItem but Task 8
// enriched it with avg_health + secrets_found + duration_seconds.
// We extend locally to pick up those fields without modifying the shared type.
interface EnrichedListItem extends AnalysisListItem {
  avg_health?: number | null
  secrets_found?: number
  duration_seconds?: number | null
}

const emit = defineEmits<{
  (e: 'open', analysis: EnrichedListItem): void
}>()

const analyses = ref<EnrichedListItem[]>([])

onMounted(async () => {
  try {
    const raw = await listAnalyses(4)
    analyses.value = raw as EnrichedListItem[]
  } catch {
    // Silently skip — rail is best-effort
  }
})
</script>

<template>
  <section v-if="analyses.length > 0">
    <div class="flex items-end justify-between mb-3">
      <div>
        <h2 class="text-[15px] font-semibold text-slate-100">Recent analyses</h2>
        <p class="text-[12px] text-slate-500">Reopen a prior run instead of starting over.</p>
      </div>
      <a href="#" @click.prevent class="text-[12px] text-indigo-300 hover:text-indigo-200">
        View all →
      </a>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
      <button
        v-for="a in analyses"
        :key="a.id"
        @click="emit('open', a)"
        class="text-left rounded-lg ring-1 ring-inset ring-slate-800 bg-slate-900/40 hover:bg-slate-900 hover:ring-slate-700 p-4 transition-colors"
      >
        <div class="flex items-baseline gap-2 mb-1">
          <span class="font-mono text-[12px] text-slate-300 truncate flex-1">{{ a.directory_path }}</span>
          <span class="shrink-0 text-[10px] text-slate-500">{{ fmtRelative(a.analyzed_at) }}</span>
        </div>
        <div class="grid grid-cols-3 gap-1 mt-3">
          <div>
            <div class="text-[15px] font-semibold tabular-nums text-slate-100">{{ a.total_projects }}</div>
            <div class="text-[9.5px] uppercase tracking-[0.12em] text-slate-500">Projects</div>
          </div>
          <div>
            <div class="text-[15px] font-semibold tabular-nums text-slate-100">{{ fmtNum(a.total_files) }}</div>
            <div class="text-[9.5px] uppercase tracking-[0.12em] text-slate-500">Files</div>
          </div>
          <div>
            <div class="text-[15px] font-semibold tabular-nums text-slate-100">{{ fmtNum(a.total_lines) }}</div>
            <div class="text-[9.5px] uppercase tracking-[0.12em] text-slate-500">Lines</div>
          </div>
        </div>
        <div class="mt-3 flex items-center gap-3 text-[11px] tabular-nums">
          <span class="flex items-center gap-1">
            <span :class="['w-1.5 h-1.5 rounded-full', TONE[healthBucket(a.avg_health).tone].bar]"/>
            <span class="text-slate-300">{{ a.avg_health ?? '—' }}</span>
            <span class="text-slate-500">avg health</span>
          </span>
          <span v-if="a.secrets_found && a.secrets_found > 0" class="ml-auto text-rose-300 flex items-center gap-1">
            <svg width="11" height="11" viewBox="0 0 20 20" fill="none">
              <path d="M10 2l8 14H2L10 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
              <path d="M10 8v3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              <circle cx="10" cy="13.5" r=".75" fill="currentColor"/>
            </svg>
            {{ a.secrets_found }} secret{{ a.secrets_found > 1 ? 's' : '' }}
          </span>
          <span :class="a.secrets_found && a.secrets_found > 0 ? '' : 'ml-auto'">
            <span class="text-slate-500">in</span>
            <span class="text-slate-300"> {{ fmtDuration(a.duration_seconds) }}</span>
          </span>
        </div>
      </button>
    </div>
  </section>
</template>
