import { fetchApi } from './index'
import type { Analysis, AnalysisFilters, AnalysisListItem, RecentPath } from '@/types'

export async function startAnalysis(
  directoryPath: string,
  filters?: AnalysisFilters
): Promise<{ id: number; status: string }> {
  return fetchApi('/analysis/start', {
    method: 'POST',
    body: JSON.stringify({
      directory_path: directoryPath,
      filters,
    }),
  })
}

export async function getAnalysis(id: number): Promise<Analysis> {
  return fetchApi(`/analysis/${id}`)
}

export async function getAnalysisStatus(id: number): Promise<{
  status: string
  current: number
  total: number
  message: string
}> {
  return fetchApi(`/analysis/status/${id}`)
}

export async function listAnalyses(
  limit = 20,
  offset = 0
): Promise<AnalysisListItem[]> {
  return fetchApi(`/analysis/?limit=${limit}&offset=${offset}`)
}

export async function deleteAnalysis(id: number): Promise<void> {
  await fetchApi(`/analysis/${id}`, { method: 'DELETE' })
}

export async function getRecentPaths(limit = 10): Promise<RecentPath[]> {
  return fetchApi(`/recent-paths?limit=${limit}`)
}

export async function validatePath(path: string): Promise<{
  exists: boolean
  is_directory: boolean
  path: string
}> {
  return fetchApi('/validate-path', {
    method: 'POST',
    body: JSON.stringify({ path }),
  })
}
