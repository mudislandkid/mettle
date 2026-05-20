<script setup lang="ts">
import type { SecretMatch } from '@/types'

defineProps<{
  count: number
  detail: SecretMatch[] | null
}>()

const emit = defineEmits<{ (e: 'open'): void }>()
</script>

<template>
  <button
    v-if="count > 0"
    @click="emit('open')"
    class="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-mono font-semibold bg-red-900/40 text-red-200 hover:bg-red-900/60 border border-red-700/50"
    :title="`${count} potential secret${count === 1 ? '' : 's'} — click for detail`"
  >
    <svg class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"/>
    </svg>
    {{ count }}
  </button>
  <span v-else class="text-zinc-600">—</span>
</template>
