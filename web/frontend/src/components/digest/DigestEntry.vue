<script setup lang="ts">
import { ref, computed } from 'vue'
import type { DigestEntry as DigestEntryType, DigestSectionKind } from '@/types'
import DependencyDriftExpansion from './DependencyDriftExpansion.vue'
import StaleEntryExpansion from './StaleEntryExpansion.vue'

const props = defineProps<{
  entry: DigestEntryType
  kind: DigestSectionKind
  rank: number
  tone: 'narrative' | 'coverage'
}>()

const expanded = ref(false)

const hasExpansion = computed(() =>
  ['dependency_drift', 'stalled_with_todos', 'newly_stale', 'new_since', 'no_recent_activity'].includes(props.kind)
)

const showDelta = computed(() =>
  props.entry.baseline_value !== null && props.entry.current_value !== null,
)

const headlineColor = computed(() => {
  const v = props.entry.headline_value
  if (props.kind === 'grown_most') return 'text-emerald-300'
  if (props.kind === 'biggest_swing') {
    return v > 0 ? 'text-emerald-300' : v < 0 ? 'text-rose-300' : 'text-slate-200'
  }
  if (props.kind === 'dependency_drift') return 'text-amber-200'
  if (props.kind === 'stalled_with_todos') return 'text-orange-200'
  if (props.kind === 'newly_stale') return 'text-rose-200'
  if (props.kind === 'new_since') return 'text-sky-200'
  return 'text-slate-200'
})

const rankStr = computed(() => String(props.rank).padStart(2, '0'))

function toggle() {
  expanded.value = !expanded.value
}
</script>

<template>
  <li :class="`group/entry relative ${tone === 'coverage' ? 'py-2' : 'py-3'}`">
    <div class="flex items-baseline gap-3">
      <!-- Rank -->
      <span class="w-5 shrink-0 text-[11px] tabular-nums text-slate-600 text-right select-none">
        {{ rankStr }}
      </span>

      <!-- Name + path -->
      <div class="min-w-0 flex-1">
        <div class="flex items-baseline gap-2 flex-wrap">
          <a :href="`/projects/${entry.project_id}`"
             @click.prevent
             class="text-[14px] font-semibold text-slate-100 hover:text-indigo-300 truncate">
            {{ entry.project_name }}
          </a>
          <a v-if="entry.repo_url"
             :href="entry.repo_url"
             :title="entry.repo_url"
             target="_blank" rel="noreferrer"
             @click.stop
             class="text-slate-500 hover:text-slate-300">
            <svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38v-1.35c-2.22.48-2.69-1.07-2.69-1.07-.36-.92-.89-1.16-.89-1.16-.73-.5.06-.49.06-.49.8.06 1.23.83 1.23.83.72 1.23 1.88.88 2.34.67.07-.52.28-.88.51-1.08-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.83-2.15-.08-.2-.36-1.02.08-2.13 0 0 .67-.21 2.2.82a7.66 7.66 0 014 0c1.53-1.03 2.2-.82 2.2-.82.44 1.11.16 1.93.08 2.13.52.56.83 1.28.83 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.55.74.55 1.5v2.22c0 .21.15.46.55.38C13.71 14.53 16 11.54 16 8c0-4.42-3.58-8-8-8z"/>
            </svg>
          </a>
        </div>
        <div v-if="tone !== 'coverage'"
             :title="entry.project_path"
             class="text-[11px] text-slate-500 font-mono truncate">
          {{ entry.project_path }}
        </div>
      </div>

      <!-- Headline metric -->
      <div class="text-right shrink-0">
        <div :class="`text-[15px] font-semibold tabular-nums ${headlineColor}`">
          {{ entry.headline_label }}
        </div>
        <div v-if="showDelta" class="text-[11px] text-slate-500 tabular-nums">
          {{ entry.baseline_value!.toLocaleString() }}
          <span class="text-slate-600">→</span>
          {{ entry.current_value!.toLocaleString() }}
        </div>
      </div>

      <!-- Expand affordance -->
      <button v-if="hasExpansion"
              @click="toggle"
              :class="`shrink-0 ml-1 w-7 h-7 -mr-1 rounded-md flex items-center justify-center text-slate-500 hover:text-slate-200 hover:bg-slate-800 transition-colors ${expanded ? 'bg-slate-800 text-slate-200' : ''}`"
              :aria-label="expanded ? 'Collapse details' : 'Expand details'">
        <svg width="14" height="14" viewBox="0 0 20 20" fill="none"
             :class="`transition-transform ${expanded ? 'rotate-180' : ''}`">
          <path d="M5 8l5 5 5-5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>

    <!-- Expansion area -->
    <DependencyDriftExpansion v-if="expanded && kind === 'dependency_drift'" :extra="entry.extra as any"/>
    <StaleEntryExpansion v-if="expanded && kind !== 'dependency_drift' && hasExpansion"
                          :extra="entry.extra as any" :kind="kind"/>
  </li>
</template>
