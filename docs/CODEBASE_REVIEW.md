# CodeCounter — Codebase Review

> Generated 2026-05-19. Survey of issues / footguns / gotchas across the Python
> core, FastAPI backend, and Vue 3 frontend. Findings are grouped by severity
> with file:line references so each one can be jumped to directly.

---

## Top 10 things to fix first

In rough order of risk-to-effort:

1. **Path-traversal & unauth filesystem reads in the backend.** `POST /api/analysis/start`, `POST /projects/{id}/refresh`, `POST /api/validate-path`, and `GET /api/recent-paths` all accept or expose absolute filesystem paths with no auth, allow-list, or jail. The moment this runs anywhere other than `localhost` it's a remote filesystem disclosure. Add an env-driven base-dir allow-list and reject anything that doesn't `Path.resolve().is_relative_to(allowed)`.
2. **Unauth websocket + predictable IDs.** `/ws/{analysis_id}` and `DELETE /api/analysis/{id}` have no auth and use sequential integers. Trivial to enumerate + wipe history.
3. **`git`-config RCE vector.** `git_analyzer_service.py` runs `git -C <user_path> log …` against arbitrary directories. A malicious `.git/config` with `core.fsmonitor`/`core.sshCommand` can execute commands when git starts. Either jail the path or run with `GIT_CONFIG_NOSYSTEM=1` + `safe.directory` + `GIT_OPTIONAL_LOCKS=0` and avoid scanning untrusted repos at all.
4. **CORS + `allow_credentials=True` + wildcard methods/headers.** Same hardening required before any non-local deployment.
5. **Sync analysis on the threadpool with no concurrency bounds.** `BackgroundTasks` + the captured `main_loop` race produces silent websocket no-ops under multi-worker uvicorn. Either move to a real task queue (RQ/celery/dramatiq) or use `asyncio.run_in_executor` with an explicit `ProcessPoolExecutor` and pass the analysis_id through a pub/sub channel, not a captured loop.
6. **SQLite has no `WAL` or `PRAGMA foreign_keys=ON`, FKs lack `ondelete=CASCADE`.** "database is locked" + orphan rows on delete are guaranteed under any concurrency.
7. **Debug `print` floods.** `directory_analyzer.get_language_stats` and `file_analyzer.analyze_file` print rich-formatted noise unconditionally. Slows batch runs hugely and corrupts JSON if anyone ever pipes stdout.
8. **`code_counter.py` wrapper duplicates the package entry point.** Same name as the package directory — confusing import shadowing risk. Delete the file; document `python -m code_counter` only.
9. **Two project tables in the frontend (`ProjectTable.vue` vs `ProjectTableNative.vue`)**, only the native one is routed. The AG Grid one is dead code carrying a CSS + module-registration cost. Pick one.
10. **`useAnalysis` runs websocket *and* polling in parallel.** Easy double-update + leaked timers on navigation. Pick one channel, scope it inside `setup()`, clean up in `onUnmounted`.

---

## Severity legend

- **HIGH** — security / data-loss / "will bite you in production".
- **MED** — correctness, performance, or maintenance pain.
- **LOW** — polish, cleanup, future-proofing.

---

## A. Python core (`code_counter/`, `batch_analyze.py`, `code_counter.py`)

### HIGH

