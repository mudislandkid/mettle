<script setup lang="ts">
import { ref, computed } from 'vue'
import { TONE } from '@/lib/tone'
import type { Project } from '@/types'
import ProjectTableRow from './ProjectTableRow.vue'

const props = defineProps<{
  projects: Project[]
}>()

// ─── State ─────────────────────────────────────────────────────────────────
const search      = ref('')
const sortKey     = ref<string>('health_score')
const sortDir     = ref<'asc' | 'desc'>('asc')
const activeFilters = ref<Record<string, boolean>>({})
const selected    = ref<Set<number>>(new Set())

// ─── Helpers ───────────────────────────────────────────────────────────────
function isStale(p: Project): boolean {
  if (p.flags?.includes('archived')) return false
  if (!p.last_commit_at) return true
  return (Date.now() - new Date(p.last_commit_at).getTime()) > 180 * 86_400_000
}

function toggleFilter(k: string) {
  activeFilters.value = { ...activeFilters.value, [k]: !activeFilters.value[k] }
}

function clickSort(k: string) {
  if (sortKey.value === k) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = k
    sortDir.value = k === 'name' ? 'asc' : 'desc'
  }
}

function toggleSelect(id: number) {
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
}

// ─── Derived ───────────────────────────────────────────────────────────────
const maxLines = computed(() =>
  Math.max(1, ...props.projects.map((p) => p.total_lines))
)

const counts = computed(() => ({
  stale:      props.projects.filter(isStale).length,
  lowHealth:  props.projects.filter((p) => p.health_score < 60).length,
  hasSecrets: props.projects.filter((p) => (p.secrets_found ?? 0) > 0).length,
  noLicense:  props.projects.filter((p) => !p.license_spdx).length,
  noTests:    props.projects.filter((p) => (p.test_percentage ?? 0) < 1).length,
}))

const filtered = computed(() => {
  let arr = [...props.projects]
  const q = search.value.toLowerCase().trim()

  if (q) {
    arr = arr.filter((p) =>
      p.name.toLowerCase().includes(q) ||
      p.path.toLowerCase().includes(q) ||
      p.languages.some((l) => l.toLowerCase().includes(q))
    )
  }
  if (activeFilters.value.stale)      arr = arr.filter(isStale)
  if (activeFilters.value.lowHealth)  arr = arr.filter((p) => p.health_score < 60)
  if (activeFilters.value.hasSecrets) arr = arr.filter((p) => (p.secrets_found ?? 0) > 0)
  if (activeFilters.value.noLicense)  arr = arr.filter((p) => !p.license_spdx)
  if (activeFilters.value.noTests)    arr = arr.filter((p) => (p.test_percentage ?? 0) < 1)

  arr.sort((a, b) => {
    let av: string | number, bv: string | number
    if (sortKey.value === 'name') { av = a.name; bv = b.name }
    else { av = (a as unknown as Record<string, number>)[sortKey.value] ?? 0; bv = (b as unknown as Record<string, number>)[sortKey.value] ?? 0 }
    if (typeof av === 'string') return sortDir.value === 'asc' ? av.localeCompare(bv as string) : (bv as string).localeCompare(av)
    return sortDir.value === 'asc' ? (av as number) - (bv as number) : (bv as number) - (av as number)
  })
  return arr
})

const allSelected = computed(() =>
  filtered.value.length > 0 && filtered.value.every((p) => selected.value.has(p.id))
)

function toggleSelectAll() {
  if (allSelected.value) {
    selected.value = new Set()
  } else {
    selected.value = new Set(filtered.value.map((p) => p.id))
  }
}

function clearFilters() {
  search.value = ''
  activeFilters.value = {}
}
</script>

