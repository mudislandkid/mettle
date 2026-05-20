<script setup lang="ts">
import { computed } from 'vue'
import { fmtNum } from '@/lib/format'
import type { Project } from '@/types'

const props = defineProps<{
  project: Project
  maxLines: number
}>()

// width percent relative to the largest project (min 2% to stay visible)
const w = computed(() =>
  Math.max(2, Math.round((props.project.total_lines / Math.max(1, props.maxLines)) * 100))
)
</script>

<template>
  <div class="flex items-center gap-3">
    <div class="flex flex-col items-end leading-tight w-20 shrink-0">
      <span class="text-[13px] tabular-nums text-slate-200 font-medium">{{ fmtNum(project.total_lines) }}</span>
      <span class="text-[10px] text-slate-500">{{ fmtNum(project.total_files) }} files</span>
    </div>
    <div class="h-3 w-24 rounded-sm bg-slate-800/50 overflow-hidden flex">
      <div class="bg-indigo-500/80 h-full" :style="{ width: `${w * 0.7}%` }" title="code" />
      <div class="bg-sky-500/60 h-full"    :style="{ width: `${w * 0.2}%` }" title="comments" />
      <div class="bg-slate-600 h-full"     :style="{ width: `${w * 0.1}%` }" title="blank" />
    </div>
  </div>
</template>
