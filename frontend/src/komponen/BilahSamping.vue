<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useKoneksiStore } from '../stores/koneksi'
import { 
  ShoppingCart, 
  Receipt, 
  HeartHandshake, 
  Package, 
  Boxes, 
  BarChart3, 
  Settings, 
  AlertTriangle, 
  User, 
  LogOut, 
  X, 
  Sparkles,
  Search
} from 'lucide-vue-next'

const kataKunciMenu = ref('')
const inputSearchRef = ref(null)

const props = defineProps({
  terbuka: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['tutup', 'toggle'])

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const koneksiStore = useKoneksiStore()

function navigasiKe(rute) {
  router.push(rute)
  if (window.innerWidth < 1024) {
    emit('tutup')
  }
}

// Menu Utama Kasir
const daftarMenuUtama = [
  { nama: 'Kasir (POS)', rute: '/pos', ikon: ShoppingCart, badge: null },
  { nama: 'Riwayat Transaksi', rute: '/transaksi', ikon: Receipt, badge: null },
  { nama: 'Tabungan & Donasi', rute: '/donasi', ikon: HeartHandshake, badge: 'Celengan' }
]

const menuUtamaTersaring = computed(() => {
  const q = kataKunciMenu.value.trim().toLowerCase()
  if (!q) return daftarMenuUtama
  return daftarMenuUtama.filter(m => m.nama.toLowerCase().includes(q))
})

// Menu Manajemen Toko (untuk peran manajer & owner)
const menuManajemen = computed(() => {
  const list = [
    { nama: 'Katalog Produk', rute: '/produk', ikon: Package, peran: ['manajer', 'owner'] },
    { nama: 'Stok Barang', rute: '/stok', ikon: Boxes, peran: ['manajer', 'owner'] },
    { nama: 'Laporan Penjualan', rute: '/laporan', ikon: BarChart3, peran: ['manajer', 'owner'] },
    { nama: 'Pengaturan Toko', rute: '/pengaturan', ikon: Settings, peran: ['owner'] }
  ].filter(m => m.peran.includes(authStore.peran))

  const q = kataKunciMenu.value.trim().toLowerCase()
  if (!q) return list
  return list.filter(m => m.nama.toLowerCase().includes(q))
})

function tanganiKeydownCtrlK(e) {
  if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
    e.preventDefault()
    inputSearchRef.value?.focus()
  }
}

onMounted(() => {
  window.addEventListener('keydown', tanganiKeydownCtrlK)
})

onUnmounted(() => {
  window.removeEventListener('keydown', tanganiKeydownCtrlK)
})

