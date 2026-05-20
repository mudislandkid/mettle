<script setup lang="ts">
import { computed } from 'vue'
import { TONE } from '@/lib/tone'
import type { Project } from '@/types'

const props = defineProps<{
  project: Project
}>()

const todoTone = computed(() =>
  (props.project.todos ?? 0) > 40 ? 'amber' : 'slate'
)

const hasTodos   = computed(() => (props.project.todos ?? 0) > 0)
const hasSecrets = computed(() => (props.project.secrets_found ?? 0) > 0)
const noLicense  = computed(() => !props.project.license_spdx)
const isEmpty    = computed(() => !hasTodos.value && !hasSecrets.value && !noLicense.value)
</script>

<template>
  <span v-if="isEmpty" class="text-[11px] text-slate-600">—</span>
  <div v-else class="flex flex-wrap gap-1">
    <!-- TODOs badge -->
    <span
      v-if="hasTodos"
      class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded ring-1 ring-inset"
      :class="[TONE[todoTone].bg, TONE[todoTone].text, TONE[todoTone].ring]"
      :title="`${project.todos} TODOs`"
    >
      <svg width="10" height="10" viewBox="0 0 16 16" fill="none">
        <path d="M3 4h10M3 8h10M3 12h7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      <span class="tabular-nums text-[10.5px]">{{ project.todos }}</span>
    </span>

    <!-- Secrets badge -->
    <span
      v-if="hasSecrets"
      class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded ring-1 ring-inset"
      :class="[TONE.rose.bg, TONE.rose.text, TONE.rose.ring]"
      :title="`${project.secrets_found} suspected secret${project.secrets_found > 1 ? 's' : ''}`"
    >
      <svg width="10" height="10" viewBox="0 0 16 16" fill="none">
        <path d="M8 2l6 11H2L8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
        <circle cx="8" cy="11" r=".75" fill="currentColor"/>
      </svg>
      <span class="tabular-nums text-[10.5px]">{{ project.secrets_found }}</span>
    </span>

    <!-- No license badge -->
    <span
      v-if="noLicense"
      class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded ring-1 ring-inset"
      :class="[TONE.indigo.bg, TONE.indigo.text, TONE.indigo.ring]"
      title="No SPDX license detected"
    >
      <svg width="10" height="10" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/>
        <path d="M5 8h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      <span class="text-[10px]">no license</span>
    </span>
  </div>
</template>