- `code_counter/analyzers/directory_analyzer.py:142,152,160,173,179,189,200,202` — `get_language_stats` prints `[blue]Debug:` / `[red]Error:` / `[yellow]Warning:` unconditionally, ignoring `self.debug`. Floods stdout from web backend; corrupts JSON if piped.
- `code_counter/analyzers/directory_analyzer.py:226` — `os.walk(directory)` has no try/except; a single `PermissionError` (common on `~/Library`) aborts the whole scan.
- `code_counter/analyzers/file_analyzer.py:198` — `os.path.getsize(file_path)` called a second time without try/except; races on user dirs (file disappears) crash the analysis.
- `code_counter/analyzers/file_analyzer.py:231` — File opened with `encoding='utf-8'` and no `errors=`; a single Latin-1 / CP1252 file raises and the catch (line 262) silently drops it from counts.
- `code_counter/analyzers/file_analyzer.py:235` — `content.count('\n') + 1` is off-by-one for files ending in `\n`.
- `code_counter/analyzers/factory.py:140-143` — `_save_registrations` writes `.analyzer_cache.json` into `Path(__file__).parent` — i.e. the installed package directory. Pip install / Docker = read-only, raises; writable = mutating installed package per-request. Use a per-user cache path (`platformdirs`).
- `code_counter/__main__.py:88-94,100-101` — `create_analysis_directory` uses `Path('analysis')` (CWD-relative) and `get_history_file()` writes inside the install location. Output ends up wherever the server was started. Also `project_name` is user-typed via `questionary.text` — no sanitization, so `..` or `/` slips through to a path join.
- `code_counter/analyzers/directory_analyzer.py:191` — Median is `sorted(...)[len//2]`, wrong for even-length lists (should average the two middle values).
- `code_counter/analyzers/factory.py:202-203` — Blanket `endswith('.json')` returns `'JSON'` before more specific checks (e.g. `.d.ts` branch on line 206). Fragile ordering.

### MED

- `batch_analyze.py:200-254` vs `code_counter/__main__.py:206-255` — Two parallel report-generation paths (`generate_*_report` functions vs `*Reporter` classes). Big duplication; totals recomputed three times.
- `batch_analyze.py:116-119` — Sequential `subprocess.run(['git', ...], timeout=5)` per project. 100 projects ⇒ up to 500s. Parallelize.
- `batch_analyze.py:469-472` — Multi-depth `parent_dir.glob("*/*/*")` re-walks the tree and *duplicates* hits across depths — never deduped, so the same project can be analyzed twice.
- `code_counter/analyzers/directory_analyzer.py:278` — `self.largest_files[language].sort(...)` runs inside the inner file loop ⇒ O(n² log n). Use `heapq.nlargest`.
- `code_counter/analyzers/file_analyzer.py:162-171,231` — Every text file is opened twice (binary sniff + content read). Read once.
- `code_counter/analyzers/base.py:39,42` — Two full re-tokenizations of file content per file (`split` ran twice).
- `code_counter/analyzers/base.py:52` — `content.lower().count('todo')` matches `todoList`, `Todo.py` etc. — massive over-count.
- `code_counter/analyzers/python.py:18` — Regex `\[.*for.*in.*\]` can backtrack catastrophically on minified Python.
- `code_counter/analyzers/c_style.py:71` + `javascript.py:62` + `python.py:46` + `html_css.py:47,60` — Comment-line accounting can make `code_lines = total - blank - comment_lines` go *negative* when a `/* */` shares a line with code.
- `code_counter/analyzers/c_style.py:18` — `SINGLE_COMMENT = r'//.*$'` matches `//` inside string literals (`"https://..."`).
- `code_counter/analyzers/javascript.py:14` — Function pattern matches every `if(){}`, `for(){}`, `while(){}` — function counts hugely inflated.
- `code_counter/analyzers/html_css.py:15` — `selector_pattern = r'([^{}/]+){'` is far too loose; counts unreliable.
- `code_counter/__main__.py:259-264` — Bare `except Exception`; `console` referenced before assignment ⇒ `UnboundLocalError` masks the real error.
- `code_counter/analyzers/directory_analyzer.py:123-125` — Excluded-dir matching uses `os.sep`; Windows users with `/`-separated excludes silently mismatch.
- `code_counter/config_manager.py:107-110` — Inheritance does `parent.update(lang_config)` — mutates the cached parent dict, leaking config across calls.

### LOW

