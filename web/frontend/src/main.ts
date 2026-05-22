import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { initRuntime } from './lib/runtime'
import './style.css'

// In the Tauri desktop shell we must learn the sidecar's port/token from
// Rust before any API call goes out — so block boot on initRuntime(). In
// the browser this resolves synchronously (no-op).
initRuntime()
  .catch((err) => {
    console.error('Runtime initialisation failed:', err)
  })
  .finally(() => {
    const app = createApp(App)
    app.use(router)
    app.mount('#app')
  })
