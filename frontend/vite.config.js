import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Dev: Vite on :5173 proxies /api to Django on :8003 so everything is same-origin.
// Build: assets are served by Django under /static/.
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'build' ? '/static/' : '/',
  build: { outDir: 'dist' },
  server: {
    proxy: {
      '/api': { target: 'http://127.0.0.1:8003', changeOrigin: true },
    },
  },
}))
