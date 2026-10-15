<script setup>
import { ref, onMounted, computed, onUnmounted } from 'vue'
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
  ArrowLeft
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
const transaksiTerakhir = ref(null)
const kembalianTerakhir = ref(0)
const pesanBarcodeTidakDitemukan = ref(false)

const formatRupiah = (val) => 'Rp ' + Number(val || 0).toLocaleString('id-ID')

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

// Tangani penambahan produk ke keranjang dengan alur shift yang logis
function tanganiKlikProduk(produk) {
  if (!shiftStore.apakahShiftTerbuka) {
    tampilModalBukaShift.value = true
    return
  }
  keranjangStore.tambahItem(produk)
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
    teksPencarian.value = ''
    pesanBarcodeTidakDitemukan.value = false
  } else {
    // Jika tidak ditemukan dan hanya ada 1 hasil terfilter, pilih produk tersebut
    if (produkTerfilter.value.length === 1) {
      keranjangStore.tambahItem(produkTerfilter.value[0])
      teksPencarian.value = ''
      pesanBarcodeTidakDitemukan.value = false
    } else {
      pesanBarcodeTidakDitemukan.value = true
      setTimeout(() => {
        pesanBarcodeTidakDitemukan.value = false
      }, 3000)
    }
  }
}

// Pintasan Keyboard: F2 Cari, F9 Bayar, Esc Batal
function tanganiPintasanKeyboard(e) {
  if (e.key === 'F2') {
    e.preventDefault()
    inputCari.value?.focus()
  } else if (e.key === 'F9') {
    e.preventDefault()
    if (!shiftStore.apakahShiftTerbuka) {
      tampilModalBukaShift.value = true
    } else if (keranjangStore.itemKeranjang.length > 0) {
      tampilModalBayar.value = true
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

onMounted(async () => {
  window.addEventListener('keydown', tanganiPintasanKeyboard)
  window.addEventListener('katalog:diperbarui', muatProdukLokal)

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
})

// Selesaikan transaksi
async function prosesBayar({ metode, diterima, kembalian }) {
  try {
    const hasil = await keranjangStore.selesaikanTransaksi({
      idShift: shiftStore.shiftAktif.id,
      idKasir: authStore.idPengguna,
      namaKasir: authStore.namaLengkap,
      metodeBayar: metode,
      jumlahDiterima: diterima
    })

    transaksiTerakhir.value = hasil.transaksi
    kembalianTerakhir.value = hasil.kembalian
    tampilModalBayar.value = false
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
        <span class="ikon-tab-nav">🛍️</span>
        <span class="teks-tab-nav">Pilih Barang</span>
        <span class="badge-tab-nav">{{ produkTerfilter.length }}</span>
      </button>

      <button 
        class="tab-item-responsif" 
        :class="{ 'aktif': tabAktifMobile === 'keranjang' }"
        @click="tabAktifMobile = 'keranjang'"
      >
        <span class="ikon-tab-nav">🛒</span>
        <span class="teks-tab-nav">Keranjang Kasir</span>
        <span v-if="keranjangStore.totalKuantitas > 0" class="badge-tab-nav badge-hijau">
          {{ keranjangStore.totalKuantitas }} item
        </span>
      </button>
    </div>

    <!-- TAMPILAN UTAMA KASIR -->
    <div class="grid-pos" :class="`pos-view-${tabAktifMobile}`">
      <!-- KOLOM KIRI: KATALOG & SCAN BARCODE -->
      <section class="kolom-katalog">
        <!-- Banner Status Shift Kasir: Jelas & Logis -->
        <div v-if="!shiftStore.apakahShiftTerbuka" class="banner-shift-belum-buka">
          <div class="flex items-center gap-2">
            <AlertTriangle :size="20" class="teks-peringatan" />
            <span><strong>Shift Kasir Belum Dibuka:</strong> Harap buka shift kasir & isi modal laci untuk mulai mencatat penjualan.</span>
          </div>
          <button class="btn-buka-shift-cepat" @click="tampilModalBukaShift = true">
            <span>💼 Buka Shift Kasir</span>
          </button>
        </div>

        <div v-else class="banner-shift-aktif">
          <div class="flex items-center gap-2">
            <span class="titik-aktif-shift"></span>
            <span><strong>Shift Aktif:</strong> Kasir {{ authStore.namaLengkap }} • Modal Laci: {{ formatRupiah(shiftStore.shiftAktif?.modal_awal || 0) }}</span>
          </div>
          <button class="btn-tutup-shift-cepat" @click="tampilModalTutupShift = true" title="Tutup Shift & Rekonsiliasi Kas">
            <span>🔒 Tutup Shift</span>
          </button>
        </div>

        <!-- Panduan Visual 3 Langkah Orang Awam -->
        <div class="panduan-tiga-langkah">
          <div class="langkah-item">
            <span class="nomor-langkah">1</span>
            <div class="teks-langkah">
              <strong class="judul-langkah">Pilih Barang</strong>
              <span class="sub-langkah">Klik foto/nama barang</span>
            </div>
          </div>
          <div class="panah-langkah">➔</div>
          <div class="langkah-item">
            <span class="nomor-langkah">2</span>
            <div class="teks-langkah">
              <strong class="judul-langkah">Cek Keranjang</strong>
              <span class="sub-langkah">Atur jumlah (+) atau (-)</span>
            </div>
          </div>
          <div class="panah-langkah">➔</div>
          <div class="langkah-item langkah-bayar">
            <span class="nomor-langkah nomor-hijau">3</span>
            <div class="teks-langkah">
              <strong class="judul-langkah">Bayar Selesai</strong>
              <span class="sub-langkah">Klik tombol hijau [F9]</span>
            </div>
          </div>
        </div>

        <!-- Area Pencarian & Scan -->
        <div class="bar-pencarian">
          <div class="input-scan-wrap">
            <Barcode :size="24" class="ikon-scan" />
            <input 
              ref="inputCari"
              v-model="teksPencarian"
              type="text"
              class="input-teks input-scan"
              placeholder="🔍 Ketik nama barang atau scan barcode di sini... [F2]"
              @keydown.enter="tanganiInputScanEnter"
            />
          </div>
          <button 
            v-if="shiftStore.apakahShiftTerbuka"
            class="tombol tombol-sekunder tombol-tutup-shift" 
            @click="tampilModalTutupShift = true" 
            title="Tutup Shift Kasir & Rekonsiliasi Kas"
          >
            <span>🔒 Tutup Shift</span>
          </button>
          <button 
            v-else
            class="tombol tombol-primer tombol-buka-shift" 
            @click="tampilModalBukaShift = true" 
            title="Buka Shift Kasir"
          >
            <span>💼 Buka Shift</span>
          </button>
        </div>

        <!-- Banner Peringatan Barcode Tidak Ditemukan -->
        <div v-if="pesanBarcodeTidakDitemukan" class="pesan-tak-ditemukan">
          <PackageX :size="22" />
          <span>Produk dengan barcode/kode tersebut <strong>tidak ditemukan</strong> di katalog toko!</span>
        </div>

        <!-- Kategori Filter Pills Berwarna Menarik -->
        <div class="filter-kategori">
          <button 
            v-for="kat in daftarKategori" 
            :key="kat"
            class="pill-kategori"
            :class="{ 'aktif': kategoriDipilih === kat }"
            @click="kategoriDipilih = kat"
          >
            <span class="titik-kategori" :style="{ backgroundColor: kat === 'semua' ? '#2563eb' : warnaKategori(kat).text }"></span>
            <span>{{ kat.toUpperCase() }}</span>
          </button>
        </div>

        <!-- Grid Card Produk Putih Bersih, Elegan, Dilengkapi Foto Thumbnail & Tombol Preview -->
        <div class="grid-produk">
          <div 
            v-for="produk in produkTerfilter" 
            :key="produk.id"
            class="card-produk"
            :class="{ 'stok-kosong': produk.stok <= 0 }"
            @click="tanganiKlikProduk(produk)"
            title="Klik untuk masukkan ke keranjang"
          >
            <div class="info-atas-produk">
              <span class="badge-kategori-kecil" :style="{ background: warnaKategori(produk.kategori).bg, color: warnaKategori(produk.kategori).text, borderColor: warnaKategori(produk.kategori).border }">
                {{ produk.kategori || 'Umum' }}
              </span>
              <span 
                class="badge-stok"
                :class="produk.stok <= 0 ? 'stok-merah' : (produk.stok <= produk.min_stok ? 'stok-kuning' : 'stok-hijau')"
              >
                {{ produk.stok <= 0 ? 'Habis' : (produk.stok <= produk.min_stok ? `Sisa ${produk.stok}` : `Tersedia ${produk.stok}`) }}
              </span>
            </div>

            <!-- Wadah Foto Produk Ringan & Interaktif Preview -->
            <div class="wadah-foto-produk">
              <img v-if="produk.foto" :src="produk.foto" :alt="produk.nama" class="foto-kartu-pos" loading="lazy" />
              <div v-else class="foto-pos-placeholder" :style="{ background: warnaKategori(produk.kategori).bg, color: warnaKategori(produk.kategori).text }">
                <span class="huruf-kategori-pos">{{ (produk.nama || 'P').charAt(0).toUpperCase() }}</span>
              </div>

              <!-- Tombol Zoom Preview Foto yang Jelas -->
              <button 
                class="btn-zoom-foto-kartu"
                @click.stop="bukaPreviewProduk(produk)"
                :title="produk.foto ? 'Lihat foto ukuran besar' : 'Lihat info lengkap produk'"
              >
                <ZoomIn :size="13" />
                <span>Preview</span>
              </button>
            </div>
            
            <div class="nama-produk">{{ produk.nama }}</div>
            
            <div class="bawah-kartu">
              <div class="harga-produk">{{ formatRupiah(produk.harga) }}</div>
              <div class="tombol-tambah-mini" :class="{ 'habis': produk.stok <= 0 }">
                <Plus v-if="produk.stok > 0" :size="14" />
                <span>{{ produk.stok <= 0 ? 'Habis' : 'Tambah' }}</span>
              </div>
            </div>
          </div>

          <div v-if="produkTerfilter.length === 0" class="state-kosong">
            <PackageX :size="54" class="ikon-kosong" />
            <div class="tebal">Produk tidak ditemukan</div>
            <div class="teks-redup">
              {{ sedangMuatKatalog ? 'Sedang memuat data produk...' : 'Coba periksa kata kunci pencarian atau pilih kategori lain' }}
            </div>
          </div>
        </div>
      </section>

      <!-- KOLOM KANAN: KERANJANG BELANJA (Putih Elegan & Kontras Tinggi) -->
      <aside class="kolom-keranjang panel-kartu">
        <div class="header-keranjang">
          <div class="flex items-center gap-2">
            <div class="ikon-keranjang-badge">
              <ShoppingBag :size="20" />
            </div>
            <div>
              <h2 class="judul-keranjang">Keranjang Kasir</h2>
              <div class="sub-keranjang">{{ keranjangStore.totalKuantitas }} barang dipilih</div>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <!-- Tombol Kembali ke Katalog untuk Mobile/Tablet -->
            <button 
              class="btn-kembali-katalog-mobile"
              @click="tabAktifMobile = 'katalog'"
              title="Kembali ke pilihan barang"
            >
              <ArrowLeft :size="15" />
              <span>Pilih Barang</span>
            </button>

            <button 
              v-if="keranjangStore.itemKeranjang.length > 0"
              class="tombol-kosongkan"
              @click="keranjangStore.kosongkanKeranjang"
              title="Kosongkan keranjang belanja"
            >
              <Trash2 :size="16" />
              <span>Kosongkan</span>
            </button>
          </div>
        </div>

        <!-- Daftar Baris Item Keranjang -->
        <div class="daftar-item-keranjang">
          <div v-if="keranjangStore.itemKeranjang.length === 0" class="keranjang-kosong">
            <div class="ikon-keranjang-kosong">🛒</div>
            <div class="tebal teks-utama">Keranjang Masih Kosong</div>
            <div class="hint-keranjang">Klik barang di katalog untuk menambahkan ke keranjang ini</div>
          </div>

          <div 
            v-for="it in keranjangStore.itemKeranjang" 
            :key="it.id"
            class="baris-item"
          >
            <div class="item-detail">
              <div class="item-nama">{{ it.nama }}</div>
              <div class="item-harga-satuan">{{ formatRupiah(it.harga) }} / pcs</div>
            </div>

            <!-- Kontrol Kuantitas Besar Ramah Sentuh -->
            <div class="kontrol-qty">
              <button class="btn-qty minus" @click="keranjangStore.kurangiItem(it.id)" title="Kurangi 1">
                <Minus :size="16" />
              </button>
              <input 
                :value="it.kuantitas" 
                type="number"
                min="1"
                class="input-qty"
                @input="keranjangStore.ubahKuantitas(it.id, $event.target.value)"
              />
              <button class="btn-qty plus" @click="keranjangStore.tambahItem(it)" title="Tambah 1">
                <Plus :size="16" />
              </button>
            </div>

            <!-- Subtotal Baris -->
            <div class="item-subtotal">
              {{ formatRupiah(it.harga * it.kuantitas) }}
            </div>

            <button class="btn-hapus" @click="keranjangStore.hapusItem(it.id)" title="Hapus barang ini dari keranjang">
              <Trash2 :size="16" />
            </button>
          </div>
        </div>

        <!-- Bagian Rincian Pembayaran -->
        <div class="rincian-biaya">
          <!-- Diskon Transaksi -->
          <div class="baris-rincian baris-diskon">
            <span class="label-rincian">
              <Tag :size="16" class="ikon-diskon" />
              <span class="tebal">Diskon Transaksi:</span>
            </span>
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

          <div class="baris-rincian">
            <span class="teks-redup">Subtotal Belanja:</span>
            <span class="angka-rincian">{{ formatRupiah(keranjangStore.subtotal) }}</span>
          </div>

          <!-- Total Besar Hijau Zamrud Sangat Jelas -->
          <div class="kotak-total-besar">
            <div>
              <div class="label-total-besar">TOTAL TAGIHAN</div>
              <div class="sub-total-item">{{ keranjangStore.totalKuantitas }} item belanja</div>
            </div>
            <div class="angka-total-besar">{{ formatRupiah(keranjangStore.totalAkhir) }}</div>
          </div>

          <!-- Tombol Bayar Hijau Menyala Sangat Jelas / Buka Shift Kasir Dahulu -->
          <button 
            v-if="shiftStore.apakahShiftTerbuka"
            class="tombol tombol-sukses tombol-lg w-full tombol-bayar"
            :disabled="keranjangStore.itemKeranjang.length === 0"
            @click="tampilModalBayar = true"
          >
            <CreditCard :size="24" />
            <div class="teks-btn-bayar-wrap">
              <span class="teks-utama-bayar">BAYAR SEKARANG [F9]</span>
              <span class="subteks-bayar">Uang Tunai, QRIS, atau Transfer</span>
            </div>
          </button>
          <button 
            v-else
            class="tombol tombol-peringatan tombol-lg w-full tombol-bayar-buka-shift"
            @click="tampilModalBukaShift = true"
          >
            <DoorClosed :size="24" />
            <div class="teks-btn-bayar-wrap">
              <span class="teks-utama-bayar">BUKA SHIFT UNTUK TRANSAKSI</span>
              <span class="subteks-bayar">Klik untuk masukkan uang modal laci</span>
            </div>
          </button>
        </div>
      </aside>
    </div>

    <!-- BILAH MELAYANG (FLOATING BAR) DI BAWAH UNTUK TABLET & MOBILE -->
    <div 
      v-if="tabAktifMobile === 'katalog' && keranjangStore.totalKuantitas > 0" 
      class="bar-melayang-keranjang-mobile"
      @click="tabAktifMobile = 'keranjang'"
    >
      <div class="info-melayang-kiri">
        <div class="badge-ikon-melayang">
          <ShoppingBag :size="20" />
          <span class="angka-qty-melayang">{{ keranjangStore.totalKuantitas }}</span>
        </div>
        <div class="teks-melayang">
          <div class="sub-melayang">{{ keranjangStore.totalKuantitas }} Barang Dipilih</div>
          <div class="total-melayang">{{ formatRupiah(keranjangStore.totalAkhir) }}</div>
        </div>
      </div>
      <button class="btn-buka-keranjang-melayang">
        <span>Lihat Keranjang & Bayar</span>
        <ChevronRight :size="18" />
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
      @tutup="tampilModalBayar = false" 
      @bayar="prosesBayar" 
    />

    <ModalSukses 
      v-if="tampilModalSukses" 
      :transaksi="transaksiTerakhir" 
      :kembalian="kembalianTerakhir"
      @transaksiBaru="transaksiBaru" 
    />

    <!-- MODAL PREVIEW FOTO PRODUK (ZOOM BESAR & BISA LANGSUNG BELI) -->
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
  min-height: calc(100vh - 68px);
  padding: 16px 20px;
  background: var(--warna-latar);
}
.layar-terkunci {
  min-height: 75vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.kotak-terkunci {
  max-width: 520px;
  padding: 48px;
  background: #ffffff;
  border-radius: var(--radius-xl);
  box-shadow: 0 10px 30px rgba(37, 99, 235, 0.1);
  border: 2px solid #bfdbfe;
}
.ikon-kunci-lingkaran {
  width: 80px;
  height: 80px;
  background: #eff6ff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px auto;
  color: #1d4ed8;
}
.judul-kunci { font-size: 1.6rem; font-weight: 900; color: #0f172a; }
.sub-kunci { font-size: 1rem; color: #475569; margin-top: 8px; line-height: 1.5; }

/* Tab Switcher Responsif Tablet & Mobile */
.tab-pos-responsif {
  display: none;
  gap: 10px;
  margin-bottom: 14px;
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
  padding: 12px 14px;
  background: #ffffff;
  border: 2px solid #cbd5e1;
  border-radius: var(--radius-md);
  font-weight: 800;
  font-size: 0.95rem;
  color: #334155;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}
.tab-item-responsif.aktif {
  background: #1d4ed8;
  color: #ffffff;
  border-color: #1d4ed8;
  box-shadow: 0 4px 14px rgba(29, 78, 216, 0.3);
}
.badge-tab-nav {
  padding: 3px 9px;
  border-radius: 9999px;
  font-size: 0.78rem;
  font-weight: 800;
  background: #f1f5f9;
  color: #475569;
}
.tab-item-responsif.aktif .badge-tab-nav {
  background: rgba(255, 255, 255, 0.25);
  color: #ffffff;
}
.badge-tab-nav.badge-hijau {
  background: #10b981;
  color: #ffffff;
}

/* Grid POS Responsif */
.grid-pos {
  display: grid;
  grid-template-columns: minmax(0, 1fr) clamp(380px, 32vw, 450px);
  gap: 20px;
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
  gap: 12px;
  overflow: hidden;
}

/* Banner Shift Kasir */
.banner-shift-belum-buka {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 18px;
  background: #fffbeb;
  border: 2px solid #fde68a;
  border-radius: var(--radius-md);
  color: #92400e;
  font-size: 0.95rem;
}
.banner-shift-aktif {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 18px;
  background: #eff6ff;
  border: 2px solid #bfdbfe;
  border-radius: var(--radius-md);
  color: #1e40af;
  font-size: 0.92rem;
}
.titik-aktif-shift {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.25);
  display: inline-block;
}
.btn-buka-shift-cepat {
  background: #2563eb;
  color: #ffffff;
  border: none;
  font-weight: 800;
  font-size: 0.85rem;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.2);
}
.btn-buka-shift-cepat:hover {
  background: #1d4ed8;
  transform: translateY(-1px);
}
.btn-tutup-shift-cepat {
  background: #ffffff;
  color: #dc2626;
  border: 1px solid #fca5a5;
  font-weight: 700;
  font-size: 0.8rem;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
}
.btn-tutup-shift-cepat:hover {
  background: #fee2e2;
}

/* Panduan Visual 3 Langkah Orang Awam */
.panduan-tiga-langkah {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 16px;
  background: #ffffff;
  border: 1.5px solid #dbeafe;
  border-radius: var(--radius-md);
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.05);
}
.langkah-item {
  display: flex;
  align-items: center;
  gap: 10px;
}
.nomor-langkah {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #2563eb;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  font-size: 0.9rem;
  flex-shrink: 0;
}
.nomor-langkah.nomor-hijau {
  background: #059669;
}
.teks-langkah {
  display: flex;
  flex-direction: column;
}
.judul-langkah {
  font-size: 0.88rem;
  font-weight: 800;
  color: #0f172a;
}
.sub-langkah {
  font-size: 0.75rem;
  color: #64748b;
}
.panah-langkah {
  color: #94a3b8;
  font-weight: 900;
  font-size: 0.95rem;
}
@media (max-width: 640px) {
  .panduan-tiga-langkah {
    display: none;
  }
}

/* Wadah Foto Produk & Tombol Zoom Preview */
.wadah-foto-produk {
  width: 100%;
  height: 110px;
  border-radius: 8px;
  overflow: hidden;
  margin: 8px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  position: relative;
}
.foto-kartu-pos {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.25s ease;
}
.card-produk:hover .foto-kartu-pos {
  transform: scale(1.06);
}
.foto-pos-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
}
.huruf-kategori-pos {
  font-size: 2.2rem;
  font-weight: 900;
  letter-spacing: -1px;
}

.btn-zoom-foto-kartu {
  position: absolute;
  top: 6px;
  right: 6px;
  background: rgba(255, 255, 255, 0.92);
  color: #1d4ed8;
  border: 1px solid #cbd5e1;
  border-radius: 9999px;
  padding: 4px 9px;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.72rem;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
  transition: all 0.2s ease;
  backdrop-filter: blur(2px);
  z-index: 2;
}
.btn-zoom-foto-kartu:hover {
  background: #1d4ed8;
  color: #ffffff;
  border-color: #1d4ed8;
  transform: scale(1.05);
}

/* Tombol Bayar Buka Shift */
.tombol-bayar-buka-shift {
  background: #f59e0b !important;
  color: #ffffff !important;
  border: 2px solid #d97706 !important;
  box-shadow: 0 4px 14px rgba(245, 158, 11, 0.3) !important;
  cursor: pointer;
}
.tombol-bayar-buka-shift:hover {
  background: #d97706 !important;
}
.bar-pencarian {
  display: flex;
  gap: 12px;
}
.input-scan-wrap {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
}
.ikon-scan {
  position: absolute;
  left: 16px;
  color: #2563eb;
}
.input-scan {
  padding-left: 50px;
  font-size: 1.05rem;
  font-weight: 700;
  height: 52px;
  border-radius: var(--radius-md);
  background: #ffffff;
  border: 2px solid #cbd5e1;
  color: #0f172a;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.input-scan:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.15);
}

.tombol-tutup-shift {
  background: #ffffff;
  border: 2px solid #cbd5e1;
  color: #334155;
  font-weight: 700;
  padding: 0 18px;
  height: 52px;
  border-radius: var(--radius-md);
}
.tombol-tutup-shift:hover {
  background: #fee2e2;
  border-color: #fca5a5;
  color: #dc2626;
}

.pesan-tak-ditemukan {
  background: #fef2f2;
  border: 2px solid #fecaca;
  color: #dc2626;
  padding: 10px 16px;
  border-radius: var(--radius-md);
  font-size: 0.95rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-kategori {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 4px;
}
.pill-kategori {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  background: #ffffff;
  border: 2px solid #cbd5e1;
  border-radius: 9999px;
  color: #334155;
  font-size: 0.85rem;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
  transition: var(--transisi-halus);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
}
.pill-kategori:hover {
  border-color: #2563eb;
  color: #1d4ed8;
  background: #eff6ff;
}
.pill-kategori.aktif {
  background: #1d4ed8;
  color: #ffffff;
  border-color: #1d4ed8;
  box-shadow: 0 4px 12px rgba(29, 78, 216, 0.3);
}
.titik-kategori {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.pill-kategori.aktif .titik-kategori {
  background-color: #ffffff !important;
}

.grid-produk {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 14px;
  overflow-y: auto;
  padding-right: 6px;
  flex: 1;
}
.card-produk {
  background: #ffffff;
  border: 2px solid #e2e8f0;
  border-radius: var(--radius-md);
  padding: 16px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 140px;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(30, 64, 175, 0.04);
}
.card-produk:hover {
  transform: translateY(-3px);
  border-color: #2563eb;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.14);
}
.card-produk.stok-kosong {
  opacity: 0.7;
  border-left: 4px solid #dc2626;
  background: #fafafa;
}

.info-atas-produk {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
}
.badge-kategori-kecil {
  font-size: 0.7rem;
  font-weight: 800;
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid;
}
.badge-stok { 
  font-weight: 800; 
  font-size: 0.7rem; 
  border-radius: 6px; 
  padding: 3px 7px; 
}
.stok-hijau { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }
.stok-kuning { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
.stok-merah { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }

.nama-produk {
  font-weight: 800;
  font-size: 1.05rem;
  color: #0f172a;
  margin: 10px 0 6px 0;
  line-height: 1.3;
}

.bawah-kartu {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
  padding-top: 8px;
}
.harga-produk {
  font-size: 1.15rem;
  font-weight: 900;
  color: #1d4ed8;
  font-family: var(--font-angka);
}
.tombol-tambah-mini {
  font-size: 0.75rem;
  font-weight: 800;
  background: #eff6ff;
  color: #2563eb;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid #bfdbfe;
  transition: all 0.2s ease;
}
.card-produk:hover .tombol-tambah-mini {
  background: #2563eb;
  color: #ffffff;
}

.state-kosong {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 20px;
  color: #64748b;
  background: #ffffff;
  border-radius: var(--radius-lg);
  border: 2px dashed #cbd5e1;
}
.ikon-kosong { margin-bottom: 12px; color: #94a3b8; }

/* Kolom Keranjang */
.kolom-keranjang {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
  background: #ffffff;
  border: 2px solid #cbd5e1;
  border-radius: var(--radius-lg);
}
.header-keranjang {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 14px;
  border-bottom: 2px solid #f1f5f9;
}
.ikon-keranjang-badge {
  width: 38px;
  height: 38px;
  background: #eff6ff;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #1d4ed8;
}
.judul-keranjang { font-size: 1.25rem; font-weight: 900; color: #0f172a; }
.sub-keranjang { font-size: 0.85rem; color: #64748b; font-weight: 600; }
.tombol-kosongkan {
  background: #fee2e2;
  border: 1px solid #fecaca;
  color: #dc2626;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.825rem;
  font-weight: 800;
  padding: 6px 12px;
  border-radius: 8px;
  transition: all 0.2s ease;
}
.tombol-kosongkan:hover {
  background: #dc2626;
  color: #ffffff;
}

.daftar-item-keranjang {
  flex: 1;
  overflow-y: auto;
  padding: 12px 0;
}
.keranjang-kosong {
  text-align: center;
  padding: 70px 20px;
  color: #64748b;
}
.ikon-keranjang-kosong {
  font-size: 3rem;
  margin-bottom: 10px;
}
.teks-utama { color: #0f172a; font-size: 1.1rem; }
.hint-keranjang { font-size: 0.875rem; color: #64748b; margin-top: 6px; }

.baris-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 8px;
  border-bottom: 1px solid #f1f5f9;
  transition: background 0.15s ease;
  border-radius: 8px;
}
.baris-item:hover {
  background: #f8fafc;
}
.item-detail { flex: 1.5; min-width: 0; }
.item-nama {
  font-size: 0.95rem;
  font-weight: 800;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.item-harga-satuan { font-size: 0.8rem; color: #64748b; font-weight: 600; font-family: var(--font-angka); }

.kontrol-qty {
  display: flex;
  align-items: center;
  background: #ffffff;
  border: 2px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.btn-qty {
  background: #f8fafc;
  border: none;
  padding: 6px 9px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  transition: all 0.15s ease;
}
.btn-qty.minus { color: #d97706; }
.btn-qty.minus:hover { background: #fffbeb; }
.btn-qty.plus { color: #2563eb; }
.btn-qty.plus:hover { background: #eff6ff; }

.input-qty {
  width: 38px;
  text-align: center;
  background: none;
  border: none;
  color: #0f172a;
  font-weight: 900;
  font-size: 0.95rem;
  font-family: var(--font-angka);
}
.item-subtotal {
  font-size: 0.95rem;
  font-weight: 900;
  color: #1d4ed8;
  font-family: var(--font-angka);
  width: 95px;
  text-align: right;
}
.btn-hapus {
  background: #fee2e2;
  border: 1px solid #fecaca;
  color: #dc2626;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}
.btn-hapus:hover { background: #dc2626; color: #ffffff; }

.rincian-biaya {
  border-top: 2px solid #e2e8f0;
  padding-top: 14px;
}
.baris-rincian {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9rem;
  color: #475569;
  margin-bottom: 8px;
}
.baris-diskon {
  background: #fffbeb;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid #fde68a;
}
.ikon-diskon { color: #d97706; }
.diskon-input-wrap { display: flex; align-items: center; gap: 6px; font-size: 0.85rem; }
.input-diskon {
  width: 52px;
  padding: 4px 6px;
  text-align: center;
  background: #ffffff;
  border: 1.5px solid #d97706;
  border-radius: 6px;
  color: #92400e;
  font-weight: 900;
}
.satuan-persen { font-weight: 800; color: #92400e; }
.nominal-diskon { font-weight: 800; color: #b45309; }
.angka-rincian { font-family: var(--font-angka); font-weight: 800; color: #0f172a; font-size: 0.95rem; }

.kotak-total-besar {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border: 2px solid #3b82f6;
  border-radius: var(--radius-md);
  padding: 14px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 12px 0 16px 0;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08);
}
.label-total-besar { font-size: 0.85rem; font-weight: 900; color: #1e40af; letter-spacing: 0.04em; }
.sub-total-item { font-size: 0.8rem; color: #3b82f6; font-weight: 700; }
.angka-total-besar {
  font-size: 1.9rem;
  font-weight: 900;
  font-family: var(--font-angka);
  color: #047857;
}

.tombol-bayar {
  height: 60px;
  font-size: 1.15rem;
  letter-spacing: 0.02em;
  background: linear-gradient(135deg, #059669, #10b981);
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}
.tombol-bayar:hover:not(:disabled) {
  background: linear-gradient(135deg, #047857, #059669);
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.5);
}

.teks-btn-bayar-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
}
.teks-utama-bayar {
  font-size: 1.1rem;
  font-weight: 900;
  line-height: 1.2;
}
.subteks-bayar {
  font-size: 0.72rem;
  opacity: 0.92;
  font-weight: 600;
}

/* Tombol Kembali ke Katalog Khusus Mobile / Tablet */
.btn-kembali-katalog-mobile {
  display: none;
}
@media (max-width: 1024px) {
  .btn-kembali-katalog-mobile {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: #eff6ff;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    font-weight: 800;
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .btn-kembali-katalog-mobile:hover {
    background: #dbeafe;
  }
}

/* Bilah Melayang Keranjang Belanja di Mobile */
.bar-melayang-keranjang-mobile {
  display: none;
}
@media (max-width: 1024px) {
  .bar-melayang-keranjang-mobile {
    display: flex;
    position: fixed;
    bottom: 14px;
    left: 14px;
    right: 14px;
    background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%);
    color: #ffffff;
    padding: 12px 18px;
    border-radius: 14px;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 10px 25px rgba(29, 78, 216, 0.45);
    z-index: 99;
    cursor: pointer;
    border: 1px solid rgba(255, 255, 255, 0.25);
    animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  }
}
.info-melayang-kiri {
  display: flex;
  align-items: center;
  gap: 12px;
}
.badge-ikon-melayang {
  width: 40px;
  height: 40px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.angka-qty-melayang {
  position: absolute;
  top: -4px;
  right: -4px;
  background: #ef4444;
  color: #ffffff;
  font-size: 0.7rem;
  font-weight: 900;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #ffffff;
}
.teks-melayang {
  display: flex;
  flex-direction: column;
}
.sub-melayang {
  font-size: 0.8rem;
  opacity: 0.9;
  font-weight: 600;
}
.total-melayang {
  font-size: 1.25rem;
  font-weight: 900;
  font-family: var(--font-angka);
}
.btn-buka-keranjang-melayang {
  background: #ffffff;
  color: #1d4ed8;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-weight: 800;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
@keyframes slideUp {
  from { transform: translateY(100%); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.tombol-tambah-mini {
  font-size: 0.8rem;
  font-weight: 800;
  background: #eff6ff;
  color: #2563eb;
  padding: 5px 10px;
  border-radius: 6px;
  border: 1px solid #bfdbfe;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.tombol-tambah-mini.habis {
  background: #f1f5f9;
  color: #94a3b8;
  border-color: #cbd5e1;
}
.card-produk:hover .tombol-tambah-mini:not(.habis) {
  background: #2563eb;
  color: #ffffff;
}
</style>