- `code_counter/reporters/console.py:87` (and `markdown.py:84`, `pdf.py:167,220`) — "avg line length" = `characters / lines`, but `characters` already excludes whitespace (per `base.py:39`) ⇒ semantically wrong.
- `code_counter/reporters/pdf.py:81-143` — Uses global `pyplot`; not thread-safe under FastAPI concurrent requests. Also empty-metrics path will pass empty sequences to `plt.pie` and raise.
- `code_counter/reporters/pdf.py:113-114` — `language_distribution.png` filename collides between concurrent analyses sharing an output_dir.
- `code_counter/analyzers/file_analyzer.py:187` — Logs every binary file at default verbosity.
- `code_counter/analyzers/template_analyzer.py` — Dead template, only excluded by name in factory; rename to `_template_example.py.disabled` or move to `docs/` as an example.
- `code_counter/analyzers/factory.py:265-269` — A fresh analyzer instance per file (regex re-compile per file). Cache instances.
- `code_counter/__init__.py:5` — `__version__` hard-coded; will drift from packaging metadata.
- `code_counter/__main__.py:121-129` — Unbounded re-numbering loop on existing reports (cosmetic).
- `batch_analyze.py` (541 lines) and `code_counter/reporters/pdf.py` (429 lines) — At/over the 500-line guideline; split into focused modules.

---

## B. FastAPI backend (`web/backend/`, `web/run.py`)

### HIGH

- `web/backend/main.py:36-42` — CORS `allow_origins=...` + `allow_credentials=True` + `allow_methods=["*"]` + `allow_headers=["*"]`. No env-driven prod tightening.
- `web/backend/api/routes_analysis.py:199-253` — `POST /api/analysis/start` ingests any directory the server process can read. `validate_directory` only checks `exists()`/`is_dir()`.
- `web/backend/api/routes_analysis.py:370-391` — `/ws/{analysis_id}` has no auth, no origin check, no ownership check.
- `web/backend/api/routes_analysis.py:357-367` — `DELETE /api/analysis/{id}` is unauthenticated with sequential int IDs.
- `web/backend/api/routes_projects.py:204-259` — `POST /{project_id}/refresh` rescans the stored absolute path with no auth; also leaks `str(e)` in the 500 detail.
- `web/backend/api/routes_analysis.py:57-208` — `run_analysis_sync` registered with `BackgroundTasks` runs sync work in the default 40-thread executor and uses `asyncio.run_coroutine_threadsafe(...)` against a `main_loop` captured lazily on first request. Under multi-worker uvicorn the captured loop is per-worker, so progress events drop silently when the analysis is created on a different worker than the websocket.
- `web/backend/services/git_analyzer_service.py:292-294` — `@lru_cache(maxsize=128)` claims a "5-minute TTL" but no TTL is implemented; cache is forever, unbounded by repo size.
- `web/backend/services/git_analyzer_service.py:40-50` — `git -C <user_path>` against arbitrary directories ⇒ malicious `.git/config` (`core.fsmonitor`/`core.sshCommand`) is a known RCE vector. Either jail the path or set `GIT_CONFIG_NOSYSTEM`, `safe.directory`, and avoid untrusted repos.

### MED

- `web/backend/api/routes_analysis.py:43-54` — Debug `print` statements in the broadcast path.
- `web/backend/api/routes_analysis.py:206-208` — `asyncio.get_event_loop()` is deprecated; use `asyncio.get_running_loop()` from the async handler.
- `web/backend/api/routes_analysis.py:180-196` — `str(e)` broadcast to websocket clients leaks internal paths; no server-side `traceback.format_exc()` logged.
- `web/backend/database/models.py:35,70,99-100` — FK relationships have no `ondelete="CASCADE"`; `DELETE /analyses/{id}` orphans `projects`, `project_flags`, `project_tags`.
- `web/backend/database/connection.py:9-13` — SQLite engine has no `PRAGMA journal_mode=WAL`, no `PRAGMA foreign_keys=ON`. Concurrent analysis + websocket reads = "database is locked".
- `web/backend/api/routes_analysis.py:329-354` — `list_analyses` accepts unbounded `limit` (no `Query(..., le=...)`).
- `web/backend/api/routes_projects.py:111-201` + `routes_tags.py` — All mutations unauthenticated.
- `web/backend/api/routes_export.py:152-207` — CSV export does no quote/newline escaping and no CSV-injection guard for cells starting with `=`, `+`, `-`, `@`.
- `web/backend/api/routes_export.py:211-214` — `POST /validate-path` confirms existence of arbitrary paths to anyone.
- `web/backend/main.py:28-33` — `/docs` and `/openapi.json` exposed by default; even `run.py --mode prod` advertises `/docs`.
- `web/backend/api/routes_projects.py:88` — `sort_column = getattr(Project, sort_by, ...)`; `sort_by` is user-controlled with no allowlist.
- `web/backend/api/routes_projects.py:223-227` — `sys.path.insert(0, ...)` runs per refresh request without dedup.
- `web/backend/services/analyzer_service.py:36` — `Path(directory).resolve()` follows symlinks (combine with the missing path jail = cross-mount leak).

