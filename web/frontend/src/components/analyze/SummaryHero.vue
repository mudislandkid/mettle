<script setup lang="ts">
import { computed } from 'vue'
import { TONE, healthBucket } from '@/lib/tone'
import { fmtNum, fmtNumExact } from '@/lib/format'
import type { Analysis } from '@/types'

const props = defineProps<{
  analysis: Analysis
}>()

// Average health across all projects
const avgHealth = computed(() => {
  if (!props.analysis.projects.length) return 0
  const sum = props.analysis.projects.reduce((acc, p) => acc + (p.health_score ?? 0), 0)
  return Math.round(sum / props.analysis.projects.length)
})
const hb = computed(() => healthBucket(avgHealth.value))

// Composition totals derived from projects (Analysis model lacks these aggregates)
const totalCodeLines = computed(() =>
  props.analysis.projects.reduce((s, p) => s + (p.code_lines ?? 0), 0)
)
const totalCommentLines = computed(() =>
  props.analysis.projects.reduce((s, p) => s + (p.comment_lines ?? 0), 0)
)
const totalBlankLines = computed(() =>
  props.analysis.projects.reduce((s, p) => s + (p.blank_lines ?? 0), 0)
)
// Markdown totals — fall back to summing projects when the analysis-level
// aggregate is missing (older analyses without markdown_files/lines fields).
const totalMarkdownFiles = computed(() => {
  if (typeof props.analysis.total_markdown_files === 'number') {
    return props.analysis.total_markdown_files
  }
  return props.analysis.projects.reduce((s, p) => s + (p.markdown_files ?? 0), 0)
})
const totalMarkdownLines = computed(() => {
  if (typeof props.analysis.total_markdown_lines === 'number') {
    return props.analysis.total_markdown_lines
  }
  return props.analysis.projects.reduce((s, p) => s + (p.markdown_lines ?? 0), 0)
})

const compositionTotal = computed(() =>
  totalCodeLines.value + totalCommentLines.value + totalBlankLines.value + totalMarkdownLines.value
)

type Seg = { k: string; n: number; label: string; bar: string; chip: string }
const segs = computed((): Seg[] => [
  { k: 'code',     n: totalCodeLines.value,     label: 'Code',     bar: 'bg-indigo-400', chip: 'text-indigo-300' },
  { k: 'markdown', n: totalMarkdownLines.value, label: 'Markdown', bar: 'bg-violet-400', chip: 'text-violet-300' },
  { k: 'comments', n: totalCommentLines.value,  label: 'Comments', bar: 'bg-sky-400',    chip: 'text-sky-300' },
  { k: 'blank',    n: totalBlankLines.value,    label: 'Blank',    bar: 'bg-slate-500',  chip: 'text-slate-300' },
])

// Risk strip — derived from projects
const staleCount = computed(() =>
  props.analysis.projects.filter((p) => {
    if (p.flags?.includes('archived')) return false
    if (!p.last_commit_at) return true
    return (Date.now() - new Date(p.last_commit_at).getTime()) > 180 * 86_400_000
  }).length
)
const missingLicenseCount = computed(() =>
  props.analysis.projects.filter((p) => !p.license_spdx).length
)
const totalTodos = computed(() =>
  props.analysis.projects.reduce((s, p) => s + (p.todos ?? 0), 0)
)
const totalSecrets = computed(() =>
  props.analysis.projects.reduce((s, p) => s + (p.secrets_found ?? 0), 0)
)

const riskRows = computed((): Array<{ label: string; n: number; tone: import('@/lib/tone').Tone }> => {
  const secretsTone: import('@/lib/tone').Tone  = totalSecrets.value > 0 ? 'rose' : 'slate'
  const staleTone: import('@/lib/tone').Tone    = staleCount.value > 0 ? 'orange' : 'slate'
  const licenseTone: import('@/lib/tone').Tone  = missingLicenseCount.value > 0 ? 'indigo' : 'slate'
  return [
    { label: 'TODOs',           n: totalTodos.value,          tone: 'amber'       },
    { label: 'Secrets',         n: totalSecrets.value,        tone: secretsTone   },
    { label: 'Stale',           n: staleCount.value,          tone: staleTone     },
    { label: 'Missing license', n: missingLicenseCount.value, tone: licenseTone   },
  ]
})

const pct = (n: number) =>
  compositionTotal.value > 0 ? ((n / compositionTotal.value) * 100).toFixed(1) : '0.0'
</script>