function keluar() {
  if (confirm('Apakah Anda yakin ingin keluar dari akun kasir?')) {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<template>
  <div class="sidebar-wrapper">
    <!-- 1. Backdrop Gelap (Khusus Mobile / Tablet saat Sidebar Terbuka) -->
    <transition name="fade">
      <div 
        v-if="terbuka" 
        class="backdrop-sidebar" 
        @click="emit('tutup')"
        aria-label="Tutup menu sidebar"
      ></div>
    </transition>

    <!-- 2. Container Bilah Samping (Sidebar) -->
    <aside 
      class="bilah-samping"
      :class="{ 'sidebar-terbuka': terbuka, 'sidebar-tertutup': !terbuka }"
    >
      <!-- Header Sidebar: Logo Toko & Tombol Tutup -->
      <div class="header-sidebar">
        <div class="brand-sidebar" @click="navigasiKe('/pos')" title="Kasirku POS">
          <div class="logo-badge-sidebar">K</div>
          <div class="brand-text">
            <span class="brand-nama">Kasirku</span>
            <span class="brand-tagline">Sistem Operasional Toko</span>
          </div>
        </div>

        <button 
          type="button" 
          class="btn-tutup-sidebar" 
          @click="emit('tutup')" 
          title="Tutup Sidebar"
        >
          <X :size="18" />
        </button>
      </div>

      <!-- Kotak Pencarian Menu Cepat -->
      <div class="sidebar-search-area">
        <div class="sidebar-search-box">
          <Search :size="14" class="ikon-search-sidebar" />
          <input 
            ref="inputSearchRef"
            v-model="kataKunciMenu" 
            type="text" 
            placeholder="Cari menu... (Ctrl+K)" 
            class="input-search-sidebar"
          />
          <button 
            v-if="kataKunciMenu" 
            class="btn-bersih-cari-sidebar" 
            @click="kataKunciMenu = ''"
            title="Hapus pencarian"
          >
            ✕
          </button>
          <kbd v-else class="kbd-sidebar">Ctrl+K</kbd>
        </div>
      </div>

      <!-- Area Navigasi Scrollable (Dapat Menampung Banyak Menu ke Bawah) -->
      <nav class="nav-sidebar-scroll">
        <!-- GRUP 1: MENU UTAMA (Kasir, Riwayat Transaksi, Tabungan & Donasi) -->
        <div v-if="menuUtamaTersaring.length > 0" class="grup-menu-sidebar">
          <div class="label-grup">MENU UTAMA</div>

          <router-link 
            v-for="item in menuUtamaTersaring"
            :key="item.rute"
            :to="item.rute" 
            class="item-menu-sidebar"
            :class="{ 
              'aktif': route.path === item.rute,
              'btn-menu-donasi': item.rute === '/donasi'
            }"
            @click="window.innerWidth < 1024 && emit('tutup')"
          >
            <div class="ikon-wrapper" :class="{ 'ikon-donasi': item.rute === '/donasi' }">
              <component :is="item.ikon" :size="18" />
            </div>
            <div class="teks-menu">
              <span class="nama-menu">{{ item.nama }}</span>
            </div>
            <span v-if="item.badge" class="badge-tabungan-sidebar">
              <Sparkles :size="11" class="teks-emas" />
              <span>{{ item.badge }}</span>
            </span>
          </router-link>
        </div>

        <!-- GRUP 2: MANAJEMEN TOKO (Untuk Manajer & Owner) -->
        <div v-if="menuManajemen.length > 0" class="grup-menu-sidebar mt-4">
          <div class="label-grup">MANAJEMEN TOKO</div>
          
          <router-link 
            v-for="item in menuManajemen" 
            :key="item.rute"
            :to="item.rute"
            class="item-menu-sidebar"
            :class="{ 'aktif': route.path === item.rute }"
            @click="window.innerWidth < 1024 && emit('tutup')"
          >
            <div class="ikon-wrapper">
              <component :is="item.ikon" :size="18" />
            </div>
            <div class="teks-menu">
              <span class="nama-menu">{{ item.nama }}</span>
            </div>
          </router-link>

          <!-- Indikator Tindakan Gagal Sync (Jika Ada) -->
          <router-link 
            v-if="koneksiStore.jumlahGagal > 0"
            to="/tindakan-gagal"
            class="item-menu-sidebar item-gagal-sync"
            :class="{ 'aktif': route.path === '/tindakan-gagal' }"
            @click="window.innerWidth < 1024 && emit('tutup')"
          >
            <div class="ikon-wrapper">
              <AlertTriangle :size="18" />
            </div>
            <div class="teks-menu">
              <span class="nama-menu">Perlu Tindakan</span>
            </div>
            <span class="badge-angka-gagal">{{ koneksiStore.jumlahGagal }}</span>
          </router-link>
        </div>

        <!-- State jika tidak ada menu cocok -->
        <div 
          v-if="menuUtamaTersaring.length === 0 && menuManajemen.length === 0" 
          class="menu-kosong-sidebar"
        >
          <span>Tidak ada menu yang sesuai</span>
        </div>
      </nav>

      <!-- Footer Sidebar: Info Pengguna & Tombol Keluar (Sesuai Mockup) -->
      <div class="footer-sidebar">
        <div class="kartu-user-sidebar">
          <div class="avatar-user-sidebar">
            <User :size="16" />
          </div>
          <div class="detail-user-sidebar">
            <span class="nama-user-sidebar" :title="authStore.namaLengkap">{{ authStore.namaLengkap }}</span>
            <span class="peran-user-sidebar">{{ authStore.namaPengguna || 'kasir' }}@kasirku.id</span>
          </div>
          <button 
            type="button" 
            class="btn-logout-sidebar" 
            @click="keluar" 
            title="Keluar dari akun kasir"
          >
            <LogOut :size="15" />
          </button>
        </div>
      </div>
    </aside>
  </div>
</template>

<style scoped>
/* Backdrop Blur untuk Mobile / Tablet (< 1024px) */
.backdrop-sidebar {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(4px);
  z-index: 998;
}

@media (max-width: 1023px) {
  .backdrop-sidebar {
    display: block;
  }
}

/* Container Bilah Samping */
.bilah-samping {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 260px;
  background: #f8f9fa;
  border-right: 1px solid #eaedf2;
  display: flex;
  flex-direction: column;
  z-index: 999;
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 2px 0 12px rgba(0, 0, 0, 0.02);
}

/* Keadaan Tertutup & Terbuka di Desktop */
@media (min-width: 1024px) {
  .bilah-samping.sidebar-tertutup {
    transform: translateX(-100%);
    box-shadow: none;
  }
  .bilah-samping.sidebar-terbuka {
    transform: translateX(0);
  }
}

/* Keadaan Tertutup & Terbuka di Mobile (< 1024px) */
@media (max-width: 1023px) {
  .bilah-samping {
    transform: translateX(-100%);
  }
  .bilah-samping.sidebar-terbuka {
    transform: translateX(0);
  }
}

/* Header Sidebar */
.header-sidebar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  height: 60px;
  border-bottom: 1px solid #eaedf2;
  flex-shrink: 0;
  background: #f8f9fa;
}

