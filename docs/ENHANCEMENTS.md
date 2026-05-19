# Code Counter — Enhancement Backlog

Living list of feature / accuracy improvements identified after the 2026-05-19
review pass. Status column reflects what's been done; new ideas can be added
at the end with status `proposed`.

Legend: **S** = small (~hours), **M** = medium (~day), **L** = large (multi-day).

---

## Tier 1 — High-impact, fits how this tool is actually used

| # | Title | Type | Effort | Status |
|---|-------|------|--------|--------|
| 1 | Test-code segregation | Accuracy | S | **done (2026-05-19)** |
| 2 | Health score per project | Feature | S | **done (2026-05-19)** |
| 3 | Project notes field | Feature | S | **done (2026-05-19)** |
| 4 | Diff mode — compare two analyses of the same project | Feature | M | **done (2026-05-19)** |
| 5 | AST-based analysis for Python | Accuracy | M | **done (2026-05-19)** |

### 1. Test-code segregation
**Why:** A 30k-line project might be 25k of tests. No current metric distinguishes them. "Code vs test" ratio is critical for triage.
**Sketch:** Add `test_files`, `test_lines`, `test_code_lines` to `FileMetrics`. Detect via filename (`test_*.py`, `*_test.go`, `*.spec.ts`, `*.test.tsx`) and parent dir (`tests/`, `__tests__/`, `spec/`, `cypress/`, `e2e/`). Surface on project detail page + batch summary + console.

### 2. Health score per project
**Why:** One sortable number that says "this needs love" beats scanning ten metrics.
**Sketch:** Composite 0-100 score from: comment ratio (not too low, not too high), code-to-test ratio, last-commit recency, TODO density, avg-lines-per-file (smaller = healthier), presence of `README.md` / `LICENSE` / packaging file. Expose breakdown so the score is explainable.

### 3. Project notes field
**Why:** ADHD-friendly. "What was IPL-R for again?"
**Sketch:** Free-text markdown field per project, persisted by `path` (so it survives re-analyses). New `project_notes(path, notes, updated_at)` table. Inline editable on project detail page with debounced auto-save.

### 4. Diff mode
**Why:** Most powerful "did I make progress?" answer. Two analyses of the same project at different times → see deltas.
**Sketch:** Both analyses already exist in the DB (same `path`, different `analysis_id`). New view `/project/{id}/diff/{other_id}` showing per-language deltas, top growth files, TODO delta. CLI: `code-counter --compare-to-last`.

### 5. AST-based analysis for Python
**Why:** Python's stdlib `ast` makes this a 50-line file that's perfectly accurate. Eliminates "is this triple-quoted string a docstring or just data?" guessing.
**Sketch:** New `PythonAstAnalyzer` that walks the parsed tree. Falls back to current regex-based one on `SyntaxError` (Python 2 files, partials).

---

## Tier 2 — Strong additions

| # | Title | Type | Effort | Status |
|---|-------|------|--------|--------|
| 6 | Dependency inventory | Feature | M | **done (2026-05-19)** |
| 7 | mtime-based per-file cache | Performance | M | **done (2026-05-19)** |
| 8 | Largest/oldest panels on home view | Feature | S | **done (2026-05-19)** |
| 9 | TODO inspector view | Feature | S | **done (2026-05-19)** |
| 10 | Tree-sitter for JS/TS metrics | Accuracy | M | **done (2026-05-19) — enhanced regex, no native dep** |
| 11 | Stale-project detection | Feature | S | **done (2026-05-19)** |
| 12 | Per-author git stats | Feature | S | **done (2026-05-19)** |

### 6. Dependency inventory
Parse `package.json` / `pyproject.toml` / `Cargo.toml` per project. Store `(project_id, name, version, manager)`. Detail view shows the list; batch view shows cross-tab of dep × project.

### 7. mtime-based per-file cache
Re-analyzing a 5000-file project shouldn't re-read every file. Cache `FileMetrics` keyed by `(path, mtime, size)`. Refresh time drops from minutes to seconds.

### 8. Largest/oldest panels
Top-N panels on the home / history dashboard. Pure SQL, no new tables.

### 9. TODO inspector view
Don't just count TODOs — capture them. Walk the file, store `(line_no, text)` for top N per project. Detail page shows them grouped by file.

### 10. Tree-sitter for JS/TS
Handle JSX, TS generics, optional chaining, decorators properly. `tree-sitter` PyPI package + `tree-sitter-typescript` grammar. Regex stays as fallback.

