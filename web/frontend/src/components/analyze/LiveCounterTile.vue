<script setup lang="ts">
import { computed } from 'vue'
import { TONE } from '@/lib/tone'
import type { Tone } from '@/lib/tone'

const props = withDefaults(defineProps<{
  label: string
  value: number | string
  tone?: Tone
}>(), {
  tone: 'slate',
})

const t = computed(() => TONE[props.tone] ?? TONE.slate)
</script>

<template>
  <div
    :class="[
      'rounded-lg ring-1 ring-inset px-3 py-2.5 flex items-center gap-3',
      t.ring,
      t.bg,
    ]"
  >
    <!-- Icon slot -->
    <div
      :class="[
        'w-7 h-7 rounded-md flex items-center justify-center bg-slate-950/40',
        t.text,
      ]"
    >
      <slot name="icon" />
    </div>

    <div class="min-w-0">
      <div :class="['text-[18px] font-semibold tabular-nums leading-none', t.text]">
        {{ value }}
      </div>
      <div class="text-[10px] uppercase tracking-[0.12em] text-slate-500 mt-1">
        {{ label }}
      </div>
    </div>
  </div>
</template>
