# Contributing to Mettle

Thanks for your interest. Mettle is a small open-source project — if you
spot a bug, want a feature, or just have a question, jumping in is welcome.

## Project structure

- `mettle/` — Python package: scanner, analysers, license resolver, CLI
- `web/backend/` — FastAPI app: REST API, persistence, auth
- `web/frontend/` — Vue 3 + Vite + TypeScript SPA
- `web/frontend/src-tauri/` — Rust shell for the desktop build
- `docs/` — design specs, plans, architecture notes

## Local dev setup

```bash
# Clone
git clone https://github.com/mudislandkid/mettle.git
cd mettle

# Python: venv + install with web + dev extras
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[web,dev,watch]"

# Pre-commit hooks (ruff, whitespace, etc.)
pre-commit install

# Frontend deps
cd web/frontend
npm install
```

## Running tests

```bash
# Python (from repo root)
pytest mettle/tests/        # core
pytest web/backend/tests/   # API

# Frontend (from web/frontend/)
npm run build               # type-check + bundle
```

## Running the app in dev

Two terminals:

```bash
# Terminal 1: backend
.venv/bin/python -m uvicorn web.backend.main:app --reload --port 8000

# Terminal 2: frontend
cd web/frontend && npm run dev
```

Then open http://localhost:5173.

## Desktop build (Tauri)

```bash
cd /Volumes/1tbSSD/mettle  # repo root

# Build the PyInstaller sidecar first
.venv/bin/pyinstaller --clean --noconfirm \
  --distpath ./web/dist-sidecar --workpath ./web/build-sidecar \
  web/sidecar.spec

# Stage sidecar for Tauri
cp web/dist-sidecar/mettle-sidecar \
   web/frontend/src-tauri/binaries/mettle-sidecar-aarch64-apple-darwin

# Build the .app
cd web/frontend
npx tauri build --target aarch64-apple-darwin --bundles app
```

See `docs/DESKTOP.md` for the architecture reference.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/) prefixes:
`feat:`, `fix:`, `docs:`, `ci:`, `chore:`, `refactor:`, `test:`, `release:`.

Subject line ≤ 72 chars. Body wraps at 72.

## PR expectations

- Tests pass locally before opening the PR (`pytest`, `npm run build`)
- Pre-commit hooks pass (auto-runs `ruff` and basic hygiene checks)
- New behaviour has a test
- UI changes have a screenshot
- Linked to an issue when relevant

## Reporting bugs

Use the bug template (`.github/ISSUE_TEMPLATE/bug.yml`). Include:
- Mettle version (`mettle --version` or "About" in the app)
- macOS version
- What you tried, what happened, what you expected
- Relevant logs (Console.app, terminal output)

## Security issues

Do not file public issues for security vulnerabilities. See
[SECURITY.md](SECURITY.md) for the coordinated disclosure channel.