### LOW

- `web/run.py:43-55` — Auto `pip install` / `npm install` on every start: supply-chain footgun, slow first launches.
- `web/run.py:78-95,186` — `--reload` is hardcoded for backend even in `--mode prod`.
- `web/run.py:163-178,220,225` — `cleanup()` invoked from signal handler *and* main loop; non-reentrant, `sys.exit` from a handler can deadlock; a single child crash takes everything down with no restart.
- `web/backend/api/routes_analysis.py:380-385` — WS echoes any payload the client sends back without size limit (amplification vector).
- `web/backend/api/routes_analysis.py:238` — `datetime.utcnow()` deprecated in 3.12+.
- `web/backend/database/models.py` — All counters typed `int`; SQLite is 64-bit so overflow is theoretical, but frontend formatting could break on absurd values.

---

## C. Vue 3 frontend (`web/frontend/`)

### HIGH

- `web/frontend/src/composables/useAnalysis.ts:35-73` — Websocket *and* a `setInterval` polling loop are started together; on `completed` the WS disconnects but the poller can run up to 10 min and double-fetch. Stale closure risk.
- `web/frontend/src/composables/useAnalysis.ts:35` — `useWebSocket` is invoked inside a regular function (not in `setup`); no `onUnmounted` cleanup ⇒ leaked WS + timers on navigation mid-analysis.
- `web/frontend/src/composables/useWebSocket.ts:10-35` — No reconnect, no error logging, no listener removal on close; backend restart during analysis silently drops progress.
- `web/frontend/src/components/ProjectTable.vue:100-117` — `cellRendererParams` bound to `flagTypes.value` at column-def-creation, before `onMounted` resolves; columns render with empty arrays forever (the AG Grid table is unused — see below — but still a real bug).
- `web/frontend/src/components/ProjectFlagsCell.vue:16-25` — Hardcoded `flagTypes` array duplicates the backend's `/tags/flags/types`; will silently diverge.
- `web/frontend/src/components/GitStats/LinesTrendChart.vue:127-136` — `window.addEventListener('resize')` inside a `watch` with no `removeEventListener`; also redundant with the `<v-chart :autoresize>` prop.
- `web/frontend/src/components/ProjectTable.vue:13` — `ModuleRegistry.registerModules` runs at import time but nothing routes to `ProjectTable.vue`. Entire AG Grid setup is dead code.

### MED

- `web/frontend/src/api/index.ts:16-18` — FastAPI 422 returns `detail: Array<...>`; `new Error(detail)` stringifies to `[object Object]`.
- `web/frontend/src/api/analysis.ts:46-54` — `validatePath` posts a bare string body, but the backend likely expects `{"path": "..."}` — payload-shape mismatch.
- `web/frontend/src/composables/useWebSocket.ts:7-50` — `any` for `lastMessage`/`send`/`onMessage`; defeats the typed `AnalysisProgress`.
- `web/frontend/src/components/ProjectTable.vue:129-167` — Direct mutation of `props.projects[i].flags/tags`. One-way data flow violation.
- `web/frontend/src/components/AnalysisProgress.vue:14-24` — Watcher *appends* the entire incoming logs array on every WS message ⇒ O(n²) growth and visual duplication.
- `web/frontend/src/views/ProjectDetailView.vue:50` — `loadProject()` called at script top level, not in `onMounted`; route-param changes don't refetch.
- `web/frontend/src/components/ProjectTagsCell.vue:85` + `ProjectFlagsCell.vue:76` — Dropdowns close only on `mouseleave`; keyboard/mobile users cannot dismiss.
- `web/frontend/src/composables/useAnalysis.ts:67-69` — Polling errors silently swallowed; backend down ⇒ infinite spinner.

