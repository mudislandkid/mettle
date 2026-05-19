<script setup lang="ts">
import { computed } from 'vue'
import LinesTrendChart from './LinesTrendChart.vue'
import CommitsBarChart from './CommitsBarChart.vue'
import ActivityHeatmap from './ActivityHeatmap.vue'
import TimePatternHeatmap from './TimePatternHeatmap.vue'
import AuthorBarChart from './AuthorBarChart.vue'
import type { GitStatsResponse } from '@/types'

const props = defineProps<{
  stats: GitStatsResponse | null
  loading: boolean
  error: string | null
}>()

const hasData = computed(() => {
  return props.stats && props.stats.commits && props.stats.commits.length > 0
})
</script>

<template>
  <div class="space-y-6">
    <!-- Loading State -->
    <div v-if="loading" class="space-y-6">
      <div class="bg-white rounded-lg border border-slate-200 p-4 animate-pulse dark:bg-slate-900 dark:border-slate-700">
        <div class="h-8 bg-slate-200 rounded w-1/3 mx-auto mb-4 dark:bg-slate-700"></div>
        <div class="h-80 bg-slate-100 rounded dark:bg-slate-800"></div>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="bg-white rounded-lg border border-slate-200 p-4 animate-pulse dark:bg-slate-900 dark:border-slate-700">
          <div class="h-8 bg-slate-200 rounded w-1/3 mx-auto mb-4 dark:bg-slate-700"></div>
          <div class="h-64 bg-slate-100 rounded dark:bg-slate-800"></div>
        </div>
        <div class="bg-white rounded-lg border border-slate-200 p-4 animate-pulse dark:bg-slate-900 dark:border-slate-700">
          <div class="h-8 bg-slate-200 rounded w-1/3 mx-auto mb-4 dark:bg-slate-700"></div>
          <div class="h-64 bg-slate-100 rounded dark:bg-slate-800"></div>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-white rounded-lg border border-slate-200 p-8 text-center dark:bg-slate-900 dark:border-slate-700">
      <svg class="w-12 h-12 text-slate-400 mx-auto mb-4 dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <h3 class="text-lg font-semibold text-slate-700 mb-2 dark:text-slate-300">{{ error }}</h3>
      <p class="text-sm text-slate-500 dark:text-slate-400">
        {{ error === 'Not a Git repository'
          ? 'This project is not a Git repository. Git history visualization is only available for Git projects.'
          : 'Unable to load Git statistics. Please try again later.' }}
      </p>
    </div>

    <!-- No Data State -->
    <div v-else-if="!hasData" class="bg-white rounded-lg border border-slate-200 p-8 text-center dark:bg-slate-900 dark:border-slate-700">
      <svg class="w-12 h-12 text-slate-400 mx-auto mb-4 dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <h3 class="text-lg font-semibold text-slate-700 mb-2 dark:text-slate-300">No Commit History</h3>
      <p class="text-sm text-slate-500 dark:text-slate-400">
        This Git repository has no commit history yet.
      </p>
    </div>

    <!-- Charts -->
    <div v-else class="space-y-6">
      <!-- Success Indicator -->
      <div class="bg-green-50 border border-green-200 rounded-lg p-3 flex items-center gap-2 dark:bg-green-500/15 dark:border-green-500/30">
        <svg class="w-5 h-5 text-green-600 flex-shrink-0 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div class="flex-1">
          <p class="text-sm font-medium text-green-800 dark:text-green-300">
            Git history data loaded successfully
          </p>
          <p class="text-xs text-green-600 mt-0.5 dark:text-green-400">
            {{ stats?.total_commits.toLocaleString() }} commits analyzed from {{ stats?.first_commit_date ? new Date(stats.first_commit_date).toLocaleDateString() : 'N/A' }} to {{ stats?.last_commit_date ? new Date(stats.last_commit_date).toLocaleDateString() : 'N/A' }}
          </p>
        </div>
      </div>

      <!-- Summary Stats -->
      <div class="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div class="bg-white rounded-lg border border-slate-200 p-4 dark:bg-slate-900 dark:border-slate-700">
          <div class="text-sm text-slate-500 mb-1 dark:text-slate-400">Total Commits</div>
          <div class="text-2xl font-bold text-slate-900 dark:text-slate-100">{{ stats?.total_commits.toLocaleString() }}</div>
        </div>
        <div class="bg-white rounded-lg border border-slate-200 p-4 dark:bg-slate-900 dark:border-slate-700">
          <div class="text-sm text-slate-500 mb-1 dark:text-slate-400">Contributors</div>
          <div class="text-2xl font-bold text-slate-900 dark:text-slate-100">{{ stats?.unique_authors.toLocaleString() }}</div>
        </div>
        <div class="bg-white rounded-lg border border-slate-200 p-4 dark:bg-slate-900 dark:border-slate-700">
          <div class="text-sm text-slate-500 mb-1 dark:text-slate-400">First Commit</div>
          <div class="text-sm font-semibold text-slate-900 dark:text-slate-100">
            {{ stats?.first_commit_date ? new Date(stats.first_commit_date).toLocaleDateString() : 'N/A' }}
          </div>
        </div>
        <div class="bg-white rounded-lg border border-slate-200 p-4 dark:bg-slate-900 dark:border-slate-700">
          <div class="text-sm text-slate-500 mb-1 dark:text-slate-400">Last Commit</div>
          <div class="text-sm font-semibold text-slate-900 dark:text-slate-100">
            {{ stats?.last_commit_date ? new Date(stats.last_commit_date).toLocaleDateString() : 'N/A' }}
          </div>
        </div>
      </div>

      <!-- Lines Trend Chart -->
      <LinesTrendChart :commits="stats!.commits" />

      <!-- Bottom Row: Bar Chart and Heatmap -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CommitsBarChart
          :monthly-commits="stats!.monthly_commits"
          :weekly-commits="stats!.weekly_commits"
        />
        <ActivityHeatmap :heatmap-data="stats!.heatmap_data" />
      </div>

      <!-- Time Pattern Heatmap -->
      <TimePatternHeatmap :time-patterns="stats!.time_patterns" />

      <!-- Per-author breakdown -->
      <AuthorBarChart v-if="stats!.authors && stats!.authors.length > 1" :authors="stats!.authors" />
    </div>
  </div>
</template>
