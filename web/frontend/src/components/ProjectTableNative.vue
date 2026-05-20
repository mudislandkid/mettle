<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { FlagType, Project, Tag, SecretMatch } from '@/types'
import { bulkUpdateFlags, bulkUpdateTag, getFlagTypes, listTags } from '@/api/projects'
import SecretsBadge from './SecretsBadge.vue'
import LicenseBadge from './LicenseBadge.vue'
import SecretsDrawer from './SecretsDrawer.vue'

const router = useRouter()

const props = defineProps<{
  projects: Project[]
}>()

const emit = defineEmits<{ (e: 'projects-changed'): void }>()

// Sorting
type SortKey = keyof Project | 'code_percentage' | 'test_percentage' | 'health_score'
const sortKey = ref<SortKey>('name')
const sortOrder = ref<'asc' | 'desc'>('asc')

function sort(key: SortKey) {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortOrder.value = 'asc'
  }
}

// Pagination
const currentPage = ref(1)
const pageSize = ref(50)

// Search/Filter
const searchQuery = ref('')
const showStaleOnly = ref(false)
const staleDays = 180

function isStale(p: Project): boolean {
  // No commit info ⇒ treat as stale (often "I never committed this"). Also
  // skip projects explicitly flagged as archived since they're meant to be inactive.
  if (p.flags?.includes('archived')) return false
  if (!p.last_commit_at) return true
  const age = Date.now() - new Date(p.last_commit_at).getTime()
  if (Number.isNaN(age)) return false
  return age > staleDays * 86_400_000
}

const staleCount = computed(() => props.projects.filter(isStale).length)

// --- Bulk selection -------------------------------------------------------
const selectedIds = ref<Set<number>>(new Set())
const bulkFlag = ref<string>('')
const bulkTagId = ref<number | null>(null)
const bulkOp = ref<'add' | 'remove'>('add')
const bulkBusy = ref(false)
const bulkMessage = ref<string | null>(null)
const flagTypes = ref<FlagType[]>([])
const availableTags = ref<Tag[]>([])

// Reset selection if the project list changes (e.g. new analysis loaded).
watch(() => props.projects, () => {
  selectedIds.value = new Set()
  bulkMessage.value = null
}, { deep: false })

function toggleSelect(projectId: number) {
  const next = new Set(selectedIds.value)
  if (next.has(projectId)) next.delete(projectId)
  else next.add(projectId)
  selectedIds.value = next
}

function isSelected(projectId: number): boolean {
  return selectedIds.value.has(projectId)
}

const allVisibleSelected = computed(() => {
  if (paginatedProjects.value.length === 0) return false
  return paginatedProjects.value.every(p => selectedIds.value.has(p.id))
})

function toggleSelectAllVisible() {
  const next = new Set(selectedIds.value)
  if (allVisibleSelected.value) {
    for (const p of paginatedProjects.value) next.delete(p.id)
  } else {
    for (const p of paginatedProjects.value) next.add(p.id)
  }
  selectedIds.value = next
}

function clearSelection() {
  selectedIds.value = new Set()
}

async function loadBulkOptions() {
  try {
    const [ft, tags] = await Promise.all([getFlagTypes(), listTags()])
    flagTypes.value = ft
    availableTags.value = tags
  } catch {
    /* surface via bulk action attempts instead */
  }
}

// Load flag/tag options lazily on first hover/focus of the bulk bar.
let bulkOptionsLoaded = false
function ensureBulkOptions() {
  if (bulkOptionsLoaded) return
  bulkOptionsLoaded = true
  loadBulkOptions()
}

async function applyBulkFlag() {
  if (!bulkFlag.value || selectedIds.value.size === 0) return
  bulkBusy.value = true
  bulkMessage.value = null
  try {
    const result = await bulkUpdateFlags(
      Array.from(selectedIds.value),
      [bulkFlag.value],
      bulkOp.value,
    )
    bulkMessage.value = `${bulkOp.value === 'add' ? 'Added' : 'Removed'} flag on ${result.updated} project${result.updated === 1 ? '' : 's'}`
    emit('projects-changed')
  } catch (e) {
    bulkMessage.value = (e as Error).message
  } finally {
    bulkBusy.value = false
  }
}

function openCompare() {
  // Compare endpoint is capped at 8 — the UI hint here matches.
  const ids = Array.from(selectedIds.value).slice(0, 8)
  if (ids.length < 2) return
  router.push({ name: 'project-compare', query: { ids: ids.join(',') } })
}

