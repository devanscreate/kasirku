<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import { sinkronkanKatalogProduk, prosesAntreanKeluar } from './layanan/sinkronisasi'
import BilahSamping from './komponen/BilahSamping.vue'
import HeaderAtas from './komponen/HeaderAtas.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// State apakah sidebar terbuka
const sidebarTerbuka = ref(true)

const apakahPerluNavigasi = computed(() => {
  return authStore.apakahLogin && route.path !== '/login'
})

onMounted(() => {
  window.addEventListener('auth:kadaluarsa', () => {
    alert('Sesi Anda telah berakhir. Silakan login kembali.')
    router.push('/login')
  })

  // Pulihkan preferensi sidebar pengguna dari localStorage
  const tersimpan = localStorage.getItem('kasirku_sidebar_terbuka')
  if (tersimpan !== null) {
    sidebarTerbuka.value = tersimpan === 'true'
  } else {
    // Default terbuka di layar desktop luas (>= 1280px), tertutup di layar mobile/tablet
    sidebarTerbuka.value = window.innerWidth >= 1280
  }

  // Sinkronisasi otomatis awal saat aplikasi dibuka
  if (navigator.onLine) {
    sinkronkanKatalogProduk()
    prosesAntreanKeluar()
  }

  // Pintasan Keyboard Ctrl+B untuk buka/tutup sidebar
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && (e.key === 'b' || e.key === 'B')) {
      e.preventDefault()
      if (apakahPerluNavigasi.value) {
        sidebarTerbuka.value = !sidebarTerbuka.value
      }
    }
  })
})

watch(sidebarTerbuka, (val) => {
  localStorage.setItem('kasirku_sidebar_terbuka', String(val))
})
</script>

<template>
  <div class="wadah-aplikasi" :class="{ 'dengan-sidebar': apakahPerluNavigasi }">
    <!-- Bilah Samping (Sidebar Vertikal Pengganti Navbar) -->
    <BilahSamping 
      v-if="apakahPerluNavigasi"
      :terbuka="sidebarTerbuka"
      @tutup="sidebarTerbuka = false"
      @toggle="sidebarTerbuka = !sidebarTerbuka"
    />

    <!-- Area Konten Utama (Header Atas dengan Tombol 3 Garis + Isi Halaman) -->
    <div 
      class="area-konten-utama" 
      :class="{ 
        'sidebar-aktif': sidebarTerbuka && apakahPerluNavigasi,
        'tanpa-navigasi': !apakahPerluNavigasi
      }"
    >
      <!-- Header Atas (Top Bar dengan Tombol 3 Garis Hamburger) -->
      <HeaderAtas 
        v-if="apakahPerluNavigasi"
        :sidebar-terbuka="sidebarTerbuka"
        @toggle-sidebar="sidebarTerbuka = !sidebarTerbuka"
      />

      <!-- Isi Halaman Dinamis -->
      <main class="isi-halaman">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.wadah-aplikasi {
  min-height: 100vh;
  display: flex;
  background: var(--warna-latar);
  position: relative;
  overflow-x: hidden;
}

.area-konten-utama {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  transition: margin-left 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  background: var(--warna-latar);
}

/* Di Desktop (>= 1024px), geser konten saat sidebar terbuka */
@media (min-width: 1024px) {
  .area-konten-utama.sidebar-aktif {
    margin-left: 260px;
  }
}

.isi-halaman {
  flex: 1;
  min-height: 0;
}
</style>
