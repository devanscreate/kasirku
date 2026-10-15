import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { router } from './router'
import App from './App.vue'
import './gaya/index.css'

const aplikasi = createApp(App)
const pinia = createPinia()

aplikasi.use(pinia)
aplikasi.use(router)

aplikasi.mount('#app')

// Pendaftaran Service Worker untuk PWA Offline-First
if ('serviceWorker' in navigator && (window.location.protocol === 'https:' || window.location.hostname === 'localhost')) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((err) => {
      console.warn('Gagal mendaftarkan service worker:', err)
    })
  })
}
