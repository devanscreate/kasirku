import { createRouter, createWebHistory } from 'vue-router'
import TampilanLogin from '../views/TampilanLogin.vue'
import TampilanPOS from '../views/TampilanPOS.vue'
import TampilanTransaksi from '../views/TampilanTransaksi.vue'
import TampilanProduk from '../views/TampilanProduk.vue'
import TampilanStok from '../views/TampilanStok.vue'
import TampilanLaporan from '../views/TampilanLaporan.vue'
import TampilanTindakanGagal from '../views/TampilanTindakanGagal.vue'
import TampilanPengaturan from '../views/TampilanPengaturan.vue'

const rute = [
  {
    path: '/',
    redirect: '/pos'
  },
  {
    path: '/login',
    name: 'Login',
    component: TampilanLogin,
    meta: { bebasAkses: true }
  },
  {
    path: '/pos',
    name: 'POS',
    component: TampilanPOS,
    meta: { butuhAuth: true }
  },
  {
    path: '/transaksi',
    name: 'Transaksi',
    component: TampilanTransaksi,
    meta: { butuhAuth: true }
  },
  {
    path: '/produk',
    name: 'Produk',
    component: TampilanProduk,
    meta: { butuhAuth: true, peran: ['manajer', 'owner'] }
  },
  {
    path: '/stok',
    name: 'Stok',
    component: TampilanStok,
    meta: { butuhAuth: true, peran: ['manajer', 'owner'] }
  },
  {
    path: '/laporan',
    name: 'Laporan',
    component: TampilanLaporan,
    meta: { butuhAuth: true, peran: ['manajer', 'owner'] }
  },
  {
    path: '/tindakan-gagal',
    name: 'TindakanGagal',
    component: TampilanTindakanGagal,
    meta: { butuhAuth: true, peran: ['manajer', 'owner'] }
  },
  {
    path: '/pengaturan',
    name: 'Pengaturan',
    component: TampilanPengaturan,
    meta: { butuhAuth: true, peran: ['owner'] }
  }
]

export const router = createRouter({
  history: createWebHistory(),
  routes: rute
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token_akses')
  const penggunaStr = localStorage.getItem('pengguna')
  const pengguna = penggunaStr ? JSON.parse(penggunaStr) : null

  if (to.meta.butuhAuth && !token) {
    return next('/login')
  }

  if (to.meta.peran && pengguna) {
    if (!to.meta.peran.includes(pengguna.peran)) {
      alert(`Akses ditolak: Anda tidak memiliki hak akses sebagai ${pengguna.peran}.`)
      return next('/pos')
    }
  }

  if (to.path === '/login' && token) {
    return next('/pos')
  }

  next()
})