<template>
  <div class="rounded-2xl ring-1 ring-slate-800 bg-slate-900/50 overflow-hidden">

    <!-- Toolbar -->
    <div class="border-b border-slate-800 px-4 sm:px-5 py-3 flex flex-col gap-3">
      <!-- Search row -->
      <div class="flex items-center gap-3 flex-wrap">
        <div class="relative flex-1 min-w-[200px]">
          <svg width="14" height="14" viewBox="0 0 20 20" fill="none"
            class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500">
            <circle cx="9" cy="9" r="5" stroke="currentColor" stroke-width="1.75"/>
            <path d="M13 13l3 3" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
          </svg>
          <input
            v-model="search"
            type="text"
            placeholder="Search by project name, path, or language…"
            class="w-full rounded-md ring-1 ring-inset ring-slate-700 bg-slate-950/60 pl-8 pr-3 py-1.5 text-[13px] text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-indigo-500/60"
          />
        </div>
        <div class="text-[11.5px] text-slate-500 tabular-nums">
          <template v-if="filtered.length === projects.length">
            <span>{{ projects.length }} projects</span>
          </template>
          <template v-else>
            <span class="text-slate-300">{{ filtered.length }}</span> of {{ projects.length }}
          </template>
        </div>
      </div>

      <!-- Filter chips -->
      <div class="flex items-center gap-1.5 flex-wrap">
        <span class="text-[10px] uppercase tracking-[0.12em] text-slate-500 font-semibold mr-1">Quick filters:</span>
        <!-- Health < 60 -->
        <button
          class="group inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11.5px] font-medium ring-1 ring-inset transition-colors"
          :class="activeFilters.lowHealth
            ? `${TONE.amber.bg} ${TONE.amber.text} ${TONE.amber.ring}`
            : 'ring-slate-800 bg-slate-900 text-slate-400 hover:text-slate-100 hover:ring-slate-700'"
          @click="toggleFilter('lowHealth')"
        >
          <span>Health &lt; 60</span>
          <span class="tabular-nums text-[10px] px-1 rounded" :class="activeFilters.lowHealth ? 'bg-slate-950/40' : 'bg-slate-800'">{{ counts.lowHealth }}</span>
        </button>
        <!-- Has secrets -->
        <button
          class="group inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11.5px] font-medium ring-1 ring-inset transition-colors"
          :class="activeFilters.hasSecrets
            ? `${TONE.rose.bg} ${TONE.rose.text} ${TONE.rose.ring}`
            : 'ring-slate-800 bg-slate-900 text-slate-400 hover:text-slate-100 hover:ring-slate-700'"
          @click="toggleFilter('hasSecrets')"
        >
          <span>Has secrets</span>
          <span class="tabular-nums text-[10px] px-1 rounded" :class="activeFilters.hasSecrets ? 'bg-slate-950/40' : 'bg-slate-800'">{{ counts.hasSecrets }}</span>
        </button>
        <!-- Stale -->
        <button
          class="group inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11.5px] font-medium ring-1 ring-inset transition-colors"
          :class="activeFilters.stale
            ? `${TONE.orange.bg} ${TONE.orange.text} ${TONE.orange.ring}`
            : 'ring-slate-800 bg-slate-900 text-slate-400 hover:text-slate-100 hover:ring-slate-700'"
          @click="toggleFilter('stale')"
        >
          <span>Stale</span>
          <span class="tabular-nums text-[10px] px-1 rounded" :class="activeFilters.stale ? 'bg-slate-950/40' : 'bg-slate-800'">{{ counts.stale }}</span>
        </button>
        <!-- No license -->
        <button
          class="group inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11.5px] font-medium ring-1 ring-inset transition-colors"
          :class="activeFilters.noLicense
            ? `${TONE.indigo.bg} ${TONE.indigo.text} ${TONE.indigo.ring}`
            : 'ring-slate-800 bg-slate-900 text-slate-400 hover:text-slate-100 hover:ring-slate-700'"
          @click="toggleFilter('noLicense')"
        >
          <span>No license</span>
          <span class="tabular-nums text-[10px] px-1 rounded" :class="activeFilters.noLicense ? 'bg-slate-950/40' : 'bg-slate-800'">{{ counts.noLicense }}</span>
        </button>
        <!-- No tests -->
        <button
          class="group inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11.5px] font-medium ring-1 ring-inset transition-colors"
          :class="activeFilters.noTests
            ? `${TONE.sky.bg} ${TONE.sky.text} ${TONE.sky.ring}`
            : 'ring-slate-800 bg-slate-900 text-slate-400 hover:text-slate-100 hover:ring-slate-700'"
          @click="toggleFilter('noTests')"
        >
          <span>No tests</span>
          <span class="tabular-nums text-[10px] px-1 rounded" :class="activeFilters.noTests ? 'bg-slate-950/40' : 'bg-slate-800'">{{ counts.noTests }}</span>
        </button>
      </div>

      <!-- Bulk action bar -->
      <div
        v-if="selected.size > 0"
        class="flex flex-wrap items-center gap-2 px-3 py-2 rounded-lg bg-indigo-500/10 ring-1 ring-inset ring-indigo-500/30"
      >
        <span class="text-[12px] font-semibold text-indigo-200">{{ selected.size }} selected</span>
        <button
          class="text-[11px] text-indigo-300 hover:text-indigo-100 underline underline-offset-2"
          @click="selected = new Set()"
        >Clear</button>
        <span class="text-slate-600">·</span>
        <button class="px-2 py-1 text-[11px] rounded-md bg-slate-900/70 text-slate-200 ring-1 ring-inset ring-slate-700 hover:ring-slate-600">
          Add tag…
        </button>
        <button class="px-2 py-1 text-[11px] rounded-md bg-slate-900/70 text-slate-200 ring-1 ring-inset ring-slate-700 hover:ring-slate-600">
          Set flag…
        </button>
        <button
          :disabled="selected.size < 2 || selected.size > 8"
          class="px-2 py-1 text-[11px] rounded-md bg-indigo-500/30 text-indigo-100 ring-1 ring-inset ring-indigo-500/40 hover:bg-indigo-500/40 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Compare {{ selected.size >= 2 && selected.size <= 8 ? `(${selected.size})` : '' }}
        </button>
      </div>
    </div>

    <!-- Table -->
    <div class="overflow-x-auto">
      <table class="min-w-full text-left">
        <thead>
          <tr class="text-[10px] uppercase tracking-[0.12em] text-slate-500 font-semibold bg-slate-950/40">
            <th class="px-4 py-2.5 w-8">
              <input
                type="checkbox"
                :checked="allSelected"
                class="rounded bg-slate-900 text-indigo-500 border-slate-700 focus:ring-indigo-500"
                aria-label="Select all"
                @change="toggleSelectAll"
              />
            </th>
            <!-- Project -->
            <th
              class="px-3 py-2.5 font-semibold cursor-pointer hover:text-slate-300 select-none"
              @click="clickSort('name')"
            >
              <span class="inline-flex items-center gap-1.5">
                Project
                <span :class="sortKey === 'name' ? 'text-indigo-300' : 'text-slate-700'">
                  {{ sortKey !== 'name' ? '↕' : sortDir === 'asc' ? '↑' : '↓' }}
                </span>
              </span>
            </th>
            <!-- Health -->
            <th
              class="px-3 py-2.5 font-semibold cursor-pointer hover:text-slate-300 select-none w-40"
              @click="clickSort('health_score')"
            >
              <span class="inline-flex items-center gap-1.5">
                Health
                <span :class="sortKey === 'health_score' ? 'text-indigo-300' : 'text-slate-700'">
                  {{ sortKey !== 'health_score' ? '↕' : sortDir === 'asc' ? '↑' : '↓' }}
                </span>
              </span>
            </th>
            <!-- Volume -->
            <th
              class="px-3 py-2.5 font-semibold cursor-pointer hover:text-slate-300 select-none w-56"
              @click="clickSort('total_lines')"
            >
              <span class="inline-flex items-center gap-1.5">
                Volume
                <span :class="sortKey === 'total_lines' ? 'text-indigo-300' : 'text-slate-700'">
                  {{ sortKey !== 'total_lines' ? '↕' : sortDir === 'asc' ? '↑' : '↓' }}
                </span>
              </span>
            </th>
            <!-- Activity -->
            <th
              class="px-3 py-2.5 font-semibold cursor-pointer hover:text-slate-300 select-none w-28"
              @click="clickSort('last_commit_at')"
            >
              <span class="inline-flex items-center gap-1.5">
                Activity
                <span :class="sortKey === 'last_commit_at' ? 'text-indigo-300' : 'text-slate-700'">
                  {{ sortKey !== 'last_commit_at' ? '↕' : sortDir === 'asc' ? '↑' : '↓' }}
                </span>
              </span>
            </th>
            <th class="px-3 py-2.5 font-semibold">Risk</th>
            <th class="px-3 py-2.5 font-semibold w-24">License</th>
            <th class="px-3 py-2.5 w-8"></th>
          </tr>
        </thead>
        <tbody>
          <ProjectTableRow
            v-for="p in filtered"
            :key="p.id"
            :project="p"
            :max-lines="maxLines"
            :selected="selected.has(p.id)"
            @toggle-select="toggleSelect(p.id)"
          />
          <tr v-if="filtered.length === 0">
            <td colspan="8" class="px-5 py-12 text-center">
              <div class="text-[13px] text-slate-400">No projects match your filters.</div>
              <button
                class="mt-2 text-[12px] text-indigo-300 hover:text-indigo-200"
                @click="clearFilters"
              >Clear filters</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Footer -->
    <div class="px-4 sm:px-5 py-3 border-t border-slate-800 bg-slate-950/30 flex items-center justify-between text-[11px] text-slate-500">
      <span>Showing {{ filtered.length }} of {{ projects.length }}</span>
      <span class="font-mono">Click a row to open · Cmd/Ctrl-click to multi-select</span>
    </div>
  </div>
</template>
