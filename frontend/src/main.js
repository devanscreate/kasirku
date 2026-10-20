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

// Pengelolaan Service Worker & Cache:
// Di lingkungan lokal/dev, unregister service worker dan bersihkan cache agar perubahan kode langsung tampil
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then((registrations) => {
    for (const reg of registrations) {
      reg.unregister()
    }
  })
}
if ('caches' in window) {
  caches.keys().then((names) => {
    for (const name of names) {
      caches.delete(name)
    }
  })
}
