<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { isTauri } from '@/lib/runtime'

type Stage = 'idle' | 'checking' | 'available' | 'uptodate' | 'downloading' | 'installing' | 'error'

const stage = ref<Stage>('idle')
const message = ref<string>('')
const progress = ref<number>(0)        // 0..1
const newVersion = ref<string | null>(null)
const currentVersion = ref<string>('0.9.0')

// Lazily-imported plugin modules so the browser build doesn't try to resolve
// @tauri-apps/* at runtime when we're not in the desktop shell.
async function loadUpdater() {
  const updater = await import('@tauri-apps/plugin-updater')
  const process = await import('@tauri-apps/plugin-process')
  const app = await import('@tauri-apps/api/app')
  return { updater, process, app }
}

async function checkAndInstall() {
  if (!isTauri()) return
  stage.value = 'checking'
  message.value = 'Checking GitHub for a newer release…'
  try {
    const { updater, process } = await loadUpdater()
    const update = await updater.check()
    if (!update) {
      stage.value = 'uptodate'
      message.value = `You're on the latest version (${currentVersion.value}).`
      return
    }
    newVersion.value = update.version
    stage.value = 'downloading'
    let total = 0
    let received = 0
    await update.downloadAndInstall((event) => {
      switch (event.event) {
        case 'Started':
          total = event.data.contentLength ?? 0
          message.value = total
            ? `Downloading ${(total / 1_000_000).toFixed(1)} MB…`
            : 'Downloading update…'
          break
        case 'Progress':
          received += event.data.chunkLength
          if (total) progress.value = Math.min(1, received / total)
          break
        case 'Finished':
          stage.value = 'installing'
          message.value = 'Installing update…'
          break
      }
    })
    // Relaunch into the new version. `relaunch()` re-execs the just-installed
    // app bundle; the Python sidecar is re-spawned by the new binary.
    await process.relaunch()
  } catch (err) {
    stage.value = 'error'
    message.value = err instanceof Error ? err.message : String(err)
  }
}

onMounted(async () => {
  if (!isTauri()) return
  try {
    const { app } = await loadUpdater()
    currentVersion.value = await app.getVersion()
  } catch {
    // best-effort; UI still works
  }
})
</script>

<template>
  <div v-if="isTauri()" class="flex items-center gap-2">
    <button
      @click="checkAndInstall"
      :disabled="stage === 'checking' || stage === 'downloading' || stage === 'installing'"
      class="px-3 py-1.5 text-[12px] rounded-md border border-slate-800 bg-slate-900 text-slate-300
             hover:text-slate-100 hover:border-slate-700 transition-colors flex items-center gap-1.5
             disabled:opacity-50 disabled:cursor-progress"
      :title="`Current version: ${currentVersion}`"
    >
      <svg width="13" height="13" viewBox="0 0 20 20" fill="none"
           :class="['transition-transform', (stage === 'checking' || stage === 'downloading') ? 'animate-spin' : '']">
        <path d="M10 3v10m0 0l-3.5-3.5M10 13l3.5-3.5M4 16h12" stroke="currentColor" stroke-width="1.5"
              stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <span v-if="stage === 'idle'">Check for updates</span>
      <span v-else-if="stage === 'checking'">Checking…</span>
      <span v-else-if="stage === 'downloading'">Downloading {{ Math.round(progress * 100) }}%</span>
      <span v-else-if="stage === 'installing'">Installing…</span>
      <span v-else-if="stage === 'available'">Update to {{ newVersion }}</span>
      <span v-else-if="stage === 'uptodate'">Up to date</span>
      <span v-else-if="stage === 'error'">Retry</span>
    </button>

    <!-- Tiny status line under the button for non-button states. Kept inline
         in the header so it doesn't push layout around. -->
    <span
      v-if="message && (stage === 'uptodate' || stage === 'error')"
      class="text-[11px]"
      :class="stage === 'error' ? 'text-rose-300' : 'text-slate-500'"
      :title="message"
    >
      {{ stage === 'error' ? 'Update failed' : '✓' }}
    </span>
  </div>
</template>
