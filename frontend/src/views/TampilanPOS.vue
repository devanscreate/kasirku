<script setup>
import { ref, onMounted, computed, onUnmounted, nextTick } from 'vue'
import { dbLokal } from '../basis_data'
import { panggilApi } from '../layanan/api'
import { sinkronkanKatalogProduk } from '../layanan/sinkronisasi'
import { useAuthStore } from '../stores/auth'
import { useShiftStore } from '../stores/shift'
import { useKeranjangStore } from '../stores/keranjang'
import { useKoneksiStore } from '../stores/koneksi'
import ModalBukaShift from '../komponen/ModalBukaShift.vue'
import ModalTutupShift from '../komponen/ModalTutupShift.vue'
import ModalBayar from '../komponen/ModalBayar.vue'
import ModalSukses from '../komponen/ModalSukses.vue'
import ModalPreviewFoto from '../komponen/ModalPreviewFoto.vue'
import ModalDonasiPelanggan from '../komponen/ModalDonasiPelanggan.vue'
import { setorDonasiKembalian, cairkanDonasiPelanggan } from '../layanan/donasi'

import { 
  Search, 
  Barcode, 
  Trash2, 
  Plus, 
  Minus, 
  CreditCard, 
  Tag, 
  DoorClosed, 
  AlertTriangle,
  PackageX,
  Sparkles,
  ShoppingBag,
  Info,
  Layers,
  Check,
  ZoomIn,
  ChevronRight,
  ArrowLeft,
  HeartHandshake,
  Gift,
  Coins,
  Banknote,
  Split
} from 'lucide-vue-next'

const authStore = useAuthStore()
const shiftStore = useShiftStore()
const keranjangStore = useKeranjangStore()
const koneksiStore = useKoneksiStore()

// Pilihan Metode Bayar Cepat ala Confidency OS (Card / Cash / Split)
const metodeBayarPOS = ref('cash')

function pilihMetodeSplitDonasi() {
  metodeBayarPOS.value = 'split'
  if (!prefillPotongDonasiAktif.value) {
    tampilModalDonasiPelanggan.value = true
  }
}

function jumlahDiKeranjang(idProduk) {
  const item = keranjangStore.itemKeranjang.find(it => it.id === idProduk)
  return item ? item.kuantitas : 0
}

// Menghitung sisa stok barang yang masih bisa diambil ke keranjang
function sisaStokTersedia(produk) {
  const diKeranjang = jumlahDiKeranjang(produk.id)
  return Math.max(0, Number(produk.stok || 0) - diKeranjang)
}

const pesanPeringatanStok = ref('')
let timerPeringatanStok = null

function tampilkanPeringatanStok(pesan) {
  pesanPeringatanStok.value = pesan
  if (timerPeringatanStok) clearTimeout(timerPeringatanStok)
  timerPeringatanStok = setTimeout(() => {
    pesanPeringatanStok.value = ''
  }, 3500)
}

function tambahKuantitasDariKeranjang(it) {
  const prod = daftarProduk.value.find(p => p.id === it.id) || it
  const stokMaks = Number(prod.stok !== undefined ? prod.stok : (it.stok || 0))
  if (it.kuantitas >= stokMaks) {
    tampilkanPeringatanStok(`Kuantitas "${it.nama}" sudah mencapai batas stok (${stokMaks} unit).`)
    return
  }
  const hasil = keranjangStore.tambahItem(prod, 1)
  if (hasil && !hasil.sukses) {
    tampilkanPeringatanStok(hasil.pesan)
  }
}

const inputCari = ref(null)
const teksPencarian = ref('')
const kategoriDipilih = ref('semua')
const daftarProduk = ref([])
const sedangMuatKatalog = ref(false)

// State Responsif Mobile / Tablet
const tabAktifMobile = ref('katalog') // 'katalog' | 'keranjang'

// State Modal Pratinjau Foto Produk
const tampilModalPreview = ref(false)
const produkPreview = ref(null)

function bukaPreviewProduk(produk) {
  produkPreview.value = produk
  tampilModalPreview.value = true
}

function tambahItemDariPreview() {
  if (produkPreview.value) {
    tanganiKlikProduk(produkPreview.value)
    tampilModalPreview.value = false
  }
}

const tampilModalBukaShift = ref(false)
const tampilModalTutupShift = ref(false)
const tampilModalBayar = ref(false)
const tampilModalSukses = ref(false)
const tampilModalDonasiPelanggan = ref(false)
const prefillPotongDonasiAktif = ref(null)
const transaksiTerakhir = ref(null)
const kembalianTerakhir = ref(0)
const pesanBarcodeTidakDitemukan = ref(false)

function tanganiPotongBelanjaDariDonasi({ nomorHp, namaPelanggan, saldoMaksimal }) {
  prefillPotongDonasiAktif.value = { nomorHp, namaPelanggan, saldoMaksimal }
  tampilModalDonasiPelanggan.value = false
  if (keranjangStore.itemKeranjang.length > 0) {
    // Jika masih ada sisa yang harus dibayar setelah dipotong tabungan, buka modal bayar tunai/non-tunai
    const sisa = Math.max(0, keranjangStore.totalAkhir - Number(saldoMaksimal || 0))
    if (sisa > 0) {
      tampilModalBayar.value = true
    }
  } else {
    alert(`Saldo tabungan Rp ${Number(saldoMaksimal).toLocaleString('id-ID')} atas nama ${namaPelanggan} (${nomorHp}) siap digunakan.\nSilakan pilih barang belanjaan ke keranjang.`)
  }
}

function tanganiKlikBayarPOS() {
  if (keranjangStore.itemKeranjang.length === 0) return

  // Jika tombol Split dipilih tapi pelanggan belum ditautkan, buka modal donasi
  if (metodeBayarPOS.value === 'split' && !prefillPotongDonasiAktif.value) {
    tampilModalDonasiPelanggan.value = true
    return
  }

  // Jika tagihan sudah 100% lunas dari potongan tabungan donasi pembeli (Rp 0), pembeli tidak membayar
  if (prefillPotongDonasiAktif.value && totalTagihanBersihPOS.value === 0) {
    prosesBayar({
      metode: 'tabungan',
      diterima: 0,
      kembalian: 0,
      donasi: null,
      potonganDonasi: {
        nominal: nominalPotongTabunganAktif.value,
        nomorHp: prefillPotongDonasiAktif.value.nomorHp,
        namaPelanggan: prefillPotongDonasiAktif.value.namaPelanggan,
        saldoAwal: prefillPotongDonasiAktif.value.saldoMaksimal
      }
    })
    return
  }

  // Jika masih ada sisa tagihan atau pembayaran tunai biasa, buka modal bayar
  tampilModalBayar.value = true
}

