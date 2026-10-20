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
  if (p === '/pos') return { judul: 'Kasir (POS)', sub: 'Penjualan Toko', ikon: ShoppingCart }
  if (p === '/transaksi') return { judul: 'Riwayat Transaksi', sub: 'Daftar Struk', ikon: Receipt }
  if (p === '/donasi') return { judul: 'Tabungan & Donasi', sub: 'Celengan Kembalian', ikon: HeartHandshake }
  if (p === '/produk') return { judul: 'Katalog Produk', sub: 'Kelola Barang', ikon: Package }
  if (p === '/stok') return { judul: 'Stok Barang', sub: 'Inventori Toko', ikon: Boxes }
  if (p === '/laporan') return { judul: 'Laporan Penjualan', sub: 'Statistik Toko', ikon: BarChart3 }
  if (p === '/pengaturan') return { judul: 'Pengaturan Toko', sub: 'Konfigurasi', ikon: Settings }
  if (p === '/tindakan-gagal') return { judul: 'Perlu Tindakan', sub: 'Gagal Sinkron', ikon: AlertTriangle }
  return { judul: 'Kasirku', sub: 'Aplikasi Kasir', ikon: ShoppingCart }
})

function picuTutupShift() {
  window.dispatchEvent(new CustomEvent('shift:tutup'))
}

function picuBukaShift() {
  window.dispatchEvent(new CustomEvent('shift:buka'))
}
</script>

<template>
  <header class="header-atas">
    <!-- Sisi Kiri: Hamburger + Breadcrumb + Status Pill Kasir ala Confidency OS -->
    <div class="sisi-kiri-header">
      <!-- TOMBOL 3 GARIS UNTUK BUKA/TUTUP SIDEBAR -->
      <button 
        type="button" 
        class="btn-hamburger"
        :class="{ 'aktif': sidebarTerbuka }"
        @click="emit('toggleSidebar')"
        title="Buka / Tutup Sidebar Menu (Ctrl+B)"
      >
        <Menu :size="18" class="ikon-hamburger" />
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
        <component :is="infoHalaman.ikon" :size="16" class="ikon-halaman" />
        <span class="halaman-judul">{{ infoHalaman.judul }}</span>
      </div>

      <!-- Cashier Status Pill: dot, Kasir, Mulai Shift, Kas Laci -->
      <div v-if="shiftStore.apakahShiftTerbuka" class="cashier-status-pill">
        <span class="dot-aktif"></span>
        <span class="teks-cashier">Kasir: <strong class="cashier-nama">{{ authStore.namaLengkap }}</strong></span>
        <span class="divider-pill">•</span>
        <span class="cashier-meta">Mulai Shift: <strong>{{ shiftStore.shiftAktif?.waktu_buka ? new Date(shiftStore.shiftAktif.waktu_buka).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }) : 'Aktif' }}</strong></span>
        <span class="divider-pill">•</span>
        <span class="cashier-meta">Kas Laci: <strong class="font-angka">{{ formatRupiah(shiftStore.shiftAktif?.modal_awal || shiftStore.shiftAktif?.kas_awal || 0) }}</strong></span>
      </div>
      <div v-else class="cashier-status-pill closed">
        <span class="dot-closed"></span>
        <span class="cashier-meta">Laci Kasir Belum Dibuka</span>
      </div>
    </div>

    <!-- Sisi Kanan: Status Sinkron Otomatis, Tutup Shift, Status Koneksi & Profil -->
    <div class="sisi-kanan-header">
      <span class="auto-refresh-teks">Sinkron otomatis tiap 2dtk</span>

      <!-- Tombol Tutup Shift / Buka Shift -->
      <button 
        v-if="shiftStore.apakahShiftTerbuka" 
        type="button" 
        class="btn-shift-confidency"
        @click="picuTutupShift"
        title="Tutup Shift Kasir & Hitung Laci"
      >
        Tutup Shift
      </button>
      <button 
        v-else 
        type="button" 
        class="btn-shift-confidency buka"
        @click="picuBukaShift"
        title="Buka Shift Kasir & Modal Awal"
      >
        Buka Shift
      </button>

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
        <RefreshCw :size="13" :class="{ 'animasi-putar': koneksiStore.sedangSinkron }" />
        <span v-if="koneksiStore.jumlahPending > 0" class="badge-pending">
          {{ koneksiStore.jumlahPending }}
        </span>
      </button>

      <!-- Tombol Notifikasi Lingkar -->
      <button type="button" class="btn-notifikasi" title="Notifikasi Sistem">
        <Bell :size="15" />
        <span class="titik-notif-oranye"></span>
      </button>
    </div>
  </header>
