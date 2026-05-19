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
}

export interface AnalysisListItem {
  id: number
  directory_path: string
  analyzed_at: string
  status: string
  total_projects: number
  total_files: number
  total_lines: number
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