async function applyBulkTag() {
  if (bulkTagId.value === null || selectedIds.value.size === 0) return
  bulkBusy.value = true
  bulkMessage.value = null
  try {
    const result = await bulkUpdateTag(
      Array.from(selectedIds.value),
      bulkTagId.value,
      bulkOp.value,
    )
    bulkMessage.value = `${bulkOp.value === 'add' ? 'Added' : 'Removed'} tag on ${result.updated} project${result.updated === 1 ? '' : 's'}`
    emit('projects-changed')
  } catch (e) {
    bulkMessage.value = (e as Error).message
  } finally {
    bulkBusy.value = false
  }
}

// Computed sorted and filtered data
const filteredProjects = computed(() => {
  let filtered = [...props.projects]

  // Apply search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(p =>
      p.name.toLowerCase().includes(query) ||
      p.languages.some(lang => lang.toLowerCase().includes(query))
    )
  }

  if (showStaleOnly.value) {
    filtered = filtered.filter(isStale)
  }

  // Apply sorting
  filtered.sort((a, b) => {
    let aVal: any
    let bVal: any

    if (sortKey.value === 'code_percentage') {
      aVal = a.total_lines > 0 ? (a.code_lines / a.total_lines) * 100 : 0
      bVal = b.total_lines > 0 ? (b.code_lines / b.total_lines) * 100 : 0
    } else if (sortKey.value === 'test_percentage') {
      aVal = getTestPercentage(a)
      bVal = getTestPercentage(b)
    } else {
      aVal = a[sortKey.value as keyof Project]
      bVal = b[sortKey.value as keyof Project]
    }

    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortOrder.value === 'asc'
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal)
    }

    if (aVal < bVal) return sortOrder.value === 'asc' ? -1 : 1
    if (aVal > bVal) return sortOrder.value === 'asc' ? 1 : -1
    return 0
  })

  return filtered
})

// Paginated data
const paginatedProjects = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredProjects.value.slice(start, end)
})

const totalPages = computed(() =>
  Math.ceil(filteredProjects.value.length / pageSize.value)
)

function handleRowClick(project: Project) {
  router.push({ name: 'project-detail', params: { id: project.id } })
}

function formatNumber(n: number): string {
  return n.toLocaleString()
}

function getCodePercentage(project: Project): number {
  return project.total_lines > 0
    ? (project.code_lines / project.total_lines) * 100
    : 0
}

function getTestPercentage(project: Project): number {
  // Backend provides test_percentage but legacy analyses may lack it; recompute.
  if (typeof project.test_percentage === 'number' && project.test_percentage > 0) {
    return project.test_percentage
  }
  return project.total_lines > 0 && project.test_total_lines
    ? (project.test_total_lines / project.total_lines) * 100
    : 0
}

function healthColorClass(score: number): string {
  if (score >= 80) return 'bg-emerald-100 text-emerald-700'
  if (score >= 60) return 'bg-lime-100 text-lime-700'
  if (score >= 40) return 'bg-amber-100 text-amber-700'
  if (score >= 20) return 'bg-orange-100 text-orange-700'
  return 'bg-red-100 text-red-700'
}

// Secrets drawer state
const drawerOpen = ref(false)
const drawerProject = ref<{ name: string; matches: SecretMatch[] } | null>(null)

function openSecretsDrawer(project: Project) {
  drawerProject.value = {
    name: project.name,
    matches: project.secrets_detail ?? [],
  }
  drawerOpen.value = true
}

function closeSecretsDrawer() {
  drawerOpen.value = false
}
</script>

