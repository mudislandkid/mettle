export interface AnalysisFilters {
  github_user: string | null
  skip_public_sdks: boolean
  max_files: number
  include_internal: boolean
}

export interface Tag {
  id: number
  name: string
  color: string
}

export interface SecretMatch {
  file: string
  line: number
  kind: string
  snippet_hash: string
  severity: 'high' | 'medium'
}

export interface Project {
  id: number
  analysis_id: number
  name: string
  path: string
  total_dirs: number
  total_files: number
  total_lines: number
  code_lines: number
  comment_lines: number
  blank_lines: number
  characters: number
  words: number
  functions: number
  classes: number
  todos: number
  imports: number
  languages: string[]
  avg_lines_per_file: number
  code_percentage: number
  test_files: number
  test_total_lines: number
  test_code_lines: number
  test_percentage: number
  repo_url: string | null
  last_commit_at: string | null
  health_score: number
  todo_items: TodoItem[]
  dependencies: Dependency[]
  complex_functions: ComplexFunction[]
  jsx_components: number
  react_hooks: number
  async_functions: number
  interfaces: number
  type_aliases: number
  enums: number
  notes: string
  flags: string[]
  tags: Tag[]
  // Phase C — scanner output
  secrets_found: number
  secrets_detail: SecretMatch[] | null
  license_spdx: string | null
}

export interface TodoItem {
  file: string
  line: number
  marker: string
  text: string
}

export interface Dependency {
  name: string
  version: string | null
  manager: string
}

export interface ComplexFunction {
  file: string
  name: string
  qualname: string
  complexity: number
  line: number
}

export interface DependencyUsage {
  name: string
  manager: string
  project_count: number
  projects: Array<{ id: number; name: string; version: string | null }>
}

export interface DependencyUsageResponse {
  by_manager: Record<string, DependencyUsage[]>
  total_unique: number
}

export interface ProjectCompareEntry {
  id: number
  name: string
  path: string
  analysis_id: number
  analyzed_at: string
  total_files: number
  total_lines: number
  code_lines: number
  comment_lines: number
  blank_lines: number
  functions: number
  classes: number
  todos: number
  imports: number
  test_files: number
  test_total_lines: number
  avg_lines_per_file: number
  languages: string[]
  last_commit_at: string | null
  health_score: number
}

export interface ProjectCompareResponse {
  projects: ProjectCompareEntry[]
}

export interface HealthComponent {
  name: string
  score: number
  weight: number
  detail: string
}

export interface HealthBreakdown {
  project_id: number
  score: number
  components: HealthComponent[]
}

export interface ProjectMetricsSnapshot {
  analysis_id: number
  project_id: number
  analyzed_at: string
  total_files: number
  total_lines: number
  code_lines: number
  comment_lines: number
  blank_lines: number
  functions: number
  classes: number
  todos: number
  imports: number
  test_files: number
  test_total_lines: number
  test_code_lines: number
  languages: string[] | null
  health_score: number
}

export interface ProjectDiffEntry {
  metric: string
  before: number
  after: number
  delta: number
  delta_pct: number | null
}

export interface ProjectDiff {
  project_path: string
  before: ProjectMetricsSnapshot
  after: ProjectMetricsSnapshot
  entries: ProjectDiffEntry[]
  days_between: number
  languages_added: string[]
  languages_removed: string[]
}

export interface ProjectHighlight {
  id: number
  analysis_id: number
  name: string
  path: string
  total_lines: number
  total_files: number
  todos: number
  last_commit_at: string | null
  health_score: number
}

export interface ProjectHighlights {
  biggest: ProjectHighlight[]
  stalest: ProjectHighlight[]
  todo_heavy: ProjectHighlight[]
  lowest_health: ProjectHighlight[]
}

export interface Analysis {
  id: number
  directory_path: string
  analyzed_at: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  total_projects: number
  total_files: number
  total_lines: number
  total_code_lines: number
  total_functions: number
  total_classes: number
  filters_applied: AnalysisFilters | null
  error_message: string | null
  projects: Project[]
  // Phase D — enriched fields from GET /api/analysis/
  completed_at?: string | null
  duration_seconds?: number | null
  avg_health?: number | null
  secrets_found?: number
}

export interface AnalysisListItem {
  id: number
  directory_path: string
  analyzed_at: string
  status: string
  total_projects: number
  total_files: number
  total_lines: number
  // Phase D — enriched fields returned by GET /api/analysis/ (Task 8)
  completed_at?: string | null
  duration_seconds?: number | null
  avg_health?: number | null
  secrets_found?: number
  error_message?: string | null
  progress_pct?: number | null
}

export interface RecentPath {
  id: number
  path: string
  last_used: string
  use_count: number
}

export interface FlagType {
  type: string
  label: string
  color: string
}

export type AnalysisProgressStatus =
  | 'idle'
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'

export interface AnalysisProgress {
  status: AnalysisProgressStatus
  current: number
  total: number
  project_name: string
  message: string
  error?: string
  logs?: string[]
  // Reserved for richer telemetry. Backend currently emits the base
  // shape; the analyzer can populate these later without a frontend
  // type change. UI components must tolerate undefined.
  phase?: string
  started_at?: string
  projects_discovered?: number
  files_counted?: number
  todos_found?: number
  secrets_found?: number
  progress_pct?: number
}

export interface GitCommitStats {
  date: string
  commits_count: number
  lines_added: number
  lines_deleted: number
  net_lines: number
  cumulative_lines: number
  authors: string[]
}

export interface TimePatterns {
  by_hour: number[]
  by_weekday: number[]
  heatmap: [number, number, number][]
}

export interface AuthorStats {
  author: string
  commits: number
  lines_added: number
  lines_deleted: number
  net_lines: number
  first_commit_date: string
  last_commit_date: string
}

export interface GitStatsResponse {
  project_id: number
  project_name: string
  is_git_repo: boolean
  total_commits: number
  first_commit_date: string | null
  last_commit_date: string | null
  unique_authors: number
  commits: GitCommitStats[]
  monthly_commits: Record<string, number>
  weekly_commits: Record<string, number>
  heatmap_data: [string, number][]
  time_patterns: TimePatterns
  authors: AuthorStats[]
}

// Phase D — cross-project digest types
// Mirrors web/backend/schemas/digest.py (Pydantic) and mettle/digest.py (dataclasses).
export interface DigestEntry {
  project_id: number
  project_name: string
  project_path: string
  repo_url: string | null
  headline_value: number
  headline_label: string
  baseline_value: number | null
  current_value: number | null
  extra: Record<string, unknown> | null
}

export type DigestSectionKind =
  | 'grown_most'
  | 'biggest_swing'
  | 'dependency_drift'
  | 'stalled_with_todos'
  | 'newly_stale'
  | 'new_since'
  | 'no_recent_activity'

export interface DigestSection {
  kind: DigestSectionKind
  title: string
  description: string
  entries: DigestEntry[]
  empty_message: string | null
}

export interface DigestReport {
  generated_at: string
  window_days: number
  window_start: string
  stale_days: number
  top_n: number
  total_projects: number
  projects_with_baseline: number
  projects_new: number
  projects_no_recent: number
  sections: DigestSection[]
}
