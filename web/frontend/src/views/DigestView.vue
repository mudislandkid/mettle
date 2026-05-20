<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useDigest } from '@/composables/useDigest'
import { KIND_STYLE } from '@/lib/tone'
import DigestHeader from '@/components/digest/DigestHeader.vue'
import DigestSection from '@/components/digest/DigestSection.vue'

const d = useDigest({ since: '7d', top: 5, staleDays: 30 })

onMounted(() => d.load())

// Debounce param changes
let timer: number | undefined
watch([d.since, d.top, d.staleDays], () => {
  if (timer) window.clearTimeout(timer)
  timer = window.setTimeout(() => d.load(), 80)
})
</script>

<template>
  <div v-if="d.loading.value && !d.report.value" class="py-12 text-center text-slate-400">Loading…</div>
  <div v-else-if="d.error.value" class="py-12 text-center text-rose-300">{{ d.error.value }}</div>
  <div v-else-if="d.report.value" class="space-y-8">
    <DigestHeader
      :report="d.report.value"
      :since="d.since.value"
      :top="d.top.value"
      :stale-days="d.staleDays.value"
      :loading="d.loading.value"
      @update:since="d.since.value = $event"
      @update:top="d.top.value = $event"
      @update:stale-days="d.staleDays.value = $event"
      @refresh="d.load()"
    />

    <!-- Narrative sections — two-column on wide viewports -->
    <div class="grid grid-cols-1 xl:grid-cols-2 gap-5">
      <DigestSection
        v-for="s in d.report.value.sections.filter((sec) => KIND_STYLE[sec.kind]?.tone !== 'coverage')"
        :key="s.kind"
        :section="s"
      />
    </div>

    <!-- Coverage sections — separated by a divider -->
    <div class="space-y-4">
      <div class="flex items-center gap-3">
        <span class="h-px flex-1 bg-slate-800"/>
        <span class="text-[10px] uppercase tracking-[0.18em] text-slate-500 font-semibold">Portfolio coverage</span>
        <span class="h-px flex-1 bg-slate-800"/>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <DigestSection
          v-for="s in d.report.value.sections.filter((sec) => KIND_STYLE[sec.kind]?.tone === 'coverage')"
          :key="s.kind"
          :section="s"
        />
      </div>
    </div>

    <!-- Footer -->
    <footer class="pt-6 border-t border-slate-800/60 flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
      <span>Powered by <span class="text-slate-300 font-semibold">Mettle</span> · cross-project digest</span>
      <span class="text-slate-700">·</span>
      <span>7 sections, fixed order</span>
      <span class="text-slate-700">·</span>
      <span>Read-only computation — no DB writes</span>
      <span class="ml-auto font-mono">generated_at: {{ d.report.value.generated_at }}</span>
    </footer>
  </div>
</template>
