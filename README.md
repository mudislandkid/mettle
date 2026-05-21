# 📊 Mettle

<div align="center">

![Version](https://img.shields.io/badge/version-0.9.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-brightgreen.svg)
![License](https://img.shields.io/badge/license-Apache--2.0-orange.svg)

**A triage dashboard for the AI-coding era. Honest line counts, secret + license scanning, health scoring, and a cross-project digest that tells you what actually moved across your whole portfolio.**

</div>

<div align="center">

```
  _____          _        _____                  _
 / ____|        | |      / ____|                | |
| |     ___   __| | ___ | |     ___  _   _ _ __ | |_ ___ _ __
| |    / _ \ / _` |/ _ \| |    / _ \| | | | '_ \| __/ _ \ '__|
| |___| (_) | (_| |  __/| |___| (_) | |_| | | | | ||  __/ |
 \_____\___/ \__,_|\___| \_____\___/ \__,_|_| |_|\__\___|_|
```

</div>

---

## 🤔 What does this do?

Point Mettle at a project (or a directory full of them) and get back:

- **A cross-project digest** — _the hero feature._ One report covering your whole portfolio: which projects grew most, biggest health swings, dependency drift (added / removed / version bumps), stale-but-with-open-TODOs, newly-stale, new since last run, and no-recent-activity. Markdown, JSON, or live in the web UI.
- **Honest line counts.** Blank / comment / code lines that always sum to `total_lines` — no double-counting, no `//` matched inside strings, no `if (x) {}` counted as a function.
- **Secret scanning.** Detects API keys / tokens / private keys with per-file context and severity. Surfaced in the project table, the project detail page, and the digest's `dependency_drift` cross-checks.
- **SPDX license detection.** Identifies `LICENSE` / `COPYING` files and resolves them to SPDX identifiers (Apache-2.0, MIT, GPL-3.0-only, etc.). Flags projects missing a license entirely.
- **Structural metrics.** Functions, classes, imports, TODO/FIXME/XXX/HACK markers (with file + line capture for inspection), per-language.
- **Python AST analysis.** Stdlib `ast` walker counts async functions, nested defs, decorators-with-arguments, set/dict/generator comprehensions, and per-function McCabe cyclomatic complexity. Falls back to the regex analyzer on `SyntaxError`.
- **Test-code segregation.** Detects test files by filename/dir convention so a 30k-line project doesn't read as code when 25k of it is tests.
- **Dependency inventory.** Parses `package.json` / `pyproject.toml` / `requirements.txt` / `Cargo.toml` / `go.mod` / `composer.json` / `Gemfile`.
- **Health score per project.** Composite 0-100 from comment ratio, test ratio, commit recency, TODO density, average file size, and packaging metadata — with full per-component breakdown.
- **Diff mode.** `--compare-to-last` shows per-metric deltas (and language adds/removes) vs the most recent prior run for the same directory.
- **Per-project reports** in console, Markdown, JSON, **HTML** (self-contained with inline SVG charts), and PDF.
- **Git history.** Lines-over-time, commit cadence, contribution heatmap, per-author totals, hour-of-day / day-of-week patterns.
- **Batch reports** across many projects with GitHub-owner filtering, public-SDK skipping, file-count caps, and depth-limited discovery.
- **A redesigned web UI** with three hero pages — **Digest**, **Analyze** (Empty → Running → Results), and **History** (activity heatmap + portfolio highlights + per-directory timelines). Dark slate-950 + indigo, ambient gradient, Inter + JetBrains Mono. Plus the existing per-project drill-in (TODO inspector, dependency panel, complexity panel, health breakdown, project comparison, git history charts).
- **CI / pre-commit mode** (`mettle check . --fail-on file-lines-over=500`) — non-interactive, exits non-zero on threshold violations.
- **Watch mode** (`mettle watch .`) — re-analyses on file change with debouncing, prints compact per-metric deltas.
- **mtime-based per-file cache.** Re-analysing a 5,000-file project skips disk reads + regex passes for files that haven't changed.
- **Hardened for local use.** Per-IP rate limiting, path-jail on every directory input, CSRF tokens on state-changing endpoints, and `localhost`-only bind by default. The web UI explicitly refuses to listen on non-loopback addresses without `--allow-public-bind`.
- **Extensible via entry points.** Ship a `BaseAnalyzer` subclass in your own pip package, register it under `[project.entry-points."mettle.analyzers"]`, and it loads on the next run.

It's useful when you want to:

- Open the dashboard on Monday and see what _actually_ changed across all your projects last week without scanning ten repos by hand.
- See "what languages do I actually write?" across all your projects in one table.
- Identify the largest, oldest, most-complex, or most-changed projects in a folder.
- Catch a leaked API key or missing license before you push.
- Generate a PDF/Markdown/HTML snapshot of a single codebase for a stakeholder or yourself.
- Tag and triage a sea of repos (e.g. mark which ones are vendored / wip / archived).
- Track lines-of-code evolution over time on any git repo.
- Wire a "no file > 500 lines, no function with complexity > 20" check into pre-commit / CI.

---

## 🚦 Quickstart

The fast path to a running web UI on your machine:

```bash
git clone https://github.com/mudislandkid/mettle.git
cd mettle

python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

pip install -e ".[web]"              # backend + CLI
cd web/frontend && npm install       # frontend
cd ../..                             # back to repo root

mettle web                           # dev mode: API on :8000, Vite on :5173
```

Open **http://localhost:5173**.

> **Note for pyenv users:** if `mettle web` fails with `ModuleNotFoundError: No module named 'mettle'`, your shell is resolving an old `mettle` shim ahead of the venv's binary. Run `hash -r` to refresh the command cache, or call `python -m mettle web` instead (works inside any activated venv regardless of pyenv).
>
> **Note for systems without `venv`:** if `python -m venv .venv` fails with `No module named venv`, use `python3 -m venv .venv` (or `python3.12 -m venv .venv` if you have it). Some pyenv builds of 3.10 ship without `venv`.

Or skip the UI and run a one-shot analysis from the terminal:

```bash
mettle scan /path/to/your/project              # full single-project analysis
mettle batch /path/to/your/projects/           # cross-project batch
mettle digest --since 7d --top 5 --format md   # what changed in the last week
mettle check . --fail-on file-lines-over=500   # CI/pre-commit mode
```

Run any subcommand with `--help` for flags. Full details below.

---

## ✨ Features

### 📚 Languages supported

File-extension detection covers ~28 languages including Python, JavaScript, TypeScript, HTML, CSS, Vue, JSON, YAML, Markdown, SQL, Shell, Dockerfile, XML, Ruby, Java, C / C++, Go, Rust, PHP, Swift, Objective-C, Kotlin, GraphQL, Protocol Buffers, Terraform, Mako, AsciiDoc/RST/LaTeX.

Deep structural analysis (functions / classes / imports / comments) is implemented for:

- **Python** — also tracks decorators, list comprehensions, lambda functions, f-strings.
- **JavaScript / TypeScript** — `function`, `function*`, arrow assigned to `const/let/var`, and method shorthand; **never** matches `if/for/while/switch/catch/...`.
- **HTML** — element tags, attributes (under `.html`, `.htm`, `.xhtml`, `.vue`, `.svelte`).
- **CSS** — selectors, `@media` queries (also handles `.scss`, `.sass`, `.less`, `.postcss`).
- **C-style languages** — Rust, Go, C/C++, Java, Swift, Kotlin, Objective-C (with `@interface`/`@implementation`/`@protocol`), Terraform, PHP. Strips `//` and `/* */` comments correctly even when they appear inside string literals.
- **Shell** — bash / zsh / fish. Treats `#` as a comment except in shebangs and inside string literals.

Other detected languages get accurate line counts and language attribution but no structural metrics. Drop a new analyzer into `mettle/analyzers/` and it's auto-registered (see "Extending Mettle" below).

### 📏 Metrics

- Per-file: total / code / comment / blank lines, characters (non-whitespace), words, max / avg line length, functions, classes, imports, TODO markers (word-bounded match of `TODO|FIXME|XXX|HACK`).
- Per-language aggregates: same totals plus largest files (top 5 per language via min-heap, not O(n²) sort), average and median lines per file (correct for even-length lists).
- Per-project: language breakdown, total dirs / files, code percentage.

### 🌐 Web UI

Three hero pages built on a shared slate-950 + indigo + ambient-gradient shell (Inter / JetBrains Mono):

- **Digest (`/digest`)** — cross-portfolio report with 7 ranked sections (grown most, biggest health swings, dependency drift, stalled-with-TODOs, newly stale, new since the window, no recent activity). Live param controls for window / top-N / stale-after, "Copy Markdown" action, coverage bar showing how many projects feed the report.
- **Analyze (`/`)** — three-state machine:
  - _Empty:_ path input with recent-paths dropdown + quick-reuse chips + advanced filters disclosure + a 4-card rail of recent analyses.
  - _Running:_ progress ring, 4-step phase tracker (Discover → Count → Analyze → Finalize), live counter tiles (Projects / Files / TODOs / Secrets), terminal-style console with auto-scroll.
  - _Results:_ unified summary hero (replaces the old gradient cards) + redesigned project table with search, quick-filter chips (Health <60, Has secrets, Stale, No license, No tests), bulk-action bar, inline health bar, language pills, risk cluster, SPDX badge.
- **History (`/history`)** — hero counters + 8-week GitHub-style activity heatmap + 4-card portfolio highlights grid (Biggest / Stalest / Most TODOs / Lowest health) + Runs-by-Directory with search, status filter, collapsible directory groups, growth sparkline, and per-run timeline rows with View / Diff / Delete.

Per-project drill-in (from any project row) still has:

- **TODO inspector** with marker filters (TODO / FIXME / XXX / HACK), file grouping, and text search across captured `(file, line, marker, text)` rows.
- **Dependency panel** grouped by manager with filter input and color-coded badges, plus a cross-project "who uses react?" view.
- **Complexity panel** showing top complex Python functions color-coded by McCabe thresholds (≤10 simple, ≤20 moderate, ≤50 complex, >50 untestable).
- **Secrets drawer** listing detected secrets with severity, file path, and line.
- **Health score breakdown** — per-component contribution to the composite score.
- **Project diff view** — `/project/:id/diff` shows before/after/delta for every metric across two snapshots.
- **Project comparison view** — pick 2-8 projects and render a side-by-side metrics table with per-row winner highlighting.
- **Git history**: lines-of-code trend, monthly/weekly commit bars, calendar heatmap, hour-of-day × day-of-week pattern grid, per-author bar chart. Cached with a 5-minute TTL. (ECharts is lazy-loaded in its own chunk — initial app payload stays light.)
- **Project notes** keyed by project path — survive re-analyses, auto-saved with debounce.
- **Bulk operations.** Multi-select projects via checkboxes and apply add/remove/replace operations for flags and tags (capped at 500 per call).
- **Export** any analysis to Markdown, JSON, or CSV (CSV cells safely quoted with OWASP formula-prefix escaping).

**Stack:** Vue 3 + Vite + TypeScript + Tailwind on the frontend; FastAPI + SQLModel + SQLite (WAL mode) on the backend. Progress streamed live over WebSocket with auto-reconnect and exponential backoff. 8 predefined flags (`not_mine`, `archived`, `wip`, `vendored`, `tutorial`, `fork`, `deprecated`, `production`) plus custom user tags with colors, all editable inline.

### 📦 Batch analysis

- Discovers project directories under a parent path (optional `--depth` for nested layouts, with dedup so the same project isn't analyzed twice across depths).
- Filters: `--github-user` (owner of the git remote), `--skip-public-sdks` (linux / tensorflow / esp-idf / etc.), `--max-files`, `--include-internal`, `--all`.
- Output: rich console table + optional Markdown + JSON.
- Git-remote ownership detection runs in parallel via a thread pool.

---

## 🚀 Installation

Mettle ships as a single Python package with optional extras. Everything is driven by one `mettle` command with subcommands.

**Requirements:**
- Python **3.10+**
- (Web UI only) Node.js **18+**
- SQLite (bundled with Python)
- `git` on `$PATH` (for the git-history features; everything else works without it)

### CLI only

```bash
git clone https://github.com/mudislandkid/mettle.git
cd mettle

python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

pip install -e .
```

This puts a single `mettle` command on your PATH with subcommands `scan`, `batch`, `watch`, `check`, `digest`, `web`:

```bash
mettle --help                  # list subcommands
mettle scan /path/to/project   # single-project analysis with PDF
mettle batch /path/to/parent   # batch summary across many projects
```

`python -m mettle` continues to work too. (`python batch_analyze.py` is also still there for legacy callers.)

### Web Application (CLI + web extras)

```bash
pip install -e ".[web]"              # backend deps (FastAPI, SQLModel, alembic, ...)
cd web/frontend && npm install       # frontend deps (Vue, Vite, ECharts)
cd ../..                             # back to repo root

mettle web                           # dev mode: API on :8000, Vite on :5173
```

Then open **http://localhost:5173**.

### Watch mode (optional)

`mettle watch` re-runs analysis on file changes. It needs the [`watchfiles`](https://watchfiles.helpmanual.io/) package:

```bash
pip install -e ".[watch]"            # adds watchfiles
mettle watch /path/to/project
```

### Developer install

```bash
pip install -e ".[web,dev,watch]"    # adds pytest, ruff, mypy, httpx, watchfiles
python -m pytest                     # 216 tests (CLI + backend)
```

### Reproducible installs

`pyproject.toml` declares only lower bounds. For locked installs:

```bash
pip install pip-tools
pip-compile --extra web --output-file requirements.lock pyproject.toml
pip install -r requirements.lock
```

---

## 📋 Usage

### 🌐 Web UI — `mettle web`

```bash
# Dev mode: hot-reload backend + Vite dev server (default)
mettle web
# → frontend at http://localhost:5173
# → API docs at http://localhost:8000/docs

# Backend only (useful if you want to point your own frontend at it)
mettle web --mode backend-only

# Production: build the frontend bundle, then serve everything from FastAPI
mettle web --mode prod

# Custom ports
mettle web --backend-port 8001 --frontend-port 5174

# Auto-install missing Python / npm deps on first run (off by default
# to avoid surprise installs)
mettle web --auto-install

# Bind to a non-loopback address (refused unless you explicitly allow it)
mettle web --backend-host 0.0.0.0 --allow-public-bind
```

Then in the UI:

- Hit **Analyze**, pick a directory, watch progress stream live, see the redesigned summary + project table on completion.
- Visit **History** for the activity heatmap, portfolio highlights, and per-directory timelines.
- Visit **Digest** for the cross-portfolio "what changed this week" report. Tweak the window / top-N / stale-after live; copy the markdown to share.
- Click any project row to drill into TODOs, dependencies, complexity, secrets, health breakdown, git history, and notes.
- Export an analysis to Markdown / JSON / CSV from the results header.

### 📊 Single-project analysis — `mettle scan`

```bash
# Interactive: prompts for path and project name on first run
mettle scan

# Direct
mettle scan /path/to/your/project

# Custom PDF output path
mettle scan /path/to/your/project -o custom_report.pdf

# Skip PDF / HTML
mettle scan /path/to/your/project --no-pdf
mettle scan /path/to/your/project --no-html

# Skip files over N lines (e.g. minified bundles)
mettle scan /path/to/your/project --max-lines 1000

# Exclude language buckets or directories by name
mettle scan /path/to/your/project --exclude-types Other Binary Data
mettle scan /path/to/your/project --exclude-dirs models node_modules

# Diff against the most recent prior run for this directory
mettle scan /path/to/your/project --compare-to-last

# Verbose logging (stack traces, large-file detection, etc.)
mettle scan /path/to/your/project --debug
```

#### CI / pre-commit mode — `mettle check`

Non-interactive, no PDF/HTML/Markdown writes, exits non-zero on threshold violations:

```bash
# Single threshold
mettle check /path/to/project --fail-on file-lines-over=500

# Multiple thresholds (--fail-on is repeatable)
mettle check /path/to/project \
  --fail-on file-lines-over=500 \
  --fail-on functions-over=50 \
  --fail-on cyclomatic-over=20 \
  --fail-on todo-density-over=10        # TODOs per 1k lines of code
```

Available threshold keys:

| Key | Meaning |
|-----|---------|
| `file-lines-over` | Fail if any file exceeds this many total lines. |
| `functions-over` | Fail if any file has more than this many functions. |
| `cyclomatic-over` | Fail if any Python function's McCabe complexity exceeds this. |
| `todo-density-over` | Fail if project-wide TODOs-per-1k-LOC exceeds this. |

Wire into `pre-commit` via a `repo: local` hook, or into CI as a build step. Output groups violations by rule and prints one line per offender.

#### Watch mode — `mettle watch`

Re-runs the analysis on file changes (debounced) and prints a compact per-metric delta. Needs the `[watch]` extra (`pip install -e ".[watch]"`):

```bash
mettle watch /path/to/project
mettle watch /path/to/project --watch-debounce 3000   # ms
```

Changes inside the same exclude list the analyzer normally skips (`.git`, `node_modules`, `dist/`, ...) don't trigger re-runs. `Ctrl+C` to stop.

### 📦 Batch CLI — `mettle batch`

```bash
# Basic batch — every direct subdirectory that looks like a project
mettle batch /path/to/parent/directory

# Filter to projects you own via git remote
mettle batch /path/to/parent --github-user mudislandkid

# Skip linux / tensorflow / esp-idf / react / etc.
mettle batch /path/to/parent --skip-public-sdks

# Skip vast projects (e.g. monorepos with 100k files)
mettle batch /path/to/parent --max-files 5000

# Emit a Markdown table + JSON
mettle batch /path/to/parent --markdown report.md --output results.json

# Walk deeper (handy if projects live two levels down)
mettle batch /path/to/parent --depth 2

# Treat every subdirectory as a project, ignoring heuristics
mettle batch /path/to/parent --all

# Combine
mettle batch /Volumes/Projects \
  --github-user mudislandkid \
  --skip-public-sdks \
  --max-files 5000
```

### 📰 Cross-project digest — `mettle digest`

Produces a portfolio-level "what changed" report by diffing the most recent batch run against an older baseline within the window. Output is Markdown by default (great for pasting into a journal) or JSON for piping into other tools.

```bash
# Default: last 7 days, top 5 per section, 30-day stale cutoff, Markdown to stdout
mettle digest

# Different window
mettle digest --since 1d
mettle digest --since 14d
mettle digest --since 1m

# More entries per section, looser stale threshold
mettle digest --since 30d --top 10 --stale-days 60

# JSON for machine consumption
mettle digest --format json --out digest.json
```

Sections in the report:

| Section | Meaning |
|---------|---------|
| `grown_most` | Biggest code-line increases since the start of the window. |
| `biggest_swing` | Largest health-score deltas (up or down). |
| `dependency_drift` | Added / removed / version-bumped dependencies per project. |
| `stalled_with_todos` | No commits in `stale_days` but TODOs still open. |
| `newly_stale` | Projects that crossed the stale-days line _during_ the window. |
| `new_since` | First-analyzed inside the digest window. |
| `no_recent_activity` | All analyses older than the window. |

Requires at least one historical analysis in the web DB (created by running `mettle web` and analysing a directory, or via the API). The digest reads `web/mettle.db`.

### 🔄 Analysis process (single-project CLI)

When `mettle scan` runs interactively:

1. **Project naming.** You're offered the previous name used for this directory (if any), recent project names, the directory name as default, or a fresh name. Names are sanitized against path separators and parent-dir refs.
2. **Output location.** A timestamped directory is created under `$METTLE_HOME/analysis/` (default: `~/.mettle/analysis/`). Format: `YYYYMMDD_HHMMSS_project_name`.
3. **Generated files:**
   - `<project>_analysis.md` — Markdown report
   - `<project>_analysis.html` — self-contained HTML with inline SVG charts (unless `--no-html`)
   - `<project>_analysis.pdf` — PDF with charts (unless `--no-pdf`)
   - `<project>_metrics.json` — raw metrics

### 📁 Where state lives

| Path | Purpose |
|------|---------|
| `~/.mettle/analysis/` | CLI analysis output (override with `$METTLE_HOME`). |
| `~/.mettle/history.json` | Last-used paths, recent project names. |
| `~/.cache/mettle/analyzer_cache.json` | Auto-discovered analyzer registrations (honors `$XDG_CACHE_HOME`). |
| `~/.cache/mettle/file_cache.sqlite3` | Per-file mtime cache for the analyzer. Disable with `METTLE_DISABLE_CACHE=1`. |
| `web/mettle.db` | Web UI SQLite database (created on first run). |

Nothing is written inside the installed package, so installing read-only (pip, Docker, `pipx`) works fine.

---

## ⚙️ Configuration

The CLI ships with sensible defaults baked into `mettle/config.yaml`. To override, drop a `.mettle.yaml` in:

1. The directory you run the tool from, **or**
2. The directory you're analyzing, **or**
3. Your home directory.

The first match wins. Broken YAML in a config file is reported, not silently skipped.

```yaml
# Exclusion patterns
exclude:
  directories:
    - .git
    - node_modules
    - venv
    - .venv
    - __pycache__
  files:
    - "*.pyc"
    - "*.min.js"
    - "package-lock.json"

# Per-report toggles
reports:
  console:
    enabled: true
    show_summary: true
    show_language_details: true
  markdown:
    enabled: true
    include_timestamp: true
  pdf:
    enabled: true
    include_charts: true
    page_size: letter        # letter | a4 | legal

# Language-specific options
languages:
  JavaScript:
    enabled: true
  TypeScript:
    enabled: true
    inherit_from: JavaScript     # inheritance does not mutate the parent dict
  Python:
    enabled: true
    metrics:
      - decorators
      - list_comprehensions
      - lambda_functions
      - f_strings
```

---

## 📁 Project structure

```
Mettle/
├── mettle/                         # Core analysis engine
│   ├── __init__.py
│   ├── __main__.py                 # python -m mettle entry → CLI
│   ├── cli.py                      # Click app: scan / batch / watch / check / web / digest
│   ├── digest.py                   # Cross-project digest: data classes, 7 section helpers, renderers
│   ├── secrets.py                  # Secret scanner: API keys, tokens, private keys
│   ├── license_detection.py        # SPDX license detector
│   ├── license_corpus.py           # Bundled SPDX text corpus for scoring
│   ├── watch.py                    # Debounced re-run + delta printing
│   ├── config.yaml                 # Bundled default configuration
│   ├── config_manager.py
│   ├── analyzers/
│   │   ├── base.py                 # BaseAnalyzer + classify_lines() + string masking
│   │   ├── cache.py                # SQLite-backed mtime cache for per-file metrics
│   │   ├── code_analyzer.py        # Top-level analyzer; orchestrates the per-project pass
│   │   ├── directory_analyzer.py   # os.walk, exclusion, per-language aggregation
│   │   ├── file_analyzer.py        # Single-file analysis, binary + generated-file detection
│   │   ├── factory.py              # Language detection + analyzer registration / entry-point plugins
│   │   ├── dependency_detection.py # package.json / pyproject.toml / requirements.txt / Cargo.toml / go.mod
│   │   ├── test_detection.py       # Filename/dir heuristics for test code segregation
│   │   ├── python.py               # Regex-based Python analyzer (fallback)
│   │   ├── python_ast.py           # AST-based analyzer + McCabe complexity
│   │   ├── javascript.py           # TypeScript, JSX, hooks, interfaces, enums
│   │   ├── html_css.py             # Vue / Svelte for elements
│   │   ├── c_style.py              # CStyleAnalyzer, ObjectiveCAnalyzer, ShellAnalyzer
│   │   └── template_analyzer.py    # Reference template (not auto-registered)
│   ├── metrics/file_metrics.py
│   ├── reporters/                  # console / markdown / html / pdf
│   └── tests/                      # CLI / digest / secrets / license / analyzers / cache / ...
│
├── batch_analyze.py                # Legacy batch entry (now also reachable as `mettle batch`)
│
├── web/
│   ├── backend/                    # FastAPI app
│   │   ├── main.py                 # App, CORS, lifespan, routers, security middleware
│   │   ├── config.py
│   │   ├── database/
│   │   │   ├── connection.py       # Engine + SQLite PRAGMAs (WAL, foreign_keys)
│   │   │   └── models.py           # SQLModel models with ondelete=CASCADE
│   │   ├── api/
│   │   │   ├── routes_analysis.py  # /api/analysis + WebSocket (enriched list response)
│   │   │   ├── routes_digest.py    # /api/digest/ — cross-portfolio report
│   │   │   ├── routes_projects.py  # /api/projects (flags, tags, refresh, highlights)
│   │   │   ├── routes_git.py       # /api/projects/{id}/git/stats
│   │   │   ├── routes_tags.py      # /api/tags + /api/tags/flags/types
│   │   │   └── routes_export.py    # Markdown / JSON / CSV export + path utils
│   │   ├── services/               # analyzer_service, git_analyzer_service (TTL cache + sandboxed env)
│   │   ├── schemas/                # Pydantic mirrors (analysis, digest, common, git, tags)
│   │   ├── security/               # CSRF, rate limiter, path jail
│   │   └── tests/                  # Backend test suite (216-test total includes these)
│   ├── frontend/                   # Vue 3 + Vite + TypeScript
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── digest/         # DigestHeader, DigestSection, DigestEntry,
│   │   │   │   │                   # DependencyDriftExpansion, StaleEntryExpansion
│   │   │   │   ├── analyze/        # 3-state (Empty/Running/Results) + leaf pieces:
│   │   │   │   │                   # PathInput, ProgressRing, PhaseTracker,
│   │   │   │   │                   # SummaryHero, ProjectTable, RiskBadges, ...
│   │   │   │   ├── history/        # ActivityHeatmap, HistoryHero, PortfolioHighlights,
│   │   │   │   │                   # HighlightCard, RunsByDirectory, DirectoryGroup,
│   │   │   │   │                   # AnalysisTimelineRow, GrowthSparkline, RunsToolbar
│   │   │   │   ├── GitStats/       # ECharts visualizations (lazy-loaded vendor chunk)
│   │   │   │   └── ...             # TodoInspector, DependencyPanel, ComplexityPanel,
│   │   │   │                       # SecretsDrawer, HealthBreakdownPanel, ProjectTableNative
│   │   │   ├── views/              # AnalysisView, HistoryView, DigestView,
│   │   │   │                       # ProjectDetailView, ProjectDiffView, ProjectCompareView
│   │   │   ├── composables/        # useAnalysis, useDigest, useWebSocket, useGitStats, useTheme
│   │   │   ├── api/                # Typed API client (fetchDigest, listAnalyses, ...)
│   │   │   ├── lib/                # format.ts (fmtNum/fmtRelative/...), tone.ts (TONE/healthBucket)
│   │   │   └── types/
│   │   ├── package.json
│   │   └── vite.config.ts          # ECharts split into a vendor chunk via manualChunks
│   └── run.py                      # Dev/prod launcher (invoked by `mettle web`)
│
├── alembic/                        # Migrations (incl. 0003_analysis_completed_at)
│
├── docs/
│   ├── CODEBASE_REVIEW.md          # Architectural review / threat model
│   ├── images/
│   └── reports/                    # Historical example reports
│
└── pyproject.toml                  # Single source of truth for deps + console scripts
```

CLI runtime state lives under `~/.mettle/` (not in the repo). The web UI database lives at `web/mettle.db` and is what `mettle digest` reads.

---

## 🏗️ Web application architecture

### Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + SQLModel + SQLAlchemy + SQLite (WAL, `foreign_keys=ON`, `busy_timeout=5000`) |
| Real-time | WebSocket with server-side `asyncio.run_coroutine_threadsafe` into the captured lifespan loop |
| Frontend | Vue 3 (`<script setup>`) + Vite + TypeScript |
| Styling | Tailwind CSS |
| Charts | Apache ECharts (via `vue-echarts`) |
| Tables | Native Vue table (`ProjectTableNative.vue`) — no AG Grid |

### Database schema

| Table | Purpose |
|-------|---------|
| `analyses` | One row per batch run (directory, filters, status, totals). |
| `projects` | Per-project metrics within an analysis. **Deleting an analysis cascades** to projects, flags, and tag links. |
| `project_flags` | Flag assignments. Unique on `(project_id, flag_type)`. |
| `tags` | User-defined tags with name + color. |
| `project_tags` | Many-to-many join. |
| `recent_paths` | Path autocomplete history. |

### API endpoints

All routes are prefixed under `/api/`. Backend captures the asyncio loop at startup so background-thread progress updates always broadcast to the right loop.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/analysis/start` | Start a new analysis. Returns `{id, status}`. |
| `GET` | `/api/analysis/` | List analyses (paginated; `limit` capped at 200). Each row is enriched with `avg_health`, `secrets_found`, `duration_seconds`, `completed_at`, `error_message`. |
| `GET` | `/api/analysis/{id}` | Get analysis + nested projects. |
| `GET` | `/api/analysis/status/{id}` | Lightweight status poll. |
| `DELETE` | `/api/analysis/{id}` | Delete analysis (cascades). |
| `WS` | `/api/analysis/ws/{id}` | Live progress updates. |
| `GET` | `/api/digest/` | Cross-portfolio digest report. Query params: `since` (e.g. `7d`), `top` (entries per section), `stale_days`. |
| `GET` | `/api/projects/` | List projects (filterable, sortable; supports `?stale_days=N`). |
| `GET` | `/api/projects/{id}` | Single project. |
| `PATCH` | `/api/projects/{id}/flags` | Update flags. |
| `POST` | `/api/projects/{id}/tags/{tag_id}` | Add tag. |
| `DELETE` | `/api/projects/{id}/tags/{tag_id}` | Remove tag. |
| `POST` | `/api/projects/{id}/refresh` | Re-analyze the project's directory. |
| `GET` | `/api/projects/{id}/notes` | Get free-text notes. |
| `PUT` | `/api/projects/{id}/notes` | Replace notes (auto-saved by the UI). |
| `GET` | `/api/projects/{id}/health` | Health-score breakdown (per-component). |
| `GET` | `/api/projects/{id}/diff?other=N` | Per-metric diff vs another analysis. |
| `GET` | `/api/projects/{id}/git/stats` | Git history + heatmap + per-author data. |
| `GET` | `/api/projects/highlights/?limit=N` | Top-N biggest, stalest, todo-heavy, lowest-health. |
| `GET` | `/api/projects/dependencies/?min_projects=N` | Cross-project dependency usage. |
| `GET` | `/api/projects/compare/?ids=1,2,3` | Side-by-side metrics for up to 8 projects. |
| `POST` | `/api/projects/bulk/flags` | Body: `{project_ids, flags, operation: add\|remove\|replace}`. Capped at 500 ids. |
| `POST` | `/api/projects/bulk/tags` | Body: `{project_ids, tag_id, operation: add\|remove}`. Capped at 500 ids. |
| `GET` | `/api/tags/` | List tags. |
| `POST` | `/api/tags/` | Create tag. |
| `GET` | `/api/tags/{id}` | Get tag. |
| `PATCH` | `/api/tags/{id}` | Rename / recolor tag. |
| `DELETE` | `/api/tags/{id}` | Delete tag. |
| `GET` | `/api/tags/flags/types` | Enumerate predefined flag types. |
| `GET` | `/api/markdown/{id}` | Download analysis as Markdown. |
| `GET` | `/api/json/{id}` | Download analysis as JSON. |
| `GET` | `/api/csv/{id}` | Download analysis as CSV (cells safely quoted). |
| `POST` | `/api/validate-path` | Body: `{"path": "..."}`. Confirm directory exists. |
| `GET` | `/api/recent-paths` | Recent directories for autocomplete. |

### Security notes

Mettle is designed for **local / single-user use on `localhost`**. The web endpoints have no authentication (v2 will add it). What is in place for v0.9:

- **Loopback bind by default.** `mettle web` refuses to bind `--backend-host` to anything other than a loopback address unless you pass `--allow-public-bind` explicitly.
- **Per-IP rate limiting.** All routes are rate-limited (default: 60 req/min per IP) to blunt accidental loops or aggressive polling.
- **CSRF tokens.** State-changing endpoints (POST/PUT/PATCH/DELETE) require a CSRF token issued at session start.
- **Path jail.** Every directory input (`/api/analysis/start`, `/api/validate-path`, etc.) is resolved and checked against an allowlist root — symlink escapes are blocked.
- **Sandboxed git.** The git history feature shells out to `git` against directories you've pointed it at. The subprocess runs with `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`, and a scrubbed environment, so a malicious `.git/config` inside a scanned repo can't trigger code execution via `core.fsmonitor` / `core.sshCommand`.
- **OWASP formula-prefix escaping** on CSV exports so a cell starting with `=`/`+`/`-`/`@` can't fire as a formula in Excel / Sheets.

If you intend to expose Mettle beyond your machine, you still want an auth layer in front of it. See `docs/CODEBASE_REVIEW.md` for the full threat model.

---

## 🧩 Extending Mettle

### Add a new language analyzer

1. Drop a file into `mettle/analyzers/` (e.g. `ruby.py`) that defines a class ending in `Analyzer`. The factory auto-discovers it the next time `mettle` runs.
2. Subclass `BaseAnalyzer` (or `CStyleAnalyzer` if your language uses `// ... /* ... */`).
3. Use the shared `classify_lines()` helper from `base.py` to get a blank / comment / code split that always sums to `total_lines`.
4. Use class-level `re.compile(...)` constants — they're compiled once per class, not per file.

```python
import re
from .base import BaseAnalyzer, classify_lines, mask_string_literals
from ..metrics.file_metrics import FileMetrics


class RubyAnalyzer(BaseAnalyzer):
    SINGLE_COMMENT = re.compile(r'#')
    FUNCTION_PATTERN = re.compile(r'^\s*def\s+\w+', re.MULTILINE)
    CLASS_PATTERN = re.compile(r'^\s*class\s+\w+', re.MULTILINE)
    IMPORT_PATTERN = re.compile(r'^\s*(?:require|require_relative|load)\s+', re.MULTILINE)

    def analyze_content(self, content: str, file_path: str = '') -> FileMetrics:
        metrics = super().analyze_content(content, file_path)

        blank, comment, code = classify_lines(content, self.SINGLE_COMMENT, None)
        metrics.blank_lines = blank
        metrics.comment_lines = comment
        metrics.code_lines = code

        masked = mask_string_literals(content)
        masked = re.sub(r'#[^\n]*', '', masked)
        metrics.functions = len(self.FUNCTION_PATTERN.findall(masked))
        metrics.classes = len(self.CLASS_PATTERN.findall(masked))
        metrics.imports = len(self.IMPORT_PATTERN.findall(masked))
        return metrics
```

You can also register an analyzer manually via `AnalyzerFactory.register_analyzer("Ruby", RubyAnalyzer, [".rb", ".erb"])` from your own script.

### Ship an analyzer in a separate package (entry-point plugins)

You don't have to fork this repo to add a language. Ship a pip-installable package that exposes a `BaseAnalyzer` subclass with `LANGUAGE: str` and `EXTENSIONS: Iterable[str]` class attributes, then advertise it via the `mettle.analyzers` entry-point group in your own `pyproject.toml`:

```toml
[project.entry-points."mettle.analyzers"]
cobol = "my_pkg.cobol:CobolAnalyzer"
```

```python
# my_pkg/cobol.py
from mettle.analyzers.base import BaseAnalyzer
from mettle.metrics.file_metrics import FileMetrics


class CobolAnalyzer(BaseAnalyzer):
    LANGUAGE = "COBOL"
    EXTENSIONS = [".cob", ".cbl"]

    def analyze_content(self, content: str, file_path: str = "") -> FileMetrics:
        metrics = super().analyze_content(content, file_path)
        # ... fill in line classification, structural metrics, etc.
        return metrics
```

`pip install my-pkg`, then the next `mettle` run discovers `CobolAnalyzer` via `importlib.metadata.entry_points()` and routes `.cob`/`.cbl` files to it.

- Plugins **override** built-in / cached registrations for the same language.
- Extensions are normalised (lower-cased, dot-prefixed).
- A plugin that fails to import, isn't a `BaseAnalyzer` subclass, or declares no `EXTENSIONS` is logged at WARNING and skipped.
- Entry-point plugins are **not** persisted to the user cache — they're re-resolved on each run from installed package metadata, so `pip uninstall` cleanly drops the registration.

See `mettle/analyzers/README.md` for the full contract.

### Local override of bundled defaults

The bundled `mettle/config.yaml` is never written to. Override behavior with a `.mettle.yaml` in your home directory (or cwd / project dir) — see the **Configuration** section above.

---

## 🧪 Tests

```bash
pip install -e ".[web,dev]"
python -m pytest                # 216 tests (CLI + backend, full suite)
```

Or run each layer individually:

```bash
python -m pytest mettle/tests           # CLI / analyzer / digest / secrets / license
python -m pytest web/backend/tests      # API + WebSocket + security
```

The CLI test suite covers:

- a `LineSumInvariant` group that asserts `blank + comment + code == total_lines` across every analyzer
- regression tests for the bugs the rewrite fixed (`//` inside strings, JS `if(){}` being miscounted as a function, Python `#` inside strings)
- the digest module (7 section helpers, dependency diff, baseline classifier, markdown + JSON renderers)
- the secret scanner (per-kind detectors + severity)
- the SPDX license detector against a curated corpus
- coverage for the mtime cache, dependency detection, generated-file detection, the HTML / markdown reporters, CI check mode, watch mode, and entry-point analyzer plugins.

The backend test suite covers the REST routes (including the digest endpoint), the WebSocket progress channel, alembic migrations, path-jail, CSRF, and rate-limiting middleware.

CI runs the full suite on a 3 × 2 matrix (Python 3.10 / 3.11 / 3.12 × ubuntu-latest / macos-latest) on every push.

---

## 📄 License

Apache License 2.0 — see `LICENSE`.

---

## 🙏 Acknowledgments

### Tooling

This project was developed with the assistance of [Claude Code](https://claude.ai/code).

### Key dependencies

**Backend / CLI:**
- [Rich](https://rich.readthedocs.io/) — terminal formatting
- [ReportLab](https://www.reportlab.com/) — PDF generation
- [Matplotlib](https://matplotlib.org/) — chart rendering (used via Figure/Agg, not pyplot global state)
- [Questionary](https://github.com/tmbo/questionary) — interactive CLI prompts
- [PyYAML](https://pyyaml.org/) — config parsing
- [FastAPI](https://fastapi.tiangolo.com/) — web API
- [SQLModel](https://sqlmodel.tiangolo.com/) — ORM
- [Uvicorn](https://www.uvicorn.org/) — ASGI server

**Frontend:**
- [Vue 3](https://vuejs.org/) — UI framework
- [Vite](https://vitejs.dev/) — build tooling
- [TypeScript](https://www.typescriptlang.org/)
- [Tailwind CSS](https://tailwindcss.com/) — styling
- [Apache ECharts](https://echarts.apache.org/) — charts (`vue-echarts` wrapper)
- [VueUse](https://vueuse.org/) — composition utilities

All dependencies are used under their respective open-source licenses (MIT / Apache 2.0 / BSD).
