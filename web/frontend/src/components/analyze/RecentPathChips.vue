<script setup lang="ts">
import type { RecentPath } from '@/types'

const props = defineProps<{
  recentPaths: RecentPath[]
  activePath: string
}>()

const emit = defineEmits<{
  (e: 'select', path: string): void
}>()

function shortPath(path: string): string {
  return path.replace(/^\/Users\/[^/]+/, '~')
}
</script>

<template>
  <div v-if="recentPaths.length > 0" class="flex flex-wrap gap-1.5 -mt-1">
    <span class="text-[10px] uppercase tracking-[0.12em] text-slate-500 font-semibold mr-1 self-center">Quick:</span>
    <button
      v-for="rp in recentPaths.slice(0, 3)"
      :key="rp.id"
      type="button"
      @click="emit('select', rp.path)"
      :class="[
        'text-[11px] font-mono px-2 py-0.5 rounded-md ring-1 ring-inset transition-colors',
        activePath === rp.path
          ? 'bg-indigo-500/20 text-indigo-200 ring-indigo-500/30'
          : 'bg-slate-950/60 text-slate-300 ring-slate-700 hover:ring-slate-600'
      ]"
    >
      {{ shortPath(rp.path) }}
    </button>
  </div>
</template>
