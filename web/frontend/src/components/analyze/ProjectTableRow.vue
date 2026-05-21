<script setup lang="ts">
import { fmtRelative, fmtCalendar } from '@/lib/format'
import type { Project } from '@/types'
import LangPills from './LangPills.vue'
import HealthBar from './HealthBar.vue'
import VolumeMiniBar from './VolumeMiniBar.vue'
import RiskBadges from './RiskBadges.vue'

const props = defineProps<{
  project: Project
  maxLines: number
  selected: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle-select'): void
  (e: 'open', event: MouseEvent): void
}>()

function activityDate(iso: string | null | undefined): string {
  if (!iso) return ''
  return fmtCalendar(iso).split(',')[0]
}
</script>

<template>
  <tr
    class="border-t border-slate-800/70 group transition-colors cursor-pointer"
    :class="selected ? 'bg-indigo-500/10' : 'hover:bg-slate-800/40'"
    @click="(e: MouseEvent) => emit('open', e)"
  >
    <!-- Checkbox -->
    <td class="px-4 py-3 align-middle" @click.stop="emit('toggle-select')">
      <input
        type="checkbox"
        :checked="selected"
        class="rounded bg-slate-900 text-indigo-500 border-slate-700 focus:ring-indigo-500"
        :aria-label="`Select ${project.name}`"
        @change="emit('toggle-select')"
      />
    </td>

    <!-- Project name + path + langs -->
    <td class="px-3 py-3 align-middle min-w-[260px]">
      <div class="flex items-center gap-2">
        <span
          class="text-[14px] font-semibold text-slate-100 group-hover:text-indigo-200 truncate"
        >{{ project.name }}</span>
        <span
          v-if="project.flags?.includes('archived')"
          class="text-[9.5px] uppercase tracking-[0.12em] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 ring-1 ring-inset ring-slate-700"
        >Archived</span>
      </div>
      <div class="flex items-center gap-2 mt-1 flex-wrap">
        <div
          class="text-[11px] text-slate-500 font-mono truncate max-w-[260px]"
          :title="project.path"
        >{{ project.path }}</div>
        <LangPills :languages="project.languages" :max="3" />
      </div>
    </td>

    <!-- Health -->
    <td class="px-3 py-3 align-middle">
      <HealthBar :score="project.health_score" />
    </td>

    <!-- Volume -->
    <td class="px-3 py-3 align-middle">
      <VolumeMiniBar :project="project" :max-lines="maxLines" />
    </td>

    <!-- Activity -->
    <td class="px-3 py-3 align-middle">
      <div class="text-[12.5px] text-slate-200">{{ fmtRelative(project.last_commit_at) }}</div>
      <div class="text-[10px] text-slate-500">{{ activityDate(project.last_commit_at) }}</div>
    </td>

    <!-- Risk -->
    <td class="px-3 py-3 align-middle">
      <RiskBadges :project="project" />
    </td>

    <!-- License -->
    <td class="px-3 py-3 align-middle">
      <span v-if="!project.license_spdx" class="text-[11px] text-slate-600">—</span>
      <span
        v-else
        class="inline-flex items-center px-1.5 py-0.5 rounded text-[10.5px] font-mono text-slate-300 bg-slate-800/70 ring-1 ring-inset ring-slate-700"
      >{{ project.license_spdx }}</span>
    </td>

    <!-- Chevron -->
    <td class="px-3 py-3 align-middle text-right">
      <svg width="14" height="14" viewBox="0 0 20 20" fill="none"
        class="text-slate-700 group-hover:text-indigo-300 transition-colors">
        <path d="M7 5l5 5-5 5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </td>
  </tr>
</template>
