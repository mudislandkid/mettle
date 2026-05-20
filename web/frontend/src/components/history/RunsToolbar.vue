<script setup lang="ts">
// RunsToolbar.vue — search field + status segmented control with live counts.

defineProps<{
  search: string
  statusFilter: string
  counts: { all: number; completed: number; running: number; failed: number }
}>()

const emit = defineEmits<{
  'update:search': [value: string]
  'update:statusFilter': [value: string]
}>()

const TABS = ['all', 'completed', 'running', 'failed'] as const
type Tab = typeof TABS[number]

function tabCount(counts: { all: number; completed: number; running: number; failed: number }, tab: Tab): number {
  return counts[tab]
}
</script>

<template>
  <div class="rounded-lg ring-1 ring-slate-800 bg-slate-900/40 px-4 py-2.5 flex items-center gap-3 flex-wrap">
    <!-- Search -->
    <div class="relative flex-1 min-w-[200px]">
      <svg
        width="14" height="14" viewBox="0 0 20 20" fill="none"
        class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500"
      >
        <circle cx="9" cy="9" r="5" stroke="currentColor" stroke-width="1.75"/>
        <path d="M13 13l3 3" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
      </svg>
      <input
        :value="search"
        placeholder="Search by directory path…"
        class="w-full rounded-md ring-1 ring-inset ring-slate-700 bg-slate-950/60 pl-8 pr-3 py-1.5 text-[13px] text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-indigo-500/60"
        @input="emit('update:search', ($event.target as HTMLInputElement).value)"
      />
    </div>

    <!-- Status segmented control -->
    <div class="flex items-center rounded-md ring-1 ring-inset ring-slate-800 bg-slate-950/60 p-0.5">
      <button
        v-for="tab in TABS"
        :key="tab"
        class="px-2.5 py-1 text-[11px] rounded font-medium capitalize transition-colors flex items-center gap-1.5"
        :class="statusFilter === tab
          ? 'bg-indigo-500/25 text-indigo-200 ring-1 ring-inset ring-indigo-500/30'
          : 'text-slate-400 hover:text-slate-200'"
        @click="emit('update:statusFilter', tab)"
      >
        {{ tab }}
        <span
          class="text-[10px] tabular-nums px-1 rounded"
          :class="statusFilter === tab ? 'bg-slate-950/40' : 'bg-slate-800'"
        >
          {{ tabCount(counts, tab) }}
        </span>
      </button>
    </div>
  </div>
</template>
