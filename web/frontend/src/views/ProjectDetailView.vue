<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getProject, refreshProjectAnalysis } from '@/api/projects'
import { useGitStats } from '@/composables/useGitStats'
import ProjectMetricsCard from '@/components/ProjectMetricsCard.vue'
import ProjectNotesEditor from '@/components/ProjectNotesEditor.vue'
import HealthBreakdownPanel from '@/components/HealthBreakdownPanel.vue'
import TodoInspector from '@/components/TodoInspector.vue'
import DependencyPanel from '@/components/DependencyPanel.vue'
import DependencyLicensePanel from '@/components/DependencyLicensePanel.vue'
import ComplexityPanel from '@/components/ComplexityPanel.vue'
import GitStatsContainer from '@/components/GitStats/GitStatsContainer.vue'
import type { Project } from '@/types'

const route = useRoute()
const router = useRouter()

const projectId = computed(() => Number(route.params.id))
const project = ref<Project | null>(null)
const projectLoading = ref(false)
const projectError = ref<string | null>(null)

async function loadProject() {
  if (!projectId.value || Number.isNaN(projectId.value)) return
  projectLoading.value = true
  projectError.value = null

  try {
    project.value = await getProject(projectId.value)
  } catch (e) {
    projectError.value = (e as Error).message || 'Failed to load project'
  } finally {
    projectLoading.value = false
  }
}

async function handleRefreshProject() {
  projectLoading.value = true
  projectError.value = null

  try {
    project.value = await refreshProjectAnalysis(projectId.value)
  } catch (e) {
    projectError.value = (e as Error).message || 'Failed to refresh project'
  } finally {
    projectLoading.value = false
  }
}

const {
  stats: gitStats,
  loading: gitLoading,
  error: gitError,
  isGitRepo,
  refresh: refreshGitStats,
} = useGitStats(projectId)

// Fetch when mounted AND every time the :id route param changes (otherwise
// switching between two project pages without remounting kept the old data).
watch(projectId, loadProject, { immediate: true })

function goBack() {
  router.back()
}
</script>

<template>
  <div class="space-y-6">
    <!-- Breadcrumb Navigation -->
    <div class="flex items-center gap-2 text-sm">
      <button
        @click="goBack"
        class="text-indigo-600 hover:text-indigo-700 font-medium flex items-center gap-1 dark:text-indigo-400 dark:text-indigo-300"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Back to Analysis
      </button>
      <span class="text-slate-400 dark:text-slate-500">/</span>
      <span class="text-slate-600 dark:text-slate-400">{{ project?.name || 'Project Details' }}</span>
    </div>

    <!-- Loading State -->
    <div v-if="projectLoading" class="space-y-6">
      <div class="bg-white rounded-lg border border-slate-200 p-6 animate-pulse dark:bg-slate-900 dark:border-slate-700">
        <div class="h-8 bg-slate-200 rounded w-1/3 mb-4 dark:bg-slate-700"></div>
        <div class="h-4 bg-slate-100 rounded w-2/3 mb-6 dark:bg-slate-800"></div>
        <div class="grid grid-cols-6 gap-4">
          <div v-for="i in 6" :key="i" class="h-16 bg-slate-100 rounded dark:bg-slate-800"></div>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="projectError" class="bg-white rounded-lg border border-red-200 p-8 text-center dark:bg-slate-900 dark:border-red-500/30">
      <svg class="w-12 h-12 text-red-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <h3 class="text-lg font-semibold text-red-700 mb-2 dark:text-red-300">Error Loading Project</h3>
      <p class="text-sm text-red-600 mb-4 dark:text-red-400">{{ projectError }}</p>
      <button
        @click="loadProject"
        class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
      >
        Retry
      </button>
    </div>

    <!-- Project Content -->
    <div v-else-if="project" class="space-y-6">
      <!-- Project Metrics -->
      <div>
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100">Project Metrics</h3>
          <div class="flex items-center gap-2">
            <router-link
              :to="{ name: 'project-diff', params: { id: project.id } }"
              class="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-slate-700 bg-slate-100 rounded-md hover:bg-slate-200 transition-colors dark:text-slate-300 dark:bg-slate-800 dark:bg-slate-700"
            >
              Diff vs previous
            </router-link>
            <button
              @click="handleRefreshProject"
              :disabled="projectLoading"
              class="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-md hover:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:text-indigo-400 dark:bg-indigo-500/15 dark:hover:bg-indigo-500/25"
            >
              <svg
                class="w-4 h-4"
                :class="{ 'animate-spin': projectLoading }"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {{ projectLoading ? 'Re-analyzing...' : 'Re-analyze' }}
            </button>
          </div>
        </div>
        <ProjectMetricsCard :project="project" />
      </div>

      <!-- Health -->
      <HealthBreakdownPanel :project-id="project.id" />

      <!-- Dependencies -->
      <DependencyPanel :dependencies="project.dependencies || []" />

      <!-- Dependency license compliance -->
      <DependencyLicensePanel :project="project" @updated="(p) => (project = p)" />

      <!-- Complexity hotspots -->
      <ComplexityPanel
        :functions="project.complex_functions || []"
        :project-path="project.path"
      />

      <!-- TODOs -->
      <TodoInspector
        :items="project.todo_items || []"
        :project-path="project.path"
      />

      <!-- Notes -->
      <ProjectNotesEditor
        :project-id="project.id"
        :initial-notes="project.notes || ''"
      />

      <!-- Git Statistics -->
      <div>
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100">Git History Visualization</h3>
          <button
            @click="refreshGitStats"
            :disabled="gitLoading"
            class="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-md hover:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:text-indigo-400 dark:bg-indigo-500/15 dark:hover:bg-indigo-500/25"
          >
            <svg
              class="w-4 h-4"
              :class="{ 'animate-spin': gitLoading }"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {{ gitLoading ? 'Refreshing...' : 'Refresh' }}
          </button>
        </div>
        <div v-if="!gitLoading && !gitError && gitStats && !isGitRepo"
             class="bg-white rounded-lg border border-slate-200 p-6 text-center text-slate-500 dark:bg-slate-900 dark:border-slate-700 dark:text-slate-400">
          This project is not a Git repository.
        </div>
        <GitStatsContainer
          v-else
          :stats="gitStats"
          :loading="gitLoading"
          :error="gitError"
        />
      </div>
    </div>
  </div>
</template>
