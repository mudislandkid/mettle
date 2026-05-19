<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getRecentPaths } from '@/api/analysis'
import type { RecentPath } from '@/types'

const props = defineProps<{
  modelValue: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const showDropdown = ref(false)
const recentPaths = ref<RecentPath[]>([])

onMounted(async () => {
  try {
    recentPaths.value = await getRecentPaths()
  } catch (e) {
    // Ignore
  }
})

function selectPath(path: string) {
  emit('update:modelValue', path)
  showDropdown.value = false
}

function handleInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
}

function handleBlur() {
  window.setTimeout(() => showDropdown.value = false, 200)
}
</script>

<template>
  <div class="relative">
    <label class="block text-sm font-medium text-slate-700 mb-1 dark:text-slate-300">
      Directory Path
    </label>
    <div class="relative">
      <input
        type="text"
        :value="modelValue"
        @input="handleInput"
        @focus="showDropdown = true"
        @blur="handleBlur"
        :disabled="disabled"
        placeholder="/path/to/projects"
        class="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-slate-100 disabled:cursor-not-allowed dark:border-slate-600 dark:bg-slate-800"
      />
      <div class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
        </svg>
      </div>
    </div>

    <!-- Dropdown -->
    <div
      v-if="showDropdown && recentPaths.length > 0 && !disabled"
      class="absolute z-10 w-full mt-1 bg-white border border-slate-200 rounded-md shadow-lg max-h-60 overflow-auto dark:bg-slate-900 dark:border-slate-700"
    >
      <div class="px-3 py-2 text-xs font-medium text-slate-500 bg-slate-50 border-b dark:text-slate-400 dark:bg-slate-900">
        Recent Paths
      </div>
      <ul>
        <li
          v-for="rp in recentPaths"
          :key="rp.id"
          @mousedown.prevent="selectPath(rp.path)"
          class="px-3 py-2 hover:bg-slate-100 cursor-pointer flex justify-between items-center dark:bg-slate-800"
        >
          <span class="text-sm text-slate-700 truncate dark:text-slate-300">{{ rp.path }}</span>
          <span class="text-xs text-slate-400 ml-2 shrink-0 dark:text-slate-500">{{ rp.use_count }}x</span>
        </li>
      </ul>
    </div>
  </div>
</template>
