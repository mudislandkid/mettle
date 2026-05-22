import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { initRuntime } from './lib/runtime'
import './style.css'

// In the Tauri desktop shell we must learn the sidecar's port/token from
// Rust before any API call goes out — so block boot on initRuntime(). In
// the browser this resolves synchronously (no-op).
let bootError: string | null = null

initRuntime()
  .catch((err) => {
    bootError = err instanceof Error ? err.message : String(err)
    console.error('Runtime initialisation failed:', err)
  })
  .finally(() => {
    const app = createApp(App)
    app.use(router)
    app.mount('#app')
    // Fade out the boot splash once Vue has painted at least once.
    requestAnimationFrame(() => {
      const splash = document.getElementById('boot-splash')
      if (!splash) return
      if (bootError) {
        splash.classList.remove('is-leaving')
        splash.innerHTML = `
          <div style="max-width:420px;padding:24px;text-align:center;color:#fda4af;
                      font-family:Inter,system-ui,sans-serif;">
            <div style="font-size:13px;letter-spacing:0.14em;text-transform:uppercase;
                        font-weight:600;color:#fb7185;margin-bottom:10px;">
              Backend didn't start
            </div>
            <div style="font-size:13px;color:#cbd5e1;line-height:1.5;">${bootError}</div>
            <div style="font-size:11px;color:#64748b;margin-top:16px;">
              File an issue with the log if this persists.
            </div>
          </div>`
        return
      }
      splash.classList.add('is-leaving')
      setTimeout(() => splash.remove(), 260)
    })
  })
