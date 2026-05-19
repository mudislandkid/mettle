<script setup lang="ts">
import { RouterView, RouterLink, useRoute } from 'vue-router'
import { computed } from 'vue'
import { useTheme } from '@/composables/useTheme'

const route = useRoute()
const { theme, toggle: toggleTheme } = useTheme()

const isActive = (path: string) => computed(() => route.path === path)
</script>

<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors">
    <!-- Header -->
    <header class="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 sticky top-0 z-50">
      <div class="max-w-[95%] 2xl:max-w-[90%] mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <div class="flex items-center gap-2">
            <svg class="w-8 h-8 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
            <h1 class="text-xl font-bold text-slate-800 dark:text-slate-100">CodeCounter</h1>
          </div>
          <nav class="flex items-center gap-2">
            <RouterLink
              to="/"
              class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
              :class="isActive('/').value
                ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-800'"
            >
              Analyze
            </RouterLink>
            <RouterLink
              to="/history"
              class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
              :class="isActive('/history').value
                ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-800'"
            >
              History
            </RouterLink>
            <button
              @click="toggleTheme"
              :aria-label="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'"
              :title="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'"
              class="ml-2 p-2 rounded-md text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-300 dark:hover:text-white dark:hover:bg-slate-800 transition-colors"
            >
              <!-- Sun (shown in dark mode) -->
              <svg v-if="theme === 'dark'" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v2m0 14v2m9-9h-2M5 12H3m15.364-6.364l-1.414 1.414M7.05 16.95l-1.414 1.414m12.728 0l-1.414-1.414M7.05 7.05L5.636 5.636M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
              <!-- Moon (shown in light mode) -->
              <svg v-else class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            </button>
          </nav>
        </div>
      </div>
    </header>

    <!-- Main content -->
    <main class="max-w-[95%] 2xl:max-w-[90%] mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <RouterView />
    </main>
  </div>
</template>