const formatRupiah = (val) => 'Rp ' + Number(val || 0).toLocaleString('id-ID')

// Potongan dari tabungan donasi yang aktif di POS
const nominalPotongTabunganAktif = computed(() => {
  if (!prefillPotongDonasiAktif.value) return 0
  return Math.min(Number(prefillPotongDonasiAktif.value.saldoMaksimal || 0), keranjangStore.totalAkhir)
})

const totalTagihanBersihPOS = computed(() => {
  return Math.max(0, keranjangStore.totalAkhir - nominalPotongTabunganAktif.value)
})

// Kategori unik dari produk lokal
const daftarKategori = computed(() => {
  const setKategori = new Set(daftarProduk.value.map(p => p.kategori).filter(Boolean))
  return ['semua', ...Array.from(setKategori)]
})

// Warna khas per kategori agar memudahkan kasir mengenali secara visual
function warnaKategori(kat) {
  const nama = (kat || '').toLowerCase()
  if (nama === 'sembako') return { bg: '#ecfdf5', text: '#065f46', border: '#a7f3d0' }
  if (nama === 'minuman') return { bg: '#eff6ff', text: '#1e40af', border: '#bfdbfe' }
  if (nama === 'makanan') return { bg: '#fff7ed', text: '#9a3412', border: '#fed7aa' }
  if (nama === 'kebersihan') return { bg: '#f5f3ff', text: '#5b21b6', border: '#ddd6fe' }
  return { bg: '#f1f5f9', text: '#334155', border: '#cbd5e1' }
}

// Filter produk lokal berdasarkan pencarian & kategori
const produkTerfilter = computed(() => {
  let hasil = daftarProduk.value
  if (kategoriDipilih.value !== 'semua') {
    hasil = hasil.filter(p => p.kategori === kategoriDipilih.value)
  }
  if (teksPencarian.value.trim()) {
    const kueri = teksPencarian.value.toLowerCase().trim()
    hasil = hasil.filter(p => 
      p.nama.toLowerCase().includes(kueri) ||
      p.sku.toLowerCase().includes(kueri) ||
      (p.barcode && p.barcode.toLowerCase().includes(kueri))
    )
  }
  return hasil
})

// Memuat produk dari IndexedDB lokal dengan fallback auto-sync
async function muatProdukLokal() {
  sedangMuatKatalog.value = true
  try {
    let items = await dbLokal.produk.toArray()

    // 1. Jika Dexie kosong dan terhubung internet, lakukan sinkronisasi katalog
    if ((!items || items.length === 0) && navigator.onLine) {
      try {
        await sinkronkanKatalogProduk()
        items = await dbLokal.produk.toArray()
      } catch (errSync) {
        console.warn('Sinkronisasi Dexie otomatis:', errSync)
      }
    }

    // 2. Jika masih kosong, coba ambil langsung dari REST API server
    if ((!items || items.length === 0) && navigator.onLine) {
      try {
        const dariApi = await panggilApi('/products')
        if (Array.isArray(dariApi) && dariApi.length > 0) {
          const mapelProduk = dariApi.map(item => ({
            id: item.id,
            sku: item.sku,
            barcode: item.barcode,
            nama: item.nama,
            kategori: item.kategori,
            foto: item.foto || null,
            harga: item.harga,
            harga_modal: item.harga_modal,
            stok: item.stok,
            min_stok: item.min_stok,
            status_aktif: item.status_aktif && !item.apakah_dihapus,
            terakhir_diperbarui: item.diperbarui_pada
          }))
          await dbLokal.produk.bulkPut(mapelProduk)
          items = mapelProduk
        }
      } catch (errApi) {
        console.warn('Fallback API /products:', errApi)
      }
    }

    // Filter produk yang aktif (toleran terhadap boolean true maupun 1)
    daftarProduk.value = (items || []).filter(p => {
      const aktif = (p.status_aktif === true || p.status_aktif === 1 || p.status_aktif === 'true' || p.status_aktif == null)
      return aktif && !p.apakah_dihapus
    })
  } catch (err) {
    console.error('Gagal memuat produk lokal:', err)
  } finally {
    sedangMuatKatalog.value = false
  }
}

// Efek audio scan barcode kasir (Web Audio API)
function bunyikanBeepSukses() {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext
    if (!AudioCtx) return
    const ctx = new AudioCtx()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.type = 'sine'
    osc.frequency.setValueAtTime(1760, ctx.currentTime) // Nada A6
    gain.gain.setValueAtTime(0.08, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.08)
    osc.start()
    osc.stop(ctx.currentTime + 0.08)
  } catch (e) {
    // Abaikan jika browser memblokir audio otomatis
  }
}

// Tangani penambahan produk ke keranjang dengan validasi stok ketat
function tanganiKlikProduk(produk) {
  if (!shiftStore.apakahShiftTerbuka) {
    tampilModalBukaShift.value = true
    return
  }

  // 1. Cek jika stok memang sudah 0 / habis
  if (Number(produk.stok || 0) <= 0) {
    tampilkanPeringatanStok(`Stok barang "${produk.nama}" sudah habis!`)
    return
  }

  // 2. Cek apakah sisa stok sudah habis karena sudah ada di keranjang
  const sisa = sisaStokTersedia(produk)
  if (sisa <= 0) {
    tampilkanPeringatanStok(`Jumlah "${produk.nama}" di keranjang sudah mencapai batas stok (${produk.stok} unit).`)
    return
  }

  const hasil = keranjangStore.tambahItem(produk)
  if (hasil && !hasil.sukses) {
    tampilkanPeringatanStok(hasil.pesan)
    return
  }

  bunyikanBeepSukses()
  nextTick(() => inputCari.value?.focus())
}

