<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useShiftStore } from '../stores/shift'
import { useKoneksiStore } from '../stores/koneksi'
import { 
  Menu, 
  RefreshCw, 
  ShoppingCart, 
  Receipt, 
  Package, 
  Boxes, 
  BarChart3, 
  Settings, 
  AlertTriangle,
  User
} from 'lucide-vue-next'

const props = defineProps({
  sidebarTerbuka: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['toggleSidebar'])

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const shiftStore = useShiftStore()
const koneksiStore = useKoneksiStore()

const formatRupiah = (val) => 'Rp ' + Number(val || 0).toLocaleString('id-ID')

const infoHalaman = computed(() => {
  const p = route.path
  if (p === '/pos') return { judul: 'Kasir', sub: 'Point of Sale', ikon: ShoppingCart }
  if (p === '/transaksi') return { judul: 'Riwayat Struk', sub: 'Daftar Transaksi', ikon: Receipt }
  if (p === '/produk') return { judul: 'Katalog Produk', sub: 'Kelola Barang', ikon: Package }
  if (p === '/stok') return { judul: 'Stok Barang', sub: 'Inventori Toko', ikon: Boxes }
  if (p === '/laporan') return { judul: 'Laporan', sub: 'Statistik Penjualan', ikon: BarChart3 }
  if (p === '/pengaturan') return { judul: 'Pengaturan', sub: 'Konfigurasi Toko', ikon: Settings }
  if (p === '/tindakan-gagal') return { judul: 'Perlu Tindakan', sub: 'Gagal Sinkron', ikon: AlertTriangle }
  return { judul: 'Kasirku', sub: 'Aplikasi Kasir', ikon: ShoppingCart }
})
</script>

<template>
  <header class="header-atas">
    <!-- Sisi Kiri: Tombol 3 Garis (Hamburger) & Judul Halaman Aktif -->
    <div class="sisi-kiri-header">
      <!-- TOMBOL 3 GARIS UNTUK BUKA/TUTUP SIDEBAR -->
      <button 
        type="button" 
        class="btn-hamburger"
        :class="{ 'aktif': sidebarTerbuka }"
        @click="emit('toggleSidebar')"
        title="Buka / Tutup Sidebar Menu"
      >
        <Menu :size="20" class="ikon-hamburger" />
      </button>

      <!-- Logo Mini (Tampil Saat Sidebar Ditutup) -->
      <div 
        v-if="!sidebarTerbuka" 
        class="brand-mini-header" 
        @click="router.push('/pos')"
        title="Buka Kasir"
      >
        <div class="logo-badge-mini">K</div>
        <span class="logo-nama-mini">Kasirku</span>
        <span class="pemisah-mini">•</span>
      </div>

      <!-- Judul Halaman Aktif -->
      <div class="halaman-info-area">
        <span class="halaman-judul">{{ infoHalaman.judul }}</span>
      </div>
    </div>

    <!-- Sisi Kanan: Status Shift, Koneksi Online/Offline & Sinkronisasi -->
    <div class="sisi-kanan-header">
      <!-- Status Shift Kasir -->
      <div v-if="shiftStore.apakahShiftTerbuka" class="status-shift" title="Shift kasir aktif">
        <span class="titik-hijau"></span>
        <span class="shift-label">Shift Aktif:</span>
        <span class="shift-nominal font-angka">{{ formatRupiah(shiftStore.shiftAktif?.kas_awal || shiftStore.shiftAktif?.modal_awal || 0) }}</span>
      </div>

      <!-- Indikator Koneksi Online / Offline -->
      <div 
        class="status-koneksi"
        :class="koneksiStore.apakahOnline ? 'online' : 'offline'"
        :title="koneksiStore.apakahOnline ? 'Terhubung ke server' : 'Mode offline lokal'"
      >
        <span class="titik-koneksi"></span>
        <span class="teks-koneksi">{{ koneksiStore.apakahOnline ? 'Online' : 'Offline' }}</span>
      </div>

      <!-- Tombol Sinkronisasi Manual -->
      <button 
        type="button"
        class="btn-sinkron"
        :disabled="!koneksiStore.apakahOnline || koneksiStore.sedangSinkron"
        @click="koneksiStore.picuSinkronManual"
        title="Sinkronkan data transaksi ke server"
      >
        <RefreshCw :size="14" :class="{ 'animasi-putar': koneksiStore.sedangSinkron }" />
        <span v-if="koneksiStore.jumlahPending > 0" class="badge-pending">
          {{ koneksiStore.jumlahPending }}
        </span>
      </button>

      <!-- Avatar Ringkas Kasir -->
      <div class="user-badge-mini" :title="`${authStore.namaLengkap} (${authStore.peran})`">
        <div class="avatar-lingkar">
          <User :size="13" />
        </div>
        <span class="nama-user-mini">{{ authStore.namaLengkap }}</span>
      </div>
    </div>
  </header>
</template>

<style scoped>
.header-atas {
  height: 56px;
  background: #0f172a;
  border-bottom: 1px solid #1e293b;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  position: sticky;
  top: 0;
  z-index: 50;
  color: #ffffff;
  flex-shrink: 0;
}

.sisi-kiri-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* Tombol 3 Garis (Hamburger Button) */
.btn-hamburger {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #f8fafc;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.btn-hamburger:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
  transform: scale(1.03);
}

.btn-hamburger:active {
  transform: scale(0.96);
}

.btn-hamburger.aktif {
  background: #1e293b;
  border-color: #334155;
}

.ikon-hamburger {
  transition: transform 0.2s ease;
}

/* Brand Mini saat Sidebar Tertutup */
.brand-mini-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.logo-badge-mini {
  width: 24px;
  height: 24px;
  background: #ffffff;
  color: #0f172a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  font-size: 0.85rem;
  border-radius: 6px;
}

.logo-nama-mini {
  font-weight: 800;
  font-size: 0.95rem;
  color: #ffffff;
  letter-spacing: -0.01em;
}

.pemisah-mini {
  color: #475569;
  font-size: 0.9rem;
  margin-left: 2px;
}

/* Info Halaman */
.halaman-info-area {
  display: flex;
  align-items: center;
}

.halaman-judul {
  font-size: 1rem;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.01em;
}

/* Sisi Kanan Header */
.sisi-kanan-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Status Shift Kasir */
.status-shift {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.775rem;
  color: #e2e8f0;
}

@media (max-width: 640px) {
  .status-shift {
    display: none;
  }
}

.titik-hijau {
  width: 7px;
  height: 7px;
  background: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.6);
}

