<script setup lang="ts">
import { computed } from 'vue'
import type { ComplexFunction } from '@/types'

const props = defineProps<{
  functions: ComplexFunction[]
  projectPath: string
}>()

const sorted = computed(() => [...props.functions].sort((a, b) => b.complexity - a.complexity))

function relativePath(absolute: string): string {
  if (!props.projectPath) return absolute
  if (absolute.startsWith(props.projectPath)) {
    const rest = absolute.slice(props.projectPath.length)
    return rest.startsWith('/') ? rest.slice(1) : rest
  }
  return absolute
}

function complexityClass(c: number): string {
  // Standard McCabe thresholds: ≤10 simple, 11-20 medium, 21-50 complex, >50 untestable.
  if (c <= 10) return 'bg-emerald-100 text-emerald-700'
  if (c <= 20) return 'bg-amber-100 text-amber-700'
  if (c <= 50) return 'bg-orange-100 text-orange-700'
  return 'bg-red-100 text-red-700'
}

function complexityLabel(c: number): string {
  if (c <= 10) return 'simple'
  if (c <= 20) return 'moderate'
  if (c <= 50) return 'complex'
  return 'untestable'
}
</script>

<template>
  <div class="bg-white rounded-lg border border-slate-200 p-4 space-y-3 dark:bg-slate-900 dark:border-slate-700">
    <div class="flex items-baseline justify-between">
      <div>
        <h3 class="text-sm font-semibold text-slate-900 uppercase tracking-wide dark:text-slate-100">Complexity hotspots</h3>
        <p class="text-xs text-slate-500 dark:text-slate-400">McCabe cyclomatic complexity per Python function (top 30).</p>
      </div>
      <div class="text-xs text-slate-500 dark:text-slate-400">{{ functions.length }} captured</div>
    </div>

    <div v-if="functions.length === 0" class="text-sm text-slate-500 py-4 text-center dark:text-slate-400">
      No Python functions analyzed in this project — or all of them are below the complexity threshold.
    </div>

    <ul v-else class="space-y-1 max-h-[24rem] overflow-y-auto pr-1">
      <li
        v-for="(fn, idx) in sorted"
        :key="`${fn.file}:${fn.line}:${fn.qualname}:${idx}`"
        class="flex items-center gap-2 text-sm"
      >
        <span :class="['px-2 py-0.5 rounded text-xs font-semibold tabular-nums w-10 text-center', complexityClass(fn.complexity)]"
              :title="`Cyclomatic: ${fn.complexity} (${complexityLabel(fn.complexity)})`">
          {{ fn.complexity }}
        </span>
        <span class="font-mono text-xs text-slate-900 truncate dark:text-slate-100">{{ fn.qualname }}</span>
        <span class="text-xs tabular-nums text-slate-400 dark:text-slate-500">L{{ fn.line }}</span>
        <span class="ml-auto text-xs font-mono text-slate-500 truncate max-w-[40%] dark:text-slate-400" :title="relativePath(fn.file)">
          {{ relativePath(fn.file) }}
        </span>
      </li>
    </ul>
  </div>
</template>
