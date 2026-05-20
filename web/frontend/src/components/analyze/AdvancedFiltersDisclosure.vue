<script setup lang="ts">
import { ref, computed } from 'vue'
import type { AnalysisFilters } from '@/types'

const props = defineProps<{
  modelValue: AnalysisFilters
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: AnalysisFilters): void
}>()

const open = ref(false)

const activeCount = computed(() => {
  const f = props.modelValue
  return (
    (f.github_user ? 1 : 0) +
    (f.include_internal ? 1 : 0) +
    (!f.skip_public_sdks ? 1 : 0) +
    (f.max_files > 0 ? 1 : 0)
  )
})

function patch(key: keyof AnalysisFilters, value: unknown) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}

function maxFilesLabel(v: number): string {
  return v === 0 ? 'Unlimited' : v.toLocaleString()
}
</script>

<template>
  <div class="rounded-lg ring-1 ring-inset ring-slate-800 bg-slate-900/40 overflow-hidden">
    <button
      type="button"
      @click="open = !open"
      class="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-slate-900/60"
    >
      <span class="flex items-center gap-2">
        <svg
          width="14"
          height="14"
          viewBox="0 0 20 20"
          fill="none"
          :class="['text-slate-500 transition-transform', open ? 'rotate-90' : '']"
        >
          <path d="M7 5l5 5-5 5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span class="text-[12px] font-semibold tracking-wide text-slate-300">Advanced filters</span>
        <span
          v-if="activeCount > 0"
          class="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 ring-1 ring-inset ring-indigo-500/30"
        >
          {{ activeCount }} active
        </span>
      </span>
      <span class="text-[11px] text-slate-500">
        {{ open ? '' : 'GitHub user · SDKs · internal dirs · max files' }}
      </span>
    </button>

    <div v-if="open" class="px-4 pb-4 pt-1 grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- GitHub user -->
      <label class="block">
        <span class="block text-[11px] uppercase tracking-[0.14em] text-slate-500 font-semibold mb-1.5">
          GitHub user
        </span>
        <input
          type="text"
          :value="modelValue.github_user || ''"
          @input="patch('github_user', ($event.target as HTMLInputElement).value || null)"
          :disabled="disabled"
          placeholder="Filter by repo owner"
          class="w-full rounded-md ring-1 ring-inset ring-slate-700 bg-slate-950/60 px-3 py-2 text-[13px] text-slate-100 placeholder:text-slate-600 font-mono focus:outline-none focus:ring-indigo-500/60"
        />
      </label>

      <!-- Max files -->
      <label class="block">
        <span class="flex items-baseline justify-between text-[11px] uppercase tracking-[0.14em] text-slate-500 font-semibold mb-1.5">
          <span>Max files per project</span>
          <span class="text-slate-400 tabular-nums normal-case tracking-normal">
            {{ maxFilesLabel(modelValue.max_files) }}
          </span>
        </span>
        <input
          type="range"
          :value="modelValue.max_files"
          @input="patch('max_files', Number(($event.target as HTMLInputElement).value))"
          :disabled="disabled"
          min="0"
          max="50000"
          step="1000"
          class="w-full accent-indigo-500"
        />
      </label>

      <!-- Skip public SDKs toggle -->
      <button
        type="button"
        @click="patch('skip_public_sdks', !modelValue.skip_public_sdks)"
        class="flex items-start justify-between gap-3 rounded-md ring-1 ring-inset ring-slate-800 bg-slate-950/40 px-3 py-2 text-left hover:ring-slate-700"
      >
        <div class="min-w-0">
          <div class="text-[13px] font-medium text-slate-200">Skip public SDKs</div>
          <div class="text-[11px] text-slate-500 mt-0.5 leading-snug">Don't recurse into vendored SDK directories</div>
        </div>
        <span :class="['shrink-0 mt-0.5 inline-flex w-9 h-5 rounded-full p-0.5 transition-colors', modelValue.skip_public_sdks ? 'bg-indigo-500' : 'bg-slate-700']">
          <span :class="['block w-4 h-4 rounded-full bg-white shadow transition-transform', modelValue.skip_public_sdks ? 'translate-x-4' : '']"/>
        </span>
      </button>

      <!-- Include internal toggle -->
      <button
        type="button"
        @click="patch('include_internal', !modelValue.include_internal)"
        class="flex items-start justify-between gap-3 rounded-md ring-1 ring-inset ring-slate-800 bg-slate-950/40 px-3 py-2 text-left hover:ring-slate-700"
      >
        <div class="min-w-0">
          <div class="text-[13px] font-medium text-slate-200">Include internal folders</div>
          <div class="text-[11px] text-slate-500 mt-0.5 leading-snug">Scan .venv / node_modules / .next style dirs</div>
        </div>
        <span :class="['shrink-0 mt-0.5 inline-flex w-9 h-5 rounded-full p-0.5 transition-colors', modelValue.include_internal ? 'bg-indigo-500' : 'bg-slate-700']">
          <span :class="['block w-4 h-4 rounded-full bg-white shadow transition-transform', modelValue.include_internal ? 'translate-x-4' : '']"/>
        </span>
      </button>
    </div>
  </div>
</template>