// F-04: Tambah produk via scan barcode (scanner mengetik kode + Enter)
async function tanganiInputScanEnter() {
  const kode = teksPencarian.value.trim()
  if (!kode) return

  if (!shiftStore.apakahShiftTerbuka) {
    tampilModalBukaShift.value = true
    return
  }

  // 1. Cari exact match barcode atau SKU
  const produkCocok = daftarProduk.value.find(p => p.barcode === kode || p.sku.toLowerCase() === kode.toLowerCase())
  if (produkCocok) {
    if (Number(produkCocok.stok || 0) <= 0) {
      tampilkanPeringatanStok(`Stok barang "${produkCocok.nama}" sudah habis!`)
      teksPencarian.value = ''
      return
    }
    if (sisaStokTersedia(produkCocok) <= 0) {
      tampilkanPeringatanStok(`Jumlah "${produkCocok.nama}" di keranjang sudah mencapai batas stok (${produkCocok.stok} unit).`)
      teksPencarian.value = ''
      return
    }
    const hasil = keranjangStore.tambahItem(produkCocok)
    if (hasil && !hasil.sukses) {
      tampilkanPeringatanStok(hasil.pesan)
      teksPencarian.value = ''
      return
    }
    bunyikanBeepSukses()
    teksPencarian.value = ''
    pesanBarcodeTidakDitemukan.value = false
    nextTick(() => inputCari.value?.focus())
  } else {
    // Jika tidak ditemukan dan hanya ada 1 hasil terfilter, pilih produk tersebut
    if (produkTerfilter.value.length === 1) {
      const p = produkTerfilter.value[0]
      if (Number(p.stok || 0) <= 0) {
        tampilkanPeringatanStok(`Stok barang "${p.nama}" sudah habis!`)
        teksPencarian.value = ''
        return
      }
      if (sisaStokTersedia(p) <= 0) {
        tampilkanPeringatanStok(`Jumlah "${p.nama}" di keranjang sudah mencapai batas stok (${p.stok} unit).`)
        teksPencarian.value = ''
        return
      }
      const hasil = keranjangStore.tambahItem(p)
      if (hasil && !hasil.sukses) {
        tampilkanPeringatanStok(hasil.pesan)
        teksPencarian.value = ''
        return
      }
      bunyikanBeepSukses()
      teksPencarian.value = ''
      pesanBarcodeTidakDitemukan.value = false
      nextTick(() => inputCari.value?.focus())
    } else {
      pesanBarcodeTidakDitemukan.value = true
      setTimeout(() => {
        pesanBarcodeTidakDitemukan.value = false
      }, 3000)
    }
  }
}

// Pintasan Keyboard: F2 Cari, F9/F4 Bayar, Esc Batal
function tanganiPintasanKeyboard(e) {
  if (e.key === 'F2') {
    e.preventDefault()
    inputCari.value?.focus()
  } else if (e.key === 'F9' || e.key === 'F4') {
    e.preventDefault()
    if (!shiftStore.apakahShiftTerbuka) {
      tampilModalBukaShift.value = true
    } else if (keranjangStore.itemKeranjang.length > 0) {
      tanganiKlikBayarPOS()
    }
  } else if (e.key === 'Escape') {
    tampilModalBayar.value = false
    tampilModalSukses.value = false
    tampilModalTutupShift.value = false
    tampilModalBukaShift.value = false
  }
}

async function tanganiSuksesBukaShift() {
  tampilModalBukaShift.value = false
  await shiftStore.muatShiftAktif(authStore.idPengguna)
  await muatProdukLokal()
  setTimeout(() => inputCari.value?.focus(), 150)
}

async function tanganiSuksesTutupShift() {
  tampilModalTutupShift.value = false
  keranjangStore.kosongkanKeranjang()
  await shiftStore.muatShiftAktif(authStore.idPengguna)
}

function tanganiEventPotongBelanja(e) {
  if (e.detail) {
    tanganiPotongBelanjaDariDonasi(e.detail)
  }
}

function bukaModalBukaShift() {
  tampilModalBukaShift.value = true
}

function bukaModalTutupShift() {
  tampilModalTutupShift.value = true
}

onMounted(async () => {
  window.addEventListener('keydown', tanganiPintasanKeyboard)
  window.addEventListener('katalog:diperbarui', muatProdukLokal)
  window.addEventListener('donasi:potong-belanja', tanganiEventPotongBelanja)
  window.addEventListener('shift:buka', bukaModalBukaShift)
  window.addEventListener('shift:tutup', bukaModalTutupShift)

  // Periksa apakah ada instruksi potong belanja dari layar Tabungan Donasi
  const prefillTersimpan = sessionStorage.getItem('pos_prefill_donasi')
  if (prefillTersimpan) {
    try {
      const dataPrefill = JSON.parse(prefillTersimpan)
      sessionStorage.removeItem('pos_prefill_donasi')
      tanganiPotongBelanjaDariDonasi(dataPrefill)
    } catch (e) {
      console.warn('Gagal membaca pos_prefill_donasi:', e)
    }
  }

  await muatProdukLokal()
  await shiftStore.muatShiftAktif(authStore.idPengguna)

  // Fokus otomatis ke input pencarian/barcode (F-04)
  setTimeout(() => {
    inputCari.value?.focus()
  }, 100)
})

onUnmounted(() => {
  window.removeEventListener('keydown', tanganiPintasanKeyboard)
  window.removeEventListener('katalog:diperbarui', muatProdukLokal)
  window.removeEventListener('donasi:potong-belanja', tanganiEventPotongBelanja)
  window.removeEventListener('shift:buka', bukaModalBukaShift)
  window.removeEventListener('shift:tutup', bukaModalTutupShift)
})

// Selesaikan transaksi
async function prosesBayar({ metode, diterima, kembalian, donasi, potonganDonasi }) {
  try {
    const hasil = await keranjangStore.selesaikanTransaksi({
      idShift: shiftStore.shiftAktif?.id,
      idKasir: authStore.idPengguna,
      namaKasir: authStore.namaLengkap,
      metodeBayar: metode,
      jumlahDiterima: diterima,
      potonganDonasi: potonganDonasi
    })

    // 1. Jika ada potongan dari tabungan donasi pembeli (Opsi B: Potong Belanjaan)
    if (potonganDonasi && potonganDonasi.nominal > 0) {
      try {
        const resCair = await cairkanDonasiPelanggan({
          nomorHp: potonganDonasi.nomorHp,
          nominal: potonganDonasi.nominal,
          tipe: 'belanja',
          idPenjualan: hasil.transaksi.id,
          nomorStruk: hasil.transaksi.nomor_struk,
          idShift: shiftStore.shiftAktif?.id,
          catatan: `Potong tagihan belanja struk ${hasil.transaksi.nomor_struk}`,
          saldoAwal: potonganDonasi.saldoAwal
        })
        hasil.transaksi.potonganDonasi = {
          ...potonganDonasi,
          namaPelanggan: potonganDonasi.namaPelanggan || resCair?.nama_pelanggan || 'Pelanggan'
        }
        if (resCair && resCair.sisa_saldo !== undefined) {
          hasil.transaksi.sisaSaldoDonasi = resCair.sisa_saldo
        } else if (potonganDonasi.saldoAwal !== undefined && potonganDonasi.saldoAwal !== null) {
          hasil.transaksi.sisaSaldoDonasi = Math.max(0, Number(potonganDonasi.saldoAwal) - Number(potonganDonasi.nominal))
        } else if (prefillPotongDonasiAktif.value?.saldoMaksimal) {
          hasil.transaksi.sisaSaldoDonasi = Math.max(0, prefillPotongDonasiAktif.value.saldoMaksimal - potonganDonasi.nominal)
        }
      } catch (errPotong) {
        console.error('Gagal mencatat pemotongan saldo donasi:', errPotong)
      }
    }

    // 2. Jika ada donasi dari kembalian pembeli (Alur Penawaran Donasi Sesuai Flowchart)
    if (donasi && donasi.nominal > 0) {
      try {
        const resDonasi = await setorDonasiKembalian({
          nomorHp: donasi.nomorHp,
          namaPelanggan: donasi.namaPelanggan,
          nominal: donasi.nominal,
          idPenjualan: hasil.transaksi.id,
          nomorStruk: hasil.transaksi.nomor_struk,
          idShift: shiftStore.shiftAktif?.id,
          catatan: `Donasi kembalian dari transaksi ${hasil.transaksi.nomor_struk}`
        })
        hasil.transaksi.donasi = {
          ...donasi,
          totalSaldoBaru: resDonasi?.total_saldo ?? donasi.nominal
        }
      } catch (errDonasi) {
        console.error('Gagal menyetor donasi kembalian:', errDonasi)
        hasil.transaksi.donasi = donasi
      }
    }

    transaksiTerakhir.value = hasil.transaksi
    kembalianTerakhir.value = kembalian
    tampilModalBayar.value = false
    prefillPotongDonasiAktif.value = null
    tampilModalSukses.value = true

    // Segarkan data produk lokal seketika agar sisa stok terbaru langsung ter-update di layar POS
    await muatProdukLokal()
  } catch (err) {
    alert('Gagal memproses transaksi: ' + err.message)
  }
}

