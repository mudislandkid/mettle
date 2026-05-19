<script setup lang="ts">
const props = defineProps<{
  analysisId: number
}>()

function downloadExport(format: 'markdown' | 'json' | 'csv') {
  window.open(`/api/export/${format}/${props.analysisId}`, '_blank')
}
</script>

<template>
  <div class="flex gap-2">
    <button
      @click="downloadExport('markdown')"
      class="px-3 py-1.5 text-sm bg-slate-100 text-slate-700 rounded-md hover:bg-slate-200 transition-colors flex items-center gap-1 dark:bg-slate-800 dark:text-slate-300 dark:bg-slate-700"
    >
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
      Markdown
    </button>
    <button
      @click="downloadExport('json')"
      class="px-3 py-1.5 text-sm bg-slate-100 text-slate-700 rounded-md hover:bg-slate-200 transition-colors flex items-center gap-1 dark:bg-slate-800 dark:text-slate-300 dark:bg-slate-700"
    >
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
      JSON
    </button>
    <button
      @click="downloadExport('csv')"
      class="px-3 py-1.5 text-sm bg-slate-100 text-slate-700 rounded-md hover:bg-slate-200 transition-colors flex items-center gap-1 dark:bg-slate-800 dark:text-slate-300 dark:bg-slate-700"
    >
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
      CSV
    </button>
  </div>
</template>