.shift-label {
  color: #94a3b8;
}

.shift-nominal {
  font-weight: 700;
  color: #ffffff;
}

/* Status Koneksi */
.status-koneksi {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  font-size: 0.75rem;
  font-weight: 600;
  color: #94a3b8;
}

.status-koneksi .titik-koneksi {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.status-koneksi.online .titik-koneksi {
  background: #10b981;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.6);
}

.status-koneksi.offline .titik-koneksi {
  background: #ef4444;
  box-shadow: 0 0 6px rgba(239, 68, 68, 0.6);
}

.status-koneksi.offline {
  color: #f87171;
}

/* Tombol Sinkron */
.btn-sinkron {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 9px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94a3b8;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-sinkron:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.badge-pending {
  background: #f59e0b;
  color: #0f172a;
  border-radius: 9999px;
  font-size: 0.68rem;
  font-weight: 800;
  padding: 1px 5px;
}

.animasi-putar {
  animation: putar 1s linear infinite;
}

@keyframes putar {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* User Badge Mini */
.user-badge-mini {
  display: flex;
  align-items: center;
  gap: 7px;
  background: rgba(255, 255, 255, 0.04);
  padding: 4px 10px 4px 5px;
  border-radius: 9999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

@media (max-width: 768px) {
  .user-badge-mini .nama-user-mini {
    display: none;
  }
  .user-badge-mini {
    padding: 3px;
  }
}

.avatar-lingkar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #1e293b;
  color: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nama-user-mini {
  font-size: 0.78rem;
  font-weight: 600;
  color: #f1f5f9;
  max-width: 110px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
