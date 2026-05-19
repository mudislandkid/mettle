<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import type { FlagType } from '@/types'

const props = defineProps<{
  params: {
    value: string[]
    data: { id: number }
    flagTypes?: FlagType[]
    onUpdate?: (projectId: number, flags: string[]) => void
  }
}>()

const showDropdown = ref(false)
const containerRef = ref<HTMLElement | null>(null)

// Always prefer the flag types fetched from the backend; fall back to a
// minimal local set only if the parent never passed any (e.g. early render).
const flagTypes = computed<FlagType[]>(() => props.params.flagTypes ?? [])

const currentFlags = computed(() => props.params.value || [])

function toggleFlag(flagType: string) {
  const newFlags = currentFlags.value.includes(flagType)
    ? currentFlags.value.filter((f) => f !== flagType)
    : [...currentFlags.value, flagType]

  props.params.onUpdate?.(props.params.data.id, newFlags)
}

function getFlagColor(flagType: string): string {
  return flagTypes.value.find((f) => f.type === flagType)?.color || '#6b7280'
}

function getFlagLabel(flagType: string): string {
  return flagTypes.value.find((f) => f.type === flagType)?.label || flagType
}

function handleClickOutside(event: MouseEvent) {
  if (!showDropdown.value) return
  const target = event.target as Node | null
  if (target && containerRef.value && !containerRef.value.contains(target)) {
    showDropdown.value = false
  }
}

function handleEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') showDropdown.value = false
}

onMounted(() => {
  document.addEventListener('mousedown', handleClickOutside)
  document.addEventListener('keydown', handleEscape)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleClickOutside)
  document.removeEventListener('keydown', handleEscape)
})
</script>

<template>
  <div ref="containerRef" class="relative h-full flex items-center">
    <div class="flex flex-wrap gap-1">
      <span
        v-for="flag in currentFlags"
        :key="flag"
        class="px-1.5 py-0.5 text-xs rounded-full text-white"
        :style="{ backgroundColor: getFlagColor(flag) }"
      >
        {{ getFlagLabel(flag) }}
      </span>
    </div>

    <button
      @click="showDropdown = !showDropdown"
      class="ml-1 p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded dark:text-slate-500 dark:text-slate-400 dark:bg-slate-800"
      aria-label="Add flag"
    >
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
      </svg>
    </button>

    <div
      v-if="showDropdown"
      class="absolute top-full left-0 z-50 mt-1 bg-white border border-slate-200 rounded-md shadow-lg min-w-[160px] dark:bg-slate-900 dark:border-slate-700"
    >
      <ul class="py-1">
        <li
          v-for="ft in flagTypes"
          :key="ft.type"
          @click="toggleFlag(ft.type)"
          class="px-3 py-1.5 text-sm cursor-pointer hover:bg-slate-100 flex items-center gap-2 dark:bg-slate-800"
        >
          <input
            type="checkbox"
            :checked="currentFlags.includes(ft.type)"
            class="w-3 h-3 rounded"
            @click.stop
          />
          <span class="w-3 h-3 rounded-full" :style="{ backgroundColor: ft.color }"></span>
          <span>{{ ft.label }}</span>
        </li>
        <li v-if="flagTypes.length === 0" class="px-3 py-1.5 text-sm text-slate-500 dark:text-slate-400">
          No flag types available
        </li>
      </ul>
    </div>
  </div>
</template>
