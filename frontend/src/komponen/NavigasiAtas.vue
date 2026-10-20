<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useShiftStore } from '../stores/shift'
import { useKoneksiStore } from '../stores/koneksi'
import ModalDonasiPelanggan from './ModalDonasiPelanggan.vue'
import { 
  RefreshCw, 
  User, 
  LogOut, 
  ShoppingCart, 
  Receipt, 
  Package, 
  BarChart3, 
  Settings, 
  AlertTriangle,
  HeartHandshake
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const shiftStore = useShiftStore()
const koneksiStore = useKoneksiStore()

const tampilModalDonasi = ref(false)

function tanganiPotongBelanja(data) {
  tampilModalDonasi.value = false
  window.dispatchEvent(new CustomEvent('donasi:potong-belanja', { detail: data }))
  if (route.path !== '/pos') {
    router.push('/pos')
  }
}

const formatRupiah = (val) => 'Rp ' + Number(val || 0).toLocaleString('id-ID')

const navigasiMenu = computed(() => {
  const menu = [
    { nama: 'Kasir', rute: '/pos', ikon: ShoppingCart, peran: ['kasir', 'manajer', 'owner'] },
    { nama: 'Riwayat Struk', rute: '/transaksi', ikon: Receipt, peran: ['kasir', 'manajer', 'owner'] },
    { nama: 'Produk', rute: '/produk', ikon: Package, peran: ['manajer', 'owner'] },
    { nama: 'Laporan', rute: '/laporan', ikon: BarChart3, peran: ['manajer', 'owner'] },
    { nama: 'Pengaturan', rute: '/pengaturan', ikon: Settings, peran: ['owner'] },
  ]
  return menu.filter(m => m.peran.includes(authStore.peran))
})

function keluar() {
  if (confirm('Apakah Anda yakin ingin keluar dari akun kasir?')) {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<template>
  <header class="header-nav">
    <div class="header-konten">
      <!-- Sisi Kiri: Brand & Navigasi -->
      <div class="sisi-kiri">
        <!-- Brand Logo Minimalis -->
        <div class="logo-area" @click="router.push('/pos')" title="Layar Kasir">
          <div class="logo-badge">K</div>
          <span class="logo-judul">Kasirku</span>
        </div>

        <!-- Menu Navigasi Bersih & Monokrom -->
        <nav class="nav-links">
          <router-link 
            v-for="item in navigasiMenu" 
            :key="item.rute"
            :to="item.rute"
            class="nav-item"
            :class="{ 'aktif': route.path === item.rute }"
          >
            <component :is="item.ikon" :size="17" class="nav-ikon" />
            <span>{{ item.nama }}</span>
          </router-link>

          <!-- Tabungan Donasi (Tombol Nav Bersih & Elegan) -->
          <button 
            type="button"
            class="nav-item btn-nav-button" 
            @click="tampilModalDonasi = true"
            title="Tabungan Donasi Kembalian Pelanggan"
          >
            <HeartHandshake :size="17" class="nav-ikon" />
            <span>Donasi</span>
          </button>

          <!-- Badge Tindakan Gagal Outbox (Hanya jika ada kegagalan) -->
          <router-link 
            v-if="koneksiStore.jumlahGagal > 0 && authStore.punyaAkses(['manajer', 'owner'])" 
            to="/tindakan-gagal" 
            class="nav-item badge-perlu-tindakan"
          >
            <AlertTriangle :size="16" />
            <span>Perlu Tindakan ({{ koneksiStore.jumlahGagal }})</span>
          </router-link>
        </nav>
      </div>

      <!-- Sisi Kanan: Status Bar Fungsional -->
      <div class="status-area">
        <!-- Status Shift Kasir -->
        <div v-if="shiftStore.apakahShiftTerbuka" class="status-shift" title="Shift kasir aktif">
          <span class="titik-hijau"></span>
          <span class="shift-label">Shift Aktif</span>
          <span class="shift-nominal font-angka">{{ formatRupiah(shiftStore.shiftAktif.kas_awal) }}</span>
        </div>

        <!-- Indikator Koneksi Online / Offline -->
        <div 
          class="status-koneksi"
          :class="koneksiStore.apakahOnline ? 'online' : 'offline'"
          :title="koneksiStore.apakahOnline ? 'Terhubung ke server' : 'Mode offline'"
        >
          <span class="titik-koneksi"></span>
          <span class="teks-koneksi">{{ koneksiStore.apakahOnline ? 'Online' : 'Offline' }}</span>
        </div>

        <!-- Tombol Sinkronisasi -->
        <button 
          class="btn-sinkron"
          :disabled="!koneksiStore.apakahOnline || koneksiStore.sedangSinkron"
          @click="koneksiStore.picuSinkronManual"
          title="Sinkronkan data ke server"
        >
          <RefreshCw :size="14" :class="{ 'animasi-putar': koneksiStore.sedangSinkron }" />
          <span v-if="koneksiStore.jumlahPending > 0" class="badge-pending">
            {{ koneksiStore.jumlahPending }}
          </span>
        </button>

        <div class="pemisah-vertikal"></div>

        <!-- Profil Pengguna & Keluar -->
        <div class="user-area">
          <div class="user-avatar" :title="authStore.namaLengkap">
            <User :size="14" />
          </div>
          <div class="user-info">
            <span class="user-nama">{{ authStore.namaLengkap }}</span>
            <span class="user-peran">{{ authStore.peran }}</span>
          </div>
          <button class="btn-logout" @click="keluar" title="Keluar dari akun">
            <LogOut :size="15" />
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL TABUNGAN DONASI PELANGGAN -->
    <ModalDonasiPelanggan 
      v-if="tampilModalDonasi" 
      @tutup="tampilModalDonasi = false" 
      @terapkanPotongBelanja="tanganiPotongBelanja" 
    />
  </header>
</template>

<style scoped>
.header-nav {
  background: #0f172a;
  border-bottom: 1px solid #1e293b;
  position: sticky;
  top: 0;
  z-index: 50;
  padding: 0 20px;
}

.header-konten {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  gap: 16px;
}

.sisi-kiri {
  display: flex;
  align-items: center;
  gap: 24px;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.logo-badge {
  width: 28px;
  height: 28px;
  background: #ffffff;
  color: #0f172a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 0.95rem;
  border-radius: 6px;
}

.logo-judul {
  font-weight: 700;
  font-size: 1.05rem;
  letter-spacing: -0.02em;
  color: #ffffff;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 12px;
  border-radius: 6px;
  color: #94a3b8;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.85rem;
  transition: all 0.15s ease;
  background: transparent;
  border: none;
  cursor: pointer;
  font-family: inherit;
}

.nav-item:hover {
  color: #f8fafc;
  background: rgba(255, 255, 255, 0.06);
}

.nav-item.aktif {
  color: #ffffff;
  background: #1e293b;
  font-weight: 600;
}

.nav-ikon {
  color: inherit;
  opacity: 0.85;
}

.badge-perlu-tindakan {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171 !important;
  font-weight: 600;
}

.status-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-shift {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  color: #e2e8f0;
}

.titik-hijau {
  width: 7px;
  height: 7px;
  background: #10b981;
  border-radius: 50%;
}

.shift-label {
  color: #94a3b8;
}

.shift-nominal {
  font-weight: 600;
  color: #ffffff;
}

.status-koneksi {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  font-size: 0.775rem;
  font-weight: 500;
  color: #94a3b8;
}

.status-koneksi .titik-koneksi {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.status-koneksi.online .titik-koneksi {
  background: #10b981;
}

.status-koneksi.offline .titik-koneksi {
  background: #ef4444;
}

.status-koneksi.offline {
  color: #f87171;
}

.btn-sinkron {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
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
  font-size: 0.7rem;
  font-weight: 700;
  padding: 1px 6px;
}

.animasi-putar {
  animation: putar 1s linear infinite;
}

@keyframes putar {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.pemisah-vertikal {
  width: 1px;
  height: 20px;
  background: rgba(255, 255, 255, 0.12);
}

.user-area {
  display: flex;
  align-items: center;
  gap: 9px;
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #1e293b;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
}

.user-info {
  display: flex;
  flex-direction: column;
}

.user-nama {
  font-size: 0.825rem;
  font-weight: 600;
  color: #ffffff;
  line-height: 1.1;
}

.user-peran {
  font-size: 0.675rem;
  color: #94a3b8;
  text-transform: capitalize;
}

.btn-logout {
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

.btn-logout:hover {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}
</style>
