import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Konfigurasi Vite Kasirku POS PWA
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
