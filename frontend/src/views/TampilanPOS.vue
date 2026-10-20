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
  Coins
} from 'lucide-vue-next'

const authStore = useAuthStore()
const shiftStore = useShiftStore()
const keranjangStore = useKeranjangStore()
const koneksiStore = useKoneksiStore()

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

// Tangani penambahan produk ke keranjang dengan alur shift yang logis
function tanganiKlikProduk(produk) {
  if (!shiftStore.apakahShiftTerbuka) {
    tampilModalBukaShift.value = true
    return
  }
  keranjangStore.tambahItem(produk)
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
    keranjangStore.tambahItem(produkCocok)
    bunyikanBeepSukses()
    teksPencarian.value = ''
    pesanBarcodeTidakDitemukan.value = false
    nextTick(() => inputCari.value?.focus())
  } else {
    // Jika tidak ditemukan dan hanya ada 1 hasil terfilter, pilih produk tersebut
    if (produkTerfilter.value.length === 1) {
      keranjangStore.tambahItem(produkTerfilter.value[0])
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

onMounted(async () => {
  window.addEventListener('keydown', tanganiPintasanKeyboard)
  window.addEventListener('katalog:diperbarui', muatProdukLokal)
  window.addEventListener('donasi:potong-belanja', tanganiEventPotongBelanja)

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
  } catch (err) {
    alert('Gagal memproses transaksi: ' + err.message)
  }
}

function transaksiBaru() {
  tampilModalSukses.value = false
  transaksiTerakhir.value = null
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
        <span>Keranjang</span>
        <span v-if="keranjangStore.totalKuantitas > 0" class="badge-tab-nav badge-hijau">
          {{ keranjangStore.totalKuantitas }}
        </span>
      </button>
    </div>

    <!-- TAMPILAN UTAMA KASIR -->
    <div class="grid-pos" :class="`pos-view-${tabAktifMobile}`">
      <!-- KOLOM KIRI: KATALOG & SCAN BARCODE -->
      <section class="kolom-katalog">
        <!-- Banner Status Shift Kasir: Rapi & Minimalis -->
        <div v-if="!shiftStore.apakahShiftTerbuka" class="banner-shift-belum-buka">
          <div class="shift-kiri">
            <span class="titik-kuning"></span>
            <div>
              <span class="teks-shift-judul">Shift Kasir Belum Dibuka</span>
              <span class="teks-shift-sub"> — Masukkan uang modal laci kasir untuk mulai transaksi</span>
            </div>
          </div>
          <div class="shift-kanan">
            <button class="btn-shift-aksi" @click="tampilModalBukaShift = true">
              Buka Shift
            </button>
          </div>
        </div>

        <div v-else class="banner-shift-aktif">
          <div class="shift-kiri">
            <span class="titik-hijau-shift"></span>
            <span class="label-kasir-aktif">Kasir: <strong>{{ authStore.namaLengkap }}</strong></span>
            <span class="pemisah-shift">•</span>
            <span class="label-modal-laci">Modal Awal: <strong class="font-angka">{{ formatRupiah(shiftStore.shiftAktif?.modal_awal || 0) }}</strong></span>
          </div>
          <div class="shift-kanan">
            <button class="btn-tutup-shift-minimal" @click="tampilModalTutupShift = true" title="Tutup Shift Kasir">
              Tutup Shift
            </button>
          </div>
        </div>

        <!-- Bar Pencarian Produk / Scan Barcode -->
        <div class="bar-pencarian">
          <div class="input-scan-wrap">
            <Search :size="18" class="ikon-scan" />
            <input 
              ref="inputCari"
              v-model="teksPencarian"
              type="text"
              class="input-teks input-scan"
              placeholder="Cari nama produk, kode SKU, atau scan barcode (F2)..."
              @keydown.enter="tanganiInputScanEnter"
            />
            <button v-if="teksPencarian" class="btn-bersih-cari" @click="teksPencarian = ''">✕</button>
          </div>
        </div>

        <!-- Banner Peringatan Barcode Tidak Ditemukan -->
        <div v-if="pesanBarcodeTidakDitemukan" class="pesan-tak-ditemukan">
          <span>Produk dengan barcode atau kode tersebut tidak ditemukan.</span>
        </div>

        <!-- Kategori Filter Chips Minimalis -->
        <div class="filter-kategori">
          <button 
            v-for="kat in daftarKategori" 
            :key="kat"
            class="pill-kategori"
            :class="{ 'aktif': kategoriDipilih === kat }"
            @click="kategoriDipilih = kat"
          >
            <span>{{ kat === 'semua' ? 'Semua' : kat }}</span>
          </button>
        </div>

        <!-- Grid Card Produk: Minimalis, Bersih, Cepat Diakses -->
        <div class="grid-produk">
          <div 
            v-for="produk in produkTerfilter" 
            :key="produk.id"
            class="card-produk"
            :class="{ 'stok-kosong': produk.stok <= 0 }"
            @click="tanganiKlikProduk(produk)"
            title="Klik untuk masukkan ke keranjang"
          >
            <!-- Wadah Foto Produk Bersih & Proporsional -->
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

              <!-- Badge Status Stok jika Menipis / Habis saja -->
              <span 
                v-if="produk.stok <= 0 || produk.stok <= produk.min_stok"
                class="badge-stok-overlay"
                :class="produk.stok <= 0 ? 'habis' : 'menipis'"
              >
                {{ produk.stok <= 0 ? 'Habis' : `Sisa ${produk.stok}` }}
              </span>
            </div>
            
            <!-- Detail Keterangan Produk: Rapi, Terstruktur, Bebas Tabrakan -->
            <div class="detail-kartu">
              <div class="nama-produk" :title="produk.nama">{{ produk.nama }}</div>
              
              <!-- Baris Meta: SKU & Kategori -->
              <div class="meta-sub-kartu font-angka">
                <span class="sku-teks">{{ produk.sku }}</span>
                <span v-if="produk.kategori" class="kategori-sub">• {{ produk.kategori }}</span>
              </div>

              <!-- Baris Harga: Sendiri di Bawah, Jelas, & Tidak Terpotong -->
              <div class="harga-produk font-angka">{{ formatRupiah(produk.harga) }}</div>
            </div>
          </div>

          <div v-if="produkTerfilter.length === 0" class="state-kosong">
            <div class="tebal">Produk tidak ditemukan</div>
            <div class="teks-redup">
              {{ sedangMuatKatalog ? 'Sedang memuat data produk...' : 'Coba periksa kata kunci pencarian atau pilih kategori lain' }}
            </div>
          </div>
        </div>
      </section>

      <!-- KOLOM KANAN: KERANJANG BELANJA (Clean POS Receipt Style) -->
      <aside class="kolom-keranjang">
        <div class="header-keranjang">
          <div class="judul-wrap">
            <h2 class="judul-keranjang">Keranjang</h2>
            <span class="badge-hitung-item">{{ keranjangStore.totalKuantitas }} item</span>
          </div>

          <div class="flex items-center gap-2">
            <button 
              class="btn-kembali-katalog-mobile"
              @click="tabAktifMobile = 'katalog'"
              title="Kembali ke pilihan barang"
            >
              <span>Katalog</span>
            </button>

            <button 
              v-if="keranjangStore.itemKeranjang.length > 0"
              class="btn-kosongkan-minimal"
              @click="keranjangStore.kosongkanKeranjang"
              title="Kosongkan keranjang"
            >
              <Trash2 :size="14" />
              <span>Kosongkan</span>
            </button>
          </div>
        </div>

        <!-- Daftar Baris Item Keranjang -->
        <div class="daftar-item-keranjang">
          <div v-if="keranjangStore.itemKeranjang.length === 0" class="keranjang-kosong">
            <div class="teks-utama">Keranjang Kosong</div>
            <div class="hint-keranjang">Klik produk di katalog untuk menambahkan pesanan</div>
          </div>

          <div 
            v-for="it in keranjangStore.itemKeranjang" 
            :key="it.id"
            class="baris-item"
          >
            <div class="item-detail">
              <div class="item-nama">{{ it.nama }}</div>
              <div class="item-meta-baris">
                <span class="item-kode font-angka">{{ it.sku }}</span>
                <span class="item-pemisah">•</span>
                <span class="item-harga-satuan font-angka">{{ formatRupiah(it.harga) }}</span>
              </div>
            </div>

            <div class="kontrol-qty">
              <button class="btn-qty" @click="keranjangStore.kurangiItem(it.id)" title="Kurangi 1">
                <Minus :size="13" />
              </button>
              <input 
                :value="it.kuantitas" 
                type="number"
                min="1"
                class="input-qty font-angka"
                @input="keranjangStore.ubahKuantitas(it.id, $event.target.value)"
                @change="keranjangStore.ubahKuantitas(it.id, $event.target.value)"
              />
              <button class="btn-qty" @click="keranjangStore.tambahItem(it)" title="Tambah 1">
                <Plus :size="13" />
              </button>
            </div>

            <div class="item-subtotal font-angka">
              {{ formatRupiah(it.harga * it.kuantitas) }}
            </div>

            <button class="btn-hapus-item" @click="keranjangStore.hapusItem(it.id)" title="Hapus">
              <Trash2 :size="14" />
            </button>
          </div>
        </div>

        <!-- Rincian Biaya & Total -->
        <div class="rincian-biaya">
          <!-- Diskon Transaksi -->
          <div class="baris-diskon-minimal">
            <span class="label-diskon">Diskon:</span>
            <div class="diskon-input-wrap">
              <input 
                :value="keranjangStore.diskonPersen"
                type="number" 
                min="0" 
                max="100" 
                class="input-diskon"
                placeholder="0"
                @input="keranjangStore.aturDiskon($event.target.value, 'persen')"
              />
              <span class="satuan-persen">%</span>
              <span v-if="keranjangStore.nilaiDiskon > 0" class="nominal-diskon">(-{{ formatRupiah(keranjangStore.nilaiDiskon) }})</span>
            </div>
          </div>

          <!-- Tabungan Donasi Pelanggan -->
          <div v-if="prefillPotongDonasiAktif" class="baris-tabungan-donasi">
            <div class="teks-tabungan-info">
              <div class="flex items-center gap-1.5">
                <Sparkles :size="13" class="teks-emas" />
                <span>Tabungan: <strong>{{ prefillPotongDonasiAktif.namaPelanggan }}</strong></span>
              </div>
              <div class="nominal-tabungan-siap font-angka">
                Saldo: {{ formatRupiah(prefillPotongDonasiAktif.saldoMaksimal) }} 
                (Dipotong: <strong class="teks-hijau">-{{ formatRupiah(nominalPotongTabunganAktif) }}</strong>)
              </div>
              <div v-if="totalTagihanBersihPOS === 0" class="badge-lunas-pos font-angka">
                ✓ Lunas Tabungan — Sisa Saldo: {{ formatRupiah(Math.max(0, prefillPotongDonasiAktif.saldoMaksimal - nominalPotongTabunganAktif)) }}
              </div>
            </div>
            <button class="btn-batal-tabungan" @click="prefillPotongDonasiAktif = null" title="Batalkan potongan">✕</button>
          </div>
          <div v-else class="baris-opsi-tabungan">
            <button class="btn-tautkan-tabungan" @click="tampilModalDonasiPelanggan = true">
              <Coins :size="14" class="teks-emas" />
              <span>Gunakan Celengan Tabungan Pelanggan</span>
            </button>
          </div>

          <div class="baris-rincian">
            <span class="teks-redup">Subtotal:</span>
            <span class="angka-rincian font-angka">{{ formatRupiah(keranjangStore.subtotal) }}</span>
          </div>

          <div v-if="keranjangStore.nilaiDiskon > 0" class="baris-rincian">
            <span class="teks-redup">Diskon Toko:</span>
            <span class="angka-rincian teks-merah font-angka">-{{ formatRupiah(keranjangStore.nilaiDiskon) }}</span>
          </div>

          <div v-if="nominalPotongTabunganAktif > 0" class="baris-rincian">
            <span class="teks-redup">Potongan Tabungan:</span>
            <span class="angka-rincian teks-hijau font-angka">-{{ formatRupiah(nominalPotongTabunganAktif) }}</span>
          </div>

          <!-- Total Besar Minimalis & Kontras Tinggi -->
          <div class="kotak-total-besar" :class="{ 'lunas-total-box': totalTagihanBersihPOS === 0 && nominalPotongTabunganAktif > 0 }">
            <div class="label-total-besar">
              {{ (totalTagihanBersihPOS === 0 && nominalPotongTabunganAktif > 0) ? 'Total Bayar Tunai (Lunas Tabungan)' : (nominalPotongTabunganAktif > 0 ? 'Sisa yang Harus Dibayar' : 'Total Tagihan') }}
            </div>
            <div class="angka-total-besar font-angka">{{ formatRupiah(totalTagihanBersihPOS) }}</div>
          </div>

          <!-- Tombol Bayar / Selesaikan Transaksi -->
          <button 
            v-if="shiftStore.apakahShiftTerbuka"
            class="tombol-bayar-utama"
            :class="{ 'btn-lunas-sukses-pos': totalTagihanBersihPOS === 0 && nominalPotongTabunganAktif > 0 }"
            :disabled="keranjangStore.itemKeranjang.length === 0"
            @click="tanganiKlikBayarPOS"
          >
            <template v-if="totalTagihanBersihPOS === 0 && nominalPotongTabunganAktif > 0">
              <Check :size="20" />
              <span>SELESAIKAN (Lunas Tabungan)</span>
            </template>
            <template v-else-if="nominalPotongTabunganAktif > 0">
              <span>BAYAR SISA (F9 / F4)</span>
              <span class="nominal-bayar-btn font-angka">{{ formatRupiah(totalTagihanBersihPOS) }}</span>
            </template>
            <template v-else>
              <span>BAYAR (F9 / F4)</span>
              <span class="nominal-bayar-btn font-angka">{{ formatRupiah(totalTagihanBersihPOS) }}</span>
            </template>
          </button>
          <button 
            v-else
            class="tombol-buka-shift-utama"
            @click="tampilModalBukaShift = true"
          >
            Buka Laci Kasir (Mulai Transaksi)
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
        <span>Lihat Keranjang & Bayar →</span>
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
  min-height: calc(100vh - 56px);
  padding: 16px 20px;
  background: var(--warna-latar);
}

/* Tab Switcher Responsif Tablet & Mobile */
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
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--warna-teks-redup);
  cursor: pointer;
  transition: all 0.15s ease;
}
.tab-item-responsif.aktif {
  background: #0f172a;
  color: #ffffff;
  border-color: #0f172a;
}
.badge-tab-nav {
  padding: 2px 7px;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  background: #f1f5f9;
  color: #475569;
}
.tab-item-responsif.aktif .badge-tab-nav {
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
}

