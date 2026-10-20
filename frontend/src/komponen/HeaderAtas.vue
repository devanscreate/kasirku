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
  HeartHandshake,
  Package, 
  Boxes, 
  BarChart3, 
  Settings, 
  AlertTriangle,
  User,
  Bell
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
  if (p === '/donasi') return { judul: 'Tabungan Donasi', sub: 'Celengan Kembalian Pembeli', ikon: HeartHandshake }
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
        <Menu :size="19" class="ikon-hamburger" />
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

      <!-- Tombol Notifikasi Lingkar (Sesuai Referensi Gambar) -->
      <button type="button" class="btn-notifikasi" title="Notifikasi Sistem">
        <Bell :size="16" />
        <span class="titik-notif-oranye"></span>
      </button>

      <!-- Avatar Ringkas Kasir (Gaya Bubble POS) -->
      <div class="user-badge-mini" :title="`${authStore.namaLengkap} (${authStore.peran})`">
        <div class="avatar-lingkar">
          <User :size="14" />
        </div>
        <div class="user-info-teks">
          <span class="nama-user-mini">{{ authStore.namaLengkap }}</span>
          <span class="peran-user-mini">{{ authStore.peran }}</span>
        </div>
      </div>
    </div>
  </header>
</template>

<style scoped>
.header-atas {
  height: 60px;
  background: #ffffff;
  border-bottom: 1.5px solid #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  position: sticky;
  top: 0;
  z-index: 50;
  color: #1e293b;
  flex-shrink: 0;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.02);
}

.sisi-kiri-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* Tombol 3 Garis (Hamburger Button) */
.btn-hamburger {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: #ffffff;
  border: 1.5px solid #e2e8f0;
  color: #475569;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.18s ease;
}

.btn-hamburger:hover {
  background: #eff6ff;
  border-color: #2563eb;
  color: #1d4ed8;
  transform: scale(1.03);
}

.btn-hamburger:active {
  transform: scale(0.96);
}

.btn-hamburger.aktif {
  background: #eff6ff;
  border-color: #2563eb;
  color: #1d4ed8;
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
  width: 28px;
  height: 28px;
  background: #2563eb;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  font-size: 0.95rem;
  border-radius: 8px;
  box-shadow: none;
}

.logo-nama-mini {
  font-weight: 800;
  font-size: 1rem;
  color: #0f172a;
  letter-spacing: -0.02em;
}

.pemisah-mini {
  color: #cbd5e1;
  font-size: 0.9rem;
  margin-left: 2px;
}

/* Info Halaman */
.halaman-info-area {
  display: flex;
  align-items: center;
}

.halaman-judul {
  font-size: 1.05rem;
  font-weight: 800;
  color: #0f172a;
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
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 0.775rem;
  color: #1e40af;
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
  box-shadow: none;
}

.shift-label {
  color: #1e40af;
  font-weight: 600;
}

.shift-nominal {
  font-weight: 800;
  color: #2563eb;
}

/* Status Koneksi */
.status-koneksi {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 9px;
  font-size: 0.75rem;
  font-weight: 700;
  border-radius: 9999px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #64748b;
}

.status-koneksi .titik-koneksi {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.status-koneksi.online {
  background: #ecfdf5;
  border-color: #a7f3d0;
  color: #065f46;
}
.status-koneksi.online .titik-koneksi {
  background: #10b981;
  box-shadow: none;
}

.status-koneksi.offline {
  background: #fef2f2;
  border-color: #fecaca;
  color: #991b1b;
}
.status-koneksi.offline .titik-koneksi {
  background: #ef4444;
  box-shadow: none;
}

/* Tombol Sinkron */
.btn-sinkron {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border-radius: 8px;
  background: #ffffff;
  border: 1.5px solid #e2e8f0;
  color: #64748b;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-sinkron:hover:not(:disabled) {
  background: #eff6ff;
  border-color: #2563eb;
  color: #1d4ed8;
}

.badge-pending {
  background: #2563eb;
  color: #ffffff;
  border-radius: 9999px;
  font-size: 0.68rem;
  font-weight: 800;
  padding: 1px 6px;
}

.animasi-putar {
  animation: putar 1s linear infinite;
}

@keyframes putar {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Tombol Notifikasi Lingkar */
.btn-notifikasi {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #ffffff;
  border: 1.5px solid #e2e8f0;
  color: #475569;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  transition: all 0.18s ease;
}
.btn-notifikasi:hover {
  background: #eff6ff;
  border-color: #2563eb;
  color: #1d4ed8;
}
.titik-notif-oranye {
  position: absolute;
  top: 7px;
  right: 8px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #2563eb;
  border: 1.5px solid #ffffff;
}

/* User Badge Kasir */
.user-badge-mini {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #ffffff;
  padding: 4px 12px 4px 5px;
  border-radius: 9999px;
  border: 1.5px solid #e2e8f0;
  transition: border-color 0.18s ease;
}
.user-badge-mini:hover {
  border-color: #bfdbfe;
}

.avatar-lingkar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #2563eb;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: none;
  flex-shrink: 0;
}

.user-info-teks {
  display: flex;
  flex-direction: column;
}

.nama-user-mini {
  font-size: 0.825rem;
  font-weight: 700;
  color: #0f172a;
  max-width: 110px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.15;
}

.peran-user-mini {
  font-size: 0.68rem;
  color: #64748b;
  text-transform: capitalize;
  line-height: 1.1;
}

@media (max-width: 768px) {
  .user-badge-mini .user-info-teks {
    display: none;
  }
  .user-badge-mini {
    padding: 3px;
  }
}
</style>
