<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import { sinkronkanKatalogProduk, prosesAntreanKeluar } from './layanan/sinkronisasi'
import NavigasiAtas from './komponen/NavigasiAtas.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

onMounted(() => {
  window.addEventListener('auth:kadaluarsa', () => {
    alert('Sesi Anda telah berakhir. Silakan login kembali.')
    router.push('/login')
  })

  // Sinkronisasi otomatis awal saat aplikasi dibuka
  if (navigator.onLine) {
    sinkronkanKatalogProduk()
    prosesAntreanKeluar()
  }
})
</script>

<template>
  <div class="wadah-aplikasi">
    <!-- Header Navigasi hanya tampil saat user login & bukan di halaman login -->
    <NavigasiAtas v-if="authStore.apakahLogin && route.path !== '/login'" />
    
    <main class="isi-halaman">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.wadah-aplikasi {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.isi-halaman {
  flex: 1;
}
</style>