<template>
  <div class="bg-white rounded-xl shadow-lg border border-slate-200/50 overflow-hidden dark:bg-slate-900 dark:border-slate-800/50">
    <!-- Search and controls -->
    <div class="p-5 border-b border-slate-200 bg-gradient-to-r from-slate-50 to-slate-100/50 dark:border-slate-700">
      <div class="flex items-center justify-between gap-4">
        <div class="flex-1 max-w-md">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search projects by name or language..."
            class="w-full px-4 py-2.5 border border-slate-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all dark:border-slate-600"
          />
        </div>
        <div class="flex items-center gap-3">
          <label class="flex items-center gap-2 text-sm text-slate-700 cursor-pointer select-none dark:text-slate-300" :title="`Last commit older than ${staleDays} days (or never), excludes archived`">
            <input
              v-model="showStaleOnly"
              type="checkbox"
              class="rounded text-indigo-600 focus:ring-indigo-500 dark:text-indigo-400"
            />
            Show stale only <span class="text-slate-400 dark:text-slate-500">({{ staleCount }})</span>
          </label>
          <div class="text-sm font-medium text-slate-700 bg-white px-4 py-2 rounded-lg shadow-sm border border-slate-200 dark:text-slate-300 dark:bg-slate-900 dark:border-slate-700">
            {{ filteredProjects.length }} {{ filteredProjects.length === 1 ? 'project' : 'projects' }}
          </div>
        </div>
      </div>

      <!-- Bulk action bar: visible only when something is selected -->
      <div
        v-if="selectedIds.size > 0"
        @mouseenter="ensureBulkOptions"
        @focusin="ensureBulkOptions"
        class="mt-3 flex flex-wrap items-center gap-2 p-3 bg-indigo-50 border border-indigo-200 rounded-lg dark:bg-indigo-500/15"
      >
        <span class="text-sm font-semibold text-indigo-700 dark:text-indigo-300">
          {{ selectedIds.size }} selected
        </span>
        <button
          @click="clearSelection"
          class="text-xs text-indigo-700 underline underline-offset-2 hover:text-indigo-900 dark:text-indigo-300"
        >
          Clear
        </button>

        <span class="ml-4 text-xs text-slate-500 dark:text-slate-400">Operation:</span>
        <div class="inline-flex rounded-md overflow-hidden border border-slate-200 dark:border-slate-700">
          <button
            @click="bulkOp = 'add'"
            :class="['px-2 py-1 text-xs', bulkOp === 'add' ? 'bg-indigo-600 text-white' : 'bg-white text-slate-700']"
          >Add</button>
          <button
            @click="bulkOp = 'remove'"
            :class="['px-2 py-1 text-xs', bulkOp === 'remove' ? 'bg-indigo-600 text-white' : 'bg-white text-slate-700']"
          >Remove</button>
        </div>

        <select
          v-model="bulkFlag"
          class="text-xs px-2 py-1 border border-slate-200 rounded-md bg-white dark:border-slate-700 dark:bg-slate-900"
        >
          <option value="">Flag…</option>
          <option v-for="ft in flagTypes" :key="ft.type" :value="ft.type">{{ ft.label }}</option>
        </select>
        <button
          @click="applyBulkFlag"
          :disabled="bulkBusy || !bulkFlag"
          class="px-2 py-1 text-xs bg-indigo-600 text-white rounded-md disabled:bg-slate-300 dark:bg-slate-600"
        >
          Apply flag
        </button>

        <select
          v-model="bulkTagId"
          class="text-xs px-2 py-1 border border-slate-200 rounded-md bg-white dark:border-slate-700 dark:bg-slate-900"
        >
          <option :value="null">Tag…</option>
          <option v-for="t in availableTags" :key="t.id" :value="t.id">{{ t.name }}</option>
        </select>
        <button
          @click="applyBulkTag"
          :disabled="bulkBusy || bulkTagId === null"
          class="px-2 py-1 text-xs bg-indigo-600 text-white rounded-md disabled:bg-slate-300 dark:bg-slate-600"
        >
          Apply tag
        </button>

        <button
          @click="openCompare"
          :disabled="selectedIds.size < 2 || selectedIds.size > 8"
          :title="selectedIds.size < 2 ? 'Select 2-8 projects to compare' : 'Open side-by-side comparison'"
          class="px-2 py-1 text-xs bg-slate-700 text-white rounded-md disabled:bg-slate-300 dark:bg-slate-700 dark:disabled:bg-slate-800"
        >
          Compare selected
        </button>

        <span v-if="bulkMessage" class="ml-auto text-xs text-slate-600 dark:text-slate-400">{{ bulkMessage }}</span>
      </div>
    </div>

    <!-- Table -->
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-slate-200">
        <thead class="bg-gradient-to-r from-slate-50 via-slate-100/50 to-slate-50">
          <tr>
            <th class="px-4 py-4 text-left">
              <input
                type="checkbox"
                :checked="allVisibleSelected"
                :indeterminate.prop="selectedIds.size > 0 && !allVisibleSelected"
                @change="toggleSelectAllVisible"
                class="rounded text-indigo-600 focus:ring-indigo-500 dark:text-indigo-400"
                aria-label="Select all visible"
              />
            </th>
            <th
              @click="sort('name')"
              class="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider cursor-pointer hover:bg-slate-200 select-none transition-colors dark:text-slate-300 dark:bg-slate-700"
            >
              <div class="flex items-center gap-1">
                Project
                <span v-if="sortKey === 'name'" class="text-indigo-600 dark:text-indigo-400">
                  {{ sortOrder === 'asc' ? '↑' : '↓' }}
                </span>
              </div>
            </th>
            <th
              @click="sort('health_score')"
              class="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider cursor-pointer hover:bg-slate-200 select-none transition-colors dark:text-slate-300 dark:bg-slate-700"
              title="Composite 0-100 score across comment ratio, tests, commit recency, TODO density, avg file size, and metadata"
            >
              <div class="flex items-center gap-1">
                Health
                <span v-if="sortKey === 'health_score'" class="text-indigo-600 dark:text-indigo-400">
                  {{ sortOrder === 'asc' ? '↑' : '↓' }}
                </span>
              </div>
            </th>
            <th
              @click="sort('total_files')"
              class="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider cursor-pointer hover:bg-slate-200 select-none transition-colors dark:text-slate-300 dark:bg-slate-700"
            >
              <div class="flex items-center gap-1">
                Files
                <span v-if="sortKey === 'total_files'" class="text-indigo-600 dark:text-indigo-400">
                  {{ sortOrder === 'asc' ? '↑' : '↓' }}
                </span>
              </div>
            </th>
            <th
              @click="sort('total_lines')"
              class="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider cursor-pointer hover:bg-slate-200 select-none transition-colors dark:text-slate-300 dark:bg-slate-700"
            >
              <div class="flex items-center gap-1">
                Total Lines
                <span v-if="sortKey === 'total_lines'" class="text-indigo-600 dark:text-indigo-400">
                  {{ sortOrder === 'asc' ? '↑' : '↓' }}
                </span>
              </div>
            </th>
            <th
              @click="sort('code_lines')"
              class="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider cursor-pointer hover:bg-slate-200 select-none transition-colors dark:text-slate-300 dark:bg-slate-700"
            >
              <div class="flex items-center gap-1">
                Code Lines
                <span v-if="sortKey === 'code_lines'" class="text-indigo-600 dark:text-indigo-400">
                  {{ sortOrder === 'asc' ? '↑' : '↓' }}
                </span>
              </div>
            </th>
            <th
              @click="sort('code_percentage')"
              class="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider cursor-pointer hover:bg-slate-200 select-none transition-colors dark:text-slate-300 dark:bg-slate-700"
            >
              <div class="flex items-center gap-1">
                Code %
                <span v-if="sortKey === 'code_percentage'" class="text-indigo-600 dark:text-indigo-400">
                  {{ sortOrder === 'asc' ? '↑' : '↓' }}
                </span>
              </div>
            </th>
            <th
              @click="sort('test_percentage')"
              class="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider cursor-pointer hover:bg-slate-200 select-none transition-colors dark:text-slate-300 dark:bg-slate-700"
              title="Percentage of total lines that live in test files"
            >
              <div class="flex items-center gap-1">
                Tests %
                <span v-if="sortKey === 'test_percentage'" class="text-indigo-600 dark:text-indigo-400">
                  {{ sortOrder === 'asc' ? '↑' : '↓' }}
                </span>
              </div>
            </th>
            <th
              @click="sort('functions')"
              class="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider cursor-pointer hover:bg-slate-200 select-none transition-colors dark:text-slate-300 dark:bg-slate-700"
            >
              <div class="flex items-center gap-1">
                Functions
                <span v-if="sortKey === 'functions'" class="text-indigo-600 dark:text-indigo-400">
                  {{ sortOrder === 'asc' ? '↑' : '↓' }}
                </span>
              </div>
            </th>
            <th
              @click="sort('classes')"
              class="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider cursor-pointer hover:bg-slate-200 select-none transition-colors dark:text-slate-300 dark:bg-slate-700"
            >
              <div class="flex items-center gap-1">
                Classes
                <span v-if="sortKey === 'classes'" class="text-indigo-600 dark:text-indigo-400">
                  {{ sortOrder === 'asc' ? '↑' : '↓' }}
                </span>
              </div>
            </th>
            <th class="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider dark:text-slate-300">
              Secrets
            </th>
            <th class="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider dark:text-slate-300">
              License
            </th>
            <th class="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider dark:text-slate-300">
              Languages
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-slate-200 dark:bg-slate-900">
          <tr
            v-for="project in paginatedProjects"
            :key="project.id"
            @click="handleRowClick(project)"
            :class="[
              'hover:bg-gradient-to-r hover:from-indigo-50 hover:to-purple-50 cursor-pointer transition-all duration-150 border-b border-slate-100',
              isSelected(project.id) ? 'bg-indigo-50/40' : '',
            ]"
          >
            <td class="px-4 py-4" @click.stop>
              <input
                type="checkbox"
                :checked="isSelected(project.id)"
                @change="toggleSelect(project.id)"
                class="rounded text-indigo-600 focus:ring-indigo-500 dark:text-indigo-400"
                :aria-label="`Select ${project.name}`"
              />
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold text-slate-900 dark:text-slate-100">
              {{ project.name }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm">
              <span
                class="inline-block px-2 py-0.5 rounded text-xs font-semibold tabular-nums"
                :class="healthColorClass(project.health_score)"
                :title="`Health: ${project.health_score?.toFixed(1) ?? '0'}/100`"
              >
                {{ project.health_score?.toFixed(0) ?? '–' }}
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
              {{ formatNumber(project.total_files) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
              {{ formatNumber(project.total_lines) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
              {{ formatNumber(project.code_lines) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
              {{ getCodePercentage(project).toFixed(1) }}%
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
              {{ getTestPercentage(project).toFixed(1) }}%
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
              {{ formatNumber(project.functions) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
              {{ formatNumber(project.classes) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm" @click.stop>
              <SecretsBadge
                :count="project.secrets_found ?? 0"
                :detail="project.secrets_detail ?? null"
                @open="openSecretsDrawer(project)"
              />
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm">
              <LicenseBadge :spdx="project.license_spdx ?? null" />
            </td>
            <td class="px-6 py-4 text-sm text-slate-600 max-w-xs truncate dark:text-slate-400">
              {{ project.languages.slice(0, 3).join(', ') }}{{ project.languages.length > 3 ? '...' : '' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="px-6 py-4 border-t border-slate-200 bg-gradient-to-r from-slate-50 to-slate-100/50 dark:border-slate-700">
      <div class="flex items-center justify-between">
        <div class="text-sm text-slate-600 dark:text-slate-400">
          Showing {{ ((currentPage - 1) * pageSize) + 1 }} to {{ Math.min(currentPage * pageSize, filteredProjects.length) }} of {{ filteredProjects.length }}
        </div>
        <div class="flex gap-2">
          <button
            @click="currentPage = 1"
            :disabled="currentPage === 1"
            class="px-4 py-2 text-sm font-medium border border-slate-300 rounded-lg shadow-sm hover:bg-white hover:shadow transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-sm dark:border-slate-600 dark:bg-slate-900"
          >
            First
          </button>
          <button
            @click="currentPage--"
            :disabled="currentPage === 1"
            class="px-4 py-2 text-sm font-medium border border-slate-300 rounded-lg shadow-sm hover:bg-white hover:shadow transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-sm dark:border-slate-600 dark:bg-slate-900"
          >
            Previous
          </button>
          <div class="px-4 py-2 text-sm font-medium text-slate-700 bg-white rounded-lg shadow-sm border border-slate-200 dark:text-slate-300 dark:bg-slate-900 dark:border-slate-700">
            Page {{ currentPage }} of {{ totalPages }}
          </div>
          <button
            @click="currentPage++"
            :disabled="currentPage === totalPages"
            class="px-4 py-2 text-sm font-medium border border-slate-300 rounded-lg shadow-sm hover:bg-white hover:shadow transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-sm dark:border-slate-600 dark:bg-slate-900"
          >
            Next
          </button>
          <button
            @click="currentPage = totalPages"
            :disabled="currentPage === totalPages"
            class="px-4 py-2 text-sm font-medium border border-slate-300 rounded-lg shadow-sm hover:bg-white hover:shadow transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-sm dark:border-slate-600 dark:bg-slate-900"
          >
            Last
          </button>
        </div>
      </div>
    </div>

    <SecretsDrawer
      v-if="drawerProject"
      :open="drawerOpen"
      :project-name="drawerProject.name"
      :matches="drawerProject.matches"
      @close="closeSecretsDrawer"
    />
  </div>
</template>
