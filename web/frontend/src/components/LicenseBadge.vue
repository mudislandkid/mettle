<script setup lang="ts">
defineProps<{
  spdx: string | null
}>()

const colourFor = (id: string | null): string => {
  if (!id) return 'text-zinc-500 border-zinc-700/50 bg-zinc-800/40'
  if (['MIT', 'Apache-2.0', 'BSD-3-Clause', 'ISC', '0BSD', 'BSD-2-Clause'].includes(id)) {
    return 'text-emerald-300 border-emerald-700/50 bg-emerald-900/40'
  }
  if (id.startsWith('GPL') || id.startsWith('AGPL') || id.startsWith('LGPL')) {
    return 'text-amber-300 border-amber-700/50 bg-amber-900/40'
  }
  return 'text-sky-300 border-sky-700/50 bg-sky-900/40'
}
</script>

<template>
  <span
    class="inline-block rounded px-2 py-0.5 text-xs font-mono border"
    :class="colourFor(spdx)"
    :title="spdx ?? 'License not detected'"
  >{{ spdx ?? '—' }}</span>
</template>
