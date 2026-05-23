# Desktop release — session handoff

**Last touched**: 2026-05-23. Repo + local dir just renamed from
`CodeCounter` → `mettle`. Next session: pick up at "Release checklist"
below.

This doc is the source-of-truth resume guide for the `feat/tauri-desktop`
branch. If you're a fresh Claude Code session with no context: read this
top to bottom, then `docs/DESKTOP.md` for the architecture reference.

---

## What's done

The branch `feat/tauri-desktop` is ready to ship. ~10 commits, all local
(not pushed to origin yet). Highlights:

| Commit (subject)                                                | Touches                                               |
|-----------------------------------------------------------------|-------------------------------------------------------|
| `feat(backend): sidecar entry + env-driven paths`               | `web/backend/desktop.py`, `config.py`, `sidecar.spec` |
| `feat(desktop): Tauri 2 shell with Python sidecar`              | `web/frontend/src-tauri/` whole tree, `.gitignore`    |
| `feat(desktop): frontend runtime detection + dynamic API base`  | `lib/runtime.ts`, `api/index.ts`, `lib/auth.ts`       |
| `feat(desktop): in-app updater + GH release workflow + docs`    | `UpdateButton.vue`, `.github/workflows/`              |
| `feat(analyze): native folder picker + accuracy hero copy`      | `PathInput.vue`, `AnalyzeEmptyState.vue`              |
| `fix(desktop): boot race, CORS preflight, dark theme, errors`   | `auth.py`, `lib.rs`, `useTheme.ts`, `main.ts`         |
| `feat(desktop): PAT-authenticated updater for private repo`     | `lib.rs`, `build.rs`, workflow                        |
| `ci(desktop): Apple Developer ID signing + notarization`        | workflow, docs                                        |

End-to-end works locally: the .app launches, sidecar handshakes, UI loads
in dark mode, folder picker pops the native dialog, analyses run.

## Architecture (60-second tour)

- **Tauri 2 shell** in Rust (`web/frontend/src-tauri/`) — wraps the Vue
  WebView in a native macOS window.
- **PyInstaller sidecar** (`web/backend/desktop.py` + `web/sidecar.spec`)
  — boots the existing FastAPI app on a random localhost port, prints
  `MettleReady port=N token=H` to stdout once ready (~5–7 s cold).
- **Vue frontend** (`web/frontend/src/lib/runtime.ts`) — calls Rust's
  `get_sidecar` invoke command at boot to learn the port + token,
  rewrites the API base URL accordingly.
- **Boot splash** in `index.html` covers the sidecar warm-up.
- **In-app updater** (`UpdateButton.vue` + `tauri-plugin-updater`) — polls
  a `latest.json` on the `release-manifest` branch, verifies Ed25519
  signatures against an embedded public key, downloads, swaps the bundle,
  relaunches.
- **CI** (`.github/workflows/desktop-release.yml`) — on `v*` tag push,
  builds both Mac arches in parallel (PyInstaller → `cargo tauri build`),
  uploads to the GH release, force-pushes `latest.json`.

## Release checklist

Resume from here.

### 1. Secrets (9 total)

```bash
REPO=mudislandkid/mettle

# Updater bundle signing (Ed25519 minisign)
gh secret set TAURI_SIGNING_PRIVATE_KEY --repo $REPO \
  --body "$(cat /Volumes/1tbSSD/mettle/.tauri-updater)"
gh secret set TAURI_SIGNING_PRIVATE_KEY_PASSWORD --repo $REPO --body ""

# Private-repo PAT — bakes into the binary via option_env! at compile time.
# Create at https://github.com/settings/personal-access-tokens/new
#   - Resource owner: mudislandkid
#   - Repository access: Only `mettle`
#   - Permissions: Contents read-only, Metadata read-only
gh secret set METTLE_UPDATER_PAT --repo $REPO --body "github_pat_..."

# Apple Developer ID code signing + notarization
gh secret set APPLE_CERTIFICATE --repo $REPO \
  --body "$(base64 -i /path/to/mettle-signing.p12)"
gh secret set APPLE_CERTIFICATE_PASSWORD --repo $REPO --body "<p12 password>"
gh secret set APPLE_SIGNING_IDENTITY --repo $REPO \
  --body "Developer ID Application: Greg Herriott (XXXXXXXXXX)"
gh secret set APPLE_ID --repo $REPO --body "greg.herriott@outlook.com"
gh secret set APPLE_PASSWORD --repo $REPO --body "xxxx-xxxx-xxxx-xxxx"
gh secret set APPLE_TEAM_ID --repo $REPO --body "XXXXXXXXXX"
```

