<script setup lang="ts">
import { managerPill } from '@/lib/tone'

interface DepEntry { name: string; manager: string; from?: string; to?: string }
interface Extra {
  added?: DepEntry[]
  removed?: DepEntry[]
  bumped?: DepEntry[]
}

const props = defineProps<{ extra: Extra | null }>()

const added = (): DepEntry[] => props.extra?.added ?? []
const removed = (): DepEntry[] => props.extra?.removed ?? []
const bumped = (): DepEntry[] => props.extra?.bumped ?? []
</script>

<template>
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 pt-4 border-t border-slate-800">
    <!-- ADDED -->
    <div>
      <div class="flex items-center gap-2 mb-2">
        <span class="text-[10px] font-semibold tracking-[0.12em] text-emerald-400 uppercase">Added</span>
        <span class="text-[11px] tabular-nums text-slate-500">{{ added().length }}</span>
      </div>
      <ul class="space-y-1">
        <li v-if="added().length === 0" class="text-[11px] italic text-slate-500">none</li>
        <li v-for="d in added()" :key="`a-${d.manager}-${d.name}`"
            class="flex items-center gap-2 text-[12px] font-mono">
          <span :class="`shrink-0 px-1.5 py-[1px] rounded text-[9px] font-sans font-semibold tracking-wider uppercase ring-1 ring-inset ${managerPill(d.manager)}`">
            {{ d.manager }}
          </span>
          <span class="flex-1 min-w-0 text-slate-200 truncate">{{ d.name }}</span>
        </li>
      </ul>
    </div>
    <!-- REMOVED -->
    <div>
      <div class="flex items-center gap-2 mb-2">
        <span class="text-[10px] font-semibold tracking-[0.12em] text-rose-400 uppercase">Removed</span>
        <span class="text-[11px] tabular-nums text-slate-500">{{ removed().length }}</span>
      </div>
      <ul class="space-y-1">
        <li v-if="removed().length === 0" class="text-[11px] italic text-slate-500">none</li>
        <li v-for="d in removed()" :key="`r-${d.manager}-${d.name}`"
            class="flex items-center gap-2 text-[12px] font-mono">
          <span :class="`shrink-0 px-1.5 py-[1px] rounded text-[9px] font-sans font-semibold tracking-wider uppercase ring-1 ring-inset ${managerPill(d.manager)}`">
            {{ d.manager }}
          </span>
          <span class="flex-1 min-w-0 text-slate-200 truncate line-through decoration-rose-400/40">{{ d.name }}</span>
        </li>
      </ul>
    </div>
    <!-- BUMPED -->
    <div>
      <div class="flex items-center gap-2 mb-2">
        <span class="text-[10px] font-semibold tracking-[0.12em] text-amber-400 uppercase">Bumped</span>
        <span class="text-[11px] tabular-nums text-slate-500">{{ bumped().length }}</span>
      </div>
      <ul class="space-y-1">
        <li v-if="bumped().length === 0" class="text-[11px] italic text-slate-500">none</li>
        <li v-for="d in bumped()" :key="`b-${d.manager}-${d.name}`"
            class="flex items-center gap-2 text-[12px] font-mono">
          <span :class="`shrink-0 px-1.5 py-[1px] rounded text-[9px] font-sans font-semibold tracking-wider uppercase ring-1 ring-inset ${managerPill(d.manager)}`">
            {{ d.manager }}
          </span>
          <span class="flex-1 min-w-0 text-slate-200 truncate">{{ d.name }}</span>
          <span class="shrink-0 text-[11px] text-slate-500 tabular-nums whitespace-nowrap">
            {{ d.from }}<span class="text-slate-600 px-1">→</span><span class="text-amber-300">{{ d.to }}</span>
          </span>
        </li>
      </ul>
    </div>
  </div>
</template>