/* Grid POS Responsif */
.grid-pos {
  display: grid;
  grid-template-columns: minmax(0, 1fr) clamp(360px, 30vw, 420px);
  gap: 16px;
  height: calc(100vh - 88px);
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
  gap: 12px;
  overflow: hidden;
}

/* Banner Shift Minimalis */
.banner-shift-belum-buka {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 14px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: var(--radius-md);
  color: #92400e;
}
.shift-kiri {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
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
  color: #92400e;
}
.teks-shift-sub {
  color: #b45309;
  font-size: 0.8rem;
}
.btn-shift-aksi {
  background: #0f172a;
  color: #ffffff;
  border: none;
  font-weight: 600;
  font-size: 0.8rem;
  padding: 5px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-shift-aksi:hover {
  background: #1e293b;
}

.banner-shift-aktif {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 14px;
  background: #f8fafc;
  border: 1px solid var(--warna-batas);
  border-radius: var(--radius-md);
  font-size: 0.825rem;
}
.titik-hijau-shift {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #10b981;
  flex-shrink: 0;
}
.label-kasir-aktif {
  color: var(--warna-teks-utama);
}
.pemisah-shift {
  color: #cbd5e1;
}
.label-modal-laci {
  color: var(--warna-teks-redup);
}
.btn-tutup-shift-minimal {
  background: transparent;
  color: #64748b;
  border: 1px solid #cbd5e1;
  font-weight: 500;
  font-size: 0.775rem;
  padding: 3px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-tutup-shift-minimal:hover {
  background: #fee2e2;
  color: #dc2626;
  border-color: #fca5a5;
}

/* Bar Pencarian */
.bar-pencarian {
  display: flex;
  gap: 8px;
}
.input-scan-wrap {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
}
.ikon-scan {
  position: absolute;
  left: 14px;
  color: #94a3b8;
  pointer-events: none;
}
.input-scan {
  padding-left: 42px;
  padding-right: 36px;
  font-size: 0.925rem;
  height: 42px;
  border-radius: var(--radius-md);
  background: #ffffff;
  border: 1px solid var(--warna-batas);
  color: var(--warna-teks-utama);
  font-weight: 500;
}
.btn-bersih-cari {
  position: absolute;
  right: 12px;
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 0.8rem;
  cursor: pointer;
  padding: 4px;
}
.btn-bersih-cari:hover {
  color: #0f172a;
}

.pesan-tak-ditemukan {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  font-size: 0.85rem;
  font-weight: 500;
}

/* Filter Kategori Chips */
.filter-kategori {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 2px;
}
.pill-kategori {
  display: flex;
  align-items: center;
  padding: 6px 14px;
  background: #ffffff;
  border: 1px solid var(--warna-batas);
  border-radius: 9999px;
  color: #475569;
  font-size: 0.825rem;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
  text-transform: capitalize;
}
.pill-kategori:hover {
  background: #f1f5f9;
  color: #0f172a;
}
.pill-kategori.aktif {
  background: #0f172a;
  color: #ffffff;
  border-color: #0f172a;
  font-weight: 600;
}

/* Grid Card Produk Responsif & Rapi */
.grid-produk {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
  overflow-y: auto;
  padding-right: 4px;
  padding-bottom: 12px;
  flex: 1;
  align-content: start;
}

.card-produk {
  background: #ffffff;
  border: 1.5px solid #e2e8f0;
  border-radius: var(--radius-md);
  padding: 10px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  transition: all 0.15s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
  position: relative;
  user-select: none;
}
.card-produk:hover {
  border-color: #0f172a;
  transform: translateY(-2px);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.07);
}
.card-produk:active {
  transform: translateY(0);
}
.card-produk.stok-kosong {
  opacity: 0.55;
  background: #f8fafc;
}

.wadah-foto-produk {
  width: 100%;
  aspect-ratio: 4 / 3;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  position: relative;
  border: 1px solid #f1f5f9;
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
  border-radius: 6px;
  transition: all 0.2s ease;
}
.huruf-kategori-pos {
  font-size: 1.75rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.badge-stok-overlay {
  position: absolute;
  bottom: 6px;
  right: 6px;
  font-size: 0.68rem;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}
.badge-stok-overlay.habis {
  background: #fee2e2;
  color: #b91c1c;
  border: 1px solid #fca5a5;
}
.badge-stok-overlay.menipis {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fde68a;
}

.detail-kartu {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.nama-produk {
  font-weight: 700;
  font-size: 0.88rem;
  color: #0f172a;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 2.35rem;
  margin-bottom: 4px;
  word-break: break-word;
}

.meta-sub-kartu {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 6px;
  overflow: hidden;
  white-space: nowrap;
}
.sku-teks {
  font-size: 0.68rem;
  font-weight: 700;
  color: #475569;
  background: #f1f5f9;
  padding: 1.5px 5px;
  border-radius: 4px;
  letter-spacing: 0.02em;
  flex-shrink: 0;
  border: 1px solid #e2e8f0;
}

.kategori-sub {
  font-size: 0.72rem;
  color: #64748b;
  font-weight: 600;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
  text-transform: capitalize;
}

.harga-produk {
  font-size: 1.05rem;
  font-weight: 900;
  color: #0f172a;
  font-family: var(--font-angka);
  white-space: nowrap;
  margin-top: auto;
  line-height: 1.2;
}

@media (max-width: 1200px) {
  .grid-produk {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 10px;
  }
}

@media (max-width: 768px) {
  .grid-produk {
    grid-template-columns: repeat(auto-fill, minmax(135px, 1fr));
    gap: 8px;
  }
  .nama-produk {
    font-size: 0.82rem;
    min-height: 2.2rem;
  }
  .harga-produk {
    font-size: 0.95rem;
  }
  .card-produk {
    padding: 8px;
  }
}

@media (max-width: 440px) {
  .grid-produk {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }
}

.state-kosong {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 20px;
  color: #94a3b8;
  background: #ffffff;
  border-radius: var(--radius-lg);
  border: 1px dashed var(--warna-batas);
}

/* Kolom Keranjang Minimalis */
.kolom-keranjang {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px;
  background: #ffffff;
  border: 1px solid var(--warna-batas);
  border-radius: var(--radius-lg);
  box-shadow: var(--bayangan-kartu);
}

.header-keranjang {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--warna-batas);
}

.judul-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.judul-keranjang {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--warna-teks-utama);
}
.badge-hitung-item {
  font-size: 0.75rem;
  font-weight: 600;
  background: #f1f5f9;
  color: #475569;
  padding: 2px 8px;
  border-radius: 9999px;
}

.btn-kosongkan-minimal {
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.775rem;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.15s ease;
}
.btn-kosongkan-minimal:hover {
  background: #fee2e2;
  color: #dc2626;
}

.daftar-item-keranjang {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.keranjang-kosong {
  text-align: center;
  padding: 60px 20px;
  color: #94a3b8;
}
.teks-utama {
  color: #475569;
  font-size: 0.95rem;
  font-weight: 600;
}
.hint-keranjang {
  font-size: 0.8rem;
  margin-top: 4px;
}

.baris-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 4px;
  border-bottom: 1px solid #f8fafc;
  transition: background 0.15s ease;
}
.baris-item:hover {
  background: #f8fafc;
}
.item-detail {
  flex: 1.2;
  min-width: 0;
}
.item-nama {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--warna-teks-utama);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.item-meta-baris {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 2px;
}
.item-kode {
  background: #f1f5f9;
  padding: 1px 4px;
  border-radius: 4px;
  font-size: 0.68rem;
  font-weight: 600;
  color: #475569;
}
.item-pemisah {
  font-size: 0.65rem;
  color: #cbd5e1;
}
.item-harga-satuan {
  font-size: 0.775rem;
  color: #475569;
  font-weight: 600;
  font-family: var(--font-angka);
}

.kontrol-qty {
  display: flex;
  align-items: center;
  border: 1px solid var(--warna-batas);
  border-radius: 6px;
  overflow: hidden;
}
.btn-qty {
  background: #f8fafc;
  border: none;
  padding: 4px 7px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #475569;
}
.btn-qty:hover {
  background: #e2e8f0;
}
.input-qty {
  width: 32px;
  text-align: center;
  background: none;
  border: none;
  color: var(--warna-teks-utama);
  font-weight: 700;
  font-size: 0.85rem;
  font-family: var(--font-angka);
}

.item-subtotal {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--warna-teks-utama);
  font-family: var(--font-angka);
  width: 85px;
  text-align: right;
}