Notes:
- `APPLE_SIGNING_IDENTITY` must match keychain exactly. Find it with
  `security find-identity -p codesigning -v | grep "Developer ID"`.
- `APPLE_PASSWORD` is an app-specific password, **not** the Apple ID
  password. Generate at https://appleid.apple.com → Sign-In and Security
  → App-Specific Passwords.
- The fine-grained PAT must be scoped to **just** `mettle` repo — it gets
  baked into every shipped `.app` and is extractable, so blast radius
  matters.

### 2. Push, PR, merge

```bash
git push -u origin feat/tauri-desktop
gh pr create --base main --head feat/tauri-desktop \
  --title "feat: Tauri desktop build with signed in-app updater" \
  --body "See docs/DESKTOP.md"
gh pr merge --squash --delete-branch
git checkout main && git pull
```

### 3. Cut v0.9.1

Bump `0.9.0` → `0.9.1` in **all four** of these (the updater compares
version strings literally):

- `pyproject.toml` → `[project] version`
- `web/frontend/package.json` → top-level `"version"`
- `web/frontend/src-tauri/Cargo.toml` → `[package] version`
- `web/frontend/src-tauri/tauri.conf.json` → `"version"`

Then:

```bash
git commit -am "release: v0.9.1"
git tag v0.9.1
git push origin main --tags
gh run watch --repo mudislandkid/mettle
```

The workflow takes ~7–10 min (first notarization can be 10–15 min if
Apple's notary service is cold).

### 4. Verify the in-app updater

Two ways:

**Fast wiring check** (does the PAT-authenticated manifest fetch work?):

```bash
cd /Volumes/1tbSSD/mettle/web/frontend
METTLE_UPDATER_PAT="github_pat_..." \
  npx tauri build --debug --target aarch64-apple-darwin --bundles app
open src-tauri/target/aarch64-apple-darwin/debug/bundle/macos/Mettle.app
# Click "Check for updates" — should find v0.9.1 and offer to install.
```

**Real user flow** (the production path):

1. Download the `.dmg` from the GH release.
2. Install. macOS shows a normal "downloaded from internet" prompt with
   a plain **Open** button (no right-click workaround, no
   System Settings detour — that's what notarization buys).
3. Run a quick analysis to confirm sidecar boots fine in the signed
   bundle.
4. Bump to `v0.9.2`, tag, push, wait for workflow.
5. In the running 0.9.1 app, click "Check for updates" — should auto-
   update to 0.9.2.

## Gotchas to remember

- **First `tauri build` after a fresh clone takes 10+ min** — Tauri's
  Rust deps compile cold. Subsequent builds are 30–60 s.
- **Sidecar binary is target-triple-named.** The Tauri build expects
  `web/frontend/src-tauri/binaries/mettle-sidecar-<triple>` and the
  workflow stages it. For local builds, this script does it:
  ```bash
  .venv/bin/pyinstaller --clean --noconfirm \
    --distpath ./web/dist-sidecar --workpath ./web/build-sidecar \
    web/sidecar.spec
  cp web/dist-sidecar/mettle-sidecar \
     web/frontend/src-tauri/binaries/mettle-sidecar-aarch64-apple-darwin
  ```
- **`.tauri-updater`** at the repo root is the Ed25519 **private key**.
  It's gitignored. **Back it up somewhere safe** (password manager) —
  losing it means existing users can't auto-update to any build signed
  by a new key. The `.tauri-updater.pub` next to it is the public half;
  the same value is embedded in `tauri.conf.json`.
- **Rustc reports `x86_64-apple-darwin` on this Mac** even though it's
  M-series, because Rust was installed under Rosetta. We use
  `--target aarch64-apple-darwin` explicitly. CI doesn't have this
  issue — `macos-14` runner has native aarch64 rustc.
- **Apple Silicon-only** for the local debug builds. The CI workflow
  builds both arches.

## If something breaks

- Updater says "not found" → most likely the `release-manifest` branch
  hasn't been created yet (it's only created by the `publish-manifest`
  CI job). Wait for the workflow's second job to finish.
- Updater says "signature invalid" → mismatch between the private key in
  `TAURI_SIGNING_PRIVATE_KEY` and the public key in `tauri.conf.json`.
  Regenerate the pair with `cargo tauri signer generate --write-keys
  ./.tauri-updater --password ""`, update `pubkey` in tauri.conf.json,
  rebuild the **already-installed** app (existing builds with the old
  key can never upgrade — they'd reject the new signature).
- Backend won't start in a release build → check Console.app filtered
  by "mettle" — the sidecar's stderr lands there.
