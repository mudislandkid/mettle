<script setup lang="ts">
import { computed } from 'vue'
import type { Project } from '@/types'

const props = defineProps<{
  project: Project
}>()

// Older analyses (pre-test-segregation) may not have these fields populated.
const hasTestData = computed(() => (props.project.test_files ?? 0) > 0)
const hasJsTsData = computed(() => {
  const p = props.project
  return (
    (p.jsx_components ?? 0) +
    (p.react_hooks ?? 0) +
    (p.async_functions ?? 0) +
    (p.interfaces ?? 0) +
    (p.type_aliases ?? 0) +
    (p.enums ?? 0)
  ) > 0
})

// Translate `git@github.com:foo/bar.git` style URLs into clickable https links;
// leave http(s) URLs alone.
const webRepoUrl = computed(() => {
  const raw = props.project.repo_url
  if (!raw) return ''
  const ssh = raw.match(/^git@([^:]+):(.+?)(?:\.git)?$/)
  if (ssh) return `https://${ssh[1]}/${ssh[2]}`
  return raw.replace(/\.git$/, '')
})

const formattedLastCommit = computed(() => {
  if (!props.project.last_commit_at) return ''
  const d = new Date(props.project.last_commit_at)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString()
})

const commitAge = computed(() => {
  if (!props.project.last_commit_at) return ''
  const ms = Date.now() - new Date(props.project.last_commit_at).getTime()
  if (Number.isNaN(ms)) return ''
  const days = Math.floor(ms / 86_400_000)
  if (days < 1) return 'today'
  if (days < 30) return `${days}d ago`
  if (days < 365) return `${Math.floor(days / 30)}mo ago`
  return `${Math.floor(days / 365)}y ago`
})

const testPercentage = computed(() => {
  if (typeof props.project.test_percentage === 'number' && props.project.test_percentage > 0) {
    return props.project.test_percentage
  }
  if (props.project.total_lines > 0 && props.project.test_total_lines) {
    return (props.project.test_total_lines / props.project.total_lines) * 100
  }
  return 0
})
</script>

<template>
  <div class="bg-white rounded-lg border border-slate-200 p-6 space-y-4 dark:bg-slate-900 dark:border-slate-700">
    <!-- Project Name and Path -->
    <div>
      <h2 class="text-2xl font-bold text-slate-900 mb-1 dark:text-slate-100">{{ project.name }}</h2>
      <p class="text-sm text-slate-500 font-mono truncate dark:text-slate-400">{{ project.path }}</p>
      <div v-if="project.repo_url || project.last_commit_at" class="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs">
        <a
          v-if="project.repo_url"
          :href="webRepoUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="text-indigo-600 hover:text-indigo-700 hover:underline dark:text-indigo-400 dark:text-indigo-300"
        >↗ {{ project.repo_url }}</a>
        <span v-if="project.last_commit_at" class="text-slate-500 dark:text-slate-400">
          last commit: {{ formattedLastCommit }} <span class="text-slate-400 dark:text-slate-500">({{ commitAge }})</span>
        </span>
      </div>
    </div>

    <!-- Metrics Grid -->
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
      <div>
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 dark:text-slate-400">Total Lines</div>
        <div class="text-lg font-semibold text-slate-900 dark:text-slate-100">{{ project.total_lines.toLocaleString() }}</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 dark:text-slate-400">Code Lines</div>
        <div class="text-lg font-semibold text-indigo-600 dark:text-indigo-400">{{ project.code_lines.toLocaleString() }}</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 dark:text-slate-400">Code %</div>
        <div class="text-lg font-semibold text-green-600 dark:text-green-400">{{ project.code_percentage.toFixed(1) }}%</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 dark:text-slate-400">Files</div>
        <div class="text-lg font-semibold text-slate-900 dark:text-slate-100">{{ project.total_files.toLocaleString() }}</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 dark:text-slate-400">Functions</div>
        <div class="text-lg font-semibold text-slate-900 dark:text-slate-100">{{ project.functions.toLocaleString() }}</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 dark:text-slate-400">Classes</div>
        <div class="text-lg font-semibold text-slate-900 dark:text-slate-100">{{ project.classes.toLocaleString() }}</div>
      </div>
    </div>

    <!-- Test coverage block (heuristic by filename / dir) -->
    <div v-if="hasTestData" class="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-slate-100 dark:border-slate-800">
      <div>
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 dark:text-slate-400">Test Files</div>
        <div class="text-lg font-semibold text-slate-900 dark:text-slate-100">{{ project.test_files.toLocaleString() }}</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 dark:text-slate-400">Test Lines</div>
        <div class="text-lg font-semibold text-slate-900 dark:text-slate-100">{{ project.test_total_lines.toLocaleString() }}</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 dark:text-slate-400">Tests %</div>
        <div class="text-lg font-semibold text-purple-600">{{ testPercentage.toFixed(1) }}%</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 dark:text-slate-400">Production Lines</div>
        <div class="text-lg font-semibold text-slate-900 dark:text-slate-100">
          {{ Math.max(0, project.total_lines - project.test_total_lines).toLocaleString() }}
        </div>
      </div>
    </div>

    <!-- JS / TS specifics -->
    <div v-if="hasJsTsData" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 pt-4 border-t border-slate-100 dark:border-slate-800">
      <div>
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 dark:text-slate-400">JSX Components</div>
        <div class="text-lg font-semibold text-slate-900 dark:text-slate-100">{{ (project.jsx_components || 0).toLocaleString() }}</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 dark:text-slate-400">React Hooks</div>
        <div class="text-lg font-semibold text-slate-900 dark:text-slate-100">{{ (project.react_hooks || 0).toLocaleString() }}</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 dark:text-slate-400">Async Funcs</div>
        <div class="text-lg font-semibold text-slate-900 dark:text-slate-100">{{ (project.async_functions || 0).toLocaleString() }}</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 dark:text-slate-400">Interfaces</div>
        <div class="text-lg font-semibold text-slate-900 dark:text-slate-100">{{ (project.interfaces || 0).toLocaleString() }}</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 dark:text-slate-400">Type Aliases</div>
        <div class="text-lg font-semibold text-slate-900 dark:text-slate-100">{{ (project.type_aliases || 0).toLocaleString() }}</div>
      </div>
      <div>
        <div class="text-xs text-slate-500 uppercase tracking-wide mb-1 dark:text-slate-400">Enums</div>
        <div class="text-lg font-semibold text-slate-900 dark:text-slate-100">{{ (project.enums || 0).toLocaleString() }}</div>
      </div>
    </div>

    <!-- Languages -->
    <div v-if="project.languages && project.languages.length > 0">
      <div class="text-xs text-slate-500 uppercase tracking-wide mb-2 dark:text-slate-400">Languages</div>
      <div class="flex flex-wrap gap-2">
        <span
          v-for="lang in project.languages"
          :key="lang"
          class="px-2 py-1 text-xs font-medium bg-slate-100 text-slate-700 rounded dark:bg-slate-800 dark:text-slate-300"
        >
          {{ lang }}
        </span>
      </div>
    </div>
  </div>
</template>
