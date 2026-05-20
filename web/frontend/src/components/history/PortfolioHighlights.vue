<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getProjectHighlights } from '@/api/projects'
import type { ProjectHighlights } from '@/types'
import HighlightCard from './HighlightCard.vue'

const highlights = ref<ProjectHighlights | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    highlights.value = await getProjectHighlights(5)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

onMounted(load)

defineExpose({ reload: load })
</script>

<template>
  <section>
    <!-- Section heading -->
    <div class="flex items-baseline justify-between mb-3">
      <div>
        <h2 class="text-[15px] font-semibold text-slate-100">Portfolio highlights</h2>
        <p class="text-[12px] text-slate-500">
          Across every completed analysis · latest snapshot per project.
        </p>
      </div>
    </div>

    <!-- Loading -->
    <div
      v-if="loading"
      class="rounded-xl ring-1 ring-slate-800 bg-slate-900/40 px-6 py-10 text-center text-[13px] text-slate-400"
    >
      Loading highlights…
    </div>

    <!-- Error -->
    <div
      v-else-if="error"
      class="rounded-xl ring-1 ring-rose-500/30 bg-rose-500/10 px-6 py-10 text-center text-[13px] text-rose-300"
    >
      {{ error }}
    </div>

    <!-- Grid -->
    <div
      v-else-if="highlights"
      class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3"
    >
      <HighlightCard kind="biggest"       :items="highlights.biggest" />
      <HighlightCard kind="stalest"       :items="highlights.stalest" />
      <HighlightCard kind="todo_heavy"    :items="highlights.todo_heavy" />
      <HighlightCard kind="lowest_health" :items="highlights.lowest_health" />
    </div>
  </section>
</template>
