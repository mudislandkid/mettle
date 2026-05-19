<script setup lang="ts">
import { ref, watch, computed, onBeforeUnmount } from 'vue'
import { updateProjectNotes } from '@/api/projects'

const props = defineProps<{
  projectId: number
  initialNotes: string
}>()

type SaveState = 'idle' | 'pending' | 'saving' | 'saved' | 'error'

const text = ref(props.initialNotes ?? '')
const state = ref<SaveState>('idle')
const errorMessage = ref<string | null>(null)
let debounceTimer: ReturnType<typeof setTimeout> | null = null
let lastSaved = props.initialNotes ?? ''

const charCount = computed(() => text.value.length)
const dirty = computed(() => text.value !== lastSaved)

function scheduleSave() {
  state.value = 'pending'
  if (debounceTimer !== null) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(commitSave, 800)
}

async function commitSave() {
  debounceTimer = null
  if (!dirty.value) {
    state.value = 'idle'
    return
  }
  state.value = 'saving'
  errorMessage.value = null
  try {
    const { notes } = await updateProjectNotes(props.projectId, text.value)
    lastSaved = notes
    text.value = notes // canonical (trimmed by server clamp)
    state.value = 'saved'
    // Drop back to idle after a moment so the indicator doesn't shout.
    setTimeout(() => {
      if (state.value === 'saved') state.value = 'idle'
    }, 1500)
  } catch (err) {
    state.value = 'error'
    errorMessage.value = (err as Error).message
  }
}

// Reset editor state when the parent navigates between projects.
watch(
  () => props.projectId,
  () => {
    text.value = props.initialNotes ?? ''
    lastSaved = props.initialNotes ?? ''
    state.value = 'idle'
    errorMessage.value = null
  },
)

// Best-effort save on unmount if the user typed and bounced away.
onBeforeUnmount(() => {
  if (debounceTimer !== null) {
    clearTimeout(debounceTimer)
    debounceTimer = null
    if (dirty.value) commitSave()
  }
})

const statusLabel = computed(() => {
  switch (state.value) {
    case 'pending': return 'Unsaved changes…'
    case 'saving': return 'Saving…'
    case 'saved': return 'Saved'
    case 'error': return errorMessage.value ? `Save failed: ${errorMessage.value}` : 'Save failed'
    default: return dirty.value ? 'Unsaved changes' : ''
  }
})
const statusClass = computed(() => {
  if (state.value === 'error') return 'text-red-600'
  if (state.value === 'saved') return 'text-emerald-600'
  if (state.value === 'saving' || state.value === 'pending') return 'text-slate-500'
  return 'text-slate-400'
})
</script>

<template>
  <div class="bg-white rounded-lg border border-slate-200 p-4 space-y-2 dark:bg-slate-900 dark:border-slate-700">
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-sm font-semibold text-slate-900 dark:text-slate-100">Notes</h3>
        <p class="text-xs text-slate-500 dark:text-slate-400">Private notes about this project. Auto-saved.</p>
      </div>
      <div class="text-xs" :class="statusClass">{{ statusLabel }}</div>
    </div>
    <textarea
      v-model="text"
      @input="scheduleSave"
      placeholder="What is this project for? What's the next step? What broke last time?"
      class="w-full min-h-[120px] resize-y px-3 py-2 border border-slate-200 rounded-md font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-slate-700"
      maxlength="100000"
    ></textarea>
    <div class="text-right text-xs text-slate-400 dark:text-slate-500">
      {{ charCount.toLocaleString() }} / 100,000
    </div>
  </div>
</template>
