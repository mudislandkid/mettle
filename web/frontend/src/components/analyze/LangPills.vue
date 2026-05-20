<script setup lang="ts">
import { TONE, LANG_TONE } from '@/lib/tone'

defineProps<{
  languages: string[]
  max?: number
}>()
</script>

<template>
  <div class="flex flex-wrap gap-1">
    <span
      v-for="lang in languages.slice(0, max ?? languages.length)"
      :key="lang"
      class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ring-1 ring-inset"
      :class="[
        TONE[LANG_TONE[lang] ?? 'slate'].bg,
        TONE[LANG_TONE[lang] ?? 'slate'].text,
        TONE[LANG_TONE[lang] ?? 'slate'].ring,
      ]"
    >
      <span
        class="w-1.5 h-1.5 rounded-full"
        :class="TONE[LANG_TONE[lang] ?? 'slate'].bar"
      />
      {{ lang }}
    </span>
    <span
      v-if="max != null && languages.length > max"
      class="text-[10px] text-slate-500"
    >+{{ languages.length - max }}</span>
  </div>
</template>
