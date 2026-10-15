<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useShiftStore } from '../stores/shift'
import { useKoneksiStore } from '../stores/koneksi'
import { 
  Wifi, 
  WifiOff, 
  RefreshCw, 
  Clock, 
  User, 
  LogOut, 
  ShoppingCart, 
  Receipt, 
  Package, 
  BarChart3, 
  Settings, 
  AlertTriangle 
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const shiftStore = useShiftStore()
const koneksiStore = useKoneksiStore()

const formatRupiah = (val) => 'Rp ' + Number(val || 0).toLocaleString('id-ID')

const navigasiMenu = computed(() => {
  const menu = [
    { nama: 'Kasir POS', rute: '/pos', ikon: ShoppingCart, peran: ['kasir', 'manajer', 'owner'], warna: '#38bdf8' },
    { nama: 'Riwayat Struk', rute: '/transaksi', ikon: Receipt, peran: ['kasir', 'manajer', 'owner'], warna: '#c084fc' },
    { nama: 'Katalog Produk', rute: '/produk', ikon: Package, peran: ['manajer', 'owner'], warna: '#4ade80' },
    { nama: 'Laporan Keuangan', rute: '/laporan', ikon: BarChart3, peran: ['manajer', 'owner'], warna: '#fbbf24' },
    { nama: 'Pengaturan Toko', rute: '/pengaturan', ikon: Settings, peran: ['owner'], warna: '#94a3b8' },
  ]
  return menu.filter(m => m.peran.includes(authStore.peran))
})

function keluar() {
  if (confirm('Apakah Anda yakin ingin keluar / logout dari akun kasir?')) {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<template>
  <header class="header-nav">
    <div class="header-konten">
      <!-- Logo & Nama Aplikasi -->
      <div class="logo-area" @click="router.push('/pos')" title="Buka Layar Kasir">
        <div class="logo-ikon">K</div>
        <div>
          <div class="logo-judul">Kasirku</div>
          <div class="logo-sub">POS Ringan & Offline</div>
        </div>
      </div>

      <!-- Menu Navigasi Sesuai Hak Akses (Tombol Jelas & Berwarna) -->
      <nav class="nav-links">
        <router-link 
          v-for="item in navigasiMenu" 
          :key="item.rute"
          :to="item.rute"
          class="nav-item"
          :class="{ 'aktif': route.path === item.rute }"
        >
          <component :is="item.ikon" :size="20" class="nav-ikon" :style="{ color: route.path === item.rute ? '#1d4ed8' : item.warna }" />
          <span>{{ item.nama }}</span>
        </router-link>

        <!-- Badge Tindakan Gagal Outbox (Khusus Manajer/Owner) -->
        <router-link 
          v-if="koneksiStore.jumlahGagal > 0 && authStore.punyaAkses(['manajer', 'owner'])" 
          to="/tindakan-gagal" 
          class="nav-item badge-perlu-tindakan"
        >
          <AlertTriangle :size="20" />
          <span>Perlu Tindakan ({{ koneksiStore.jumlahGagal }})</span>
        </router-link>
      </nav>

      <!-- Status Bar Kanan: Koneksi, Outbox, Shift, User -->
      <div class="status-area">
        <!-- Status Online / Offline -->
        <div 
          class="lencana-koneksi"
          :class="koneksiStore.apakahOnline ? 'online' : 'offline'"
          :title="koneksiStore.apakahOnline ? 'Internet Aktif: Terhubung ke Server' : 'Internet Terputus: Mode Offline Aktif'"
        >
          <Wifi v-if="koneksiStore.apakahOnline" :size="16" />
          <WifiOff v-else :size="16" />
          <span>{{ koneksiStore.apakahOnline ? 'ONLINE' : 'OFFLINE' }}</span>
        </div>

        <!-- Tombol Sinkron & Indikator Pending -->
        <button 
          class="tombol-sinkron"
          :disabled="!koneksiStore.apakahOnline || koneksiStore.sedangSinkron"
          @click="koneksiStore.picuSinkronManual"
          title="Sinkronkan data transaksi ke server"
        >
          <RefreshCw :size="16" :class="{ 'animasi-putar': koneksiStore.sedangSinkron }" />
          <span v-if="koneksiStore.jumlahPending > 0" class="badge-pending">
            {{ koneksiStore.jumlahPending }} Pending
          </span>
          <span v-else>Sinkron</span>
        </button>

        <!-- Status Shift -->
        <div v-if="shiftStore.apakahShiftTerbuka" class="shift-info" title="Shift kasir saat ini sedang aktif">
          <span class="titik-aktif"></span>
          <span class="shift-teks">Shift Aktif</span>
          <span class="shift-kas">({{ formatRupiah(shiftStore.shiftAktif.kas_awal) }})</span>
        </div>

        <!-- Info Pengguna Login -->
        <div class="user-card">
          <div class="user-avatar">
            <User :size="18" />
          </div>
          <div class="user-teks">
            <div class="user-nama">{{ authStore.namaLengkap }}</div>
            <div class="user-peran">{{ authStore.peran.toUpperCase() }}</div>
          </div>
          <button class="tombol-logout" @click="keluar" title="Keluar / Logout Akun">
            <LogOut :size="18" />
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<style scoped>
.header-nav {
  background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 50%, #2563eb 100%);
  border-bottom: 3px solid #1d4ed8;
  box-shadow: 0 4px 16px rgba(30, 64, 175, 0.2);
  position: sticky;
  top: 0;
  z-index: 50;
  padding: 0 20px;
}
.header-konten {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 68px;
  gap: 16px;
}
.logo-area {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  user-select: none;
  transition: transform 0.2s ease;
}
.logo-area:hover {
  transform: scale(1.02);
}
.logo-ikon {
  width: 42px;
  height: 42px;
  background: #ffffff;
  color: #1d4ed8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  font-size: 1.4rem;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
.logo-judul {
  font-weight: 900;
  font-size: 1.25rem;
  letter-spacing: -0.02em;
  color: #ffffff;
  line-height: 1.1;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
}
.logo-sub {
  font-size: 0.75rem;
  color: #bfdbfe;
  font-weight: 700;
  letter-spacing: 0.03em;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 8px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 10px 16px;
  border-radius: 12px;
  color: #e0e7ff;
  text-decoration: none;
  font-weight: 700;
  font-size: 0.95rem;
  transition: all 0.2s ease;
}
.nav-item:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.15);
}
.nav-item.aktif {
  color: #1e3a8a;
  background: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
.badge-perlu-tindakan {
  background: #fee2e2;
  color: #b91c1c !important;
  font-weight: 800;
  border: 1.5px solid #f87171;
}

.status-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.lencana-koneksi {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 9999px;
  font-size: 0.825rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}
.lencana-koneksi.online {
  background: #10b981;
  color: #ffffff;
}
.lencana-koneksi.offline {
  background: #ef4444;
  color: #ffffff;
  animation: denyut 1.5s infinite;
}
@keyframes denyut {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.85; transform: scale(1.04); }
}

.tombol-sinkron {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #ffffff;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}
.tombol-sinkron:hover:not(:disabled) {
  background: #ffffff;
  color: #1e40af;
}
.badge-pending {
  background: #f59e0b;
  color: #78350f;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 800;
  padding: 2px 8px;
}
.animasi-putar {
  animation: putar 1s linear infinite;
}
@keyframes putar {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.shift-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.25);
  padding: 7px 14px;
  border-radius: 10px;
  color: #ffffff;
}
.titik-aktif {
  width: 10px;
  height: 10px;
  background: #34d399;
  border-radius: 50%;
  box-shadow: 0 0 8px #34d399;
}
.shift-teks {
  font-weight: 800;
}
.shift-kas {
  font-family: var(--font-angka);
  font-size: 0.825rem;
  color: #bfdbfe;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #ffffff;
  padding: 6px 14px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}
.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #eff6ff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #1d4ed8;
}
.user-teks {
  display: flex;
  flex-direction: column;
}
.user-nama {
  font-size: 0.875rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.1;
}
.user-peran {
  font-size: 0.7rem;
  color: #2563eb;
  font-weight: 900;
  letter-spacing: 0.05em;
}
.tombol-logout {
  background: #fee2e2;
  border: none;
  color: #dc2626;
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}
.tombol-logout:hover {
  background: #dc2626;
  color: #ffffff;
}
</style>