### LOW

- `web/frontend/src/router.ts:1-22` — No 404 catch-all route.
- `web/frontend/src/types/index.ts:77` — `AnalysisProgress.status: string` too loose (backend enum is `pending|running|completed|failed`); use a string literal union.
- `web/frontend/src/main.ts:9` — Pinia installed but no stores; either remove or migrate the composables.
- `web/frontend/src/components/ExportButtons.vue:7` — `window.open('/api/export/...')` relies on Vite proxy; non-proxied prod origin will break.
- `web/frontend/src/composables/useGitStats.ts:23-24` — Sets `error.value = 'Not a Git repository'` even when the request *succeeded*; UI shows error branch.
- `web/frontend/src/components/ProjectTable.vue:207-208` — AG Grid CSS in unscoped `<style>` loads even when component isn't mounted (after deleting the unused table this goes away).

---

## D. Cross-cutting / structural

- **`code_counter.py` (12-line wrapper) vs `code_counter/` package** — Same name; `python code_counter.py` works only by Python's CWD-on-sys.path trick. README documents both — pick `python -m code_counter` and delete the wrapper.
- **Two `requirements.txt` files** — `requirements.txt` (CLI deps) and `web/requirements.txt` (backend deps). Fine as a split, but neither pins exact versions. Recommend moving to `pyproject.toml` with optional extras: `pip install -e ".[web]"`.
- **`analysis/` has 14 historical runs (~11 MB)**, including three that died mid-run (no PDF: `20260327_194047_*`, `20260327_195246_*`, `20260505_013104_*`). Already git-ignored; consider a `--keep-last N` flag for `batch_analyze.py` or just `rm -rf analysis/2026032*` to prune.
- **`web/codecounter.db`** lives inside `web/` but `analysis/` lives at the repo root. Pick one home for runtime state, e.g. `var/codecounter.db` and `var/analysis/`, both git-ignored.
- **No tests for the web backend.** `code_counter/tests/test_analyzers.py` + `test_reporters.py` cover the core but `web/backend` is untested.
- **No CI configured.** With this many footguns (especially the comment/regex parsing bugs), a small pytest run + a `ruff` lint would catch regressions cheaply.
- **`.project-mapper.db*`** at the repo root belongs to the project-mapper MCP server, not the app. The new `.gitignore` now excludes it.
- **`__pycache__` was tracked in many subdirs** (now removed). Pre-commit hook recommended: `pre-commit` + `check-added-large-files` + `python-debug-statements`.

---

## What was changed in this pass

- Removed all `__pycache__/` trees, stray `*.pyc`, and `.DS_Store` files outside `venv/`/`node_modules/`.
- Moved `report.md` → `docs/reports/example-batch-report.md`.
- Moved `SECURITY_AUDIT_2025.md` → `docs/reports/security-audit-2025.md`.
- Rewrote `.gitignore` to cover Python build artifacts, virtualenvs, Node, all DB-file variants, OS files, IDE files, project-mapper MCP cache, and `.claude/settings.local.json`. Removed the now-redundant `web/.gitignore`.
- Updated the project-structure block in `README.md` to reflect the moves.

## What was deliberately *not* changed

- `code_counter/venv/` (265 MB) — left in place; deleting a venv is irreversible local destruction. Recommend `rm -rf code_counter/venv` once you're sure nothing references it; the proper home is the repo root or `~/.venvs/codecounter`.
- `analysis/*` historical runs — left in place; these are user output, not build artifacts.
- `web/codecounter.db` — left in place; deleting wipes flags/tags history.
- `code_counter.py` shim — left in place; recommended deletion is called out above but kept until you confirm.
- No code-behavior changes were made to the analyzer / backend / frontend — only files moved and ignore rules tightened. All bugs above are *findings*, not yet fixes.
