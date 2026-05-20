<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

const props = withDefaults(defineProps<{
  logs: string[]
  shimmer?: boolean
}>(), {
  shimmer: true,
})

const consoleEl = ref<HTMLElement | null>(null)

// Auto-scroll on new logs
watch(
  () => props.logs.length,
  async () => {
    await nextTick()
    if (consoleEl.value) {
      consoleEl.value.scrollTop = consoleEl.value.scrollHeight
    }
  },
)

function lineClass(line: string): string {
  if (/^[⚠Ww]arn|⚠/.test(line)) return 'text-amber-300'
  if (/^\[\d+\/\d+\]/.test(line))  return 'text-sky-300'
  return 'text-emerald-300'
}

function padLine(i: number): string {
  return String(i + 1).padStart(3, '0')
}
</script>

<template>
  <div class="rounded-2xl ring-1 ring-slate-800 bg-slate-950 overflow-hidden">
    <!-- Title bar -->
    <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-800 bg-slate-900/50">
      <div class="flex items-center gap-2">
        <div class="flex gap-1.5">
          <span class="w-2.5 h-2.5 rounded-full bg-rose-500/60" />
          <span class="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
          <span class="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
        </div>
        <span class="text-[10px] uppercase tracking-[0.14em] text-slate-500 font-semibold ml-2">
          Console
        </span>
      </div>
      <span class="text-[10.5px] text-slate-500 tabular-nums">
        {{ logs.length }} lines · auto-scroll
      </span>
    </div>

    <!-- Log body -->
    <div
      ref="consoleEl"
      class="max-h-72 overflow-y-auto px-4 py-3 font-mono text-[12px] leading-relaxed space-y-0.5"
    >
      <div
        v-for="(line, i) in logs"
        :key="i"
        class="flex gap-2 whitespace-pre-wrap"
      >
        <span class="text-slate-600 select-none w-7 text-right shrink-0 tabular-nums">
          {{ padLine(i) }}
        </span>
        <span :class="lineClass(line)">{{ line }}</span>
      </div>

      <!-- Shimmer cursor -->
      <div v-if="shimmer" class="flex gap-2">
        <span class="text-slate-600 select-none w-7 text-right tabular-nums">
          {{ padLine(logs.length) }}
        </span>
        <span class="text-emerald-300">▍</span>
      </div>
    </div>
  </div>
</template>
