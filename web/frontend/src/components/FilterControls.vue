<script setup lang="ts">
import { computed } from 'vue'
import type { AnalysisFilters } from '@/types'

const props = defineProps<{
  modelValue: AnalysisFilters
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: AnalysisFilters): void
}>()

const filters = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

function updateFilter<K extends keyof AnalysisFilters>(key: K, value: AnalysisFilters[K]) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}
</script>

<template>
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
    <!-- GitHub User -->
    <div>
      <label class="block text-sm font-medium text-slate-700 mb-1 dark:text-slate-300">
        GitHub User
      </label>
      <input
        type="text"
        :value="filters.github_user || ''"
        @input="updateFilter('github_user', ($event.target as HTMLInputElement).value || null)"
        :disabled="disabled"
        placeholder="Filter by owner"
        class="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-slate-100 disabled:cursor-not-allowed text-sm dark:border-slate-600 dark:bg-slate-800"
      />
    </div>

    <!-- Skip Public SDKs -->
    <div class="flex items-end">
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          :checked="filters.skip_public_sdks"
          @change="updateFilter('skip_public_sdks', ($event.target as HTMLInputElement).checked)"
          :disabled="disabled"
          class="w-4 h-4 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500 disabled:cursor-not-allowed dark:text-indigo-400 dark:border-slate-600"
        />
        <span class="text-sm text-slate-700 dark:text-slate-300">Skip Public SDKs</span>
      </label>
    </div>

    <!-- Include Internal -->
    <div class="flex items-end">
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          :checked="filters.include_internal"
          @change="updateFilter('include_internal', ($event.target as HTMLInputElement).checked)"
          :disabled="disabled"
          class="w-4 h-4 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500 disabled:cursor-not-allowed dark:text-indigo-400 dark:border-slate-600"
        />
        <span class="text-sm text-slate-700 dark:text-slate-300">Include Internal Folders</span>
      </label>
    </div>

    <!-- Max Files -->
    <div>
      <label class="block text-sm font-medium text-slate-700 mb-1 dark:text-slate-300">
        Max Files: {{ filters.max_files === 0 ? 'Unlimited' : filters.max_files.toLocaleString() }}
      </label>
      <input
        type="range"
        :value="filters.max_files"
        @input="updateFilter('max_files', Number(($event.target as HTMLInputElement).value))"
        :disabled="disabled"
        min="0"
        max="50000"
        step="1000"
        class="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer disabled:cursor-not-allowed dark:bg-slate-700"
      />
    </div>
  </div>
</template>
