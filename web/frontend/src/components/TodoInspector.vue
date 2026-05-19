<script setup lang="ts">
import { computed, ref } from 'vue'
import type { TodoItem } from '@/types'

const props = defineProps<{
  items: TodoItem[]
  projectPath: string
}>()

const markerFilter = ref<string>('ALL')
const searchQuery = ref('')

const counts = computed(() => {
  const c: Record<string, number> = { ALL: props.items.length, TODO: 0, FIXME: 0, XXX: 0, HACK: 0 }
  for (const item of props.items) {
    const m = (item.marker || '').toUpperCase()
    if (m in c) c[m] += 1
  }
  return c
})

const filtered = computed(() => {
  const q = searchQuery.value.toLowerCase()
  return props.items.filter((item) => {
    if (markerFilter.value !== 'ALL' && item.marker.toUpperCase() !== markerFilter.value) {
      return false
    }
    if (!q) return true
    return (
      item.text.toLowerCase().includes(q) ||
      item.file.toLowerCase().includes(q)
    )
  })
})

const groupedByFile = computed<Array<[string, TodoItem[]]>>(() => {
  const groups = new Map<string, TodoItem[]>()
  for (const item of filtered.value) {
    const rel = relativePath(item.file)
    const list = groups.get(rel) ?? []
    list.push(item)
    groups.set(rel, list)
  }
  // Sort files by todo count desc, then alpha.
  return Array.from(groups.entries())
    .sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]))
})

function relativePath(absolute: string): string {
  if (!props.projectPath) return absolute
  if (absolute.startsWith(props.projectPath)) {
    const rest = absolute.slice(props.projectPath.length)
    return rest.startsWith('/') ? rest.slice(1) : rest
  }
  return absolute
}

function markerClass(marker: string): string {
  switch (marker.toUpperCase()) {
    case 'TODO': return 'bg-blue-100 text-blue-700'
    case 'FIXME': return 'bg-red-100 text-red-700'
    case 'XXX': return 'bg-orange-100 text-orange-700'
    case 'HACK': return 'bg-purple-100 text-purple-700'
    default: return 'bg-slate-100 text-slate-700'
  }
}
</script>

<template>
  <div class="bg-white rounded-lg border border-slate-200 p-4 space-y-3 dark:bg-slate-900 dark:border-slate-700">
    <div class="flex items-baseline justify-between">
      <div>
        <h3 class="text-sm font-semibold text-slate-900 uppercase tracking-wide dark:text-slate-100">TODOs</h3>
        <p class="text-xs text-slate-500 dark:text-slate-400">Up to 500 markers captured during analysis.</p>
      </div>
      <div class="text-xs text-slate-500 dark:text-slate-400">{{ items.length }} captured</div>
    </div>

    <div v-if="items.length === 0" class="text-sm text-slate-500 py-4 text-center dark:text-slate-400">
      No TODO / FIXME / XXX / HACK markers in this project.
    </div>

    <template v-else>
      <div class="flex flex-wrap items-center gap-2 text-xs">
        <button
          v-for="m in ['ALL', 'TODO', 'FIXME', 'XXX', 'HACK']"
          :key="m"
          @click="markerFilter = m"
          class="px-2 py-1 rounded transition-colors"
          :class="markerFilter === m
            ? 'bg-indigo-600 text-white'
            : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'"
        >
          {{ m }} <span class="opacity-70">({{ counts[m] || 0 }})</span>
        </button>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Filter text or path…"
          class="ml-auto px-2 py-1 border border-slate-200 rounded text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-slate-700"
        />
      </div>

      <div class="space-y-3 max-h-[28rem] overflow-y-auto pr-1">
        <div
          v-for="[file, fileItems] in groupedByFile"
          :key="file"
        >
          <div class="text-xs font-mono text-slate-500 mb-1 dark:text-slate-400">
            {{ file }} <span class="text-slate-400 dark:text-slate-500">({{ fileItems.length }})</span>
          </div>
          <ul class="space-y-1">
            <li
              v-for="(item, idx) in fileItems"
              :key="`${item.file}:${item.line}:${idx}`"
              class="flex items-start gap-2 text-sm"
            >
              <span :class="['px-1.5 rounded text-[10px] font-semibold tracking-wider mt-0.5', markerClass(item.marker)]">
                {{ item.marker }}
              </span>
              <span class="text-xs tabular-nums text-slate-400 mt-0.5 dark:text-slate-500">L{{ item.line }}</span>
              <span class="font-mono text-xs text-slate-700 break-words dark:text-slate-300">{{ item.text }}</span>
            </li>
          </ul>
        </div>
        <div v-if="filtered.length === 0" class="text-sm text-slate-500 py-4 text-center dark:text-slate-400">
          No TODOs match the current filter.
        </div>
      </div>
    </template>
  </div>
</template>
