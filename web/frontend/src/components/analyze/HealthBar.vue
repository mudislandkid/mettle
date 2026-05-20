<script setup lang="ts">
import { computed } from 'vue'
import { TONE, healthBucket } from '@/lib/tone'

const props = defineProps<{
  score: number | null | undefined
}>()

const hb = computed(() => healthBucket(props.score))
const pct = computed(() => Math.round(props.score ?? 0))
</script>

<template>
  <div class="flex items-center gap-2.5">
    <div class="relative h-1.5 w-16 rounded-full bg-slate-800 overflow-hidden">
      <div
        class="absolute inset-y-0 left-0 transition-[width]"
        :class="TONE[hb.tone].bar"
        :style="{ width: `${pct}%` }"
      />
    </div>
    <span
      class="text-[13px] font-semibold tabular-nums w-7 text-right"
      :class="TONE[hb.tone].text"
    >{{ pct }}</span>
  </div>
</template>