.btn-hapus-item {
  background: none;
  border: none;
  color: #cbd5e1;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}
.btn-hapus-item:hover {
  color: #dc2626;
  background: #fef2f2;
}

/* Rincian Biaya Bawah */
.rincian-biaya {
  border-top: 1px solid var(--warna-batas);
  padding-top: 12px;
}

.baris-rincian {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  color: var(--warna-teks-redup);
  margin-bottom: 6px;
}
.angka-rincian {
  font-family: var(--font-angka);
  font-weight: 600;
  color: var(--warna-teks-utama);
}

.baris-diskon-minimal {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.825rem;
  color: var(--warna-teks-redup);
  margin-bottom: 6px;
}
.diskon-input-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
}
.input-diskon {
  width: 44px;
  padding: 2px 4px;
  text-align: center;
  background: #ffffff;
  border: 1px solid var(--warna-batas);
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.8rem;
}
.satuan-persen {
  color: #64748b;
}
.nominal-diskon {
  font-weight: 600;
  color: #d97706;
}

.baris-tabungan-donasi {
  background: #f0fdf4;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid #bbf7d0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
  margin-bottom: 6px;
}
.nominal-tabungan-siap {
  color: #15803d;
  font-family: var(--font-angka);
  margin-left: 6px;
}
.btn-batal-tabungan {
  background: none;
  border: none;
  color: #dc2626;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 700;
}