</template>

<style scoped>
.header-atas {
  height: 58px;
  background: #ffffff;
  border-bottom: 1px solid #eaedf2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  position: sticky;
  top: 0;
  z-index: 50;
  color: #0f172a;
  flex-shrink: 0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.sisi-kiri-header {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

/* Tombol 3 Garis (Hamburger Button) */
.btn-hamburger {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  background: #ffffff;
  border: 1px solid #eaedf2;
  color: #475569;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.btn-hamburger:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #0f172a;
}

.btn-hamburger.aktif {
  background: #f8fafc;
  color: #0f172a;
}

/* Brand Mini saat Sidebar Tertutup */
.brand-mini-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  flex-shrink: 0;
}

.logo-badge-mini {
  width: 28px;
  height: 28px;
  background: #6366f1;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 0.95rem;
  border-radius: 8px;
}

.logo-nama-mini {
  font-weight: 800;
  font-size: 0.95rem;
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
  gap: 6px;
  flex-shrink: 0;
}

.ikon-halaman {
  color: #6366f1;
}

.halaman-judul {
  font-size: 0.95rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.01em;
}

/* Cashier Status Pill ala Confidency OS */
.cashier-status-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #ffffff;
  border: 1px solid #eaedf2;
  border-radius: 8px;
  padding: 4px 12px;
  font-size: 0.775rem;
  color: #475569;
  white-space: nowrap;
}

@media (max-width: 900px) {
  .cashier-status-pill {
    display: none;
  }
}

.cashier-status-pill.closed {
  background: #fffbeb;
  border-color: #fde68a;
  color: #92400e;
}

.dot-aktif {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #10b981;
  flex-shrink: 0;
}

.dot-closed {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #f59e0b;
  flex-shrink: 0;
}

.cashier-nama {
  color: #0f172a;
  font-weight: 600;
}

.divider-pill {
  color: #cbd5e1;
  font-size: 0.7rem;
}

.cashier-meta {
  color: #64748b;
}

.cashier-meta strong {
  color: #0f172a;
}

/* Sisi Kanan Header */
.sisi-kanan-header {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.auto-refresh-teks {
  font-size: 0.75rem;
  color: #94a3b8;
  font-weight: 500;
  white-space: nowrap;
}

@media (max-width: 1024px) {
  .auto-refresh-teks {
    display: none;
  }
}

/* Tombol End Shift / Buka Shift */
.btn-shift-confidency {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  color: #0f172a;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 5px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
  white-space: nowrap;
}

.btn-shift-confidency:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.btn-shift-confidency.buka {
  background: #6366f1;
  color: #ffffff;
  border-color: #4f46e5;
}

.btn-shift-confidency.buka:hover {
  background: #4f46e5;
}

/* Indikator Status Koneksi */
.status-koneksi {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  font-size: 0.72rem;
  font-weight: 600;
  border-radius: 9999px;
  border: 1px solid #eaedf2;
  background: #f8fafc;
  color: #64748b;
}

@media (max-width: 640px) {
  .status-koneksi {
    display: none;
  }
}

.status-koneksi .titik-koneksi {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-koneksi.online {
  background: #ecfdf5;
  border-color: #a7f3d0;
  color: #065f46;
}
.status-koneksi.online .titik-koneksi {
  background: #10b981;
}

.status-koneksi.offline {
  background: #fef2f2;
  border-color: #fecaca;
  color: #991b1b;
}
.status-koneksi.offline .titik-koneksi {
  background: #ef4444;
}

/* Tombol Sinkron */
.btn-sinkron {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 9px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #eaedf2;
  color: #64748b;
  font-size: 0.78rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-sinkron:hover:not(:disabled) {
  background: #f8fafc;
  color: #0f172a;
}

.badge-pending {
  background: #6366f1;
  color: #ffffff;
  border-radius: 9999px;
  font-size: 0.65rem;
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

/* Tombol Notifikasi Lingkar */
.btn-notifikasi {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #ffffff;
  border: 1px solid #eaedf2;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  transition: all 0.15s ease;
}

.btn-notifikasi:hover {
  background: #f8fafc;
  color: #0f172a;
}

.titik-notif-oranye {
  position: absolute;
  top: 6px;
  right: 7px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #6366f1;
  border: 1.5px solid #ffffff;
}
</style>