### 11. Stale-project detection
Combines git data (last commit > N days) + flags (not archived) + TODOs. One filter, immediately actionable. Requires denormalising `last_commit_date` onto Project at analysis time.

### 12. Per-author git stats
Already pulling `%an`. Group commits/lines by author. New `authors` field on git stats response + chart on project detail.

---

## Tier 3 — Polish and reach

| # | Title | Type | Effort | Status |
|---|-------|------|--------|--------|
| 13 | HTML report export | Feature | S | **done (2026-05-19)** |
| 14 | Watch mode (`code-counter watch`) | Feature | M | **done (2026-05-19)** |
| 15 | Custom analyzer plugins via entry points | DX | M | **done (2026-05-19)** |
| 16 | Bulk operations in web UI | Feature | M | **done (2026-05-19)** |
| 17 | Project comparison view | Feature | M | **done (2026-05-19)** |
| 18 | Cyclomatic complexity | Accuracy | M | **done (2026-05-19)** |
| 19 | CSV formula-prefix escaping | Security | S | **done (2026-05-19)** |
| 20 | Project URL / repo URL field | Feature | S | **done (2026-05-19)** |
| 21 | Smarter generated-file detection | Accuracy | S | **done (2026-05-19)** |
| 22 | Dark theme for web UI | UX | M | **done (2026-05-19)** |
| 23 | Pre-commit / CI check mode | Feature | S | **done (2026-05-19)** |

### 13. HTML report export
Same data as PDF, different template, ECharts embedded.

### 14. Watch mode
`code-counter watch /path` — re-runs on file changes via `watchfiles`, prints deltas.

### 15. Custom analyzer plugins
`[project.entry-points."code_counter.analyzers"]` so third-party packages can register analyzers without editing the codebase.

### 16. Bulk operations
Select N projects in the table, apply flag/tag to all. Checkbox column + bulk-action bar.

### 17. Project comparison view
Pick 2-4 projects, render side-by-side metrics table.

### 18. Cyclomatic complexity
Per-function complexity via `radon` (Python) / `lizard` (multi-lang).

### 19. CSV formula-prefix escaping
Cells starting with `=`/`+`/`-`/`@`/`\t`/`\r` get a leading `'`. We did quote-escaping; this is the remaining bite.

### 20. Project URL / repo URL field
Auto-detect via `git remote get-url origin` at analysis time. Store on Project. Clickable link in detail view.

### 21. Smarter generated-file detection
Generalise the `.json > 1 MB` skip to "low entropy / minified". Also stop counting `dist/`-style output dirs even when not in default excludes.

### 22. Dark theme for web UI
Tailwind theme toggle, persisted in `localStorage`.

### 23. Pre-commit / CI check mode
`code-counter --check --fail-on file-lines-over=500 --fail-on functions-over=50` → non-zero exit code.

---

## Rollout plan