.baris-opsi-tabungan {
  margin-bottom: 8px;
}
.btn-tautkan-tabungan {
  width: 100%;
  background: none;
  border: 1px dashed var(--warna-batas);
  color: #475569;
  font-size: 0.775rem;
  font-weight: 500;
  padding: 5px 8px;
  border-radius: 6px;
  cursor: pointer;
}
.btn-tautkan-tabungan:hover {
  background: #f8fafc;
  border-color: #94a3b8;
  color: #0f172a;
}

.kotak-total-besar {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 10px 0;
  margin: 6px 0 12px 0;
  border-top: 1px dashed var(--warna-batas);
}
.label-total-besar {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--warna-teks-utama);
}
.angka-total-besar {
  font-size: 1.5rem;
  font-weight: 800;
  color: #0f172a;
}

.tombol-bayar-utama {
  width: 100%;
  height: 48px;
  background: #059669;
  color: #ffffff;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  transition: all 0.15s ease;
}
.tombol-bayar-utama:hover:not(:disabled) {
  background: #047857;
}
.tombol-bayar-utama:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.tombol-buka-shift-utama {
  width: 100%;
  height: 44px;
  background: #0f172a;
  color: #ffffff;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.15s ease;
}
.tombol-buka-shift-utama:hover {
  background: #1e293b;
}

/* Tablet & Mobile Buttons */
.btn-kembali-katalog-mobile {
  display: none;
}
@media (max-width: 1024px) {
  .btn-kembali-katalog-mobile {
    display: inline-block;
    padding: 4px 10px;
    background: #f1f5f9;
    border: 1px solid var(--warna-batas);
    border-radius: 6px;
    font-size: 0.775rem;
    font-weight: 600;
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
    background: #0f172a;
    color: #ffffff;
    padding: 10px 16px;
    border-radius: 12px;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
    z-index: 99;
    cursor: pointer;
  }
  .info-melayang-kiri {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .badge-melayang-qty {
    background: rgba(255, 255, 255, 0.15);
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
  }
  .total-melayang {
    font-size: 1rem;
    font-weight: 700;
  }
  .btn-buka-keranjang-melayang {
    background: #ffffff;
    color: #0f172a;
    border: none;
    padding: 6px 12px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.8rem;
  }
}
</style>