function transaksiBaru() {
  tampilModalSukses.value = false
  transaksiTerakhir.value = null
  muatProdukLokal()
  setTimeout(() => {
    inputCari.value?.focus()
  }, 100)
}
</script>

<template>
  <div class="pos-layout">
    <!-- TAB SWITCHER RESPONSIF KHUSUS TABLET & MOBILE (< 1024px) -->
    <div class="tab-pos-responsif">
      <button 
        class="tab-item-responsif" 
        :class="{ 'aktif': tabAktifMobile === 'katalog' }"
        @click="tabAktifMobile = 'katalog'"
      >
        <span>Katalog Barang</span>
        <span class="badge-tab-nav">{{ produkTerfilter.length }}</span>
      </button>

      <button 
        class="tab-item-responsif" 
        :class="{ 'aktif': tabAktifMobile === 'keranjang' }"
        @click="tabAktifMobile = 'keranjang'"
      >
        <span>Pesanan</span>
        <span v-if="keranjangStore.totalKuantitas > 0" class="badge-tab-nav badge-aktif">
          {{ keranjangStore.totalKuantitas }}
        </span>
      </button>
    </div>

    <!-- TAMPILAN UTAMA KASIR ALA CONFIDENCY OS -->
    <div class="grid-pos" :class="`pos-view-${tabAktifMobile}`">
      <!-- KOLOM KIRI: KATALOG & FILTER & PENCARIAN -->
      <section class="kolom-katalog">
        <!-- Peringatan jika Shift Belum Dibuka -->
        <div v-if="!shiftStore.apakahShiftTerbuka" class="banner-shift-belum-buka">
          <div class="shift-kiri">
            <span class="titik-kuning"></span>
            <span class="teks-shift-judul">Shift Kasir Belum Dibuka — Masukkan uang modal laci kasir untuk mulai transaksi</span>
          </div>
          <button class="btn-shift-aksi" @click="tampilModalBukaShift = true">
            Buka Shift
          </button>
        </div>

        <!-- Bar Kategori Pills + Search Bar Sesuai Mockup Confidency OS -->
        <div class="bar-kategori-dan-cari">
          <!-- Kategori Pills Bar (Active = Iris Solid Pill) -->
          <div class="filter-kategori-pills">
            <button 
              v-for="kat in daftarKategori" 
              :key="kat"
              class="pill-kategori"
              :class="{ 'aktif': kategoriDipilih === kat }"
              @click="kategoriDipilih = kat"
            >
              <span>{{ kat === 'semua' ? 'Semua Produk' : kat }}</span>
            </button>
          </div>

          <!-- Kotak Pencarian Ramping di Kanan Bar Kategori -->
          <div class="kotak-cari-pos">
            <Search :size="15" class="ikon-cari-pos" />
            <input 
              ref="inputCari"
              v-model="teksPencarian"
              type="text"
              class="input-cari-pos"
              placeholder="Cari produk / barcode (F2)..."
              @keydown.enter="tanganiInputScanEnter"
            />
            <button v-if="teksPencarian" class="btn-bersih-cari" @click="teksPencarian = ''">✕</button>
          </div>
        </div>

        <!-- Banner Peringatan Barcode Tidak Ditemukan -->
        <div v-if="pesanBarcodeTidakDitemukan" class="pesan-tak-ditemukan">
          <span>Produk dengan kode tersebut tidak ditemukan di katalog.</span>
        </div>

        <!-- Banner Peringatan Stok Habis / Melebihi Batas Stok -->
        <transition name="fade">
          <div v-if="pesanPeringatanStok" class="banner-peringatan-stok flex items-center justify-between">
            <div class="flex items-center gap-2">
              <AlertTriangle :size="16" class="ikon-peringatan-stok" />
              <span>{{ pesanPeringatanStok }}</span>
            </div>
            <button type="button" class="btn-tutup-notif-stok" @click="pesanPeringatanStok = ''" title="Tutup peringatan">✕</button>
          </div>
        </transition>

        <!-- Grid Studio Card Produk Sesuai Mockup -->
        <div class="grid-produk">
          <div 
            v-for="produk in produkTerfilter" 
            :key="produk.id"
            class="card-produk"
            :class="{ 
              'stok-kosong': produk.stok <= 0,
              'stok-mentok': sisaStokTersedia(produk) <= 0 && produk.stok > 0
            }"
            @click="tanganiKlikProduk(produk)"
            :title="produk.stok <= 0 ? 'Stok produk ini sudah habis' : (sisaStokTersedia(produk) <= 0 ? 'Jumlah di keranjang sudah mencapai batas stok' : 'Klik untuk masukkan ke pesanan')"
          >
            <!-- Wadah Gambar Studio Produk -->
            <div class="wadah-foto-produk">
              <img v-if="produk.foto" :src="produk.foto" :alt="produk.nama" class="foto-kartu-pos" loading="lazy" />
              <div 
                v-else 
                class="foto-pos-placeholder"
                :style="{
                  backgroundColor: warnaKategori(produk.kategori).bg,
                  color: warnaKategori(produk.kategori).text
                }"
              >
                <span class="huruf-kategori-pos">{{ (produk.nama || 'P').charAt(0).toUpperCase() }}</span>
              </div>

              <!-- Badge Indikator Sudah di Keranjang -->
              <span v-if="jumlahDiKeranjang(produk.id) > 0" class="badge-di-keranjang font-angka">
                ✓ {{ jumlahDiKeranjang(produk.id) }}
              </span>

              <!-- Badge Habis jika stok <= 0 -->
              <span v-if="produk.stok <= 0" class="badge-stok-habis">
                Habis
              </span>
            </div>
            
            <!-- Detail Keterangan Produk: Rapi & Minimalis -->
            <div class="info-kartu-produk">
              <h3 class="nama-produk" :title="produk.nama">{{ produk.nama }}</h3>
              
              <div class="baris-harga-dan-stok">
                <span class="harga-produk font-angka">{{ formatRupiah(produk.harga) }}</span>
                
                <!-- Tampilan Sisa Jumlah Stok Barang -->
                <span 
                  class="badge-info-stok font-angka"
                  :class="{
                    'stok-nol': produk.stok <= 0,
                    'stok-menipis': produk.stok > 0 && sisaStokTersedia(produk) <= (produk.min_stok || 5),
                    'stok-aman': sisaStokTersedia(produk) > (produk.min_stok || 5)
                  }"
                  :title="`Total stok: ${produk.stok} unit`"
                >
                  <template v-if="produk.stok <= 0">
                    Habis
                  </template>
                  <template v-else-if="jumlahDiKeranjang(produk.id) > 0">
                    Sisa {{ sisaStokTersedia(produk) }}
                  </template>
                  <template v-else>
                    Stok {{ produk.stok }}
                  </template>
                </span>
              </div>
            </div>
          </div>

          <div v-if="produkTerfilter.length === 0" class="state-kosong">
            <div class="tebal">Produk tidak ditemukan</div>
            <div class="teks-redup">
              {{ sedangMuatKatalog ? 'Sedang memuat data katalog...' : 'Coba periksa kata kunci pencarian atau pilih kategori lain' }}
            </div>
          </div>
        </div>
      </section>

      <!-- KOLOM KANAN: PESANAN & CHECKOUT -->
      <aside class="kolom-keranjang">
        <!-- Header Keranjang: Antrean Pesanan & Tombol Kosongkan -->
        <div class="header-keranjang">
          <div class="judul-wrap flex items-center gap-2">
            <h2 class="judul-keranjang">Antrean Pesanan</h2>
            <span v-if="keranjangStore.totalKuantitas > 0" class="badge-hitung-pesanan font-angka">
              {{ keranjangStore.totalKuantitas }} item
            </span>
          </div>

          <div class="flex items-center gap-2">
            <button 
              class="btn-kembali-katalog-mobile"
              @click="tabAktifMobile = 'katalog'"
              title="Kembali ke katalog"
            >
              <span>← Katalog</span>
            </button>

            <button 
              v-if="keranjangStore.itemKeranjang.length > 0"
              class="btn-reset-order"
              @click="keranjangStore.kosongkanKeranjang"
              title="Kosongkan seluruh barang dalam pesanan"
            >
              <Trash2 :size="13" />
              <span>Kosongkan</span>
            </button>
          </div>
        </div>

        <!-- Daftar Baris Item Keranjang Sesuai Mockup -->
        <div class="daftar-item-keranjang">
          <div v-if="keranjangStore.itemKeranjang.length === 0" class="keranjang-kosong">
            <div class="teks-utama">Belum ada item pesanan</div>
            <div class="hint-keranjang">Pilih atau scan produk di katalog untuk menambahkan ke pesanan</div>
          </div>

          <div 
            v-for="it in keranjangStore.itemKeranjang" 
            :key="it.id"
            class="baris-item-pos"
          >
            <!-- Thumbnail Produk Mini -->
            <div class="thumb-item-keranjang">
              <img v-if="it.foto" :src="it.foto" :alt="it.nama" class="img-thumb-keranjang" />
              <div v-else class="thumb-placeholder font-angka">
                {{ (it.nama || 'P').charAt(0).toUpperCase() }}
              </div>
            </div>

            <!-- Detail Tengah: Nama, Harga & Stepper Kuantitas -->
            <div class="detail-item-tengah">
              <div class="item-nama" :title="it.nama">{{ it.nama }}</div>
              <div class="item-meta-baris">
                <span class="item-harga-satuan font-angka">{{ formatRupiah(it.harga) }}</span>
                <span class="pemisah-meta">•</span>
                <span class="item-stok-info font-angka" :class="{ 'stok-kritis': it.kuantitas >= (it.stok || 0) }">
                  Stok: {{ it.stok || 0 }}
                </span>
              </div>
              
              <!-- Stepper: [ - ] 1 [ + ] -->
              <div class="stepper-item-pos">
                <button class="btn-step" @click="keranjangStore.kurangiItem(it.id)" title="Kurangi 1">
                  <Minus :size="12" />
                </button>
                <span class="angka-step font-angka">{{ it.kuantitas }}</span>
                <button 
                  class="btn-step" 
                  :disabled="it.kuantitas >= (it.stok || 0)"
                  :class="{ 'btn-step-disabled': it.kuantitas >= (it.stok || 0) }"
                  @click="tambahKuantitasDariKeranjang(it)" 
                  :title="it.kuantitas >= (it.stok || 0) ? `Maksimal stok tercapai (${it.stok} unit)` : 'Tambah 1'"
                >
                  <Plus :size="12" />
                </button>
              </div>
            </div>

            <!-- Kanan: Total Harga & Tombol Hapus Merah -->
            <div class="kanan-item-pos">
              <button class="btn-hapus-merah" @click="keranjangStore.hapusItem(it.id)" title="Hapus produk">
                <Trash2 :size="15" />
              </button>
              <div class="subtotal-item-pos font-angka">
                Subtotal: <strong>{{ formatRupiah(it.harga * it.kuantitas) }}</strong>
              </div>
            </div>
          </div>
        </div>

        <!-- Rincian Biaya Bawah & Metode Pembayaran -->
        <div class="rincian-biaya-pos">
          <!-- Subtotal Belanja -->
          <div class="baris-rincian-pos">
            <span class="label-rincian">Subtotal Belanja</span>
            <span class="nilai-rincian font-angka">{{ formatRupiah(keranjangStore.subtotal) }}</span>
          </div>

          <!-- Diskon -->
          <div class="baris-rincian-pos">
            <span class="label-rincian">Diskon Tagihan</span>
            <div class="wrap-diskon-inline">
              <input 
                :value="keranjangStore.diskonPersen"
                type="number" 
                min="0" 
                max="100" 
                class="input-diskon-persen"
                placeholder="0"
                title="Persentase diskon"
                @input="keranjangStore.aturDiskon($event.target.value, 'persen')"
              />
              <span class="persen-simbol">%</span>
              <span class="nilai-rincian font-angka" :class="{ 'teks-merah': keranjangStore.nilaiDiskon > 0 }">
                {{ keranjangStore.nilaiDiskon > 0 ? `-${formatRupiah(keranjangStore.nilaiDiskon)}` : 'Rp 0' }}
              </span>
            </div>
          </div>

          <!-- Tabungan Celengan Donasi (Jika Terpasang) -->
          <div v-if="prefillPotongDonasiAktif" class="baris-rincian-pos donasi-terpotong">
            <span class="label-rincian flex items-center gap-1">
              <span>Potongan Tabungan ({{ prefillPotongDonasiAktif.namaPelanggan }})</span>
              <button class="btn-hapus-prefill" @click="prefillPotongDonasiAktif = null" title="Hapus potongan tabungan">✕</button>
            </span>
            <span class="nilai-rincian teks-sukses font-angka">-{{ formatRupiah(nominalPotongTabunganAktif) }}</span>
          </div>

          <!-- Total Tagihan Bersih -->
          <div class="baris-total-pos">
            <span class="label-total">Total Tagihan</span>
            <span class="nilai-total font-angka">{{ formatRupiah(totalTagihanBersihPOS) }}</span>
          </div>

          <!-- Segmented Metode Pembayaran (Tunai / QRIS & Kartu / Tabungan Donasi) -->
          <div class="payment-method-area">
            <div class="payment-label">Metode Pembayaran</div>
            <div class="segmented-payment-methods">
              <button 
                type="button" 
                class="seg-method-btn"
                :class="{ 'aktif': metodeBayarPOS === 'cash' }"
                @click="metodeBayarPOS = 'cash'"
                title="Pembayaran Tunai langsung di kasir"
              >
                <Banknote :size="14" />
                <span>Tunai</span>
              </button>

              <button 
                type="button" 
                class="seg-method-btn"
                :class="{ 'aktif': metodeBayarPOS === 'card' }"
                @click="metodeBayarPOS = 'card'"
                title="QRIS atau Kartu Debit / Non-Tunai"
              >
                <CreditCard :size="14" />
                <span>QRIS / Kartu</span>
              </button>

              <button 
                type="button" 
                class="seg-method-btn"
                :class="{ 'aktif': metodeBayarPOS === 'split' || prefillPotongDonasiAktif }"
                @click="pilihMetodeSplitDonasi"
                title="Potong dari saldo tabungan donasi pembeli"
              >
                <HeartHandshake :size="14" />
                <span>Tabungan / Potong</span>
              </button>
            </div>
          </div>

          <!-- Tombol Bayar Utama -->
          <button 
            v-if="shiftStore.apakahShiftTerbuka"
            class="btn-charge-pos"
            :disabled="keranjangStore.itemKeranjang.length === 0"
            @click="tanganiKlikBayarPOS"
          >
            <template v-if="totalTagihanBersihPOS === 0 && nominalPotongTabunganAktif > 0">
              <Check :size="18" />
              <span>Selesaikan (Lunas Tabungan) [F9]</span>
            </template>
            <template v-else>
              <span>Bayar {{ formatRupiah(totalTagihanBersihPOS) }} [F9]</span>
            </template>
          </button>
          <button 
            v-else
            class="btn-buka-shift-pos"
            @click="tampilModalBukaShift = true"
          >
            Buka Laci Kasir untuk Mulai
          </button>
        </div>
      </aside>
    </div>

    <!-- BILAH MELAYANG DI BAWAH UNTUK TABLET & MOBILE -->
    <div 
      v-if="tabAktifMobile === 'katalog' && keranjangStore.totalKuantitas > 0" 
      class="bar-melayang-keranjang-mobile"
      @click="tabAktifMobile = 'keranjang'"
    >
      <div class="info-melayang-kiri">
        <span class="badge-melayang-qty">{{ keranjangStore.totalKuantitas }} item</span>
        <span class="total-melayang font-angka">{{ formatRupiah(totalTagihanBersihPOS) }}</span>
      </div>
      <button class="btn-buka-keranjang-melayang">
        <span>Lihat Pesanan & Bayar →</span>
      </button>
    </div>

    <!-- MODAL POPUPS -->
    <ModalBukaShift 
      v-if="tampilModalBukaShift" 
      @tutup="tampilModalBukaShift = false" 
      @sukses="tanganiSuksesBukaShift" 
    />

    <ModalTutupShift 
      v-if="tampilModalTutupShift" 
      @tutup="tampilModalTutupShift = false" 
      @sukses="tanganiSuksesTutupShift" 
    />

    <ModalBayar 
      v-if="tampilModalBayar" 
      :total="keranjangStore.totalAkhir" 
      :prefill-potong-donasi="prefillPotongDonasiAktif" 
      :metode-awal="metodeBayarPOS === 'card' ? 'qris' : 'tunai'"
      @tutup="tampilModalBayar = false" 
      @bayar="prosesBayar" 
    />

    <ModalSukses 
      v-if="tampilModalSukses" 
      :transaksi="transaksiTerakhir" 
      :kembalian="kembalianTerakhir" 
      @transaksiBaru="transaksiBaru" 
    />

    <ModalDonasiPelanggan 
      v-if="tampilModalDonasiPelanggan" 
      @tutup="tampilModalDonasiPelanggan = false" 
      @terapkanPotongBelanja="tanganiPotongBelanjaDariDonasi" 
    />

    <ModalPreviewFoto 
      v-if="tampilModalPreview && produkPreview" 
      :foto="produkPreview.foto" 
      :nama="produkPreview.nama" 
      :sku="produkPreview.sku" 
      :barcode="produkPreview.barcode" 
      :kategori="produkPreview.kategori" 
      :harga="produkPreview.harga" 
      :stok="produkPreview.stok" 
      :min-stok="produkPreview.min_stok" 
      :tampilkan-aksi-keranjang="true" 
      @tutup="tampilModalPreview = false" 
      @tambah="tambahItemDariPreview" 
    />
  </div>