**First batch — done 2026-05-19** (#1 → #3 → #11 → #20 → #2 → #4):

- **#1 Test-code segregation.** New `test_files` / `test_total_lines` / `test_code_lines` columns on `Project`; heuristic detector in `code_counter/analyzers/test_detection.py`; "Tests %" column in the table; production/test split in the metrics card. 5 unit tests added.
- **#3 Project notes.** `project_notes(path, notes, updated_at)` table keyed by path; `GET/PUT /api/projects/{id}/notes`; auto-saving editor on the detail page.
- **#11 Stale-project detection.** `last_commit_at` denormalized onto `Project` at analysis time; backend `?stale_days=N` filter excludes archived; frontend "Show stale only" toggle with live count.
- **#20 Repo URL.** `repo_url` denormalized onto `Project`; clickable link in metrics card with SSH → HTTPS translation and relative "last commit Xd ago".
- **#2 Health score.** Pure function `compute_health(project)` returning a 0-100 score plus 6 weighted components (comment ratio, test ratio, commit recency, TODO density, file size, metadata). Sortable column in table, full breakdown panel on detail page, dedicated `GET /api/projects/{id}/health` endpoint. 4 unit tests in `web/backend/tests/test_health_score.py`.
- **#4 Diff mode.** `GET /api/projects/{id}/diff[?other=N]` returns per-metric before/after/delta/Δ%, language adds/removes, days between. New `/project/:id/diff` route + view. CLI flag `code-counter --compare-to-last` prints the same diff against the most recent prior run for the same source directory.

**Second batch — done 2026-05-19** (#7 → #9):

- **#7 Per-file mtime cache.** New `code_counter/analyzers/cache.py` with a SQLite-backed cache keyed by `(absolute_path, mtime_ns, size)`. Cache file lives at `$XDG_CACHE_HOME/code_counter/file_cache.sqlite3`. FileAnalyzer consults it on the hot path; cache hit skips both disk read and regex passes. Hit/miss counters threaded through to the directory analyzer output; debug mode prints the savings. 8 unit tests (6 pass, 2 skip without `rich`). Disable with `CODE_COUNTER_DISABLE_CACHE=1`.
- **#9 TODO inspector.** Base analyzer now captures `(line_no, marker, text)` per TODO marker into `FileMetrics.todo_items` (capped at 50/file). DirectoryAnalyzer aggregates project-wide (capped at 500). New `Project.todo_items` JSON column. Surfaced via `ProjectResponse.todo_items` and a `TodoInspector.vue` panel on the detail page with marker filters (TODO / FIXME / XXX / HACK), text search, and grouping by file. 1 new unit test pinning the capture behavior.

**Third batch — done 2026-05-19** (#5 → #8 → #12):

- **#5 Python AST analyzer.** New `code_counter/analyzers/python_ast.py` with `PythonAstAnalyzer` using the stdlib `ast` module. Counts async functions, nested defs, decorators-with-arguments, set/dict/generator comprehensions, and f-strings exactly. Falls back to the regex `PythonAnalyzer` on `SyntaxError` (Python 2 files, partial fragments). Factory now registers `PythonAstAnalyzer` for `.py` files; the regex variant remains available for fallback. 6 new unit tests covering the regressions the AST fixes.
- **#8 Top-N panels.** New `GET /api/projects/highlights/?limit=N` returns four lists (biggest by total_lines, stalest by last_commit_at, most TODOs, lowest health) computed from the latest snapshot per project path. New `HighlightsPanels.vue` component mounted at the top of the History view. Excludes archived projects from the stalest list.
- **#12 Per-author git stats.** New `aggregate_by_author` in the git service; per-author totals (commits, lines added/deleted, net, first/last commit) flow through to `GitStatsResponse.authors`. New `AuthorBarChart.vue` (ECharts horizontal stacked bars) on the project detail page, shown only when there's more than one contributor. 3 new unit tests in `web/backend/tests/test_git_authors.py`.

**Fourth batch — done 2026-05-19** (#6 → #18 → #16):

- **#6 Dependency inventory.** New `code_counter/analyzers/dependency_detection.py` parses package.json / pyproject.toml (PEP 621 + Poetry) / requirements.txt / Cargo.toml / go.mod / composer.json / Gemfile. New `Project.dependencies` JSON column. `DependencyPanel.vue` on the detail page groups by manager with collapsible sections, filter input, and color-coded badges. New `GET /api/projects/dependencies/` aggregates across projects ("what uses react?"). 12 unit tests pin parser behavior.
- **#18 Cyclomatic complexity.** Extended `PythonAstAnalyzer` with `_function_complexity()` (McCabe formulation: if/elif, for, while, except, bool-and/or, ternaries, comprehension ifs, asserts, match arms). Per-function results are captured with class qualnames, aggregated project-wide (top 30 by complexity), persisted to `Project.complex_functions`. `ComplexityPanel.vue` displays them color-coded by McCabe thresholds (≤10 simple, ≤20 moderate, ≤50 complex, >50 untestable). 2 new unit tests cover branch counting and class qualname inclusion.
- **#16 Bulk operations.** New `POST /api/projects/bulk/flags` (add/remove/replace) and `POST /api/projects/bulk/tags` (add/remove) endpoints, both capped at 500 project IDs per call. `ProjectTableNative.vue` now has checkbox selection (per-row + select-all-visible), and a bulk-action bar appears when anything is selected — pick add/remove + a flag or tag and apply. Parent view re-fetches after a bulk operation completes.

**Fifth batch — done 2026-05-19** (#19 → #10 → #22):

- **#19 CSV formula-prefix escaping.** New `_safe_cell()` helper prefixes any cell starting with `=`/`+`/`-`/`@`/`\t`/`\r` with a single quote (OWASP-recommended mitigation). Replaced the hand-rolled CSV builder in `routes_export.py` with the stdlib `csv` module so embedded quotes / commas / newlines are also handled correctly. 5 unit tests in `web/backend/tests/test_csv_safe.py`.
- **#10 Enhanced JS/TS metrics.** Pragmatic regex-only approach (no native dep). Added JSX components, React hooks, async functions, TypeScript interfaces, type aliases, and enums to `JavaScriptAnalyzer`. New fields on `FileMetrics` + per-language aggregation + `Project` columns + `ProjectResponse` + JS/TS metrics block on the detail card. 3 new unit tests cover the new patterns.
- **#22 Dark theme.** Tailwind `class`-mode dark variant; `useTheme()` composable persists in localStorage and honors `prefers-color-scheme` on first load; theme toggle in nav; inline `<script>` in `index.html` applies the theme before Vue boots (no white flash). All 25 component files swept with `dark:` variants via a one-shot script. ECharts charts use the built-in `dark` theme when the app theme is dark.

**Sixth batch — done 2026-05-19** (#21 → #23 → #17 → #13):

- **#21 Smarter generated-file detection.** `FileAnalyzer._looks_generated()` scans the first 4 KB for explicit markers (`@generated`, `DO NOT EDIT`, `AUTOGENERATED`), sourcemap prefixes, oversized single lines (minified bundle heuristic, >4 KB), or pathological average line length (>800 chars). Generalised data-extension size cap so big JSON/CSV/SQL fixtures don't get line-counted. Added `site-packages`, `wheels`, `_build`, `_site`, `storybook-static` etc. to `DirectoryAnalyzer.default_excludes`. 6 unit tests in `test_generated_detection.py`.
- **#23 Pre-commit / CI check mode.** New `--check` + repeatable `--fail-on KEY=VALUE` argparse flags in `__main__`. `run_check_mode()` runs the analyzer non-interactively (no PDF, no history writes), enforces thresholds for `file-lines-over`, `functions-over`, `cyclomatic-over`, `todo-density-over`, and exits non-zero with grouped violations. 5 unit tests in `test_check_mode.py`.
- **#17 Project comparison view.** New `GET /api/projects/compare/?ids=1,2,3` (cap 8) returns `ProjectCompareEntry` rows for the latest snapshot of each project. New `/compare` route + `ProjectCompareView.vue` renders a side-by-side metrics table with winner-highlighting per row (higher-is-better vs lower-is-better). Wired into `ProjectTableNative.vue` as a "Compare selected" bulk action (enabled at 2-8 selections).
- **#13 HTML report export.** New `code_counter/reporters/html.py` produces a self-contained dark-themed `.html` file with inline SVG charts via matplotlib's SVG backend — no external CDN, no JS. Wired into `__main__` alongside the markdown / PDF reporters with a `--no-html` opt-out. 2 unit tests in `test_reporters.py` covering report generation, inline-SVG embedding, and HTML-escaping of project names.

**Seventh batch — done 2026-05-19** (#14 → #15):

- **#14 Watch mode.** New `code_counter/watch.py` with `run_watch()` entry point. Wired into `__main__` via `--watch` and `--watch-debounce` (default 1500 ms) flags. Uses `watchfiles` as an optional dep (`pip install -e ".[watch]"`); the change filter subclasses `DefaultFilter` so paths inside `DirectoryAnalyzer`'s excluded dirs (`.git`, `node_modules`, build outputs, etc.) don't trigger re-runs. Runs an initial baseline scan, prints totals, then on each debounced change burst re-analyzes and emits a compact delta (TODOs use inverted colour because "more" is bad). 7 unit tests in `test_watch.py`. Mutually exclusive with `--check`.
- **#15 Entry-point analyzer plugins.** `AnalyzerFactory._discover_entry_point_plugins()` reads `importlib.metadata.entry_points(group="code_counter.analyzers")` and loads anything that resolves to a `BaseAnalyzer` subclass with `LANGUAGE: str` and `EXTENSIONS: Iterable[str]` class attributes. Extensions are normalised (lower-cased, dot-prefixed). Plugins override built-in / cached registrations for the same language; one bad plugin (import error, wrong base class, missing metadata) is logged-and-skipped, never fatal. Entry-point plugins are excluded from the JSON cache file so they're re-resolved each run from installed package metadata — `pip uninstall` cleanly removes the registration. Plugin contract documented in `code_counter/analyzers/README.md`. 7 unit tests in `test_entry_point_plugins.py`.

**All Tier 3 polish items complete. Backlog clean.**
