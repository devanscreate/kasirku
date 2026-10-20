<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { 
  HeartHandshake, 
  Coins, 
  Banknote, 
  ShoppingBag, 
  Users, 
  Search, 
  RotateCcw, 
  Printer, 
  X, 
  Check, 
  AlertCircle, 
  History, 
  Sparkles, 
  Phone, 
  User, 
  ArrowLeft,
  ChevronRight,
  TrendingUp,
  Receipt
} from 'lucide-vue-next'
import { 
  ambilDaftarPelangganDonasi, 
  cekSaldoPelanggan, 
  cairkanDonasiPelanggan, 
  ambilRingkasanDonasiToko,
  bersihkanNomorHp 
} from '../layanan/donasi'
import { cetakStrukPencairanDonasi } from '../layanan/pencetak_struk'
import { useShiftStore } from '../stores/shift'
import { useAuthStore } from '../stores/auth'
import { useKoneksiStore } from '../stores/koneksi'

const router = useRouter()
const shiftStore = useShiftStore()
const authStore = useAuthStore()
const koneksiStore = useKoneksiStore()

const formatRupiah = (val) => 'Rp ' + Number(val || 0).toLocaleString('id-ID')

// State Data
const sedangMemuat = ref(false)
const kueriCari = ref('')
const filterTab = ref('semua') // 'semua' | 'bersaldo' | 'kosong'
const daftarPelanggan = ref([])
const ringkasanToko = ref({
  total_donasi_terkumpul: 0,
  total_dicairkan: 0,
  saldo_aktif_keseluruhan: 0,
  jumlah_pelanggan_aktif: 0
})

// Pelanggan Terpilih
const pelangganTerpilih = ref(null)
const riwayatTerpilih = ref([])
const sedangMuatDetail = ref(false)

// State Tampilan Mobile: 'daftar' atau 'detail'
const tampilanMobile = ref('daftar')

// Notifikasi
const pesanSukses = ref('')
const pesanError = ref('')

// State Dialog Pencairan Tunai
const tampilDialogCairTunai = ref(false)
const nominalCairTunai = ref(0)
const sedangProsesCair = ref(false)
const buktiCairTerakhir = ref(null)

// Muat data ringkasan dan daftar pembeli
async function muatData() {
  sedangMemuat.value = true
  pesanError.value = ''
  try {
    const [ringkasan, list] = await Promise.all([
      ambilRingkasanDonasiToko(),
      ambilDaftarPelangganDonasi(kueriCari.value)
    ])
    if (ringkasan) ringkasanToko.value = ringkasan
    daftarPelanggan.value = list || []

    // Jika ada pelanggan yang sedang dipilih, segarkan juga datanya
    if (pelangganTerpilih.value) {
      await pilihPelanggan(pelangganTerpilih.value.nomor_hp, false)
    } else if (daftarPelanggan.value.length > 0 && window.innerWidth >= 1024) {
      // Di layar besar, otomatis pilih pelanggan pertama jika belum ada pilihan
      await pilihPelanggan(daftarPelanggan.value[0].nomor_hp, false)
    }
  } catch (err) {
    pesanError.value = 'Gagal memuat data donasi: ' + (err.message || 'Kesalahan jaringan')
  } finally {
    sedangMemuat.value = false
  }
}

// Cari pelanggan berdasarkan kueri teks
async function cariPelanggan() {
  sedangMemuat.value = true
  pesanError.value = ''
  try {
    const list = await ambilDaftarPelangganDonasi(kueriCari.value)
    daftarPelanggan.value = list || []

    const qClean = bersihkanNomorHp(kueriCari.value)
    if (qClean) {
      const cocok = list.find(p => bersihkanNomorHp(p.nomor_hp) === qClean)
      if (cocok) {
        await pilihPelanggan(cocok.nomor_hp)
      } else if (list.length === 1) {
        await pilihPelanggan(list[0].nomor_hp)
      }
    }
  } catch (err) {
    pesanError.value = 'Gagal mencari pelanggan'
  } finally {
    sedangMemuat.value = false
  }
}

// Pilih pelanggan untuk melihat detail saldo & mutasi
async function pilihPelanggan(nomorHp, gantiTampilanMobile = true) {
  sedangMuatDetail.value = true
  pesanError.value = ''
  try {
    const data = await cekSaldoPelanggan(nomorHp)
    pelangganTerpilih.value = data
    riwayatTerpilih.value = data?.riwayat || []
    if (gantiTampilanMobile) {
      tampilanMobile.value = 'detail'
    }
  } catch (err) {
    pesanError.value = 'Gagal memuat detail saldo pembeli: ' + err.message
  } finally {
    sedangMuatDetail.value = false
  }
}

// Filter pelanggan berdasarkan tab & kata kunci
const pelangganTerfilter = computed(() => {
  let list = daftarPelanggan.value
  if (filterTab.value === 'bersaldo') {
    list = list.filter(p => Number(p.total_saldo || 0) > 0)
  } else if (filterTab.value === 'kosong') {
    list = list.filter(p => Number(p.total_saldo || 0) === 0)
  }

  if (kueriCari.value.trim()) {
    const q = kueriCari.value.toLowerCase().trim()
    const qHp = bersihkanNomorHp(q)
    list = list.filter(p => {
      const namaCocok = (p.nama_pelanggan || '').toLowerCase().includes(q)
      const hpCocok = qHp ? (p.nomor_hp || '').includes(qHp) : false
      return namaCocok || hpCocok
    })
  }

  return list
})

