<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { AnalysisProgress } from '@/types'

const props = defineProps<{
  progress: AnalysisProgress
  percentage: number
}>()

const MAX_LOG_LINES = 2000

const allLogs = ref<string[]>([])
const consoleRef = ref<HTMLElement | null>(null)
let lastLogsRef: AnalysisProgress['logs'] | undefined

watch(
  () => props.progress.logs,
  (newLogs) => {
    if (!newLogs || newLogs.length === 0) return
    // If the same array reference fires the watcher twice (e.g. on socket
    // reconnect echoing the same payload), skip it to avoid duplicates.
    if (newLogs === lastLogsRef) return
    lastLogsRef = newLogs

    allLogs.value.push(...newLogs)
    if (allLogs.value.length > MAX_LOG_LINES) {
      allLogs.value.splice(0, allLogs.value.length - MAX_LOG_LINES)
    }

    nextTick(() => {
      if (consoleRef.value) {
        consoleRef.value.scrollTop = consoleRef.value.scrollHeight
      }
    })
  },
  { immediate: true },
)

watch(
  () => props.progress.status,
  (status) => {
    if (status === 'idle' || status === 'pending') {
      allLogs.value = []
      lastLogsRef = undefined
    }
  },
)
</script>

<template>
  <div class="bg-white rounded-lg border border-slate-200 p-4 space-y-3 dark:bg-slate-900 dark:border-slate-700">
    <!-- Progress header -->
    <div class="flex justify-between items-center">
      <span class="text-sm font-medium text-slate-700 dark:text-slate-300">
        {{ progress.message || 'Analyzing...' }}
      </span>
      <span class="text-sm text-slate-500 dark:text-slate-400">
        {{ progress.current }} / {{ progress.total }}
      </span>
    </div>

    <!-- Progress bar -->
    <div class="w-full bg-slate-200 rounded-full h-2.5 dark:bg-slate-700">
      <div
        class="bg-indigo-600 h-2.5 rounded-full transition-all duration-300"
        :style="{ width: `${percentage}%` }"
      ></div>
    </div>

    <!-- Current project -->
    <div v-if="progress.project_name" class="text-sm text-slate-500 truncate dark:text-slate-400">
      <span class="font-medium">Current:</span> {{ progress.project_name }}
    </div>

    <!-- Console output -->
    <div class="bg-slate-900 rounded-md p-3 dark:bg-slate-950">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-semibold text-slate-400 uppercase tracking-wide dark:text-slate-500">Console Output</span>
        <span class="text-xs text-slate-500 dark:text-slate-400">{{ allLogs.length }} messages</span>
      </div>
      <div
        ref="consoleRef"
        class="font-mono text-xs text-green-400 max-h-48 overflow-y-auto space-y-1 custom-scrollbar"
      >
        <div v-if="allLogs.length === 0" class="text-slate-500 dark:text-slate-400">
          Waiting for analysis to start...
        </div>
        <div v-for="(log, index) in allLogs" :key="index" class="whitespace-pre-wrap">
          <span class="text-slate-600 select-none dark:text-slate-400">› </span>{{ log }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.5);
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.7);
}
</style>