.brand-sidebar {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.logo-badge-sidebar {
  width: 36px;
  height: 36px;
  background: #6366f1;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 1.15rem;
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(99, 102, 241, 0.2);
}

.brand-text {
  display: flex;
  flex-direction: column;
}

.brand-nama {
  font-size: 1.05rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.15;
  letter-spacing: -0.02em;
}

.brand-tagline {
  font-size: 0.68rem;
  color: #64748b;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.btn-tutup-sidebar {
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.btn-tutup-sidebar:hover {
  background: #f1f5f9;
  color: #0f172a;
}

/* Kotak Pencarian Menu Cepat ala Confidency OS */
.sidebar-search-area {
  padding: 12px 14px 6px 14px;
  flex-shrink: 0;
}

.sidebar-search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #ffffff;
  border: 1px solid #eaedf2;
  border-radius: 9px;
  padding: 6px 10px;
  transition: all 0.15s ease;
}

.sidebar-search-box:focus-within {
  border-color: #6366f1;
  box-shadow: 0 0 0 1px #6366f1;
}

.ikon-search-sidebar {
  color: #94a3b8;
  flex-shrink: 0;
}

.input-search-sidebar {
  border: none;
  background: transparent;
  font-size: 0.8rem;
  color: #0f172a;
  width: 100%;
  outline: none;
  font-family: inherit;
}

.kbd-sidebar {
  font-size: 0.62rem;
  font-weight: 700;
  color: #94a3b8;
  background: #f8f9fa;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 1.5px 5px;
  font-family: inherit;
  flex-shrink: 0;
}

.btn-bersih-cari-sidebar {
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 0.75rem;
  padding: 0 2px;
  line-height: 1;
}

.btn-bersih-cari-sidebar:hover {
  color: #0f172a;
}

.menu-kosong-sidebar {
  padding: 24px 12px;
  text-align: center;
  font-size: 0.78rem;
  color: #94a3b8;
}

/* Navigasi Scrollable (Banyak Menu) */
.nav-sidebar-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 12px 12px;
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 #f8fafc;
}

.nav-sidebar-scroll::-webkit-scrollbar {
  width: 4px;
}
.nav-sidebar-scroll::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 4px;
}

/* Grup Menu */
.grup-menu-sidebar {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.mt-4 {
  margin-top: 14px;
}

.label-grup {
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #94a3b8;
  padding: 6px 10px 4px 10px;
  text-transform: uppercase;
}

/* Item Menu Sidebar: Clean Floating Card ala Confidency OS */
.item-menu-sidebar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 9px;
  color: #64748b;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.15s ease;
  background: transparent;
  border: 1px solid transparent;
  width: 100%;
  cursor: pointer;
  text-align: left;
  user-select: none;
  font-family: inherit;
}

.item-menu-sidebar:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.item-menu-sidebar.aktif {
  background: #ffffff;
  border: 1px solid #eaedf2;
  color: #0f172a;
  font-weight: 700;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.ikon-wrapper {
  width: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: inherit;
  flex-shrink: 0;
}

.item-menu-sidebar.aktif .ikon-wrapper {
  color: #6366f1;
}

.teks-menu {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nama-menu {
  display: block;
  line-height: 1.2;
}

/* Badge Donasi */
.btn-menu-donasi:hover .ikon-donasi {
  color: #6366f1;
}

.badge-tabungan-sidebar {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: #eef2ff;
  color: #6366f1;
  border: 1px solid #c7d2fe;
  padding: 1.5px 6px;
  border-radius: 6px;
  font-size: 0.65rem;
  font-weight: 700;
}

.item-menu-sidebar.aktif .badge-tabungan-sidebar {
  background: #eef2ff;
  color: #4f46e5;
  border-color: #c7d2fe;
}

.teks-emas {
  color: #6366f1;
}
.item-menu-sidebar.aktif .teks-emas {
  color: #6366f1;
}

/* Badge Peringatan Gagal Sync */
.item-gagal-sync {
  color: #dc2626 !important;
}
.badge-angka-gagal {
  background: #ef4444;
  color: #ffffff;
  font-size: 0.7rem;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 9999px;
}

/* Footer Sidebar: User Area */
.footer-sidebar {
  padding: 12px 14px;
  border-top: 1px solid #eaedf2;
  background: #f8f9fa;
  flex-shrink: 0;
}

.kartu-user-sidebar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 6px;
  border-radius: 10px;
  background: transparent;
  border: none;
}

.avatar-user-sidebar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #e0e7ff;
  color: #4338ca;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: none;
  font-weight: 700;
}

.detail-user-sidebar {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.nama-user-sidebar {
  font-size: 0.825rem;
  font-weight: 700;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.peran-user-sidebar {
  font-size: 0.68rem;
  color: #64748b;
  font-weight: 500;
}

.btn-logout-sidebar {
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.btn-logout-sidebar:hover {
  background: #fee2e2;
  color: #ef4444;
}

/* Animasi Fade Backdrop */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