// Dialog Pencairan Tunai
function bukaDialogCairTunai() {
  if (!pelangganTerpilih.value || pelangganTerpilih.value.total_saldo <= 0) {
    alert('Saldo tabungan pelanggan masih 0 atau tidak mencukupi untuk dicairkan.')
    return
  }
  nominalCairTunai.value = pelangganTerpilih.value.total_saldo
  tampilDialogCairTunai.value = true
}

function tanganiInputNominalCair(e) {
  const digitOnly = e.target.value.replace(/\D/g, '')
  const num = digitOnly ? parseInt(digitOnly, 10) : 0
  nominalCairTunai.value = num
  e.target.value = num > 0 ? num.toLocaleString('id-ID') : ''
}

async function konfirmasiCairTunai() {
  if (nominalCairTunai.value <= 0 || nominalCairTunai.value > pelangganTerpilih.value.total_saldo) {
    alert('Nominal pencairan tidak valid!')
    return
  }

  sedangProsesCair.value = true
  try {
    const hasil = await cairkanDonasiPelanggan({
      nomorHp: pelangganTerpilih.value.nomor_hp,
      nominal: nominalCairTunai.value,
      tipe: 'tunai',
      idShift: shiftStore.shiftAktif?.id,
      catatan: `Penarikan uang tunai laci oleh kasir ${authStore.namaLengkap}`,
      saldoAwal: pelangganTerpilih.value.total_saldo
    })

    buktiCairTerakhir.value = {
      ...hasil,
      namaKasir: authStore.namaLengkap,
      nominal_dicairkan: nominalCairTunai.value,
      sisa_saldo: Math.max(0, pelangganTerpilih.value.total_saldo - nominalCairTunai.value),
      waktu: new Date().toLocaleString('id-ID')
    }

    pesanSukses.value = `Uang tunai ${formatRupiah(nominalCairTunai.value)} berhasil dicairkan. Silakan serahkan uang dari laci kasir.`
    tampilDialogCairTunai.value = false
    await pilihPelanggan(pelangganTerpilih.value.nomor_hp, false)
    await muatData()
  } catch (err) {
    alert('Gagal mencairkan tabungan: ' + (err.message || 'Kesalahan server'))
  } finally {
    sedangProsesCair.value = false
  }
}

// B. Potong Belanjaan di Layar Kasir (POS)
function gunakanUntukPotongBelanja() {
  if (!pelangganTerpilih.value || pelangganTerpilih.value.total_saldo <= 0) {
    alert('Saldo tabungan pelanggan masih 0.')
    return
  }
  const payload = {
    nomorHp: pelangganTerpilih.value.nomor_hp,
    namaPelanggan: pelangganTerpilih.value.nama_pelanggan,
    saldoMaksimal: pelangganTerpilih.value.total_saldo
  }
  // Simpan ke sessionStorage agar POS langsung mengaktifkan potongan belanja
  sessionStorage.setItem('pos_prefill_donasi', JSON.stringify(payload))
  // Kirim juga event global
  window.dispatchEvent(new CustomEvent('donasi:potong-belanja', { detail: payload }))
  // Langsung arahkan kasir ke layar POS
  router.push('/pos')
}

function cetakBuktiPencairan() {
  if (!buktiCairTerakhir.value) return
  cetakStrukPencairanDonasi(buktiCairTerakhir.value, {})
}

onMounted(() => {
  muatData()
})
</script>