</template>

<style scoped>
.pos-layout {
  min-height: calc(100vh - 58px);
  padding: 16px 20px;
  background: var(--warna-latar);
}

/* Tab Switcher Responsif Tablet & Mobile (< 1024px) */
.tab-pos-responsif {
  display: none;
  gap: 8px;
  margin-bottom: 12px;
}
@media (max-width: 1024px) {
  .tab-pos-responsif {
    display: flex;
  }
}
.tab-item-responsif {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 14px;
  background: #ffffff;
  border: 1px solid var(--warna-batas);
  border-radius: 10px;
  font-weight: 600;
  font-size: 0.88rem;
  color: var(--warna-teks-redup);
  cursor: pointer;
  transition: all 0.15s ease;
}
.tab-item-responsif.aktif {
  background: #6366f1;
  color: #ffffff;
  border-color: #6366f1;
}
.badge-tab-nav {
  padding: 2px 7px;
  border-radius: 9999px;
  font-size: 0.72rem;
  font-weight: 700;
  background: #f1f5f9;
  color: #475569;
}
.tab-item-responsif.aktif .badge-tab-nav {
  background: rgba(255, 255, 255, 0.25);
  color: #ffffff;
}

/* Grid POS Responsif: Katalog & Keranjang Checkout */
.grid-pos {
  display: grid;
  grid-template-columns: minmax(0, 1fr) clamp(360px, 32vw, 420px);
  gap: 18px;
  height: calc(100vh - 90px);
}

