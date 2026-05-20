<script setup lang="ts">
import { computed } from 'vue'
import type { DigestSectionKind } from '@/types'
import { fmtCalendarLong } from '@/lib/format'

interface Extra {
  last_commit_at?: string
  last_analyzed_at?: string
  first_analyzed_at?: string
  days_stale?: number
}

const props = defineProps<{
  extra: Extra | null
  kind: DigestSectionKind
}>()

const rows = computed(() => {
  if (!props.extra) return []
  const out: Array<{ label: string; value: string }> = []
  if (props.extra.last_commit_at) out.push({ label: 'Last commit', value: fmtCalendarLong(props.extra.last_commit_at) })
  if (props.extra.last_analyzed_at) out.push({ label: 'Last analyzed', value: fmtCalendarLong(props.extra.last_analyzed_at) })
  if (props.extra.first_analyzed_at) out.push({ label: 'First analyzed', value: fmtCalendarLong(props.extra.first_analyzed_at) })
  if (typeof props.extra.days_stale === 'number') out.push({ label: 'Days quiet', value: `${props.extra.days_stale} days` })
  return out
})
</script>

<template>
  <dl v-if="rows.length > 0"
      class="mt-3 pt-3 border-t border-slate-800 grid grid-cols-2 gap-x-6 gap-y-1.5 text-[12px]">
    <div v-for="r in rows" :key="r.label" class="flex items-baseline justify-between gap-3">
      <dt class="text-slate-500">{{ r.label }}</dt>
      <dd class="text-slate-300 tabular-nums">{{ r.value }}</dd>
    </div>
  </dl>
</template>
