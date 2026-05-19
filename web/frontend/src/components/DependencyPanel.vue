<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Dependency } from '@/types'

const props = defineProps<{
  dependencies: Dependency[]
}>()

const search = ref('')
const collapsed = ref<Record<string, boolean>>({})

const grouped = computed<Array<[string, Dependency[]]>>(() => {
  const q = search.value.toLowerCase()
  const groups = new Map<string, Dependency[]>()
  for (const dep of props.dependencies) {
    if (q && !dep.name.toLowerCase().includes(q)) continue
    const key = dep.manager || 'other'
    const list = groups.get(key) ?? []
    list.push(dep)
    groups.set(key, list)
  }
  for (const list of groups.values()) {
    list.sort((a, b) => a.name.localeCompare(b.name))
  }
  return Array.from(groups.entries()).sort((a, b) => b[1].length - a[1].length)
})

const totalCount = computed(() => props.dependencies.length)

function toggleCollapsed(key: string) {
  collapsed.value = { ...collapsed.value, [key]: !collapsed.value[key] }
}

function managerLabel(m: string): string {
  switch (m) {
    case 'npm': return 'npm / Node'
    case 'pypi': return 'Python (PyPI)'
    case 'cargo': return 'Cargo (Rust)'
    case 'go': return 'Go modules'
    case 'composer': return 'Composer (PHP)'
    case 'rubygems': return 'RubyGems'
    default: return m
  }
}

function managerColor(m: string): string {
  switch (m) {
    case 'npm': return 'bg-red-100 text-red-700'
    case 'pypi': return 'bg-blue-100 text-blue-700'
    case 'cargo': return 'bg-orange-100 text-orange-700'
    case 'go': return 'bg-cyan-100 text-cyan-700'
    case 'composer': return 'bg-purple-100 text-purple-700'
    case 'rubygems': return 'bg-rose-100 text-rose-700'
    default: return 'bg-slate-100 text-slate-700'
  }
}
</script>

<template>
  <div class="bg-white rounded-lg border border-slate-200 p-4 space-y-3 dark:bg-slate-900 dark:border-slate-700">
    <div class="flex items-baseline justify-between">
      <div>
        <h3 class="text-sm font-semibold text-slate-900 uppercase tracking-wide dark:text-slate-100">Dependencies</h3>
        <p class="text-xs text-slate-500 dark:text-slate-400">Pulled from package.json / pyproject.toml / Cargo.toml / go.mod / Gemfile / composer.json.</p>
      </div>
      <div class="text-xs text-slate-500 dark:text-slate-400">{{ totalCount }} declared</div>
    </div>

    <div v-if="totalCount === 0" class="text-sm text-slate-500 py-4 text-center dark:text-slate-400">
      No dependency manifests found in this project.
    </div>

    <template v-else>
      <input
        v-model="search"
        type="text"
        placeholder="Filter by name…"
        class="w-full px-3 py-1.5 border border-slate-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-slate-700"
      />

      <div class="space-y-3 max-h-[26rem] overflow-y-auto pr-1">
        <div v-for="[manager, deps] in grouped" :key="manager">
          <button
            @click="toggleCollapsed(manager)"
            class="w-full flex items-center justify-between mb-1 text-left"
          >
            <span class="inline-flex items-center gap-2">
              <span :class="['px-1.5 py-0.5 rounded text-[10px] font-semibold tracking-wider', managerColor(manager)]">
                {{ managerLabel(manager) }}
              </span>
              <span class="text-xs text-slate-500 dark:text-slate-400">{{ deps.length }}</span>
            </span>
            <span class="text-xs text-slate-400 dark:text-slate-500">{{ collapsed[manager] ? '+' : '−' }}</span>
          </button>
          <ul v-show="!collapsed[manager]" class="space-y-0.5">
            <li
              v-for="dep in deps"
              :key="`${manager}:${dep.name}`"
              class="flex items-center justify-between gap-2 text-sm font-mono py-0.5"
            >
              <span class="text-slate-700 truncate dark:text-slate-300">{{ dep.name }}</span>
              <span class="text-xs text-slate-500 shrink-0 dark:text-slate-400">{{ dep.version || '*' }}</span>
            </li>
          </ul>
        </div>
        <div v-if="grouped.length === 0" class="text-sm text-slate-500 text-center py-4 dark:text-slate-400">
          No dependencies match the current filter.
        </div>
      </div>
    </template>
  </div>
</template>