@media (max-width: 1024px) {
  .grid-pos {
    grid-template-columns: 1fr;
    height: auto;
  }
  .pos-view-katalog .kolom-keranjang {
    display: none !important;
  }
  .pos-view-keranjang .kolom-katalog {
    display: none !important;
  }
  .pos-view-keranjang .kolom-keranjang {
    min-height: 75vh;
  }
}

/* Kolom Katalog */
.kolom-katalog {
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow: hidden;
}

/* Banner Peringatan Shift Belum Buka */
.banner-shift-belum-buka {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 14px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 10px;
  color: #92400e;
  font-size: 0.8rem;
}
.shift-kiri {
  display: flex;
  align-items: center;
  gap: 8px;
}
.titik-kuning {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #d97706;
  flex-shrink: 0;
}
.teks-shift-judul {
  font-weight: 600;
}
.btn-shift-aksi {
  background: #6366f1;
  color: #ffffff;
  border: none;
  font-weight: 700;
  font-size: 0.78rem;
  padding: 5px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-shift-aksi:hover {
  background: #4f46e5;
}

/* Bar Kategori & Cari Sesuai Mockup Confidency OS */
.bar-kategori-dan-cari {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-shrink: 0;
}

.filter-kategori-pills {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
}
.filter-kategori-pills::-webkit-scrollbar {
  display: none;
}

.pill-kategori {
  background: transparent;
  border: none;
  color: #64748b;
  font-size: 0.825rem;
  font-weight: 600;
  padding: 6px 14px;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
  font-family: inherit;
  text-transform: capitalize;
}
.pill-kategori:hover {
  color: #0f172a;
  background: #eef2ff;
}
.pill-kategori.aktif {
  background: #6366f1;
  color: #ffffff;
  box-shadow: 0 1px 2px rgba(99, 102, 241, 0.2);
}

.kotak-cari-pos {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #ffffff;
  border: 1px solid #eaedf2;
  border-radius: 8px;
  padding: 4px 10px;
  width: 170px;
  flex-shrink: 0;
  transition: all 0.18s ease;
}
.kotak-cari-pos:focus-within {
  border-color: #6366f1;
  box-shadow: 0 0 0 1px #6366f1;
  width: 220px;
}
.ikon-cari-pos {
  color: #94a3b8;
  flex-shrink: 0;
}
.input-cari-pos {
  border: none;
  background: transparent;
  outline: none;
  font-size: 0.82rem;
  color: #0f172a;
  width: 100%;
  font-family: inherit;
}
.btn-bersih-cari {
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 0.75rem;
}
.btn-bersih-cari:hover {
  color: #0f172a;
}

.pesan-tak-ditemukan {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
  padding: 7px 12px;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 600;
}

.banner-peringatan-stok {
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #b45309;
  padding: 8px 14px;
  border-radius: 10px;
  font-size: 0.82rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.ikon-peringatan-stok {
  color: #f59e0b;
  flex-shrink: 0;
}
.btn-tutup-notif-stok {
  background: none;
  border: none;
  color: #b45309;
  font-size: 0.85rem;
  cursor: pointer;
  padding: 0 4px;
}
.btn-tutup-notif-stok:hover {
  color: #78350f;
}

/* Grid Studio Card Produk Sesuai Mockup (3 Kolom Responsif) */
.grid-produk {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  overflow-y: auto;
  padding-right: 4px;
  padding-bottom: 12px;
  flex: 1;
  align-content: start;
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 #f4f5f8;
}

@media (max-width: 1200px) {
  .grid-produk {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }
}
@media (max-width: 600px) {
  .grid-produk {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }
}

.card-produk {
  background: #ffffff;
  border: 1px solid #eaedf2;
  border-radius: 16px;
  padding: 12px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
  position: relative;
  user-select: none;
}
.card-produk:hover {
  border-color: #c7d2fe;
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.05);
}
.card-produk:active {
  transform: scale(0.98);
}
.card-produk.stok-kosong {
  opacity: 0.5;
  background: #f8fafc;
  cursor: not-allowed;
}
.card-produk.stok-kosong:hover {
  border-color: #fca5a5;
  transform: none;
  box-shadow: none;
}
.card-produk.stok-mentok {
  border-color: #fde68a;
}

.wadah-foto-produk {
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
  position: relative;
}

.foto-kartu-pos {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.foto-pos-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.huruf-kategori-pos {
  font-size: 2.2rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.badge-di-keranjang {
  position: absolute;
  top: 8px;
  right: 8px;
  background: #6366f1;
  color: #ffffff;
  font-size: 0.72rem;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 9999px;
  box-shadow: 0 2px 4px rgba(99, 102, 241, 0.3);
}

.badge-stok-habis {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background: #fee2e2;
  color: #b91c1c;
  border: 1px solid #fca5a5;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 1.5px 6px;
  border-radius: 4px;
}

.info-kartu-produk {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.nama-produk {
  font-weight: 600;
  font-size: 0.88rem;
  color: #0f172a;
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.baris-harga-dan-stok {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.harga-produk {
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
}

.badge-info-stok {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 1.5px 6px;
  border-radius: 6px;
  white-space: nowrap;
}

.badge-info-stok.stok-aman {
  color: #64748b;
  background: #f1f5f9;
}

.badge-info-stok.stok-menipis {
  color: #b45309;
  background: #fef3c7;
  border: 1px solid #fde68a;
}

.badge-info-stok.stok-nol {
  color: #b91c1c;
  background: #fee2e2;
  border: 1px solid #fca5a5;
}

.state-kosong {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 20px;
  color: #94a3b8;
  background: #ffffff;
  border-radius: 16px;
  border: 1px dashed #eaedf2;
}

/* Kolom Keranjang Sesuai Mockup Confidency OS */
.kolom-keranjang {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
  background: #ffffff;
  border: 1px solid #eaedf2;
  border-radius: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.header-keranjang {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid #eaedf2;
  flex-shrink: 0;
}

.judul-keranjang {
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
}

.badge-hitung-pesanan {
  background: #eef2ff;
  color: #6366f1;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 9999px;
  border: 1px solid #c7d2fe;
}

.btn-reset-order {
  display: flex;
  align-items: center;
  gap: 5px;
  background: #fff5f5;
  color: #ef4444;
  border: 1px solid #fecaca;
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-reset-order:hover {
  background: #fee2e2;
}

.daftar-item-keranjang {
  flex: 1;
  overflow-y: auto;
  padding: 12px 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 #ffffff;
}

.keranjang-kosong {
  text-align: center;
  padding: 50px 16px;
  color: #94a3b8;
}
.teks-utama {
  color: #475569;
  font-size: 0.92rem;
  font-weight: 600;
}
.hint-keranjang {
  font-size: 0.78rem;
  margin-top: 4px;
}

/* Item Baris Keranjang Sesuai Mockup */
.baris-item-pos {
  display: flex;
  align-items: center;
  gap: 12px;
}

.thumb-item-keranjang {
  width: 46px;
  height: 46px;
  border-radius: 10px;
  background: #f8f9fa;
  border: 1px solid #eaedf2;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.img-thumb-keranjang {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.thumb-placeholder {
  font-size: 1.1rem;
  font-weight: 800;
  color: #64748b;
}

.detail-item-tengah {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.item-nama {
  font-size: 0.85rem;
  font-weight: 600;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-meta-baris {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.775rem;
}

.item-harga-satuan {
  font-size: 0.775rem;
  color: #64748b;
}

.pemisah-meta {
  color: #cbd5e1;
  font-size: 0.65rem;
}

.item-stok-info {
  color: #64748b;
  font-size: 0.72rem;
  font-weight: 600;
}

.item-stok-info.stok-kritis {
  color: #dc2626;
  font-weight: 700;
}

.stepper-item-pos {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}
.btn-step {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  color: #475569;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-step:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #0f172a;
}
.btn-step-disabled {
  opacity: 0.35;
  cursor: not-allowed !important;
  background: #f1f5f9 !important;
  border-color: #e2e8f0 !important;
  color: #94a3b8 !important;
}
.angka-step {
  font-size: 0.85rem;
  font-weight: 700;
  color: #0f172a;
  min-width: 14px;
  text-align: center;
}

.kanan-item-pos {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  flex-shrink: 0;
}
.btn-hapus-merah {
  background: none;
  border: none;
  color: #ef4444;
  cursor: pointer;
  padding: 3px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}
.btn-hapus-merah:hover {
  background: #fee2e2;
}
.subtotal-item-pos {
  font-size: 0.8rem;
  color: #64748b;
  white-space: nowrap;
}
.subtotal-item-pos strong {
  color: #0f172a;
  font-size: 0.825rem;
}

/* Rincian Biaya Bawah Sesuai Mockup */
.rincian-biaya-pos {
  border-top: 1px solid #eaedf2;
  padding-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}

.baris-rincian-pos {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.825rem;
}
.label-rincian {
  color: #64748b;
}
.nilai-rincian {
  color: #0f172a;
  font-weight: 600;
}

.wrap-diskon-inline {
  display: flex;
  align-items: center;
  gap: 6px;
}
.input-diskon-persen {
  width: 36px;
  height: 24px;
  text-align: center;
  border: 1px solid #eaedf2;
  border-radius: 6px;
  font-size: 0.775rem;
  font-weight: 600;
  background: #ffffff;
}
.persen-simbol {
  font-size: 0.75rem;
  color: #94a3b8;
}

.donasi-terpotong {
  background: #ecfdf5;
  padding: 4px 8px;
  border-radius: 6px;
}
.btn-hapus-prefill {
  background: none;
  border: none;
  color: #ef4444;
  font-size: 0.7rem;
  cursor: pointer;
  margin-left: 4px;
}
.teks-sukses {
  color: #059669;
}
.teks-merah {
  color: #ef4444;
}

/* Total Row */
.baris-total-pos {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  margin-top: 2px;
  border-top: 1px dashed #eaedf2;
}
.label-total {
  font-size: 0.95rem;
  font-weight: 700;
  color: #0f172a;
}
.nilai-total {
  font-size: 1.15rem;
  font-weight: 800;
  color: #0f172a;
}

/* Segmented Payment Method Selector Sesuai Mockup */
.payment-method-area {
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.payment-label {
  font-size: 0.8rem;
  font-weight: 700;
  color: #0f172a;
}

.segmented-payment-methods {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  background: #f8f9fa;
  padding: 3px;
  border-radius: 10px;
  border: 1px solid #eaedf2;
}

.seg-method-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 4px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 7px;
  font-size: 0.78rem;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}
.seg-method-btn:hover {
  color: #0f172a;
}
.seg-method-btn.aktif {
  background: #ffffff;
  border-color: #eaedf2;
  color: #0f172a;
  font-weight: 700;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

/* Primary CTA: Charge Button Sesuai Mockup (Solid Iris #6366f1) */
.btn-charge-pos {
  width: 100%;
  height: 46px;
  margin-top: 4px;
  background: #6366f1;
  color: #ffffff;
  border: none;
  border-radius: 12px;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.15s ease;
  font-family: inherit;
}
.btn-charge-pos:hover:not(:disabled) {
  background: #4f46e5;
}
.btn-charge-pos:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-buka-shift-pos {
  width: 100%;
  height: 46px;
  margin-top: 4px;
  background: #6366f1;
  color: #ffffff;
  border: none;
  border-radius: 12px;
  font-size: 0.88rem;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
}

.btn-kembali-katalog-mobile {
  display: none;
}
@media (max-width: 1024px) {
  .btn-kembali-katalog-mobile {
    display: inline-block;
    padding: 4px 10px;
    background: #eef2ff;
    border: 1px solid #c7d2fe;
    color: #6366f1;
    border-radius: 7px;
    font-size: 0.775rem;
    font-weight: 700;
    cursor: pointer;
  }
}

.bar-melayang-keranjang-mobile {
  display: none;
}
@media (max-width: 1024px) {
  .bar-melayang-keranjang-mobile {
    display: flex;
    position: fixed;
    bottom: 12px;
    left: 12px;
    right: 12px;
    background: #6366f1;
    color: #ffffff;
    padding: 12px 18px;
    border-radius: 14px;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.25);
    z-index: 99;
    cursor: pointer;
  }
  .info-melayang-kiri {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .badge-melayang-qty {
    background: rgba(255, 255, 255, 0.22);
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 800;
  }
  .total-melayang {
    font-size: 1.05rem;
    font-weight: 800;
  }
  .btn-buka-keranjang-melayang {
    background: #ffffff;
    color: #6366f1;
    border: none;
    padding: 6px 14px;
    border-radius: 8px;
    font-weight: 800;
    font-size: 0.825rem;
  }
}
</style>
