import { fetchApi } from '.'
import type { GitStatsResponse } from '@/types'

export async function getProjectGitStats(projectId: number): Promise<GitStatsResponse> {
  return fetchApi(`/projects/${projectId}/git/stats`)
}
