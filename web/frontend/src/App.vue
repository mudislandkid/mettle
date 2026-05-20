<script setup lang="ts">
import { RouterView, RouterLink, useRoute } from 'vue-router'
import { computed } from 'vue'
import TokenPrompt from './components/TokenPrompt.vue'

const route = useRoute()

const navLinks = [
  { label: 'Analyze', to: '/' },
  { label: 'History', to: '/history' },
  { label: 'Digest', to: '/digest' },
]

const isActive = (path: string) =>
  computed(() =>
    path === '/'
      ? route.path === '/'
      : route.path.startsWith(path)
  )
</script>

<template>
  <TokenPrompt />
  <div class="min-h-screen bg-slate-950 text-slate-200">

    <!-- Sticky header -->
    <header class="sticky top-0 z-40 border-b border-slate-800 bg-slate-900/80 backdrop-blur supports-[backdrop-filter]:bg-slate-900/70">
      <div class="max-w-[95%] 2xl:max-w-[90%] mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">

          <!-- Logo -->
          <div class="flex items-center gap-2">
            <svg class="w-7 h-7 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
            <h1 class="text-xl font-bold text-slate-100">Mettle</h1>
          </div>

          <!-- Nav + theme toggle -->
          <nav class="flex items-center gap-1">
            <RouterLink
              v-for="link in navLinks"
              :key="link.to"
              :to="link.to"
              class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
              :class="isActive(link.to).value
                ? 'bg-indigo-500/20 text-indigo-300'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'"
            >
              {{ link.label }}
            </RouterLink>

            <!-- Theme toggle — visual placeholder; light mode wired in Phase E -->
            <button
              class="ml-2 p-2 rounded-md text-slate-300 hover:bg-slate-800 transition-colors"
              aria-label="Toggle theme"
            >
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M12 3v2m0 14v2m9-9h-2M5 12H3m15.364-6.364l-1.414 1.414M7.05 16.95l-1.414 1.414m12.728 0l-1.414-1.414M7.05 7.05L5.636 5.636M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            </button>
          </nav>

        </div>
      </div>
    </header>

    <!-- Main content with ambient glow -->
    <main class="ambient">
      <div class="max-w-[95%] 2xl:max-w-[90%] mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <RouterView />
      </div>
    </main>

  </div>
</template>
