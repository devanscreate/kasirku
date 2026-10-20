<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { 
  Banknote, 
  QrCode, 
  ArrowRightLeft, 
  X, 
  Check, 
  AlertCircle, 
  Coins, 
  HeartHandshake, 
  Sparkles, 
  Phone, 
  User, 
  Gift,
  Search,
  CheckCircle2
} from 'lucide-vue-next'
import { cekSaldoPelanggan, bersihkanNomorHp, ambilDaftarPelangganDonasi } from '../layanan/donasi'

const props = defineProps({
  total: {
    type: Number,
    required: true
  },
  prefillPotongDonasi: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['tutup', 'bayar'])

const metode = ref('tunai') // 'tunai' | 'qris' | 'transfer'
const pesanError = ref('')

const formatRupiah = (val) => 'Rp ' + Number(val || 0).toLocaleString('id-ID')

// ================= FITUR POTONG TAGIHAN DARI SALDO TABUNGAN DONASI =================
const modePotongSaldo = ref(false)
const noHpCariPotong = ref('')
const namaDitemukanPotong = ref('')
const saldoDitemukanPotong = ref(0)
const pesanCariPotong = ref('')
const sedangCariSaldoPotong = ref(false)
const potonganSaldoDonasi = ref(0)

// Daftar pelanggan yang telah memiliki saldo tabungan donasi
const daftarPelangganBersaldo = ref([])
const sedangMemuatPelanggan = ref(false)
const tampilkanSemuaSaran = ref(false)

async function muatPelangganBersaldo() {
  sedangMemuatPelanggan.value = true
  try {
    const list = await ambilDaftarPelangganDonasi()
    if (Array.isArray(list)) {
      // Ambil pelanggan dengan saldo > 0 dan urutkan saldo terbanyak
      daftarPelangganBersaldo.value = list
        .filter(p => Number(p.total_saldo || 0) > 0)
        .sort((a, b) => Number(b.total_saldo || 0) - Number(a.total_saldo || 0))
    }
  } catch (err) {
    console.warn('Gagal memuat daftar pelanggan bersaldo di modal bayar:', err)
  } finally {
    sedangMemuatPelanggan.value = false
  }
}

// Filter saran pelanggan sesuai nomor HP atau nama yang sedang diketik
const daftarPelangganTersaring = computed(() => {
  const q = (noHpCariPotong.value || '').trim().toLowerCase()
  const qHp = bersihkanNomorHp(q)
  if (!q) {
    return daftarPelangganBersaldo.value
  }
  return daftarPelangganBersaldo.value.filter(p => {
    const hpCocok = qHp ? (p.nomor_hp || '').includes(qHp) : false
    const namaCocok = (p.nama_pelanggan || '').toLowerCase().includes(q)
    return hpCocok || namaCocok
  })
})

const daftarPelangganTampil = computed(() => {
  if (tampilkanSemuaSaran.value || noHpCariPotong.value) {
    return daftarPelangganTersaring.value.slice(0, 8)
  }
  return daftarPelangganTersaring.value.slice(0, 4)
})

function pilihPelangganDariSaran(pel) {
  noHpCariPotong.value = pel.nomor_hp
  namaDitemukanPotong.value = pel.nama_pelanggan || 'Pelanggan'
  saldoDitemukanPotong.value = Number(pel.total_saldo || 0)
  pesanCariPotong.value = `Ditemukan saldo tabungan donasi: ${formatRupiah(pel.total_saldo)}`
  // Langsung terapkan pemotongan saldo belanja secara otomatis
  terapkanPotongSaldo()
}

async function cariSaldoUntukPotong() {
  const q = (noHpCariPotong.value || '').trim()
  if (!q) {
    pesanCariPotong.value = 'Silakan ketik nomor HP pembeli'
    return
  }

  // Cek apakah ada kecocokan di daftar pembeli bersaldo
  const exact = daftarPelangganBersaldo.value.find(
    p => bersihkanNomorHp(p.nomor_hp) === bersihkanNomorHp(q)
  )
  if (exact) {
    pilihPelangganDariSaran(exact)
    return
  }

  // Jika hasil filter hanya 1
  if (daftarPelangganTersaring.value.length === 1) {
    pilihPelangganDariSaran(daftarPelangganTersaring.value[0])
    return
  }

  const hp = bersihkanNomorHp(q)
  if (!hp) {
    pesanCariPotong.value = 'Silakan ketik nomor HP yang valid atau pilih dari daftar'
    return
  }

  sedangCariSaldoPotong.value = true
  pesanCariPotong.value = ''
  try {
    const data = await cekSaldoPelanggan(hp)
    if (data && Number(data.total_saldo || 0) > 0) {
      saldoDitemukanPotong.value = Number(data.total_saldo)
      namaDitemukanPotong.value = data.nama_pelanggan || 'Pelanggan'
      pesanCariPotong.value = `Ditemukan saldo tabungan donasi: ${formatRupiah(data.total_saldo)}`
      // Langsung terapkan pemotongan saldo
      terapkanPotongSaldo()
    } else {
      saldoDitemukanPotong.value = 0
      potonganSaldoDonasi.value = 0
      uangDiterima.value = props.total
      teksUangDiterima.value = props.total > 0 ? Number(props.total).toLocaleString('id-ID') : '0'
      pesanCariPotong.value = 'Belum ada saldo tabungan donasi untuk nomor HP ini.'
    }
  } catch (err) {
    pesanCariPotong.value = 'Gagal memeriksa saldo: ' + err.message
  } finally {
    sedangCariSaldoPotong.value = false
  }
}

function terapkanPotongSaldo() {
  const saldo = Number(saldoDitemukanPotong.value || 0)
  const totalBelanja = Number(props.total || 0)
  const maxPotong = Math.min(saldo, totalBelanja)
  const sisaBayar = Math.max(0, totalBelanja - maxPotong)

  potonganSaldoDonasi.value = maxPotong
  uangDiterima.value = sisaBayar
  teksUangDiterima.value = sisaBayar > 0 ? Number(sisaBayar).toLocaleString('id-ID') : '0'

  // Otomatis sinkronkan nomor HP & nama ke form donasi kembalian jika nantinya ada kembalian
  if (noHpCariPotong.value) {
    nomorHpDonasi.value = noHpCariPotong.value
    namaPelangganDonasi.value = namaDitemukanPotong.value || 'Pelanggan'
  }
}

function batalkanPotongSaldo() {
  potonganSaldoDonasi.value = 0
  saldoDitemukanPotong.value = 0
  modePotongSaldo.value = false
  noHpCariPotong.value = ''
  pesanCariPotong.value = ''
  uangDiterima.value = props.total
  teksUangDiterima.value = props.total > 0 ? Number(props.total).toLocaleString('id-ID') : '0'
}

onMounted(() => {
  muatPelangganBersaldo()
  if (props.prefillPotongDonasi && Number(props.prefillPotongDonasi.saldoMaksimal || 0) > 0) {
    modePotongSaldo.value = true
    noHpCariPotong.value = props.prefillPotongDonasi.nomorHp || ''
    namaDitemukanPotong.value = props.prefillPotongDonasi.namaPelanggan || 'Pelanggan'
    saldoDitemukanPotong.value = Number(props.prefillPotongDonasi.saldoMaksimal || 0)
    terapkanPotongSaldo()
  }
})

watch(modePotongSaldo, (aktif) => {
  if (aktif && daftarPelangganBersaldo.value.length === 0) {
    muatPelangganBersaldo()
  }
})

// Total yang harus dibayar setelah dikurangi potongan donasi
const totalSetelahPotongan = computed(() => {
  return Math.max(0, props.total - potonganSaldoDonasi.value)
})

const uangDiterima = ref(props.total)
const teksUangDiterima = ref('')

// Sinkronkan teks tampilan uang diterima setiap kali nilai uangDiterima berubah
watch(
  uangDiterima,
  (val) => {
    teksUangDiterima.value = (val !== null && val !== undefined && val >= 0) ? Number(val).toLocaleString('id-ID') : '0'
  },
  { immediate: true }
)

// Sinkronkan jika total tagihan atau potongan belanja berubah
watch(
  () => props.total,
  (val) => {
    const sisa = Math.max(0, (val || 0) - potonganSaldoDonasi.value)
    uangDiterima.value = sisa
  }
)

watch(
  totalSetelahPotongan,
  (val) => {
    uangDiterima.value = val
  }
)

function tanganiInputUangDiterima(e) {
  const digitOnly = String(e.target.value || '').replace(/\D/g, '')
  const num = digitOnly ? parseInt(digitOnly, 10) : 0
  uangDiterima.value = num
  const formatAngka = num > 0 ? Number(num).toLocaleString('id-ID') : ''
  teksUangDiterima.value = formatAngka
  e.target.value = formatAngka
}

// ================= FITUR PENAWARAN DONASI KEMBALIAN (FLOWCHART KASIRKU) =================
const apakahDonasi = ref(false)
const nominalDonasi = ref(0)
const nomorHpDonasi = ref('')
const namaPelangganDonasi = ref('')
const saldoEksisPelanggan = ref(0)
const sedangCekSaldoDonasi = ref(false)

async function cekSaldoNoHp() {
  const hp = bersihkanNomorHp(nomorHpDonasi.value)
  if (!hp || hp.length < 5) return
  sedangCekSaldoDonasi.value = true
  try {
    const data = await cekSaldoPelanggan(hp)
    if (data) {
      saldoEksisPelanggan.value = data.total_saldo || 0
      if (!namaPelangganDonasi.value && data.nama_pelanggan) {
        namaPelangganDonasi.value = data.nama_pelanggan
      }
    }
  } catch (err) {
    console.warn('Gagal cek saldo nomor HP:', err)
  } finally {
    sedangCekSaldoDonasi.value = false
  }
}

function aktifkanDonasiOtomatis() {
  apakahDonasi.value = !apakahDonasi.value
  if (apakahDonasi.value) {
    // Default: paskan ke kembalian jika kecil (<= 400), atau pilih 200
    if (kembalianAsli.value <= 400) {
      nominalDonasi.value = kembalianAsli.value
    } else {
      nominalDonasi.value = 200
    }
    // Jika nomor HP sudah ada dari potong saldo, otomatis isikan
    if (!nomorHpDonasi.value && noHpCariPotong.value) {
      nomorHpDonasi.value = noHpCariPotong.value
      if (!namaPelangganDonasi.value && namaDitemukanPotong.value) {
        namaPelangganDonasi.value = namaDitemukanPotong.value
      }
      if (saldoDitemukanPotong.value > 0) {
        saldoEksisPelanggan.value = saldoDitemukanPotong.value
      }
    }
  } else {
    nominalDonasi.value = 0
  }
}

// Deteksi otomatis saat nomor HP donasi dipilih atau diketik
watch(nomorHpDonasi, (val) => {
  const hpBersih = bersihkanNomorHp(val)
  if (!hpBersih) return
  const cocok = daftarPelangganBersaldo.value.find(p => bersihkanNomorHp(p.nomor_hp) === hpBersih)
  if (cocok) {
    if (!namaPelangganDonasi.value && cocok.nama_pelanggan) {
      namaPelangganDonasi.value = cocok.nama_pelanggan
    }
    saldoEksisPelanggan.value = cocok.total_saldo || 0
  }
})

function pilihTemplateNominal(nom) {
  if (nom > kembalianAsli.value) {
    nominalDonasi.value = kembalianAsli.value
  } else {
    nominalDonasi.value = nom
  }
}

// Pilihan nominal kembalian yang bisa dimasukkan ke celengan tabungan
const daftarPilihanTemplate = computed(() => {
  const k = kembalianAsli.value
  const list = [500, 400, 300, 200, 100]
  return list.filter(nom => nom < k)
})

// Pecahan uang kertas Indonesia standar
const pecahanCepat = [10000, 20000, 50000, 100000]

// Hitung nominal bulat di atas total setelah potongan
const opsiBulat = computed(() => {
  const t = totalSetelahPotongan.value
  if (t <= 0) return []
  const daftar = [{ label: `Uang Pas (${formatRupiah(t)})`, nilai: t, tipe: 'pas' }]
  
  pecahanCepat.forEach(pecahan => {
    if (pecahan > t) {
      daftar.push({ label: formatRupiah(pecahan), nilai: pecahan, tipe: pecahan })
    }
  })

  // Nominal kelipatan 50rb / 100rb terdekat
  const bulat50 = Math.ceil(t / 50000) * 50000
  if (bulat50 > t && !daftar.some(d => d.nilai === bulat50)) {
    daftar.push({ label: formatRupiah(bulat50), nilai: bulat50, tipe: 50000 })
  }
  const bulat100 = Math.ceil(t / 100000) * 100000
  if (bulat100 > t && !daftar.some(d => d.nilai === bulat100)) {
    daftar.push({ label: formatRupiah(bulat100), nilai: bulat100, tipe: 100000 })
  }
  return daftar
})

function gayaTombolPecahan(opsi) {
  if (opsi.tipe === 'pas') {
    return { bg: '#ecfdf5', color: '#047857', border: '#10b981', aktifBg: '#059669', aktifColor: '#ffffff' }
  }
  return { bg: '#ffffff', color: '#0f172a', border: '#cbd5e1', aktifBg: '#0f172a', aktifColor: '#ffffff' }
}

const kembalianAsli = computed(() => {
  if (metode.value !== 'tunai') return 0
  return Math.max(0, uangDiterima.value - totalSetelahPotongan.value)
})

// Kembalian fisik yang benar-benar diserahkan ke pelanggan setelah dipotong donasi
const kembalianFisik = computed(() => {
  if (!apakahDonasi.value) return kembalianAsli.value
  return Math.max(0, kembalianAsli.value - nominalDonasi.value)
})

const apakahCukup = computed(() => {
  if (totalSetelahPotongan.value === 0) return true
  if (metode.value !== 'tunai') return true
  return uangDiterima.value >= totalSetelahPotongan.value
})

function konfirmasiBayar() {
  if (metode.value === 'tunai' && totalSetelahPotongan.value > 0 && uangDiterima.value < totalSetelahPotongan.value) {
    pesanError.value = 'Uang yang diterima masih kurang dari sisa tagihan belanja!'
    return
  }

  if (apakahDonasi.value && nominalDonasi.value > 0) {
    const hp = bersihkanNomorHp(nomorHpDonasi.value)
    if (!hp || hp.length < 5) {
      pesanError.value = 'Nomor HP pembeli wajib diisi agar saldo celengan tabungan tercatat!'
      return
    }
  }

  pesanError.value = ''

  const isLunasTabungan = totalSetelahPotongan.value === 0 && potonganSaldoDonasi.value > 0

  emit('bayar', {
    metode: isLunasTabungan ? 'tabungan' : metode.value,
    diterima: isLunasTabungan ? 0 : (metode.value !== 'tunai' ? totalSetelahPotongan.value : uangDiterima.value),
    kembalian: isLunasTabungan ? 0 : kembalianFisik.value,
    kembalianAsli: isLunasTabungan ? 0 : kembalianAsli.value,
    totalBelanjaAsli: props.total,
    totalSetelahPotongan: totalSetelahPotongan.value,
    donasi: (!isLunasTabungan && apakahDonasi.value && nominalDonasi.value > 0) ? {
      nominal: nominalDonasi.value,
      nomorHp: bersihkanNomorHp(nomorHpDonasi.value),
      namaPelanggan: namaPelangganDonasi.value || 'Pelanggan'
    } : null,
    potonganDonasi: potonganSaldoDonasi.value > 0 ? {
      nominal: potonganSaldoDonasi.value,
      nomorHp: bersihkanNomorHp(noHpCariPotong.value),
      namaPelanggan: namaDitemukanPotong.value || 'Pelanggan',
      saldoAwal: saldoDitemukanPotong.value
    } : null
  })
}

function tanganiPintasanModal(e) {
  if (e.key === 'F9' || e.key === 'F4' || (e.key === 'Enter' && e.target.tagName !== 'BUTTON')) {
    if (apakahCukup.value) {
      e.preventDefault()
      konfirmasiBayar()
    }
  } else if (e.key === 'Escape') {
    emit('tutup')
  }
}
</script>

<template>
  <div class="latar-modal" tabindex="-1" @keydown="tanganiPintasanModal">
    <div class="kotak-modal modal-bayar-lebar">
      <!-- 1. Header Modal Tetap (Sticky di Atas) -->
      <div class="header-modal-bayar">
        <div class="flex items-center gap-2.5">
          <div class="ikon-header-bayar">
            <Banknote :size="22" />
          </div>
          <div>
            <h2 class="judul-modal">Pembayaran Belanja</h2>
            <p class="sub-modal">Pilih cara bayar dan selesaikan transaksi</p>
          </div>
        </div>
        <button class="tombol-tutup" @click="emit('tutup')" title="Tutup (Esc)">
          <X :size="20" />
        </button>
      </div>

      <!-- 2. Isi Modal Scrollable (Aman di Layar Laptop Pendek, Tablet, & HP) -->
      <div class="body-modal-bayar">
        <!-- Peringatan Kesalahan jika Ada -->
        <div v-if="pesanError" class="peringatan-error-bayar mb-3">
          <AlertCircle :size="18" class="flex-shrink-0" />
          <span>{{ pesanError }}</span>
        </div>

        <!-- KARTU RINGKASAN TAGIHAN & SISA BAYAR (LEDGER BERSIH & JELAS) -->
        <div class="kartu-ringkasan-tagihan mb-3">
          <!-- Jika Ada Potongan Tabungan Donasi -->
          <template v-if="potonganSaldoDonasi > 0">
            <div class="baris-ledger">
              <span class="label-ledger">Total Belanja Asli:</span>
              <span class="nilai-ledger font-angka">{{ formatRupiah(props.total) }}</span>
            </div>
            <div class="baris-ledger ledger-potongan">
              <div class="flex items-center gap-1.5">
                <Sparkles :size="14" class="teks-emas flex-shrink-0" />
                <span class="label-ledger teks-sukses-tebal">Potongan Saldo Tabungan:</span>
              </div>
              <span class="nilai-ledger font-angka teks-sukses-tebal">-{{ formatRupiah(potonganSaldoDonasi) }}</span>
            </div>
            <div class="garis-pemisah-ledger"></div>
          </template>

          <!-- Baris Utama: Tagihan Akhir / Sisa Wajib Bayar -->
          <div class="baris-ledger-utama">
            <div class="info-kiri-ledger">
              <div class="label-tagihan-utama">
                {{ potonganSaldoDonasi > 0 ? 'SISA YANG HARUS DIBAYAR' : 'TOTAL TAGIHAN BELANJA' }}
              </div>
              <div v-if="potonganSaldoDonasi > 0" class="sub-sisa-saldo">
                Pembeli: <strong>{{ namaDitemukanPotong }}</strong> • Sisa Saldo: <strong class="font-angka">{{ formatRupiah(Math.max(0, saldoDitemukanPotong - potonganSaldoDonasi)) }}</strong>
              </div>
            </div>
            <div class="angka-tagihan-utama font-angka" :class="{ 'lunas-hijau': totalSetelahPotongan === 0 }">
              {{ formatRupiah(totalSetelahPotongan) }}
            </div>
          </div>
        </div>

        <!-- FITUR TABUNGAN DONASI PELANGGAN -->
        <!-- Status A: Tabungan SUDAH DIPAKAI (Ribbon Bersih & Ringkas) -->
        <div v-if="potonganSaldoDonasi > 0" class="ribbon-tabungan-terpasang mb-3">
          <div class="flex items-center gap-2 min-w-0">
            <div class="ikon-tabungan-centang">
              <Check :size="16" />
            </div>
            <div class="info-tabungan-terpasang">
              <div class="judul-terpasang">
                Saldo Tabungan Terpakai: <strong class="font-angka teks-sukses-tebal">-{{ formatRupiah(potonganSaldoDonasi) }}</strong>
              </div>
              <div class="sub-terpasang">
                Pembeli: <strong>{{ namaDitemukanPotong }}</strong> ({{ noHpCariPotong }})
              </div>
            </div>
          </div>
          <button type="button" class="btn-ganti-tabungan" @click="batalkanPotongSaldo" title="Batalkan atau ganti nomor HP pembeli">
            <X :size="13" />
            <span>Ganti / Batal</span>
          </button>
        </div>

        <!-- Status B: Tabungan BELUM DIPAKAI (Ajakan atau Form Pencarian) -->
        <div v-else class="drawer-tabungan-opsi mb-3">
          <!-- Ajakan Minimalis -->
          <div v-if="!modePotongSaldo" class="banner-ajakan-tabungan">
            <div class="flex items-center gap-2">
              <Coins :size="18" class="teks-emas flex-shrink-0" />
              <span class="teks-ajakan">Pembeli ingin bayar pakai saldo tabungan / celengan?</span>
            </div>
            <button type="button" class="btn-buka-tabungan" @click="modePotongSaldo = true">
              Pakai Saldo Tabungan
            </button>
          </div>

          <!-- Form Pencarian & Pilihan Cepat Pelanggan Bersaldo -->
          <div v-else class="kotak-pencarian-tabungan">
            <div class="header-pencarian-tabungan flex justify-between items-center mb-2">
              <div class="judul-cari-tabungan flex items-center gap-1.5">
                <Coins :size="16" class="teks-emas flex-shrink-0" />
                <span>Ketik nomor HP atau nama pembeli:</span>
              </div>
              <button type="button" class="btn-tutup-drawer" @click="batalkanPotongSaldo" title="Tutup form tabungan">
                <X :size="16" />
              </button>
            </div>

            <!-- Baris Input Pencarian -->
            <div class="baris-input-cari">
              <div class="wrap-input-cari-hp flex-1">
                <Search :size="16" class="ikon-search-hp" />
                <input 
                  v-model="noHpCariPotong" 
                  type="text" 
                  class="input-teks input-cari-hp font-angka" 
                  placeholder="Ketik nomor HP atau nama pembeli..."
                  @keydown.enter.prevent="cariSaldoUntukPotong"
                />
                <button 
                  v-if="noHpCariPotong"
                  type="button"
                  class="btn-bersihkan-hp"
                  @click="noHpCariPotong = ''; saldoDitemukanPotong = 0; pesanCariPotong = ''"
                  title="Hapus teks"
                >
                  <X :size="13" />
                </button>
              </div>
              <button 
                type="button" 
                class="tombol tombol-primer btn-aksi-cari-saldo" 
                :disabled="sedangCariSaldoPotong"
                @click="cariSaldoUntukPotong"
              >
                {{ sedangCariSaldoPotong ? 'Mencari...' : 'Cari Saldo' }}
              </button>
            </div>

            <!-- Daftar Cepat Pembeli yang Sudah Memiliki Saldo Tabungan -->
            <div v-if="daftarPelangganBersaldo.length > 0" class="area-chip-pelanggan mt-2">
              <div class="header-chip-saran flex justify-between items-center">
                <span class="label-chip-saran flex items-center gap-1">
                  <span>{{ noHpCariPotong ? 'Hasil yang Cocok:' : 'Pilih Cepat Pembeli Bersaldo:' }}</span>
                  <span class="badge-jumlah-saran">({{ daftarPelangganTersaring.length }})</span>
                </span>
                <button 
                  v-if="!noHpCariPotong && daftarPelangganTersaring.length > 4" 
                  type="button" 
                  class="btn-toggle-saran"
                  @click="tampilkanSemuaSaran = !tampilkanSemuaSaran"
                >
                  {{ tampilkanSemuaSaran ? 'Ciutkan' : `Lihat Semua (${daftarPelangganTersaring.length})` }}
                </button>
              </div>

              <!-- Grid Chips Pelanggan -->
              <div v-if="daftarPelangganTampil.length > 0" class="grid-chip-saran mt-1.5">
                <button
                  v-for="pel in daftarPelangganTampil"
                  :key="pel.nomor_hp"
                  type="button"
                  class="chip-pelanggan-item"
                  :class="{ 'chip-terpilih': noHpCariPotong === pel.nomor_hp && saldoDitemukanPotong > 0 }"
                  @click="pilihPelangganDariSaran(pel)"
                  title="Klik untuk langsung menerapkan saldo pembeli ini"
                >
                  <div class="avatar-chip">
                    <User :size="12" />
                  </div>
                  <div class="detail-chip">
                    <div class="nama-chip-teks">{{ pel.nama_pelanggan || 'Pelanggan' }}</div>
                    <div class="hp-chip-teks font-angka">{{ pel.nomor_hp }}</div>
                  </div>
                  <div class="saldo-chip-teks font-angka">
                    {{ formatRupiah(pel.total_saldo) }}
                  </div>
                </button>
              </div>

              <div v-else-if="noHpCariPotong" class="teks-tidak-ditemukan mt-1">
                Tidak ada pembeli bersaldo dengan kata kunci "<strong>{{ noHpCariPotong }}</strong>". Tekan tombol <em>Cari Saldo</em> untuk mencari ke sistem.
              </div>
            </div>

            <!-- Pesan Info Pencarian jika nomor HP belum terdaftar saldo -->
            <div v-if="pesanCariPotong && saldoDitemukanPotong === 0" class="pesan-info-cari mt-2">
              <AlertCircle :size="14" class="flex-shrink-0" />
              <span>{{ pesanCariPotong }}</span>
            </div>
          </div>
        </div>

        <!-- JIKA TAGIHAN 100% LUNAS DARI SALDO TABUNGAN (SISA BAYAR = Rp 0) -->
        <div v-if="totalSetelahPotongan === 0" class="kartu-lunas-penuh mb-3">
          <div class="ikon-lunas-lingkar">
            <CheckCircle2 :size="36" />
          </div>
          <div class="konten-lunas">
            <h3 class="judul-lunas-penuh">TAGIHAN LUNAS (Rp 0)</h3>
            <p class="deskripsi-lunas">
              Seluruh tagihan belanja sebesar <strong>{{ formatRupiah(props.total) }}</strong> telah ditutup sepenuhnya oleh saldo tabungan pembeli. Kasir tidak perlu menerima uang tunai.
            </p>
            <div class="badge-rincian-lunas">
              <span>Pembeli: <strong>{{ namaDitemukanPotong }}</strong> ({{ noHpCariPotong }})</span>
              <span class="pemisah-titik">•</span>
              <span>Sisa Tabungan: <strong class="font-angka">{{ formatRupiah(Math.max(0, saldoDitemukanPotong - potonganSaldoDonasi)) }}</strong></span>
            </div>
            <div class="petunjuk-klik-lunas">
              Tekan tombol hijau <strong>SELESAIKAN PEMBAYARAN</strong> di bawah atau tekan tombol <strong>Enter / F9</strong> untuk mencetak struk transaksi.
            </div>
          </div>
        </div>

        <!-- JIKA MASIH ADA SISA TAGIHAN YANG HARUS DIBAYAR (> Rp 0) -->
        <template v-else>
          <!-- Pilihan Cara Pembayaran -->
          <div class="label-bagian">Pilih Cara Pembayaran:</div>
          <div class="metode-pilihan">
            <button 
              type="button"
              class="metode-btn metode-tunai"
              :class="{ 'aktif': metode === 'tunai' }"
              @click="metode = 'tunai'; uangDiterima = totalSetelahPotongan"
            >
              <Banknote :size="22" class="ikon-metode" />
              <span class="nama-metode">Tunai (Cash)</span>
              <span class="sub-metode">Uang kertas / koin</span>
            </button>

            <button 
              type="button"
              class="metode-btn metode-qris"
              :class="{ 'aktif': metode === 'qris' }"
              @click="metode = 'qris'; uangDiterima = totalSetelahPotongan"
            >
              <QrCode :size="22" class="ikon-metode" />
              <span class="nama-metode">QRIS</span>
              <span class="sub-metode">Scan barcode</span>
            </button>

            <button 
              type="button"
              class="metode-btn metode-transfer"
              :class="{ 'aktif': metode === 'transfer' }"
              @click="metode = 'transfer'; uangDiterima = totalSetelahPotongan"
            >
              <ArrowRightLeft :size="22" class="ikon-metode" />
              <span class="nama-metode">Transfer Bank</span>
              <span class="sub-metode">Kirim ke rekening</span>
            </button>
          </div>

          <!-- Form Khusus Pembayaran Tunai -->
          <div v-if="metode === 'tunai'" class="bagian-tunai">
            <div class="grup-form">
              <div class="flex justify-between items-center mb-1">
                <label class="label-form">Jumlah Uang Tunai dari Pembeli:</label>
                <span class="petunjuk-wajib-bayar font-angka">
                  Wajib Bayar: <strong>{{ formatRupiah(totalSetelahPotongan) }}</strong>
                </span>
              </div>
              <div class="input-wrap-besar">
                <span class="awalan-rp">Rp</span>
                <input 
                  :value="teksUangDiterima"
                  type="text"
                  inputmode="numeric"
                  class="input-teks input-bayar-besar font-angka"
                  placeholder="0"
                  autofocus
                  @focus="$event.target.select()"
                  @input="tanganiInputUangDiterima"
                  @keydown.enter="konfirmasiBayar"
                />
              </div>
            </div>

            <!-- Tombol Pilihan Pecahan Uang Cepat -->
            <div v-if="opsiBulat.length > 0" class="area-pecahan-cepat">
              <div class="label-cepat">Pilihan Cepat Nominal:</div>
              <div class="grid-nominal">
                <button 
                  v-for="opsi in opsiBulat" 
                  :key="opsi.nilai"
                  type="button"
                  class="btn-pecahan"
                  :class="{ 
                    'btn-uang-pas': opsi.tipe === 'pas', 
                    'pecahan-terpilih': uangDiterima === opsi.nilai && opsi.tipe !== 'pas' 
                  }"
                  @click="uangDiterima = opsi.nilai"
                >
                  {{ opsi.label }}
                </button>
              </div>
            </div>

            <!-- Kotak Uang Kembalian / Status Pembayaran -->
            <div class="kotak-kembalian" :class="{ 'kurang': uangDiterima < totalSetelahPotongan }">
              <div class="flex justify-between items-center wrap-kembalian">
                <div>
                  <span class="label-kembalian">
                    {{ uangDiterima < totalSetelahPotongan ? 'Uang Pembeli Masih Kurang:' : 'Uang Kembalian untuk Pembeli:' }}
                  </span>
                  <div class="sub-kembalian-info">
                    <template v-if="uangDiterima < totalSetelahPotongan">
                      Kasir belum dapat menyelesaikan pembayaran karena uang masih kurang.
                    </template>
                    <template v-else-if="kembalianAsli === 0">
                      ✓ Uang pas — tidak ada kembalian fisik.
                    </template>
                    <template v-else>
                      Serahkan uang kembalian fisik sebesar <strong>{{ formatRupiah(kembalianFisik) }}</strong> ke pembeli.
                    </template>
                  </div>
                </div>
                <span class="angka-kembalian font-angka">
                  {{ formatRupiah(uangDiterima < totalSetelahPotongan ? (totalSetelahPotongan - uangDiterima) : kembalianAsli) }}
                </span>
              </div>
            </div>

            <!-- FITUR CELENGAN TABUNGAN KEMBALIAN (Hanya Tampil Jika Ada Kembalian Asli) -->
            <div v-if="kembalianAsli > 0" class="kotak-donasi-kembalian mt-3">
              <div class="header-donasi flex justify-between items-center wrap-hp">
                <div class="flex items-center gap-2">
                  <div class="ikon-donasi-lingkar">
                    <Coins :size="20" />
                  </div>
                  <div>
                    <div class="judul-donasi">Celengan Tabungan Kembalian</div>
                    <div class="sub-donasi">
                      Tawarkan ke pembeli: <em>"Kembaliannya <strong>{{ formatRupiah(kembalianAsli) }}</strong> mau ditabung ke nomor HP, Bu/Pak?"</em>
                    </div>
                  </div>
                </div>

                <button 
                  type="button" 
                  class="btn-toggle-donasi"
                  :class="apakahDonasi ? 'toggle-aktif-ya' : 'toggle-nonaktif'"
                  @click="aktifkanDonasiOtomatis"
                >
                  <span>{{ apakahDonasi ? '✓ Ya, Masukkan Tabungan' : 'Tidak (Kembalikan Penuh)' }}</span>
                </button>
              </div>

              <!-- Form Rincian Tabungan Jika Disetujui Pembeli -->
              <div v-if="apakahDonasi" class="form-donasi-terbuka mt-3">
                <div class="label-template-bar">Berapa kembalian yang ingin dimasukkan ke tabungan?</div>
                <div class="grid-nominal-template">
                  <button 
                    v-for="nom in daftarPilihanTemplate" 
                    :key="nom"
                    type="button"
                    class="btn-nom-template font-angka"
                    :class="{ 'aktif-template': nominalDonasi === nom }"
                    @click="pilihTemplateNominal(nom)"
                  >
                    {{ formatRupiah(nom) }}
                  </button>
                  <button 
                    type="button" 
                    class="btn-nom-template btn-paskan-kembalian font-angka"
                    :class="{ 'aktif-template': nominalDonasi === kembalianAsli }"
                    @click="nominalDonasi = kembalianAsli"
                  >
                    Semua Kembalian ({{ formatRupiah(kembalianAsli) }})
                  </button>
                </div>

                <!-- Input No HP & Nama Pembeli -->
                <div class="grid-form-donasi mt-3">
                  <div class="grup-donasi">
                    <label class="label-form-kecil">Nomor WhatsApp / HP Pembeli* (Wajib diisi):</label>
                    <div class="wrap-input-hp-donasi">
                      <Phone :size="15" class="ikon-hp-field" />
                      <input 
                        v-model="nomorHpDonasi"
                        type="tel"
                        class="input-hp-field font-angka"
                        placeholder="Contoh: 08123456789"
                        list="list-saran-hp-donasi"
                        @blur="cekSaldoNoHp"
                      />
                      <datalist id="list-saran-hp-donasi">
                        <option 
                          v-for="p in daftarPelangganBersaldo" 
                          :key="p.nomor_hp" 
                          :value="p.nomor_hp"
                        >
                          {{ p.nama_pelanggan || 'Pelanggan' }} - Saldo: {{ formatRupiah(p.total_saldo) }}
                        </option>
                      </datalist>
                    </div>
                    <span class="petunjuk-donasi-hp">Nomor ini menjadi nomor rekening tabungan pelanggan di toko.</span>
                  </div>
                  <div class="grup-donasi">
                    <label class="label-form-kecil">Nama Pembeli (Opsional):</label>
                    <input 
                      v-model="namaPelangganDonasi"
                      type="text"
                      class="input-nama-field"
                      placeholder="Nama Pelanggan"
                    />
                  </div>
                </div>

                <!-- Info Jika Pembeli Sudah Pernah Menabung Sebelumnya -->
                <div v-if="saldoEksisPelanggan > 0" class="badge-saldo-eksis mt-2">
                  <Sparkles :size="15" class="teks-emas flex-shrink-0" />
                  <span>Pelanggan ini sudah memiliki saldo tabungan sebelumnya: <strong class="font-angka">{{ formatRupiah(saldoEksisPelanggan) }}</strong></span>
                </div>

                <!-- Rincian Pembagian Uang Kembalian Fisik vs Masuk Celengan -->
                <div class="kotak-rincian-pembagian-kembalian mt-3">
                  <div class="flex justify-between rincian-baris">
                    <span>Total Kembalian Seharusnya:</span>
                    <span class="font-angka tebal">{{ formatRupiah(kembalianAsli) }}</span>
                  </div>
                  <div class="flex justify-between rincian-baris teks-hijau-donasi">
                    <span>Dimasukkan ke Tabungan / Celengan:</span>
                    <span class="font-angka tebal">+{{ formatRupiah(nominalDonasi) }}</span>
                  </div>
                  <div class="flex justify-between rincian-baris baris-kembalian-fisik">
                    <span class="tebal">Uang Tunai yang Diberikan ke Pembeli:</span>
                    <span class="font-angka tebal angka-kembalian-fisik">{{ formatRupiah(kembalianFisik) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Petunjuk Pembayaran Non-Tunai (QRIS & Transfer) -->
          <div v-else class="bagian-non-tunai">
            <div class="kotak-instruksi" :class="metode === 'qris' ? 'instruksi-qris' : 'instruksi-transfer'">
              <div v-if="metode === 'qris'">
                <div class="judul-instruksi">Cara Pembayaran QRIS:</div>
                <p>1. Tunjukkan kode QRIS toko di meja kasir kepada pembeli untuk di-scan lewat HP.</p>
                <p>2. Pastikan nominal pembayaran pas sebesar <strong>{{ formatRupiah(totalSetelahPotongan) }}</strong>.</p>
                <p>3. Jika pembayaran sudah masuk di aplikasi kasir, tekan tombol hijau di bawah.</p>
              </div>
              <div v-else>
                <div class="judul-instruksi">Cara Pembayaran Transfer Bank:</div>
                <p>1. Berikan nomor rekening bank toko kepada pembeli untuk ditransfer via m-Banking atau ATM.</p>
                <p>2. Periksa bukti transfer atau mutasi rekening toko sebesar <strong>{{ formatRupiah(totalSetelahPotongan) }}</strong>.</p>
                <p>3. Jika dana sudah masuk, tekan tombol hijau di bawah.</p>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- 3. Footer Tetap (Sticky) Selalu Terlihat Tanpa Perlu Scroll -->
      <div class="footer-modal-bayar">
        <button type="button" class="tombol tombol-sekunder tombol-batal-bayar" @click="emit('tutup')">
          <span>Batal (Esc)</span>
        </button>
        <button 
          type="button" 
          class="tombol tombol-sukses tombol-konfirmasi-bayar"
          :disabled="!apakahCukup"
          @click="konfirmasiBayar"
        >
          <Check :size="20" />
          <span>{{ totalSetelahPotongan === 0 ? 'SELESAIKAN (Lunas Tabungan) [Enter / F9]' : (apakahCukup ? 'SELESAIKAN PEMBAYARAN (Enter / F9)' : 'Uang Masih Kurang') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-bayar-lebar {
  width: 95%;
  max-width: 550px !important;
  max-height: 92vh;
  display: flex;
  flex-direction: column;
  padding: 0 !important;
  border-radius: 16px;
  overflow: hidden;
  background: #ffffff;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.22);
  border: 1px solid #e2e8f0;
}

/* Header Modal Sticky */
.header-modal-bayar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  background: #ffffff;
  border-bottom: 1.5px solid #e2e8f0;
  flex-shrink: 0;
}
.ikon-header-bayar {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: #ecfdf5;
  color: #059669;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.judul-modal {
  font-size: 1.15rem;
  font-weight: 900;
  color: #0f172a;
  margin: 0;
}
.sub-modal {
  font-size: 0.78rem;
  color: #64748b;
  margin-top: 1px;
  font-weight: 600;
}
.tombol-tutup {
  background: #f1f5f9;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}
.tombol-tutup:hover {
  background: #fee2e2;
  color: #dc2626;
}

/* Body Modal Scrollable */
.body-modal-bayar {
  padding: 16px 20px;
  overflow-y: auto;
  flex: 1;
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 #f8fafc;
}
.body-modal-bayar::-webkit-scrollbar {
  width: 6px;
}
.body-modal-bayar::-webkit-scrollbar-track {
  background: #f8fafc;
}
.body-modal-bayar::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

/* KARTU RINGKASAN TAGIHAN (LEDGER STYLE) */
.kartu-ringkasan-tagihan {
  background: #f8fafc;
  border-radius: 14px;
  padding: 14px 18px;
  border: 1.5px solid #cbd5e1;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
.baris-ledger {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  color: #475569;
  margin-bottom: 4px;
}
.label-ledger {
  font-weight: 700;
}
.nilai-ledger {
  font-weight: 800;
}
.ledger-potongan {
  color: #059669;
}
.teks-sukses-tebal {
  color: #059669;
  font-weight: 800;
}
.garis-pemisah-ledger {
  border-top: 1px dashed #cbd5e1;
  margin: 8px 0;
}
.baris-ledger-utama {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.info-kiri-ledger {
  min-width: 0;
}
.label-tagihan-utama {
  font-size: 0.78rem;
  color: #1e40af;
  font-weight: 900;
  letter-spacing: 0.04em;
}
.sub-sisa-saldo {
  font-size: 0.72rem;
  color: #059669;
  font-weight: 600;
  margin-top: 2px;
}
.angka-tagihan-utama {
  font-size: 1.75rem;
  font-weight: 900;
  color: #2563eb;
  white-space: nowrap;
}
.angka-tagihan-utama.lunas-hijau {
  color: #059669 !important;
}

/* Ribbon Tabungan Terpasang */
.ribbon-tabungan-terpasang {
  background: #ecfdf5;
  border: 1.5px solid #a7f3d0;
  border-radius: 10px;
  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}
.ikon-tabungan-centang {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #d1fae5;
  color: #059669;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.info-tabungan-terpasang {
  line-height: 1.3;
}
.judul-terpasang {
  font-size: 0.85rem;
  font-weight: 700;
  color: #065f46;
}
.sub-terpasang {
  font-size: 0.72rem;
  color: #047857;
}
.btn-ganti-tabungan {
  background: #ffffff;
  border: 1px solid #fca5a5;
  color: #dc2626;
  font-size: 0.75rem;
  font-weight: 800;
  padding: 5px 10px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.15s ease;
  white-space: nowrap;
}
.btn-ganti-tabungan:hover {
  background: #fee2e2;
}

/* Drawer Tabungan Opsi (Sebelum Diterapkan) */
.drawer-tabungan-opsi {
  border-radius: 12px;
}
.banner-ajakan-tabungan {
  background: #fffbeb;
  border: 1.5px solid #fde68a;
  border-radius: 10px;
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}
.teks-ajakan {
  font-size: 0.82rem;
  font-weight: 800;
  color: #92400e;
}
.teks-emas {
  color: #d97706;
}
.btn-buka-tabungan {
  background: #ffffff;
  color: #b45309;
  border: 1.5px solid #fde68a;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 0.78rem;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}
.btn-buka-tabungan:hover {
  background: #fef3c7;
  border-color: #f59e0b;
}

/* Kotak Pencarian Tabungan Terbuka */
.kotak-pencarian-tabungan {
  background: #fffbeb;
  border: 1.5px solid #fde68a;
  border-radius: 12px;
  padding: 12px 14px;
}
.judul-cari-tabungan {
  font-size: 0.8rem;
  font-weight: 800;
  color: #92400e;
}
.btn-tutup-drawer {
  background: none;
  border: none;
  color: #92400e;
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.btn-tutup-drawer:hover {
  background: #fde68a;
}
.baris-input-cari {
  display: flex;
  gap: 8px;
}
.wrap-input-cari-hp {
  position: relative;
  display: flex;
  align-items: center;
}
.ikon-search-hp {
  position: absolute;
  left: 10px;
  color: #d97706;
}
.input-cari-hp {
  width: 100%;
  padding-left: 32px !important;
  padding-right: 30px !important;
  height: 38px !important;
  font-size: 0.85rem !important;
  border: 1.5px solid #cbd5e1;
  border-radius: 8px;
}
.input-cari-hp:focus {
  border-color: #d97706;
  outline: none;
}
.btn-bersihkan-hp {
  position: absolute;
  right: 8px;
  background: #f1f5f9;
  border: none;
  color: #64748b;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.btn-aksi-cari-saldo {
  height: 38px;
  padding: 0 14px;
  font-size: 0.82rem;
  border-radius: 8px;
  white-space: nowrap;
}

/* Saran Chips Pelanggan Bersaldo */
.area-chip-pelanggan {
  background: #ffffff;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 8px 10px;
}
.header-chip-saran {
  margin-bottom: 4px;
}
.label-chip-saran {
  font-size: 0.74rem;
  font-weight: 800;
  color: #92400e;
}
.badge-jumlah-saran {
  font-size: 0.7rem;
  color: #b45309;
}
.btn-toggle-saran {
  background: none;
  border: none;
  font-size: 0.72rem;
  font-weight: 800;
  color: #d97706;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
}
.grid-chip-saran {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
  max-height: 130px;
  overflow-y: auto;
  padding-right: 2px;
}
.chip-pelanggan-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  background: #fefce8;
  border: 1px solid #fef08a;
  border-radius: 8px;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s ease;
}
.chip-pelanggan-item:hover {
  background: #fef9c3;
  border-color: #facc15;
  transform: translateY(-1px);
}
.chip-pelanggan-item.chip-terpilih {
  background: #ecfdf5;
  border-color: #10b981;
}
.avatar-chip {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #fef08a;
  color: #b45309;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-right: 6px;
}
.detail-chip {
  min-width: 0;
  flex: 1;
  line-height: 1.2;
}
.nama-chip-teks {
  font-size: 0.75rem;
  font-weight: 800;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hp-chip-teks {
  font-size: 0.68rem;
  color: #64748b;
}
.saldo-chip-teks {
  font-size: 0.78rem;
  font-weight: 900;
  color: #059669;
  flex-shrink: 0;
  margin-left: 6px;
}
.teks-tidak-ditemukan {
  font-size: 0.72rem;
  color: #64748b;
  font-style: italic;
  padding: 4px 0;
}
.pesan-info-cari {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  color: #b45309;
  background: #fef3c7;
  padding: 6px 10px;
  border-radius: 6px;
}

/* KARTU LUNAS PENUH (Ketiadaan Sisa Bayar = Rp 0) */
.kartu-lunas-penuh {
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  border: 2px solid #10b981;
  border-radius: 14px;
  padding: 16px 18px;
  display: flex;
  gap: 14px;
  align-items: flex-start;
  box-shadow: 0 4px 14px rgba(16, 185, 129, 0.12);
}
.ikon-lunas-lingkar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #ffffff;
  color: #059669;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(16, 185, 129, 0.2);
}
.konten-lunas {
  flex: 1;
}
.judul-lunas-penuh {
  font-size: 1.15rem;
  font-weight: 900;
  color: #065f46;
  margin: 0 0 4px 0;
}
.deskripsi-lunas {
  font-size: 0.85rem;
  color: #047857;
  margin: 0;
  line-height: 1.45;
}
.badge-rincian-lunas {
  background: #ffffff;
  border: 1px solid #a7f3d0;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 0.78rem;
  color: #065f46;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 10px 0 8px 0;
  flex-wrap: wrap;
}
.pemisah-titik {
  color: #94a3b8;
}
.petunjuk-klik-lunas {
  font-size: 0.75rem;
  color: #047857;
  font-style: italic;
}

/* PILIHAN CARA BAYAR */
.label-bagian {
  font-size: 0.85rem;
  font-weight: 800;
  color: #334155;
  margin-bottom: 8px;
}
.metode-pilihan {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 14px;
}
.metode-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 10px 6px;
  border-radius: 10px;
  border: 2px solid #cbd5e1;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
  text-align: center;
}
.ikon-metode {
  margin-bottom: 4px;
}
.nama-metode {
  font-size: 0.88rem;
  font-weight: 800;
  color: #0f172a;
}
.sub-metode {
  font-size: 0.7rem;
  color: #64748b;
  margin-top: 1px;
}
.metode-tunai .ikon-metode { color: #059669; }
.metode-tunai:hover { border-color: #059669; background: #ecfdf5; }
.metode-tunai.aktif {
  background: #ecfdf5;
  border-color: #059669;
  box-shadow: 0 4px 10px rgba(5, 150, 105, 0.15);
}
.metode-tunai.aktif .nama-metode { color: #047857; }

.metode-qris .ikon-metode { color: #0284c7; }
.metode-qris:hover { border-color: #0284c7; background: #f0f9ff; }
.metode-qris.aktif {
  background: #f0f9ff;
  border-color: #0284c7;
  box-shadow: 0 4px 10px rgba(2, 132, 199, 0.15);
}
.metode-qris.aktif .nama-metode { color: #0369a1; }

.metode-transfer .ikon-metode { color: #7c3aed; }
.metode-transfer:hover { border-color: #7c3aed; background: #f5f3ff; }
.metode-transfer.aktif {
  background: #f5f3ff;
  border-color: #7c3aed;
  box-shadow: 0 4px 10px rgba(124, 58, 237, 0.15);
}
.metode-transfer.aktif .nama-metode { color: #6d28d9; }

/* INPUT TUNAI */
.label-form {
  font-weight: 800;
  font-size: 0.88rem;
  color: #0f172a;
}
.petunjuk-wajib-bayar {
  font-size: 0.78rem;
  color: #475569;
}
.petunjuk-wajib-bayar strong {
  color: #2563eb;
}
.input-wrap-besar {
  position: relative;
  display: flex;
  align-items: center;
}
.awalan-rp {
  position: absolute;
  left: 14px;
  font-size: 1.25rem;
  font-weight: 800;
  color: #64748b;
  font-family: var(--font-angka);
}
.input-bayar-besar {
  width: 100%;
  padding-left: 50px !important;
  font-size: 1.5rem !important;
  font-weight: 800 !important;
  height: 50px !important;
  font-family: var(--font-angka);
  color: #0f172a;
  border: 2px solid #cbd5e1;
  background: #ffffff;
  border-radius: 10px;
}
.input-bayar-besar:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 1px #2563eb;
  outline: none;
}

/* PECAHAN CEPAT */
.area-pecahan-cepat {
  margin: 10px 0;
}
.label-cepat {
  font-size: 0.78rem;
  font-weight: 800;
  color: #475569;
  margin-bottom: 6px;
}
.grid-nominal {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(95px, 1fr));
  gap: 6px;
}
.btn-pecahan {
  padding: 8px 6px;
  font-size: 0.85rem;
  font-weight: 800;
  border-radius: 8px;
  border: 1.5px solid #cbd5e1;
  background: #ffffff;
  color: #0f172a;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: var(--font-angka);
  text-align: center;
}
.btn-pecahan:hover {
  transform: translateY(-1px);
  border-color: #bfdbfe;
  color: #2563eb;
}
.btn-uang-pas {
  background: #eff6ff !important;
  color: #1e40af !important;
  border-color: #bfdbfe !important;
  font-weight: 900 !important;
}
.btn-uang-pas:hover {
  background: #2563eb !important;
  color: #ffffff !important;
}
.pecahan-terpilih {
  background: #2563eb !important;
  color: #ffffff !important;
  border-color: #2563eb !important;
}

/* KOTAK KEMBALIAN */
.kotak-kembalian {
  background: #ecfdf5;
  border: 2px solid #10b981;
  border-radius: 12px;
  padding: 12px 16px;
  margin-top: 10px;
}
.kotak-kembalian.kurang {
  background: #fef2f2;
  border-color: #ef4444;
}
.label-kembalian {
  font-size: 0.88rem;
  font-weight: 800;
  color: #065f46;
}
.kotak-kembalian.kurang .label-kembalian {
  color: #991b1b;
}
.sub-kembalian-info {
  font-size: 0.75rem;
  color: #047857;
  margin-top: 2px;
}
.kotak-kembalian.kurang .sub-kembalian-info {
  color: #b91c1c;
}
.angka-kembalian {
  font-size: 1.6rem;
  font-weight: 900;
  color: #047857;
  white-space: nowrap;
}
.kotak-kembalian.kurang .angka-kembalian {
  color: #dc2626;
}

/* TABUNGAN DONASI KEMBALIAN */
.kotak-donasi-kembalian {
  background: #f0fdf4;
  border: 1.5px solid #86efac;
  border-radius: 12px;
  padding: 12px 14px;
}
.ikon-donasi-lingkar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #dcfce7;
  color: #16a34a;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.judul-donasi {
  font-size: 0.88rem;
  font-weight: 900;
  color: #14532d;
}
.sub-donasi {
  font-size: 0.75rem;
  color: #166534;
  margin-top: 1px;
}
.btn-toggle-donasi {
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 0.78rem;
  font-weight: 800;
  cursor: pointer;
  border: 1.5px solid;
  white-space: nowrap;
  transition: all 0.15s ease;
}
.toggle-aktif-ya {
  background: #16a34a;
  color: #ffffff;
  border-color: #15803d;
  box-shadow: 0 2px 6px rgba(22, 163, 74, 0.2);
}
.toggle-nonaktif {
  background: #ffffff;
  color: #64748b;
  border-color: #cbd5e1;
}

.label-template-bar {
  font-size: 0.78rem;
  font-weight: 800;
  color: #166534;
  margin-bottom: 6px;
}
.grid-nominal-template {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.btn-nom-template {
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 800;
  background: #ffffff;
  border: 1.5px solid #86efac;
  color: #15803d;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-nom-template:hover {
  background: #dcfce7;
}
.btn-nom-template.aktif-template {
  background: #16a34a;
  color: #ffffff;
  border-color: #15803d;
}
.grid-form-donasi {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 8px;
}
.label-form-kecil {
  font-size: 0.72rem;
  font-weight: 800;
  color: #166534;
  margin-bottom: 3px;
  display: block;
}
.wrap-input-hp-donasi {
  position: relative;
  display: flex;
  align-items: center;
}
.ikon-hp-field {
  position: absolute;
  left: 10px;
  color: #16a34a;
}
.input-hp-field {
  width: 100%;
  padding-left: 32px;
  height: 36px;
  border-radius: 6px;
  border: 1.5px solid #86efac;
  font-size: 0.85rem;
  font-weight: 700;
  color: #0f172a;
}
.petunjuk-donasi-hp {
  font-size: 0.68rem;
  color: #166534;
  margin-top: 2px;
  display: block;
}
.input-nama-field {
  width: 100%;
  padding: 0 10px;
  height: 36px;
  border-radius: 6px;
  border: 1.5px solid #cbd5e1;
  font-size: 0.85rem;
  font-weight: 600;
}
.badge-saldo-eksis {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 0.72rem;
  color: #92400e;
  display: flex;
  align-items: center;
  gap: 6px;
}
.kotak-rincian-pembagian-kembalian {
  background: #ffffff;
  border: 1.5px solid #bbf7d0;
  border-radius: 8px;
  padding: 8px 12px;
}
.rincian-baris {
  font-size: 0.8rem;
  color: #334155;
  margin-bottom: 3px;
}
.teks-hijau-donasi {
  color: #16a34a;
  font-weight: 700;
}
.baris-kembalian-fisik {
  border-top: 1px dashed #cbd5e1;
  margin-top: 4px;
  padding-top: 4px;
  font-size: 0.88rem;
  color: #047857;
}
.angka-kembalian-fisik {
  font-size: 1.15rem;
  color: #059669;
}

/* INSTRUKSI NON-TUNAI */
.kotak-instruksi {
  padding: 14px 16px;
  border-radius: 12px;
  font-size: 0.85rem;
  line-height: 1.5;
}
.instruksi-qris {
  background: #f0f9ff;
  border: 2px solid #bae6fd;
  color: #0369a1;
}
.instruksi-transfer {
  background: #f5f3ff;
  border: 2px solid #ddd6fe;
  color: #5b21b6;
}
.judul-instruksi {
  font-weight: 900;
  margin-bottom: 6px;
  font-size: 0.95rem;
}

/* FOOTER TETAP (STICKY) */
.footer-modal-bayar {
  padding: 12px 20px;
  background: #f8fafc;
  border-top: 1.5px solid #e2e8f0;
  flex-shrink: 0;
  display: flex;
  gap: 10px;
}
.tombol-batal-bayar {
  flex: 1;
  font-weight: 800;
  color: #475569;
  height: 46px;
}
.tombol-konfirmasi-bayar {
  flex: 2;
  height: 46px;
  font-size: 0.95rem;
  font-weight: 900;
  letter-spacing: 0.02em;
}
.peringatan-error-bayar {
  background: #fef2f2;
  border: 1.5px solid #fecaca;
  color: #dc2626;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* MEDIA QUERIES UNTUK RESPONSIVITAS TINGGI */
@media (max-width: 640px) {
  .modal-bayar-lebar {
    width: 96%;
    max-height: 94vh;
  }
  .header-modal-bayar {
    padding: 12px 14px;
  }
  .body-modal-bayar {
    padding: 12px 14px;
  }
  .footer-modal-bayar {
    padding: 10px 14px;
  }
  .angka-tagihan-utama {
    font-size: 1.4rem;
  }
  .metode-pilihan {
    gap: 6px;
  }
  .metode-btn {
    padding: 8px 4px;
  }
  .nama-metode {
    font-size: 0.78rem;
  }
  .sub-metode {
    display: none;
  }
  .grid-chip-saran {
    grid-template-columns: 1fr;
  }
  .grid-nominal {
    grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  }
  .grid-form-donasi {
    grid-template-columns: 1fr;
  }
  .wrap-kembalian {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
  .angka-kembalian {
    font-size: 1.35rem;
  }
  .wrap-hp {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  .wrap-hp button {
    width: 100%;
    text-align: center;
  }
}

@media (max-height: 720px) {
  .header-modal-bayar {
    padding: 10px 16px;
  }
  .body-modal-bayar {
    padding: 10px 16px;
  }
  .footer-modal-bayar {
    padding: 8px 16px;
  }
  .tombol-batal-bayar,
  .tombol-konfirmasi-bayar {
    height: 42px;
  }
  .input-bayar-besar {
    height: 44px !important;
    font-size: 1.3rem !important;
  }
  .kartu-ringkasan-tagihan {
    padding: 10px 14px;
  }
  .angka-tagihan-utama {
    font-size: 1.45rem;
  }
}
</style>
