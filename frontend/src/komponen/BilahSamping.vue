<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useKoneksiStore } from '../stores/koneksi'
import ModalDonasiPelanggan from './ModalDonasiPelanggan.vue'
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
  Sparkles
} from 'lucide-vue-next'

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

const tampilModalDonasi = ref(false)

function bukaDonasi() {
  tampilModalDonasi.value = true
  // Di layar mobile/tablet, otomatis tutup sidebar drawer
  if (window.innerWidth < 1024) {
    emit('tutup')
  }
}

function tanganiPotongBelanja(data) {
  tampilModalDonasi.value = false
  window.dispatchEvent(new CustomEvent('donasi:potong-belanja', { detail: data }))
  if (route.path !== '/pos') {
    router.push('/pos')
  }
}

function navigasiKe(rute) {
  router.push(rute)
  if (window.innerWidth < 1024) {
    emit('tutup')
  }
}

// Menu Manajemen Toko (untuk peran manajer & owner)
const menuManajemen = computed(() => {
  const list = [
    { nama: 'Katalog Produk', rute: '/produk', ikon: Package, peran: ['manajer', 'owner'] },
    { nama: 'Stok Barang', rute: '/stok', ikon: Boxes, peran: ['manajer', 'owner'] },
    { nama: 'Laporan Penjualan', rute: '/laporan', ikon: BarChart3, peran: ['manajer', 'owner'] },
    { nama: 'Pengaturan Toko', rute: '/pengaturan', ikon: Settings, peran: ['owner'] }
  ]
  return list.filter(m => m.peran.includes(authStore.peran))
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
            <span class="brand-tagline">POS & Tabungan</span>
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

      <!-- Area Navigasi Scrollable (Dapat Menampung Banyak Menu ke Bawah) -->
      <nav class="nav-sidebar-scroll">
        <!-- GRUP 1: MENU UTAMA (Sesuai Permintaan: Kasir, Riwayat Struk, Donasi) -->
        <div class="grup-menu-sidebar">
          <div class="label-grup">MENU UTAMA</div>

          <!-- 1. Menu Kasir -->
          <router-link 
            to="/pos" 
            class="item-menu-sidebar"
            :class="{ 'aktif': route.path === '/pos' }"
            @click="window.innerWidth < 1024 && emit('tutup')"
          >
            <div class="ikon-wrapper">
              <ShoppingCart :size="18" />
            </div>
            <div class="teks-menu">
              <span class="nama-menu">Kasir</span>
            </div>
          </router-link>

          <!-- 2. Menu Riwayat Struk -->
          <router-link 
            to="/transaksi" 
            class="item-menu-sidebar"
            :class="{ 'aktif': route.path === '/transaksi' }"
            @click="window.innerWidth < 1024 && emit('tutup')"
          >
            <div class="ikon-wrapper">
              <Receipt :size="18" />
            </div>
            <div class="teks-menu">
              <span class="nama-menu">Riwayat Struk</span>
            </div>
          </router-link>

          <!-- 3. Menu Donasi (Celengan Tabungan Kembalian Pembeli) -->
          <button 
            type="button" 
            class="item-menu-sidebar btn-menu-donasi"
            @click="bukaDonasi"
            title="Tabungan Donasi Kembalian Pembeli"
          >
            <div class="ikon-wrapper ikon-donasi">
              <HeartHandshake :size="18" />
            </div>
            <div class="teks-menu">
              <span class="nama-menu">Donasi</span>
            </div>
            <span class="badge-tabungan-sidebar">
              <Sparkles :size="11" class="teks-emas" />
              <span>Tabungan</span>
            </span>
          </button>
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
      </nav>

      <!-- Footer Sidebar: Info Pengguna & Tombol Keluar -->
      <div class="footer-sidebar">
        <div class="kartu-user-sidebar">
          <div class="avatar-user-sidebar">
            <User :size="16" />
          </div>
          <div class="detail-user-sidebar">
            <span class="nama-user-sidebar" :title="authStore.namaLengkap">{{ authStore.namaLengkap }}</span>
            <span class="peran-user-sidebar">{{ authStore.peran }}</span>
          </div>
          <button 
            type="button" 
            class="btn-logout-sidebar" 
            @click="keluar" 
            title="Keluar dari akun kasir"
          >
            <LogOut :size="16" />
          </button>
        </div>
      </div>

      <!-- MODAL TABUNGAN DONASI PELANGGAN -->
      <ModalDonasiPelanggan 
        v-if="tampilModalDonasi" 
        @tutup="tampilModalDonasi = false" 
        @terapkanPotongBelanja="tanganiPotongBelanja" 
      />
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
  background: #0f172a;
  border-right: 1px solid #1e293b;
  display: flex;
  flex-direction: column;
  z-index: 999;
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.25);
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
  padding: 16px 18px;
  height: 60px;
  border-bottom: 1px solid #1e293b;
  flex-shrink: 0;
}

.brand-sidebar {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.logo-badge-sidebar {
  width: 32px;
  height: 32px;
  background: #ffffff;
  color: #0f172a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  font-size: 1.1rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(255, 255, 255, 0.2);
}

.brand-text {
  display: flex;
  flex-direction: column;
}

.brand-nama {
  font-size: 1.05rem;
  font-weight: 800;
  color: #ffffff;
  line-height: 1.15;
  letter-spacing: -0.02em;
}

.brand-tagline {
  font-size: 0.68rem;
  color: #94a3b8;
  font-weight: 600;
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
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
}

/* Navigasi Scrollable (Banyak Menu) */
.nav-sidebar-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 16px 12px;
  scrollbar-width: thin;
  scrollbar-color: #334155 #0f172a;
}

.nav-sidebar-scroll::-webkit-scrollbar {
  width: 5px;
}
.nav-sidebar-scroll::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 4px;
}

/* Grup Menu */
.grup-menu-sidebar {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mt-4 {
  margin-top: 18px;
}

.label-grup {
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  color: #64748b;
  padding: 4px 10px 6px 10px;
  text-transform: uppercase;
}

/* Item Menu Sidebar */
.item-menu-sidebar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.88rem;
  font-weight: 600;
  transition: all 0.15s ease;
  background: transparent;
  border: none;
  width: 100%;
  cursor: pointer;
  text-align: left;
  user-select: none;
  font-family: inherit;
}

.item-menu-sidebar:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #ffffff;
  transform: translateX(2px);
}

.item-menu-sidebar.aktif {
  background: #1e293b;
  color: #ffffff;
  font-weight: 700;
  box-shadow: inset 3px 0 0 #10b981;
}

.ikon-wrapper {
  width: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: inherit;
  flex-shrink: 0;
}

.item-menu-sidebar.aktif .ikon-wrapper {
  color: #10b981;
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
  color: #f59e0b;
}

.badge-tabungan-sidebar {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.3);
  padding: 2px 6px;
  border-radius: 9999px;
  font-size: 0.68rem;
  font-weight: 700;
}

.teks-emas {
  color: #f59e0b;
}

/* Badge Peringatan Gagal Sync */
.item-gagal-sync {
  color: #f87171 !important;
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
  padding: 12px;
  border-top: 1px solid #1e293b;
  background: #0b1120;
  flex-shrink: 0;
}

.kartu-user-sidebar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
}

.avatar-user-sidebar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #1e293b;
  color: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
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
  color: #ffffff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.peran-user-sidebar {
  font-size: 0.68rem;
  color: #94a3b8;
  text-transform: capitalize;
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
  background: rgba(239, 68, 68, 0.18);
  color: #f87171;
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