<template>
  <div class="rounded-2xl ring-1 ring-slate-800 bg-slate-900/60 overflow-hidden">
    <div class="grid grid-cols-1 lg:grid-cols-[1.3fr_1fr] gap-0">

      <!-- Left: number tiles -->
      <div class="p-5 sm:p-6 grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-4">
        <!-- Projects -->
        <div>
          <div class="text-[28px] font-semibold tabular-nums leading-none text-slate-100">
            {{ analysis.total_projects }}
          </div>
          <div class="text-[10.5px] uppercase tracking-[0.14em] text-slate-500 mt-1.5">Projects</div>
        </div>
        <!-- Files -->
        <div>
          <div class="text-[28px] font-semibold tabular-nums leading-none text-slate-100">
            {{ fmtNum(analysis.total_files) }}
          </div>
          <div class="text-[10.5px] uppercase tracking-[0.14em] text-slate-500 mt-1.5">Files</div>
        </div>
        <!-- Total Lines -->
        <div>
          <div class="text-[28px] font-semibold tabular-nums leading-none text-slate-100">
            {{ fmtNum(analysis.total_lines) }}
          </div>
          <div class="text-[10.5px] uppercase tracking-[0.14em] text-slate-500 mt-1.5">Total lines</div>
        </div>
        <!-- LOC (lines of code) -->
        <div>
          <div class="text-[28px] font-semibold tabular-nums leading-none text-indigo-300">
            {{ fmtNum(analysis.total_code_lines) }}
          </div>
          <div class="text-[10.5px] uppercase tracking-[0.14em] text-slate-500 mt-1.5">LOC</div>
        </div>
        <!-- Markdown Lines -->
        <div>
          <div class="text-[28px] font-semibold tabular-nums leading-none text-violet-300">
            {{ fmtNum(totalMarkdownLines) }}
          </div>
          <div class="text-[10.5px] uppercase tracking-[0.14em] text-slate-500 mt-1.5 flex items-baseline gap-1.5">
            <span>MD lines</span>
            <span v-if="totalMarkdownFiles > 0" class="text-slate-600 normal-case tracking-normal">· {{ totalMarkdownFiles.toLocaleString() }} files</span>
          </div>
        </div>
        <!-- Functions -->
        <div>
          <div class="text-[28px] font-semibold tabular-nums leading-none text-slate-100">
            {{ fmtNum(analysis.total_functions) }}
          </div>
          <div class="text-[10.5px] uppercase tracking-[0.14em] text-slate-500 mt-1.5">Functions</div>
        </div>
        <!-- Classes -->
        <div>
          <div class="text-[28px] font-semibold tabular-nums leading-none text-slate-100">
            {{ fmtNum(analysis.total_classes) }}
          </div>
          <div class="text-[10.5px] uppercase tracking-[0.14em] text-slate-500 mt-1.5">Classes</div>
        </div>
        <!-- Avg Health -->
        <div>
          <div class="text-[28px] font-semibold tabular-nums leading-none">
            <span class="flex items-baseline gap-1.5">
              <span :class="TONE[hb.tone].text">{{ avgHealth }}</span>
              <span class="text-[12px] uppercase tracking-[0.1em] text-slate-500">{{ hb.label }}</span>
            </span>
          </div>
          <div class="text-[10.5px] uppercase tracking-[0.14em] text-slate-500 mt-1.5">Avg health</div>
        </div>
      </div>

      <!-- Right: composition bar + risk strip -->
      <div class="p-5 sm:p-6 border-t lg:border-t-0 lg:border-l border-slate-800 bg-slate-950/30 space-y-5">

        <!-- Composition bar -->
        <div>
          <div class="flex items-baseline justify-between mb-2">
            <span class="text-[11px] uppercase tracking-[0.14em] text-slate-500 font-semibold">Composition</span>
            <span class="text-[11px] text-slate-500 tabular-nums">{{ fmtNumExact(compositionTotal) }} lines</span>
          </div>
          <div class="h-1.5 w-full flex rounded-full overflow-hidden bg-slate-800">
            <div
              v-for="s in segs"
              :key="s.k"
              :class="s.bar"
              :style="{ width: `${compositionTotal > 0 ? (s.n / compositionTotal) * 100 : 0}%` }"
              :title="`${s.label}: ${s.n.toLocaleString()}`"
            />
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
            <div v-for="s in segs" :key="s.k" class="flex items-baseline gap-2">
              <span class="w-1.5 h-3 rounded-sm" :class="s.bar" />
              <div class="leading-tight">
                <div class="text-[13px] tabular-nums text-slate-100 font-medium">{{ fmtNumExact(s.n) }}</div>
                <div class="text-[10px] uppercase tracking-[0.08em] text-slate-500">
                  {{ s.label }} · {{ pct(s.n) }}%
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Risk strip -->
        <div>
          <div class="flex items-baseline justify-between mb-2">
            <span class="text-[11px] uppercase tracking-[0.14em] text-slate-500 font-semibold">Risk signals</span>
            <span class="text-[11px] text-slate-500">across {{ analysis.total_projects }} projects</span>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div
              v-for="r in riskRows"
              :key="r.label"
              class="rounded-md ring-1 ring-inset px-3 py-2"
              :class="[TONE[r.tone].ring, TONE[r.tone].bg]"
            >
              <div class="text-[18px] font-semibold tabular-nums" :class="TONE[r.tone].text">{{ r.n }}</div>
              <div class="text-[10px] uppercase tracking-[0.1em] text-slate-500 mt-0.5">{{ r.label }}</div>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>
