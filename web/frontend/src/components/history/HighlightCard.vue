<script setup lang="ts">
import { TONE } from '@/lib/tone'
import { fmtNum, fmtRelative } from '@/lib/format'
import type { ProjectHighlight } from '@/types'

type Kind = 'biggest' | 'stalest' | 'todo_heavy' | 'lowest_health'

const props = defineProps<{
  kind: Kind
  items: ProjectHighlight[]
}>()

interface Meta {
  title: string
  sub: string
  tone: keyof typeof TONE
  key: 'lines' | 'commit' | 'todos' | 'health'
}

const HIGHLIGHT_META: Record<Kind, Meta> = {
  biggest:       { title: 'Biggest projects',  sub: 'Most total lines',                  tone: 'indigo',  key: 'lines'  },
  stalest:       { title: 'Stalest projects',  sub: 'Oldest last-commit',                tone: 'rose',    key: 'commit' },
  todo_heavy:    { title: 'Most TODOs',        sub: 'Open TODO / FIXME markers',         tone: 'amber',   key: 'todos'  },
  lowest_health: { title: 'Lowest health',     sub: 'Composite health score, ascending', tone: 'orange',  key: 'health' },
}

const meta = HIGHLIGHT_META[props.kind]
const t = TONE[meta.tone]

function metricValue(p: ProjectHighlight): string {
  if (meta.key === 'lines')  return fmtNum(p.total_lines)
  if (meta.key === 'commit') return fmtRelative(p.last_commit_at)
  if (meta.key === 'todos')  return String(p.todos)
  return Math.round(p.health_score).toString()
}
</script>

<template>
  <section class="rounded-xl ring-1 ring-slate-800 bg-slate-900/60 overflow-hidden">
    <!-- Header -->
    <header class="flex items-center gap-2.5 px-4 pt-4 pb-3">
      <!-- Icon badge -->
      <div
        class="w-7 h-7 rounded-md ring-1 ring-inset flex items-center justify-center shrink-0"
        :class="[t.ring, t.bg, t.text]"
      >
        <!-- biggest: stacked lines -->
        <svg v-if="kind === 'biggest'" viewBox="0 0 20 20" fill="none" width="16" height="16">
          <path d="M3 4h14v3H3zM3 9h14v3H3zM3 14h9v3H3z" fill="currentColor" opacity=".9"/>
        </svg>
        <!-- stalest: clock -->
        <svg v-else-if="kind === 'stalest'" viewBox="0 0 20 20" fill="none" width="16" height="16">
          <circle cx="10" cy="10" r="6.5" stroke="currentColor" stroke-width="1.75"/>
          <path d="M10 6.5V10l2.5 1.5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
        </svg>
        <!-- todo_heavy: list lines -->
        <svg v-else-if="kind === 'todo_heavy'" viewBox="0 0 20 20" fill="none" width="16" height="16">
          <path d="M4 5h12M4 10h12M4 15h7" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
        </svg>
        <!-- lowest_health: heart -->
        <svg v-else viewBox="0 0 20 20" fill="none" width="16" height="16">
          <path
            d="M10 17S3.5 12.5 3.5 8a4 4 0 017-2.6A4 4 0 0117.5 8c0 4.5-7.5 9-7.5 9z"
            stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"
          />
        </svg>
      </div>

      <div>
        <h3 class="text-[13.5px] font-semibold text-slate-100 leading-tight">{{ meta.title }}</h3>
        <p class="text-[10.5px] text-slate-500">{{ meta.sub }}</p>
      </div>
    </header>

    <!-- Numbered list -->
    <ol class="px-4 pb-4 space-y-1">
      <li
        v-for="(p, i) in items"
        :key="p.id"
        class="flex items-center gap-2 text-[12.5px]"
      >
        <span class="w-4 text-right tabular-nums text-slate-600 text-[10.5px] shrink-0">
          {{ i + 1 }}
        </span>
        <router-link
          :to="{ name: 'project-detail', params: { id: p.id } }"
          class="flex-1 min-w-0 text-slate-200 hover:text-indigo-300 truncate transition-colors"
          :title="p.path"
        >
          {{ p.name }}
        </router-link>
        <span
          class="shrink-0 tabular-nums text-[12px] font-semibold"
          :class="t.text"
        >
          {{ metricValue(p) }}
        </span>
      </li>

      <li v-if="!items.length" class="text-[12px] text-slate-500 italic">
        No data yet.
      </li>
    </ol>
  </section>
</template>
