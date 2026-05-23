<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { fmtRelative } from '@/lib/format'
import { isTauri } from '@/lib/runtime'
import type { RecentPath } from '@/types'

const props = defineProps<{
  modelValue: string
  recentPaths: RecentPath[]
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const open = ref(false)
const rootRef = ref<HTMLDivElement | null>(null)
const picking = ref(false)

// In the Tauri desktop shell the folder icon is interactive — clicking it
// pops the native macOS directory picker. Browser builds can't open an
// absolute-path picker (the File System Access API hides the full path),
// so the icon stays decorative there.
const canPick = isTauri()

function onDocClick(e: MouseEvent) {
  if (rootRef.value && !rootRef.value.contains(e.target as Node)) {
    open.value = false
  }
}

onMounted(() => {
  document.addEventListener('mousedown', onDocClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDocClick)
})

function handleInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
}

function selectPath(path: string) {
  emit('update:modelValue', path)
  open.value = false
}

async function pickDirectory() {
  if (!canPick || props.disabled || picking.value) return
  picking.value = true
  try {
    const { open: openDialog } = await import('@tauri-apps/plugin-dialog')
    const result = await openDialog({
      directory: true,
      multiple: false,
      title: 'Choose a directory to analyze',
      defaultPath: props.modelValue || undefined,
    })
    // result is string | null in single-select directory mode.
    if (typeof result === 'string' && result) {
      emit('update:modelValue', result)
    }
  } catch (err) {
    console.error('Directory picker failed:', err)
  } finally {
    picking.value = false
  }
}
</script>

<template>
  <div class="relative" ref="rootRef">
    <label class="block text-[11px] uppercase tracking-[0.14em] text-slate-500 font-semibold mb-2">
      Directory
    </label>
    <div class="relative flex items-stretch rounded-lg ring-1 ring-inset ring-slate-700 bg-slate-950/60 focus-within:ring-indigo-500/60 focus-within:bg-slate-950 transition-colors">
      <button
        v-if="canPick"
        type="button"
        @click="pickDirectory"
        :disabled="disabled || picking"
        class="flex items-center pl-3 pr-2 text-slate-500 hover:text-indigo-300 focus:text-indigo-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/60 rounded-l-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        :aria-label="picking ? 'Choosing directory…' : 'Browse for a directory'"
        :title="picking ? 'Choosing directory…' : 'Browse for a directory'"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             :class="picking ? 'animate-pulse' : ''">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
        </svg>
      </button>
      <div v-else class="flex items-center pl-3 pr-2 text-slate-500" aria-hidden="true">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
        </svg>
      </div>
      <input
        type="text"
        :value="modelValue"
        @input="handleInput"
        @focus="open = true"
        :disabled="disabled"
        placeholder="/path/to/projects"
        class="flex-1 bg-transparent py-3 px-2 font-mono text-[14px] text-slate-100 placeholder:text-slate-600 focus:outline-none disabled:opacity-50"
        :spell-check="false"
      />
      <button
        v-if="recentPaths.length > 0"
        type="button"
        @click="open = !open"
        class="px-3 text-slate-500 hover:text-slate-200 border-l border-slate-800"
        aria-label="Show recent paths"
        title="Recent paths"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 20 20"
          fill="none"
          :class="['transition-transform', open ? 'rotate-180' : '']"
        >
          <path d="M5 8l5 5 5-5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>

    <div
      v-if="open && recentPaths.length > 0"
      class="absolute z-30 left-0 right-0 mt-2 rounded-lg ring-1 ring-slate-700 bg-slate-900 shadow-2xl overflow-hidden"
    >
      <div class="px-3 py-2 text-[10px] uppercase tracking-[0.14em] text-slate-500 font-semibold border-b border-slate-800">
        Recent paths
      </div>
      <ul class="max-h-72 overflow-y-auto py-1">
        <li v-for="rp in recentPaths" :key="rp.id">
          <button
            type="button"
            @mousedown.prevent="selectPath(rp.path)"
            class="w-full flex items-center justify-between gap-3 px-3 py-2 hover:bg-slate-800 text-left"
          >
            <span class="font-mono text-[13px] text-slate-200 truncate">{{ rp.path }}</span>
            <span class="shrink-0 flex items-center gap-2">
              <span class="text-[10px] text-slate-500">{{ fmtRelative(rp.last_used) }}</span>
              <span class="text-[10px] tabular-nums text-slate-400 px-1.5 py-0.5 rounded bg-slate-800">{{ rp.use_count }}×</span>
            </span>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>