<template>
  <div class="halaman-donasi">
    <div class="wadah-donasi">
      <!-- 1. HEADER HALAMAN LENGKAP & BERSAHABAT -->
      <div class="header-halaman-donasi">
        <div class="info-header-kiri">
          <div class="ikon-header-donasi">
            <HeartHandshake :size="28" />
          </div>
          <div>
            <h1 class="judul-layar">Tabungan & Donasi Kembalian Pembeli</h1>
            <p class="sub-layar">
              Pusat kelola celengan kembalian belanja pembeli. Saldo dapat dicairkan tunai dari laci kasir atau digunakan sebagai potongan belanja POS.
            </p>
          </div>
        </div>

        <div class="aksi-header-kanan">
          <button 
            type="button" 
            class="tombol tombol-sekunder btn-segarkan" 
            :disabled="sedangMemuat"
            @click="muatData"
            title="Segarkan data saldo & transaksi"
          >
            <RotateCcw :size="15" :class="{ 'animasi-putar': sedangMemuat }" />
            <span>{{ sedangMemuat ? 'Memuat...' : 'Segarkan' }}</span>
          </button>

          <router-link to="/pos" class="tombol tombol-primer btn-ke-pos">
            <ShoppingBag :size="16" />
            <span>Ke Layar Kasir</span>
          </router-link>
        </div>
      </div>

      <!-- 2. KARTU STATISTIK TOKO (4 KPI RESPONSIF) -->
      <div class="grid-kpi-donasi mt-4">
        <div class="kartu-kpi kpi-hijau">
          <div class="kpi-header">
            <span class="label-kpi">TOTAL SALDO AKTIF</span>
            <div class="ikon-kpi-lingkar">
              <Coins :size="18" />
            </div>
          </div>
          <div class="angka-kpi font-angka">{{ formatRupiah(ringkasanToko.saldo_aktif_keseluruhan) }}</div>
          <div class="sub-kpi">Tersimpan di celengan pembeli</div>
        </div>

        <div class="kartu-kpi kpi-biru">
          <div class="kpi-header">
            <span class="label-kpi">TOTAL TERKUMPUL</span>
            <div class="ikon-kpi-lingkar">
              <TrendingUp :size="18" />
            </div>
          </div>
          <div class="angka-kpi font-angka">{{ formatRupiah(ringkasanToko.total_donasi_terkumpul) }}</div>
          <div class="sub-kpi">Akumulasi seluruh kembalian</div>
        </div>

        <div class="kartu-kpi kpi-kuning">
          <div class="kpi-header">
            <span class="label-kpi">SUDAH DICAIRKAN</span>
            <div class="ikon-kpi-lingkar">
              <Banknote :size="18" />
            </div>
          </div>
          <div class="angka-kpi font-angka">{{ formatRupiah(ringkasanToko.total_dicairkan) }}</div>
          <div class="sub-kpi">Tunai & potongan belanja</div>
        </div>

        <div class="kartu-kpi kpi-ungu">
          <div class="kpi-header">
            <span class="label-kpi">PEMBELI MENABUNG</span>
            <div class="ikon-kpi-lingkar">
              <Users :size="18" />
            </div>
          </div>
          <div class="angka-kpi font-angka">{{ ringkasanToko.jumlah_pelanggan_aktif }} Orang</div>
          <div class="sub-kpi">Terdaftar dengan nomor HP</div>
        </div>
      </div>

      <!-- Alert Pesan Sukses / Error -->
      <div v-if="pesanSukses" class="alert-banner alert-sukses mt-3">
        <div class="flex items-center gap-2">
          <Check :size="18" class="flex-shrink-0" />
          <span>{{ pesanSukses }}</span>
        </div>
        <div class="flex items-center gap-2">
          <button v-if="buktiCairTerakhir" class="btn-cetak-bukti-mini" @click="cetakBuktiPencairan">
            <Printer :size="14" />
            <span>Cetak Bukti Penarikan</span>
          </button>
          <button class="btn-tutup-alert" @click="pesanSukses = ''">✕</button>
        </div>
      </div>

      <div v-if="pesanError" class="alert-banner alert-error mt-3">
        <div class="flex items-center gap-2">
          <AlertCircle :size="18" class="flex-shrink-0" />
          <span>{{ pesanError }}</span>
        </div>
        <button class="btn-tutup-alert" @click="pesanError = ''">✕</button>
      </div>

      <!-- 3. KONTEN UTAMA: 2 KOLOM (DAFTAR PEMBELI & DETAIL SALDO) -->
      <div class="panel-utama-donasi mt-4" :class="`mobile-view-${tampilanMobile}`">
        <!-- KOLOM KIRI: DAFTAR PEMBELI & PENCARIAN -->
        <div class="kolom-kiri-pembeli">
          <!-- Bar Pencarian & Filter Cepat -->
          <div class="bar-cari-wrap">
            <div class="input-cari-donasi-wrap">
              <Search :size="18" class="ikon-search" />
              <input 
                v-model="kueriCari" 
                type="text" 
                class="input-teks input-cari-donasi" 
                placeholder="Cari nomor HP atau nama pembeli..."
                @input="cariPelanggan"
                @keydown.enter="cariPelanggan"
              />
              <button v-if="kueriCari" class="btn-bersih-cari" @click="kueriCari = ''; cariPelanggan()">✕</button>
            </div>
          </div>

          <!-- Filter Tab Chips -->
          <div class="tab-filter-pembeli">
            <button 
              type="button" 
              class="chip-tab" 
              :class="{ 'aktif': filterTab === 'semua' }"
              @click="filterTab = 'semua'"
            >
              <span>Semua</span>
              <span class="badge-hitung-tab">{{ daftarPelanggan.length }}</span>
            </button>
            <button 
              type="button" 
              class="chip-tab" 
              :class="{ 'aktif': filterTab === 'bersaldo' }"
              @click="filterTab = 'bersaldo'"
            >
              <span>Ada Saldo</span>
              <span class="badge-hitung-tab badge-hijau">{{ daftarPelanggan.filter(p => Number(p.total_saldo || 0) > 0).length }}</span>
            </button>
            <button 
              type="button" 
              class="chip-tab" 
              :class="{ 'aktif': filterTab === 'kosong' }"
              @click="filterTab = 'kosong'"
            >
              <span>Saldo Rp 0</span>
              <span class="badge-hitung-tab">{{ daftarPelanggan.filter(p => Number(p.total_saldo || 0) === 0).length }}</span>
            </button>
          </div>

          <!-- Daftar Pelanggan Scrollable -->
          <div class="daftar-pelanggan-list">
            <div 
              v-for="p in pelangganTerfilter" 
              :key="p.nomor_hp"
              class="item-kartu-pelanggan"
              :class="{ 
                'pelanggan-terpilih': pelangganTerpilih?.nomor_hp === p.nomor_hp,
                'saldo-nol': Number(p.total_saldo || 0) === 0
              }"
              @click="pilihPelanggan(p.nomor_hp)"
            >
              <div class="avatar-pelanggan-lingkar">
                <User :size="18" />
              </div>

              <div class="info-kartu-tengah">
                <div class="nama-pelanggan-baris">{{ p.nama_pelanggan || 'Pelanggan Toko' }}</div>
                <div class="hp-pelanggan-baris font-angka">
                  <Phone :size="12" />
                  <span>{{ p.nomor_hp }}</span>
                </div>
              </div>

              <div class="info-kartu-kanan">
                <div class="saldo-pelanggan-angka font-angka" :class="{ 'angka-hijau': Number(p.total_saldo || 0) > 0 }">
                  {{ formatRupiah(p.total_saldo) }}
                </div>
                <div class="label-status-saldo">
                  {{ Number(p.total_saldo || 0) > 0 ? 'Saldo Aktif' : 'Telah Dicairkan' }}
                </div>
              </div>
            </div>

            <!-- State Kosong jika tidak ada hasil -->
            <div v-if="pelangganTerfilter.length === 0" class="state-kosong-pembeli">
              <HeartHandshake :size="36" class="ikon-redup" />
              <div class="tebal">Tidak ada pembeli yang sesuai</div>
              <p class="sub-redup">
                {{ kueriCari ? `Kata kunci "${kueriCari}" tidak ditemukan.` : 'Belum ada pembeli yang menabung kembalian.' }}
              </p>
            </div>
          </div>
        </div>

        <!-- KOLOM KANAN: DETAIL SALDO, AKSI PENCAIRAN, & RIWAYAT MUTASI -->
        <div class="kolom-kanan-detail">
          <!-- Tombol Kembali Khusus Tampilan Mobile -->
          <button 
            type="button" 
            class="btn-kembali-mobile" 
            @click="tampilanMobile = 'daftar'"
          >
            <ArrowLeft :size="16" />
            <span>Kembali ke Daftar Pembeli</span>
          </button>

          <!-- TAMPILAN JIKA ADA PELANGGAN TERPILIH -->
          <div v-if="pelangganTerpilih" class="detail-pelanggan-penuh">
            <!-- Header Kartu Pelanggan Terpilih -->
            <div class="kartu-header-detail">
              <div class="profil-kiri">
                <div class="avatar-detail-besar">
                  <User :size="26" />
                </div>
                <div>
                  <h2 class="nama-detail-teks">{{ pelangganTerpilih.nama_pelanggan || 'Pelanggan Toko' }}</h2>
                  <div class="hp-detail-teks font-angka">
                    <Phone :size="14" />
                    <span>{{ pelangganTerpilih.nomor_hp }}</span>
                  </div>
                </div>
              </div>

              <div class="badge-status-pembeli">
                <Sparkles :size="14" class="teks-emas" />
                <span>{{ pelangganTerpilih.total_saldo > 0 ? '⭐ Aktif Menabung' : 'Terdaftar' }}</span>
              </div>
            </div>

            <!-- KARTU HERO SALDO BESAR & BERSIH -->
            <div class="kartu-hero-saldo mt-3">
              <div class="konten-hero-kiri">
                <div class="label-hero-saldo">TOTAL SALDO TABUNGAN SAAT INI</div>
                <div class="angka-hero-saldo font-angka">{{ formatRupiah(pelangganTerpilih.total_saldo) }}</div>
                <div class="sub-hero-bulan">
                  Akumulasi Bulan Ini: <strong class="font-angka">{{ formatRupiah(pelangganTerpilih.total_donasi_bulan_ini) }}</strong>
                  <span class="pemisah-titik">•</span>
                  <span>{{ pelangganTerpilih.jumlah_transaksi || riwayatTerpilih.length }} Mutasi</span>
                </div>
              </div>
              <div class="dekorasi-koin">
                <Coins :size="64" />
              </div>
            </div>

            <!-- AKSI PENCAIRAN SESUAI FLOWCHART SISTEM (A: CASH, B: POTONG BELANJA) -->
            <div class="area-aksi-pencairan mt-4">
              <div class="judul-aksi-bagian">Pilihan Penukaran / Pencairan Saldo:</div>

              <div class="grid-dua-aksi">
                <!-- Pilihan A: Tukarkan Uang Cash dari Laci Kasir -->
                <button 
                  type="button" 
                  class="btn-kartu-aksi btn-aksi-tunai"
                  :disabled="pelangganTerpilih.total_saldo <= 0"
                  @click="bukaDialogCairTunai"
                >
                  <div class="ikon-aksi-wrap">
                    <Banknote :size="24" />
                  </div>
                  <div class="teks-aksi-wrap">
                    <div class="judul-btn-aksi">A. Tukarkan Uang Cash</div>
                    <div class="sub-btn-aksi">Berikan uang tunai dari laci kasir kepada pembeli</div>
                  </div>
                  <ChevronRight :size="18" class="panah-aksi" />
                </button>

                <!-- Pilihan B: Potong Belanjaan di Layar POS -->
                <button 
                  type="button" 
                  class="btn-kartu-aksi btn-aksi-belanja"
                  :disabled="pelangganTerpilih.total_saldo <= 0"
                  @click="gunakanUntukPotongBelanja"
                >
                  <div class="ikon-aksi-wrap">
                    <ShoppingBag :size="24" />
                  </div>
                  <div class="teks-aksi-wrap">
                    <div class="judul-btn-aksi">B. Potong Belanjaan</div>
                    <div class="sub-btn-aksi">Gunakan saldo untuk bayar belanjaan di layar kasir POS</div>
                  </div>
                  <ChevronRight :size="18" class="panah-aksi" />
                </button>
              </div>
            </div>

            <!-- RIWAYAT MUTASI LENGKAP -->
            <div class="area-riwayat-mutasi mt-4">
              <div class="header-riwayat-baris">
                <div class="flex items-center gap-2">
                  <History :size="18" class="teks-biru" />
                  <h3 class="judul-riwayat">Riwayat Setoran & Pencairan</h3>
                </div>
                <span class="total-mutasi-badge">{{ riwayatTerpilih.length }} Catatan</span>
              </div>

              <div class="daftar-riwayat-scroll">
                <div 
                  v-for="r in riwayatTerpilih" 
                  :key="r.id"
                  class="baris-riwayat-item"
                  :class="r.tipe === 'setor_kembalian' ? 'tipe-setor' : 'tipe-cair'"
                >
                  <div class="ikon-tipe-mutasi">
                    <Coins v-if="r.tipe === 'setor_kembalian'" :size="18" />
                    <Banknote v-else-if="r.tipe === 'cair_tunai'" :size="18" />
                    <ShoppingBag v-else :size="18" />
                  </div>

                  <div class="detail-mutasi-kiri">
                    <div class="judul-tipe-teks">
                      {{ r.tipe === 'setor_kembalian' ? 'Setoran Celengan (Kembalian)' : (r.tipe === 'cair_tunai' ? 'Penarikan Uang Tunai Kasir' : 'Potongan Belanja POS') }}
                    </div>
                    <div class="waktu-mutasi-teks font-angka">
                      <span>{{ new Date(r.dibuat_pada).toLocaleString('id-ID') }}</span>
                      <span v-if="r.nomor_struk" class="badge-struk-mutasi">Struk: {{ r.nomor_struk }}</span>
                    </div>
                    <div v-if="r.catatan" class="catatan-mutasi-teks">{{ r.catatan }}</div>
                  </div>

                  <div class="detail-mutasi-kanan font-angka">
                    <span class="nominal-mutasi" :class="r.tipe === 'setor_kembalian' ? 'plus-hijau' : 'minus-merah'">
                      {{ r.tipe === 'setor_kembalian' ? '+' : '-' }}{{ formatRupiah(r.nominal) }}
                    </span>
                  </div>
                </div>

                <div v-if="riwayatTerpilih.length === 0" class="state-kosong-riwayat">
                  Belum ada riwayat mutasi donasi untuk pembeli ini.
                </div>
              </div>
            </div>
          </div>

          <!-- PLACEHOLDER JIKA BELUM ADA PEMBELI YANG DIPILIH -->
          <div v-else class="placeholder-pilih-detail">
            <div class="ikon-lingkar-placeholder">
              <HeartHandshake :size="48" />
            </div>
            <h3 class="judul-placeholder">Pilih Pembeli untuk Melihat Rincian</h3>
            <p class="sub-placeholder">
              Pilih salah satu pembeli dari daftar di sebelah kiri atau ketik nomor HP untuk melihat total saldo tabungan, riwayat transaksi, serta memproses pencairan uang tunai / potongan belanja.
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL POPUP DIALOG PENCAIRAN TUNAI -->
    <div v-if="tampilDialogCairTunai" class="latar-submodal" @click.self="tampilDialogCairTunai = false">
      <div class="kartu-submodal">
        <div class="header-submodal">
          <div class="flex items-center gap-2">
            <Banknote :size="20" class="teks-hijau" />
            <h3 class="judul-submodal">Penarikan Uang Tunai Tabungan</h3>
          </div>
          <button class="btn-tutup-sub" @click="tampilDialogCairTunai = false">
            <X :size="18" />
          </button>
        </div>

        <div class="body-submodal">
          <p class="petunjuk-cair">
            Kasir akan menyerahkan uang tunai dari laci kasir kepada pembeli:
          </p>

          <div class="kotak-info-cair-pelanggan mt-2">
            <div>Pembeli: <strong>{{ pelangganTerpilih.nama_pelanggan || 'Pelanggan' }}</strong> ({{ pelangganTerpilih.nomor_hp }})</div>
            <div>Saldo Maksimal: <strong class="font-angka teks-hijau">{{ formatRupiah(pelangganTerpilih.total_saldo) }}</strong></div>
          </div>

          <div class="grup-input-cair mt-3">
            <label class="label-cair">Nominal Uang Tunai yang Dicairkan (Rp):</label>
            <div class="input-wrap-cair">
              <span class="awalan-cair-rp">Rp</span>
              <input 
                :value="nominalCairTunai > 0 ? Number(nominalCairTunai).toLocaleString('id-ID') : ''" 
                type="text" 
                inputmode="numeric"
                class="input-teks input-cair-besar font-angka"
                placeholder="0"
                autofocus
                @focus="$event.target.select()"
                @input="tanganiInputNominalCair"
                @keydown.enter="konfirmasiCairTunai"
              />
            </div>
          </div>

          <div class="flex gap-2 mt-2">
            <button 
              type="button" 
              class="btn-pilih-semua-cair" 
              @click="nominalCairTunai = pelangganTerpilih.total_saldo"
            >
              Cairkan Seluruh Saldo ({{ formatRupiah(pelangganTerpilih.total_saldo) }})
            </button>
          </div>
        </div>

        <div class="footer-submodal">
          <button 
            type="button" 
            class="tombol tombol-sekunder flex-1" 
            @click="tampilDialogCairTunai = false"
          >
            Batal
          </button>
          <button 
            type="button" 
            class="tombol tombol-sukses flex-2"
            :disabled="sedangProsesCair || nominalCairTunai <= 0 || nominalCairTunai > pelangganTerpilih.total_saldo"
            @click="konfirmasiCairTunai"
          >
            <Check :size="18" />
            <span>{{ sedangProsesCair ? 'Memproses...' : 'Serahkan Uang Cash' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.halaman-donasi {
  min-height: calc(100vh - 56px);
  padding: 20px 24px;
  background: var(--warna-latar);
}

.wadah-donasi {
  max-width: 1400px;
  margin: 0 auto;
}

/* 1. Header Halaman */
.header-halaman-donasi {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.info-header-kiri {
  display: flex;
  align-items: center;
  gap: 14px;
}

.ikon-header-donasi {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: #eff6ff;
  color: #2563eb;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: none;
  border: 1px solid #bfdbfe;
}

.judul-layar {
  font-size: 1.35rem;
  font-weight: 900;
  color: #0f172a;
  margin: 0;
}

.sub-layar {
  font-size: 0.825rem;
  color: #64748b;
  margin-top: 3px;
  max-width: 650px;
  line-height: 1.4;
}

.aksi-header-kanan {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-segarkan {
  height: 40px;
  padding: 0 14px;
  font-size: 0.85rem;
}

.btn-ke-pos {
  height: 40px;
  padding: 0 16px;
  font-size: 0.85rem;
  background: #2563eb;
  color: #ffffff;
  border-radius: var(--radius-md);
  font-weight: 700;
  border: 1px solid #1d4ed8;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}
.btn-ke-pos:hover {
  background: #1d4ed8;
}

/* 2. Grid KPI Statistik */
.grid-kpi-donasi {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

@media (max-width: 1024px) {
  .grid-kpi-donasi {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 640px) {
  .grid-kpi-donasi {
    grid-template-columns: 1fr;
  }
}

.kartu-kpi {
  background: #ffffff;
  border-radius: 14px;
  padding: 16px 18px;
  border: 1.5px solid #e2e8f0;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
  transition: all 0.2s ease;
}
.kartu-kpi:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
}

.kpi-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.label-kpi {
  font-size: 0.72rem;
  font-weight: 800;
  color: #64748b;
  letter-spacing: 0.04em;
}

.ikon-kpi-lingkar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.kpi-hijau .ikon-kpi-lingkar { background: #ecfdf5; color: #059669; }
.kpi-biru .ikon-kpi-lingkar { background: #eff6ff; color: #2563eb; }
.kpi-kuning .ikon-kpi-lingkar { background: #fffbeb; color: #d97706; }
.kpi-ungu .ikon-kpi-lingkar { background: #faf5ff; color: #7c3aed; }

.angka-kpi {
  font-size: 1.5rem;
  font-weight: 900;
  color: #0f172a;
  margin: 8px 0 2px 0;
}

.sub-kpi {
  font-size: 0.74rem;
  color: #64748b;
}

/* Alert Banner */
.alert-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 0.85rem;
  font-weight: 600;
}
.alert-sukses {
  background: #ecfdf5;
  border: 1.5px solid #a7f3d0;
  color: #065f46;
}
.alert-error {
  background: #fef2f2;
  border: 1.5px solid #fecaca;
  color: #991b1b;
}
.btn-cetak-bukti-mini {
  background: #ffffff;
  border: 1px solid #10b981;
  color: #047857;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}
.btn-tutup-alert {
  background: none;
  border: none;
  cursor: pointer;
  color: inherit;
  font-weight: 800;
}

/* 3. Panel Utama 2 Kolom */
.panel-utama-donasi {
  display: grid;
  grid-template-columns: 380px minmax(0, 1fr);
  gap: 18px;
  min-height: 600px;
}

@media (max-width: 1024px) {
  .panel-utama-donasi {
    grid-template-columns: 1fr;
  }
  .mobile-view-daftar .kolom-kanan-detail {
    display: none !important;
  }
  .mobile-view-detail .kolom-kiri-pembeli {
    display: none !important;
  }
}

/* Kolom Kiri: Daftar Pembeli */
.kolom-kiri-pembeli {
  background: #ffffff;
  border-radius: 16px;
  border: 1.5px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.03);
}

.bar-cari-wrap {
  padding: 14px 14px 8px 14px;
}

.input-cari-donasi-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.ikon-search {
  position: absolute;
  left: 12px;
  color: #94a3b8;
  pointer-events: none;
}

.input-cari-donasi {
  width: 100%;
  padding-left: 38px !important;
  padding-right: 32px !important;
  height: 42px !important;
  font-size: 0.88rem !important;
  border-radius: 10px;
}

.btn-bersih-cari {
  position: absolute;
  right: 10px;
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px;
}

.tab-filter-pembeli {
  display: flex;
  gap: 6px;
  padding: 0 14px 12px 14px;
  border-bottom: 1px solid #f1f5f9;
}

.chip-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #475569;
  font-size: 0.775rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}
.chip-tab:hover {
  background: #f1f5f9;
}
.chip-tab.aktif {
  background: #2563eb;
  color: #ffffff;
  border-color: #2563eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}
.badge-hitung-tab {
  background: rgba(0, 0, 0, 0.08);
  padding: 1px 6px;
  border-radius: 9999px;
  font-size: 0.7rem;
}
.chip-tab.aktif .badge-hitung-tab {
  background: rgba(255, 255, 255, 0.25);
}
.badge-hijau {
  background: #ecfdf5;
  color: #059669;
}

/* List Pelanggan Scrollable */
.daftar-pelanggan-list {
  flex: 1;
  overflow-y: auto;
  max-height: calc(100vh - 350px);
  padding: 8px;
}

.item-kartu-pelanggan {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1.5px solid transparent;
  cursor: pointer;
  transition: all 0.15s ease;
  margin-bottom: 6px;
}
.item-kartu-pelanggan:hover {
  background: #f8fafc;
  border-color: #e2e8f0;
}
.item-kartu-pelanggan.pelanggan-terpilih {
  background: #eff6ff;
  border-color: #2563eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
.item-kartu-pelanggan.saldo-nol {
  opacity: 0.65;
}

.avatar-pelanggan-lingkar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: #f1f5f9;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.pelanggan-terpilih .avatar-pelanggan-lingkar {
  background: #dbeafe;
  color: #1d4ed8;
}

.info-kartu-tengah {
  flex: 1;
  min-width: 0;
}
.nama-pelanggan-baris {
  font-weight: 800;
  font-size: 0.88rem;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hp-pelanggan-baris {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 2px;
}

.info-kartu-kanan {
  text-align: right;
  flex-shrink: 0;
}
.saldo-pelanggan-angka {
  font-weight: 900;
  font-size: 0.95rem;
  color: #475569;
}
.saldo-pelanggan-angka.angka-hijau {
  color: #059669;
}
.label-status-saldo {
  font-size: 0.68rem;
  color: #94a3b8;
  margin-top: 1px;
}

.state-kosong-pembeli {
  padding: 40px 20px;
  text-align: center;
}
.ikon-redup {
  color: #cbd5e1;
  margin-bottom: 8px;
}

/* Kolom Kanan: Detail & Aksi */
.kolom-kanan-detail {
  background: #ffffff;
  border-radius: 16px;
  border: 1.5px solid #e2e8f0;
  padding: 20px 24px;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.03);
  display: flex;
  flex-direction: column;
}

.btn-kembali-mobile {
  display: none;
  align-items: center;
  gap: 8px;
  background: #f1f5f9;
  border: none;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 700;
  color: #334155;
  cursor: pointer;
  margin-bottom: 14px;
}
@media (max-width: 1024px) {
  .btn-kembali-mobile {
    display: flex;
  }
}

/* Detail Pelanggan Penuh */
.detail-pelanggan-penuh {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.kartu-header-detail {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 14px;
  border-bottom: 1px solid #f1f5f9;
}

.profil-kiri {
  display: flex;
  align-items: center;
  gap: 14px;
}
.avatar-detail-besar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #eff6ff;
  color: #2563eb;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.nama-detail-teks {
  font-size: 1.25rem;
  font-weight: 900;
  color: #0f172a;
  margin: 0;
}
.hp-detail-teks {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  color: #64748b;
  margin-top: 2px;
}
.badge-status-pembeli {
  display: flex;
  align-items: center;
  gap: 5px;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #065f46;
  padding: 5px 12px;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 800;
}
.teks-emas {
  color: #d97706;
}

/* KARTU HERO SALDO */
.kartu-hero-saldo {
  background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
  border-radius: 16px;
  padding: 22px 26px;
  color: #ffffff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
  border: 1px solid #1d4ed8;
  position: relative;
  overflow: hidden;
}

.konten-hero-kiri {
  position: relative;
  z-index: 2;
}

.label-hero-saldo {
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  opacity: 0.9;
}

.angka-hero-saldo {
  font-size: 2.4rem;
  font-weight: 900;
  margin: 6px 0;
  letter-spacing: -0.02em;
}

.sub-hero-bulan {
  font-size: 0.85rem;
  opacity: 0.92;
}
.pemisah-titik {
  margin: 0 8px;
  opacity: 0.6;
}

.dekorasi-koin {
  opacity: 0.22;
  position: absolute;
  right: 18px;
  top: 50%;
  transform: translateY(-50%);
}

/* AREA AKSI PENCAIRAN */
.area-aksi-pencairan {
  background: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: 14px;
  padding: 16px 18px;
}

.judul-aksi-bagian {
  font-size: 0.825rem;
  font-weight: 800;
  color: #334155;
  margin-bottom: 12px;
}

.grid-dua-aksi {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media (max-width: 768px) {
  .grid-dua-aksi {
    grid-template-columns: 1fr;
  }
}

.btn-kartu-aksi {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1.5px solid;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s ease;
  user-select: none;
}
.btn-kartu-aksi:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}
.btn-kartu-aksi:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-aksi-tunai {
  background: #ffffff;
  border-color: #10b981;
  color: #065f46;
}
.btn-aksi-tunai:hover:not(:disabled) {
  background: #ecfdf5;
}
.btn-aksi-tunai .ikon-aksi-wrap {
  background: #d1fae5;
  color: #059669;
}

.btn-aksi-belanja {
  background: #ffffff;
  border-color: #2563eb;
  color: #1e40af;
}
.btn-aksi-belanja:hover:not(:disabled) {
  background: #eff6ff;
}
.btn-aksi-belanja .ikon-aksi-wrap {
  background: #dbeafe;
  color: #1d4ed8;
}

.ikon-aksi-wrap {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.teks-aksi-wrap {
  flex: 1;
  min-width: 0;
}
.judul-btn-aksi {
  font-size: 0.925rem;
  font-weight: 800;
  line-height: 1.25;
}
.sub-btn-aksi {
  font-size: 0.725rem;
  color: #64748b;
  margin-top: 2px;
  line-height: 1.3;
}
.panah-aksi {
  opacity: 0.5;
}

/* RIWAYAT MUTASI */
.area-riwayat-mutasi {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.header-riwayat-baris {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.judul-riwayat {
  font-size: 0.95rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
}
.total-mutasi-badge {
  font-size: 0.75rem;
  color: #64748b;
  font-weight: 700;
}

.daftar-riwayat-scroll {
  flex: 1;
  overflow-y: auto;
  max-height: 320px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 8px;
  background: #f8fafc;
}

.baris-riwayat-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  margin-bottom: 6px;
  transition: all 0.15s ease;
}
.baris-riwayat-item:hover {
  border-color: #cbd5e1;
}

.ikon-tipe-mutasi {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.tipe-setor .ikon-tipe-mutasi { background: #ecfdf5; color: #059669; }
.tipe-cair .ikon-tipe-mutasi { background: #fef2f2; color: #dc2626; }

.detail-mutasi-kiri {
  flex: 1;
  min-width: 0;
}
.judul-tipe-teks {
  font-size: 0.85rem;
  font-weight: 800;
  color: #0f172a;
}
.waktu-mutasi-teks {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.72rem;
  color: #64748b;
  margin-top: 2px;
}
.badge-struk-mutasi {
  background: #eff6ff;
  color: #1d4ed8;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 700;
}
.catatan-mutasi-teks {
  font-size: 0.72rem;
  color: #64748b;
  margin-top: 2px;
  font-style: italic;
}

.detail-mutasi-kanan {
  text-align: right;
  flex-shrink: 0;
}
.nominal-mutasi {
  font-size: 1.05rem;
  font-weight: 900;
}
.plus-hijau { color: #059669; }
.minus-merah { color: #dc2626; }

.state-kosong-riwayat {
  padding: 30px;
  text-align: center;
  color: #64748b;
  font-size: 0.85rem;
}

/* Placeholder Kolom Kanan */
.placeholder-pilih-detail {
  padding: 80px 30px;
  text-align: center;
  margin: auto;
  max-width: 480px;
}
.ikon-lingkar-placeholder {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: #f1f5f9;
  color: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px auto;
}
.judul-placeholder {
  font-size: 1.15rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
}
.sub-placeholder {
  font-size: 0.85rem;
  color: #64748b;
  margin-top: 8px;
  line-height: 1.5;
}

/* MODAL SUBMODAL PENCAIRAN */
.latar-submodal {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
  padding: 16px;
}

.kartu-submodal {
  background: #ffffff;
  border-radius: 16px;
  max-width: 480px;
  width: 100%;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
  border: 1.5px solid #e2e8f0;
  overflow: hidden;
}

.header-submodal {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1.5px solid #f1f5f9;
}
.judul-submodal {
  font-size: 1.05rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
}
.btn-tutup-sub {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 4px;
}

.body-submodal {
  padding: 20px;
}

.petunjuk-cair {
  font-size: 0.85rem;
  color: #475569;
  margin: 0;
}

.kotak-info-cair-pelanggan {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 0.85rem;
  color: #334155;
  line-height: 1.5;
}

.grup-input-cair {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.label-cair {
  font-size: 0.825rem;
  font-weight: 800;
  color: #0f172a;
}
.input-wrap-cair {
  position: relative;
  display: flex;
  align-items: center;
}
.awalan-cair-rp {
  position: absolute;
  left: 14px;
  font-size: 1.25rem;
  font-weight: 800;
  color: #64748b;
  font-family: var(--font-angka);
}
.input-cair-besar {
  width: 100%;
  padding-left: 48px !important;
  font-size: 1.5rem !important;
  font-weight: 900 !important;
  height: 48px !important;
  border-radius: 10px;
}

.btn-pilih-semua-cair {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #059669;
  font-size: 0.78rem;
  font-weight: 800;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-pilih-semua-cair:hover {
  background: #d1fae5;
}

.footer-submodal {
  padding: 14px 20px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  display: flex;
  gap: 10px;
}

.teks-hijau { color: #059669; }
.teks-biru { color: #2563eb; }
.teks-merah { color: #dc2626; }
.animasi-putar { animation: putar 1s linear infinite; }
@keyframes putar { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
