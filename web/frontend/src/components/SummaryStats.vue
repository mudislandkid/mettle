<script setup lang="ts">
import type { Analysis } from '@/types'

defineProps<{
  analysis: Analysis
}>()

function formatNumber(n: number): string {
  return n.toLocaleString()
}
</script>

<template>
  <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
    <!-- Projects Card -->
    <div class="relative overflow-hidden rounded-xl shadow-md hover:shadow-lg transition-shadow duration-200 bg-gradient-to-br from-indigo-50 to-white border border-indigo-100 p-5">
      <div class="relative z-10">
        <div class="text-3xl font-bold text-indigo-600 mb-1 dark:text-indigo-400">
          {{ formatNumber(analysis.total_projects) }}
        </div>
        <div class="text-sm font-medium text-indigo-700 dark:text-indigo-300">Projects</div>
      </div>
      <div class="absolute top-0 right-0 -mt-2 -mr-2 h-20 w-20 rounded-full bg-indigo-100 opacity-20"></div>
    </div>

    <!-- Files Card -->
    <div class="relative overflow-hidden rounded-xl shadow-md hover:shadow-lg transition-shadow duration-200 bg-gradient-to-br from-emerald-50 to-white border border-emerald-100 p-5">
      <div class="relative z-10">
        <div class="text-3xl font-bold text-emerald-600 mb-1">
          {{ formatNumber(analysis.total_files) }}
        </div>
        <div class="text-sm font-medium text-emerald-700">Files</div>
      </div>
      <div class="absolute top-0 right-0 -mt-2 -mr-2 h-20 w-20 rounded-full bg-emerald-100 opacity-20"></div>
    </div>

    <!-- Total Lines Card -->
    <div class="relative overflow-hidden rounded-xl shadow-md hover:shadow-lg transition-shadow duration-200 bg-gradient-to-br from-blue-50 to-white border border-blue-100 p-5">
      <div class="relative z-10">
        <div class="text-3xl font-bold text-blue-600 mb-1">
          {{ formatNumber(analysis.total_lines) }}
        </div>
        <div class="text-sm font-medium text-blue-700">Total Lines</div>
      </div>
      <div class="absolute top-0 right-0 -mt-2 -mr-2 h-20 w-20 rounded-full bg-blue-100 opacity-20"></div>
    </div>

    <!-- Code Lines Card -->
    <div class="relative overflow-hidden rounded-xl shadow-md hover:shadow-lg transition-shadow duration-200 bg-gradient-to-br from-purple-50 to-white border border-purple-100 p-5">
      <div class="relative z-10">
        <div class="text-3xl font-bold text-purple-600 mb-1">
          {{ formatNumber(analysis.total_code_lines) }}
        </div>
        <div class="text-sm font-medium text-purple-700">Code Lines</div>
      </div>
      <div class="absolute top-0 right-0 -mt-2 -mr-2 h-20 w-20 rounded-full bg-purple-100 opacity-20"></div>
    </div>

    <!-- Functions Card -->
    <div class="relative overflow-hidden rounded-xl shadow-md hover:shadow-lg transition-shadow duration-200 bg-gradient-to-br from-orange-50 to-white border border-orange-100 p-5">
      <div class="relative z-10">
        <div class="text-3xl font-bold text-orange-600 mb-1">
          {{ formatNumber(analysis.total_functions) }}
        </div>
        <div class="text-sm font-medium text-orange-700">Functions</div>
      </div>
      <div class="absolute top-0 right-0 -mt-2 -mr-2 h-20 w-20 rounded-full bg-orange-100 opacity-20"></div>
    </div>

    <!-- Classes Card -->
    <div class="relative overflow-hidden rounded-xl shadow-md hover:shadow-lg transition-shadow duration-200 bg-gradient-to-br from-pink-50 to-white border border-pink-100 p-5">
      <div class="relative z-10">
        <div class="text-3xl font-bold text-pink-600 mb-1">
          {{ formatNumber(analysis.total_classes) }}
        </div>
        <div class="text-sm font-medium text-pink-700">Classes</div>
      </div>
      <div class="absolute top-0 right-0 -mt-2 -mr-2 h-20 w-20 rounded-full bg-pink-100 opacity-20"></div>
    </div>
  </div>
</template>
