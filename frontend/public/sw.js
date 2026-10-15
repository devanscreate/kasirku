// Service Worker Kasirku Offline-First
const NAMA_CACHE = 'kasirku-cache-v1'
const BERKAS_CACHE = [
  '/',
  '/index.html',
  '/manifest.json'
]

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(NAMA_CACHE).then((cache) => {
      return cache.addAll(BERKAS_CACHE)
    })
  )
  self.skipWaiting()
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((k) => {
          if (k !== NAMA_CACHE) {
            return caches.delete(k)
          }
        })
      )
    })
  )
  self.clients.claim()
})

self.addEventListener('fetch', (e) => {
  // Hanya cache GET request dan jangan cache panggilan API /api/*
  if (e.request.method !== 'GET' || e.request.url.includes('/api/')) {
    return
  }

  e.respondWith(
    caches.match(e.request).then((responsCache) => {
      if (responsCache) {
        return responsCache
      }
      return fetch(e.request).then((responsJaringan) => {
        if (!responsJaringan || responsJaringan.status !== 200 || responsJaringan.type !== 'basic') {
          return responsJaringan
        }
        const salinan = responsJaringan.clone()
        caches.open(NAMA_CACHE).then((cache) => {
          cache.put(e.request, salinan)
        })
        return responsJaringan
      }).catch(() => {
        // Fallback offline jika navigasi halaman
        if (e.request.mode === 'navigate') {
          return caches.match('/index.html')
        }
      })
    })
  )
})
