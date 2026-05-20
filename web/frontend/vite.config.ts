import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  build: {
    // The echarts vendor chunk weighs ~660 KB minified; it's only fetched
    // on the project-detail page and is cached separately from the app
    // bundle, so the default 500 KB warning is noise.
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        // Split ECharts (and its Vue wrapper) into a separate vendor
        // chunk so the ProjectDetailView bundle stays small. ECharts is
        // only needed on the project-detail page; isolating it keeps the
        // initial app payload light and lets the chart bundle be cached
        // independently.
        manualChunks: {
          echarts: ['echarts', 'vue-echarts'],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
