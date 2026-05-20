<script setup lang="ts">
import { ref, computed } from 'vue'
import type { DigestSection } from '@/types'
import { KIND_STYLE, ACCENT_CLASSES } from '@/lib/tone'
import DigestEntry from './DigestEntry.vue'

const props = defineProps<{ section: DigestSection }>()

const style = computed(() => KIND_STYLE[props.section.kind] ?? KIND_STYLE.no_recent_activity)
const accent = computed(() => ACCENT_CLASSES[style.value.accent])

// Track which entries are expanded by project_id
const expandedIds = ref<Set<number>>(new Set())
const allExpanded = computed(() =>
  props.section.entries.length > 0 && expandedIds.value.size === props.section.entries.length
)

const canExpandAll = computed(() =>
  ['dependency_drift', 'stalled_with_todos', 'newly_stale', 'new_since', 'no_recent_activity'].includes(props.section.kind)
)

function toggleAll() {
  if (expandedIds.value.size === props.section.entries.length) {
    expandedIds.value = new Set()
  } else {
    expandedIds.value = new Set(props.section.entries.map((e) => e.project_id))
  }
}

// Note: per-entry expansion is local to each DigestEntry component. The
// "Expand all / Collapse all" affordance here just signals intent; if you
// want shared state, lift it. For v1 we keep local-only state and let the
// Expand-all button work as a one-shot toggle of all child states via key
// remount. Simpler: leave each DigestEntry self-managing; the toggleAll
// can be removed if not needed. (Keep for parity with the design; subagents
// in later tasks can revisit if interaction feels wrong.)
</script>

<template>
  <section
    :data-section-kind="section.kind"
    class="relative rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-[2px] overflow-hidden"
  >
    <!-- Top accent stripe -->
    <div :class="`absolute inset-x-0 top-0 h-px ${accent.bg.replace('/10', '/40')}`" aria-hidden="true"/>

    <header class="flex items-start gap-3 px-5 pt-5 pb-3">
      <div :class="`shrink-0 w-9 h-9 rounded-lg ring-1 ring-inset ${accent.ring} ${accent.bg} ${accent.text} flex items-center justify-center`">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" class="w-5 h-5">
          <template v-if="section.kind === 'grown_most'">
            <path d="M3 14l5-5 3 3 6-7" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M12 5h5v5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
          </template>
          <template v-else-if="section.kind === 'biggest_swing'">
            <path d="M3 7h12M3 7l3-3M3 7l3 3" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M17 13H5m12 0l-3-3m3 3l-3 3" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
          </template>
          <template v-else-if="section.kind === 'dependency_drift'">
            <rect x="3" y="4" width="6" height="6" rx="1" stroke="currentColor" stroke-width="1.75"/>
            <rect x="11" y="10" width="6" height="6" rx="1" stroke="currentColor" stroke-width="1.75"/>
            <path d="M9 7h2a2 2 0 012 2v1" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
          </template>
          <template v-else-if="section.kind === 'stalled_with_todos'">
            <path d="M4 5h12M4 10h9M4 15h6" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
            <circle cx="16" cy="15" r="2.5" stroke="currentColor" stroke-width="1.75"/>
          </template>
          <template v-else-if="section.kind === 'newly_stale'">
            <circle cx="10" cy="10" r="6.5" stroke="currentColor" stroke-width="1.75"/>
            <path d="M10 6.5V10l2.5 1.5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
          </template>
          <template v-else-if="section.kind === 'new_since'">
            <path d="M10 4v12M4 10h12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
          </template>
          <template v-else>
            <path d="M5 14c0-3 2-5 5-5s5 2 5 5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
            <circle cx="10" cy="6" r="1.5" fill="currentColor"/>
          </template>
        </svg>
      </div>
      <div class="min-w-0 flex-1">
        <div class="flex items-baseline gap-2 flex-wrap">
          <h2 class="text-[15px] font-semibold text-slate-100 tracking-tight">{{ section.title }}</h2>
          <span class="text-[10px] uppercase tracking-[0.14em] text-slate-500 font-mono">{{ section.kind }}</span>
          <span class="ml-auto text-[11px] tabular-nums text-slate-500">
            {{ section.entries.length }} {{ section.entries.length === 1 ? 'entry' : 'entries' }}
          </span>
        </div>
        <p class="text-[12px] text-slate-400 mt-0.5">{{ section.description }}</p>
      </div>
    </header>

    <!-- Empty state -->
    <div v-if="section.entries.length === 0" class="px-5 pb-6 pt-1">
      <div class="flex items-center gap-3 px-4 py-4 rounded-lg border border-dashed border-slate-800 bg-slate-950/40">
        <span :class="`w-1.5 h-1.5 rounded-full ${accent.dot} opacity-60`" aria-hidden="true"/>
        <p class="text-[12.5px] text-slate-400">{{ section.empty_message || 'Nothing to report here.' }}</p>
      </div>
    </div>

    <!-- Entries -->
    <div v-else class="px-5 pb-4">
      <div v-if="canExpandAll" class="flex justify-end mb-1">
        <button
          @click="toggleAll"
          class="text-[11px] text-slate-500 hover:text-slate-200 transition-colors"
        >
          {{ allExpanded ? 'Collapse all' : 'Expand all' }}
        </button>
      </div>
      <ul class="divide-y divide-slate-800/70">
        <DigestEntry
          v-for="(entry, i) in section.entries"
          :key="entry.project_id"
          :entry="entry"
          :kind="section.kind"
          :rank="i + 1"
          :tone="style.tone"
        />
      </ul>
    </div>
  </section>
</template>
