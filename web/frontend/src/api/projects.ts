import { fetchApi } from './index'
import type {
  Project,
  Tag,
  FlagType,
  HealthBreakdown,
  ProjectDiff,
  ProjectHighlights,
  DependencyUsageResponse,
  ProjectCompareResponse,
} from '@/types'

export interface ProjectsQuery {
  analysis_id?: number
  flag?: string
  tag?: string
  exclude_flag?: string
  search?: string
  stale_days?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  limit?: number
  offset?: number
}

export async function listProjects(query: ProjectsQuery = {}): Promise<Project[]> {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      params.append(key, String(value))
    }
  })
  return fetchApi(`/projects/?${params.toString()}`)
}

export async function getProject(id: number): Promise<Project> {
  return fetchApi(`/projects/${id}`)
}

export async function refreshProjectAnalysis(id: number): Promise<Project> {
  return fetchApi(`/projects/${id}/refresh`, {
    method: 'POST',
  })
}

export async function updateProjectFlags(
  projectId: number,
  flags: string[]
): Promise<Project> {
  return fetchApi(`/projects/${projectId}/flags`, {
    method: 'PATCH',
    body: JSON.stringify({ flags }),
  })
}

export async function addTagToProject(
  projectId: number,
  tagId: number
): Promise<Project> {
  return fetchApi(`/projects/${projectId}/tags/${tagId}`, {
    method: 'POST',
  })
}

export async function removeTagFromProject(
  projectId: number,
  tagId: number
): Promise<Project> {
  return fetchApi(`/projects/${projectId}/tags/${tagId}`, {
    method: 'DELETE',
  })
}

export async function getProjectNotes(projectId: number): Promise<{ path: string; notes: string }> {
  return fetchApi(`/projects/${projectId}/notes`)
}

export async function updateProjectNotes(
  projectId: number,
  notes: string,
): Promise<{ path: string; notes: string }> {
  return fetchApi(`/projects/${projectId}/notes`, {
    method: 'PUT',
    body: JSON.stringify({ notes }),
  })
}

export async function getProjectHealth(projectId: number): Promise<HealthBreakdown> {
  return fetchApi(`/projects/${projectId}/health`)
}

export async function getProjectDiff(projectId: number, other?: number): Promise<ProjectDiff> {
  const qs = other ? `?other=${other}` : ''
  return fetchApi(`/projects/${projectId}/diff${qs}`)
}

export async function getProjectHighlights(limit = 5): Promise<ProjectHighlights> {
  return fetchApi(`/projects/highlights/?limit=${limit}`)
}

export async function getDependencyUsage(minProjects = 1): Promise<DependencyUsageResponse> {
  return fetchApi(`/projects/dependencies/?min_projects=${minProjects}`)
}

export async function compareProjects(projectIds: number[]): Promise<ProjectCompareResponse> {
  const ids = projectIds.join(',')
  return fetchApi(`/projects/compare/?ids=${encodeURIComponent(ids)}`)
}

export interface BulkResult {
  updated: number
  skipped: number
  project_ids: number[]
}

export async function bulkUpdateFlags(
  projectIds: number[],
  flags: string[],
  operation: 'add' | 'remove' | 'replace' = 'add',
): Promise<BulkResult> {
  return fetchApi('/projects/bulk/flags', {
    method: 'POST',
    body: JSON.stringify({ project_ids: projectIds, flags, operation }),
  })
}

export async function bulkUpdateTag(
  projectIds: number[],
  tagId: number,
  operation: 'add' | 'remove' = 'add',
): Promise<BulkResult> {
  return fetchApi('/projects/bulk/tags', {
    method: 'POST',
    body: JSON.stringify({ project_ids: projectIds, tag_id: tagId, operation }),
  })
}

// Tags
export async function listTags(): Promise<Tag[]> {
  return fetchApi('/tags/')
}

export async function createTag(name: string, color = '#6366f1'): Promise<Tag> {
  return fetchApi('/tags/', {
    method: 'POST',
    body: JSON.stringify({ name, color }),
  })
}

export async function updateTag(
  id: number,
  updates: { name?: string; color?: string }
): Promise<Tag> {
  return fetchApi(`/tags/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  })
}

export async function deleteTag(id: number): Promise<void> {
  await fetchApi(`/tags/${id}`, { method: 'DELETE' })
}

export async function getFlagTypes(): Promise<FlagType[]> {
  return fetchApi('/tags/flags/types')
}
