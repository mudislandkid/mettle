<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listAnalyses, deleteAnalysis } from '@/api/analysis'
import HighlightsPanels from '@/components/HighlightsPanels.vue'
import type { AnalysisListItem } from '@/types'

const router = useRouter()
const analyses = ref<AnalysisListItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  await loadAnalyses()
})

async function loadAnalyses() {
  loading.value = true
  error.value = null
  try {
    analyses.value = await listAnalyses(50, 0)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

async function handleDelete(id: number) {
  if (!confirm('Are you sure you want to delete this analysis?')) return

  try {
    await deleteAnalysis(id)
    analyses.value = analyses.value.filter(a => a.id !== id)
  } catch (e) {
    error.value = (e as Error).message
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString()
}

function formatNumber(n: number): string {
  return n.toLocaleString()
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800'
    case 'running':
      return 'bg-blue-100 text-blue-800'
    case 'failed':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-slate-100 text-slate-800'
  }
}
</script>

<template>
  <div class="space-y-6">
    <HighlightsPanels />

    <div class="flex justify-between items-center">
      <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-200">Analysis History</h2>
      <button
        @click="loadAnalyses"
        class="px-3 py-1.5 text-sm bg-slate-100 text-slate-700 rounded-md hover:bg-slate-200 transition-colors dark:bg-slate-800 dark:text-slate-300 dark:bg-slate-700"
      >
        Refresh
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12">
      <div class="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto"></div>
      <p class="mt-2 text-slate-500 dark:text-slate-400">Loading...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="bg-red-50 text-red-700 p-4 rounded-md dark:bg-red-500/15 dark:text-red-300">
      {{ error }}
    </div>

    <!-- Empty -->
    <div v-else-if="analyses.length === 0" class="text-center py-12 text-slate-500 dark:text-slate-400">
      No analyses found. Start a new analysis to get started.
    </div>

    <!-- List -->
    <div v-else class="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden dark:bg-slate-900 dark:border-slate-700">
      <table class="w-full">
        <thead class="bg-slate-50 border-b border-slate-200 dark:bg-slate-900 dark:border-slate-700">
          <tr>
            <th class="px-4 py-3 text-left text-sm font-medium text-slate-700 dark:text-slate-300">Directory</th>
            <th class="px-4 py-3 text-left text-sm font-medium text-slate-700 dark:text-slate-300">Date</th>
            <th class="px-4 py-3 text-left text-sm font-medium text-slate-700 dark:text-slate-300">Status</th>
            <th class="px-4 py-3 text-right text-sm font-medium text-slate-700 dark:text-slate-300">Projects</th>
            <th class="px-4 py-3 text-right text-sm font-medium text-slate-700 dark:text-slate-300">Files</th>
            <th class="px-4 py-3 text-right text-sm font-medium text-slate-700 dark:text-slate-300">Lines</th>
            <th class="px-4 py-3 text-right text-sm font-medium text-slate-700 dark:text-slate-300">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-200">
          <tr
            v-for="analysis in analyses"
            :key="analysis.id"
            class="hover:bg-slate-50 dark:bg-slate-900"
          >
            <td class="px-4 py-3 text-sm text-slate-700 dark:text-slate-300">
              <div class="truncate max-w-xs" :title="analysis.directory_path">
                {{ analysis.directory_path }}
              </div>
            </td>
            <td class="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">
              {{ formatDate(analysis.analyzed_at) }}
            </td>
            <td class="px-4 py-3">
              <span
                class="px-2 py-1 text-xs rounded-full"
                :class="getStatusColor(analysis.status)"
              >
                {{ analysis.status }}
              </span>
            </td>
            <td class="px-4 py-3 text-sm text-slate-700 text-right dark:text-slate-300">
              {{ formatNumber(analysis.total_projects) }}
            </td>
            <td class="px-4 py-3 text-sm text-slate-700 text-right dark:text-slate-300">
              {{ formatNumber(analysis.total_files) }}
            </td>
            <td class="px-4 py-3 text-sm text-slate-700 text-right dark:text-slate-300">
              {{ formatNumber(analysis.total_lines) }}
            </td>
            <td class="px-4 py-3 text-right">
              <div class="flex justify-end gap-2">
                <button
                  v-if="analysis.status === 'completed'"
                  @click="router.push({ name: 'analysis', query: { id: analysis.id } })"
                  class="text-indigo-600 hover:text-indigo-800 text-sm dark:text-indigo-400"
                >
                  View
                </button>
                <button
                  @click="handleDelete(analysis.id)"
                  class="text-red-600 hover:text-red-800 text-sm dark:text-red-400"
                >
                  Delete
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
