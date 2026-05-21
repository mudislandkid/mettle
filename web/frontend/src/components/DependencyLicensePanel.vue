<script setup lang="ts">
import { computed, ref } from 'vue'
import { resolveProjectLicenses } from '@/api/projects'
import type {
  DependencyLicense,
  DependencyLicenseSummary,
  Project,
} from '@/types'

const props = defineProps<{
  project: Project
}>()

const emit = defineEmits<{
  (e: 'updated', updated: Project): void
}>()

const resolving = ref(false)
const error = ref<string | null>(null)

// SPDX ids considered "strong copyleft" — flagged with a stronger tone so
// a GPL-in-proprietary mismatch is visually unmissable.
const STRONG_COPYLEFT = new Set([
  'GPL-2.0-only',
  'GPL-2.0-or-later',
  'GPL-3.0-only',
  'GPL-3.0-or-later',
  'AGPL-3.0-only',
  'AGPL-3.0-or-later',
])
const WEAK_COPYLEFT = new Set([
  'LGPL-2.1-only',
  'LGPL-2.1-or-later',
  'LGPL-3.0-only',
  'LGPL-3.0-or-later',
  'MPL-2.0',
  'EPL-2.0',
  'CDDL-1.0',
  'CDDL-1.1',
])

const summary = computed<DependencyLicenseSummary | null>(
  () => props.project.dependency_license_summary
)
const licenses = computed<DependencyLicense[] | null>(
  () => props.project.dependency_licenses
)
const declaredDepCount = computed(() => (props.project.dependencies || []).length)

const spdxRows = computed(() => {
  if (!summary.value) return []
  return Object.entries(summary.value.by_spdx)
    .map(([spdx, count]) => ({
      spdx,
      count,
      tone: STRONG_COPYLEFT.has(spdx)
        ? 'rose'
        : WEAK_COPYLEFT.has(spdx)
        ? 'amber'
        : 'slate',
    }))
    .sort((a, b) => b.count - a.count)
})

const unresolvedNames = computed<string[]>(() => {
  if (!licenses.value) return []
  return licenses.value.filter((l) => l.spdx === null).map((l) => l.name).slice(0, 25)
})

async function resolve() {
  resolving.value = true
  error.value = null
  try {
    const updated = await resolveProjectLicenses(props.project.id)
    emit('updated', updated)
  } catch (e) {
    error.value = (e as Error).message || 'Failed to resolve licenses'
  } finally {
    resolving.value = false
  }
}
</script>

<template>
  <div class="bg-white rounded-lg border border-slate-200 p-4 space-y-3 dark:bg-slate-900 dark:border-slate-700">
    <div class="flex items-baseline justify-between">
      <div>
        <h3 class="text-sm font-semibold text-slate-900 uppercase tracking-wide dark:text-slate-100">
          Dependency Licenses
        </h3>
        <p class="text-xs text-slate-500 dark:text-slate-400">
          SPDX licenses resolved from npm / PyPI / crates.io. First run fetches over the network; subsequent runs hit the cache.
        </p>
      </div>
      <button
        v-if="declaredDepCount > 0"
        @click="resolve"
        :disabled="resolving"
        class="px-3 py-1.5 text-xs font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-500/15 dark:text-indigo-300 dark:hover:bg-indigo-500/25"
      >
        {{ resolving ? 'Resolving…' : licenses ? 'Re-resolve' : 'Resolve now' }}
      </button>
    </div>

    <div v-if="error" class="text-xs text-rose-600 dark:text-rose-400">{{ error }}</div>

    <div v-if="declaredDepCount === 0" class="text-sm text-slate-500 py-4 text-center dark:text-slate-400">
      No dependencies detected on this project.
    </div>

    <div v-else-if="!summary" class="text-sm text-slate-500 py-4 text-center dark:text-slate-400">
      Licenses not yet resolved.
      <span class="block text-xs mt-1">Click "Resolve now" to query the package registries.</span>
    </div>

    <template v-else>
      <!-- Risk banner -->
      <div
        v-if="project.has_license_risk"
        class="rounded-md px-3 py-2 ring-1 ring-inset ring-rose-300 bg-rose-50 text-rose-800 text-xs dark:bg-rose-500/10 dark:ring-rose-500/40 dark:text-rose-200"
      >
        <strong>Strong copyleft in proprietary context.</strong>
        {{ summary.copyleft_strong }} GPL/AGPL dep{{ summary.copyleft_strong === 1 ? '' : 's' }} declared on a project that's flagged proprietary or has no license. Review before shipping.
      </div>

      <!-- Stat tiles -->
      <div class="grid grid-cols-3 gap-2 text-center">
        <div class="rounded-md bg-slate-50 dark:bg-slate-800/60 p-2">
          <div class="text-xl font-semibold tabular-nums text-slate-900 dark:text-slate-100">{{ summary.resolved }}</div>
          <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Resolved</div>
        </div>
        <div class="rounded-md bg-slate-50 dark:bg-slate-800/60 p-2">
          <div class="text-xl font-semibold tabular-nums text-slate-900 dark:text-slate-100">{{ summary.unresolved }}</div>
          <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Unresolved</div>
        </div>
        <div class="rounded-md bg-slate-50 dark:bg-slate-800/60 p-2">
          <div
            class="text-xl font-semibold tabular-nums"
            :class="summary.copyleft_strong > 0 ? 'text-rose-600 dark:text-rose-400' : 'text-slate-900 dark:text-slate-100'"
          >
            {{ summary.copyleft_strong + summary.copyleft_weak }}
          </div>
          <div class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Copyleft</div>
        </div>
      </div>

      <!-- SPDX tally -->
      <div class="space-y-1">
        <h4 class="text-[10.5px] uppercase tracking-wider text-slate-500 dark:text-slate-400">By license</h4>
        <div class="flex flex-wrap gap-1.5">
          <span
            v-for="row in spdxRows"
            :key="row.spdx"
            class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono ring-1 ring-inset"
            :class="{
              'bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800/70 dark:text-slate-300 dark:ring-slate-700': row.tone === 'slate',
              'bg-amber-50 text-amber-800 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-200 dark:ring-amber-500/30': row.tone === 'amber',
              'bg-rose-50 text-rose-800 ring-rose-200 dark:bg-rose-500/10 dark:text-rose-200 dark:ring-rose-500/30': row.tone === 'rose',
            }"
          >
            {{ row.spdx }}
            <span class="tabular-nums text-[10px] opacity-70">× {{ row.count }}</span>
          </span>
        </div>
      </div>

      <!-- Unresolved -->
      <div v-if="unresolvedNames.length > 0" class="space-y-1">
        <h4 class="text-[10.5px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Unresolved ({{ summary.unresolved }})
        </h4>
        <div class="text-xs text-slate-500 font-mono flex flex-wrap gap-x-3 gap-y-0.5 dark:text-slate-400">
          <span v-for="name in unresolvedNames" :key="name">{{ name }}</span>
          <span v-if="summary.unresolved > unresolvedNames.length" class="text-slate-400 dark:text-slate-500">
            …and {{ summary.unresolved - unresolvedNames.length }} more
          </span>
        </div>
      </div>
    </template>
  </div>
</template>
