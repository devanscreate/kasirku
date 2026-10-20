<script setup>
import { ref, onMounted, computed } from 'vue'
import { panggilApi } from '../layanan/api'
import { 
  Boxes, 
  ArrowDownToLine, 
  Sliders, 
  ClipboardCheck, 
  History, 
  X, 
  AlertTriangle,
  Search,
  RotateCcw,
  Check,
  Package
} from 'lucide-vue-next'

const tabAktif = ref('daftar') // 'daftar' | 'terima' | 'sesuaikan' | 'opname' | 'riwayat'
const daftarProduk = ref([])
const riwayatPergerakan = ref([])
const sedangMemuat = ref(false)
const sedangSimpan = ref(false)
const pesanSukses = ref('')
const pesanError = ref('')

// State Pencarian & Filter
const kueriCariStok = ref('')
const filterStatusStok = ref('semua') // 'semua' | 'aman' | 'menipis' | 'habis'
const kueriCariForm = ref('')
const kueriCariRiwayat = ref('')

const formatRupiah = (val) => 'Rp ' + Number(val || 0).toLocaleString('id-ID')

// Form Terima Barang
const formTerima = ref({ id_produk: '', kuantitas: 1, harga_modal: null, catatan: '' })

// Form Penyesuaian
const formSesuaikan = ref({ id_produk: '', perubahan_stok: 0, alasan: '' })

// Form Opname Fisik
const formOpname = ref({ id_produk: '', stok_fisik: 0, alasan: 'Stock Opname Rutin' })

// Rekap hitung stok
const hitungStok = computed(() => {
  const semua = daftarProduk.value.length
  let habis = 0
  let menipis = 0
  let aman = 0

  daftarProduk.value.forEach(p => {
    const min = p.min_stok || 5
    if (p.stok <= 0) {
      habis++
    } else if (p.stok <= min) {
      menipis++
    } else {
      aman++
    }
  })

  return { semua, habis, menipis, aman }
})

// Filter data di tab Daftar Stok
const produkStokTersaring = computed(() => {
  let list = daftarProduk.value

  // 1. Filter status stok
  if (filterStatusStok.value === 'habis') {
    list = list.filter(p => p.stok <= 0)
  } else if (filterStatusStok.value === 'menipis') {
    list = list.filter(p => p.stok > 0 && p.stok <= (p.min_stok || 5))
  } else if (filterStatusStok.value === 'aman') {
    list = list.filter(p => p.stok > (p.min_stok || 5))
  }

  // 2. Filter kata kunci pencarian
  const q = kueriCariStok.value.trim().toLowerCase()
  if (q) {
    list = list.filter(p => 
      (p.nama || '').toLowerCase().includes(q) ||
      (p.sku || '').toLowerCase().includes(q) ||
      (p.barcode || '').toLowerCase().includes(q) ||
      (p.kategori || '').toLowerCase().includes(q)
    )
  }

  return list
})

// Filter pilihan produk di formulir (Terima, Sesuaikan, Opname)
const produkFormTersaring = computed(() => {
  const q = kueriCariForm.value.trim().toLowerCase()
  if (!q) return daftarProduk.value
  return daftarProduk.value.filter(p => 
    (p.nama || '').toLowerCase().includes(q) ||
    (p.sku || '').toLowerCase().includes(q) ||
    (p.barcode || '').toLowerCase().includes(q) ||
    (p.kategori || '').toLowerCase().includes(q)
  )
})

// Filter riwayat pergerakan stok
const riwayatPergerakanTersaring = computed(() => {
  const q = kueriCariRiwayat.value.trim().toLowerCase()
  if (!q) return riwayatPergerakan.value
  return riwayatPergerakan.value.filter(m => 
    (m.nama_produk || '').toLowerCase().includes(q) ||
    (m.alasan || '').toLowerCase().includes(q) ||
    (m.dibuat_oleh || '').toLowerCase().includes(q) ||
    (m.tipe || '').toLowerCase().includes(q)
  )
})

function pilihAksiProduk(p, tab) {
  tabAktif.value = tab
  kueriCariForm.value = ''
  if (tab === 'terima') {
    formTerima.value.id_produk = p.id
  } else if (tab === 'sesuaikan') {
    formSesuaikan.value.id_produk = p.id
  } else if (tab === 'opname') {
    formOpname.value.id_produk = p.id
    formOpname.value.stok_fisik = p.stok
  }
}

async function muatData() {
  sedangMemuat.value = true
  try {
    const [prod, movements] = await Promise.all([
      panggilApi('/products'),
      panggilApi('/stock/movements?limit=100')
    ])
    daftarProduk.value = prod
    riwayatPergerakan.value = movements
    if (prod.length > 0) {
      if (!formTerima.value.id_produk) formTerima.value.id_produk = prod[0].id
      if (!formSesuaikan.value.id_produk) formSesuaikan.value.id_produk = prod[0].id
      if (!formOpname.value.id_produk) {
        formOpname.value.id_produk = prod[0].id
        formOpname.value.stok_fisik = prod[0].stok
      }
    }
  } catch (err) {
    pesanError.value = 'Gagal memuat data stok dari server'
  } finally {
    sedangMemuat.value = false
  }
}

onMounted(() => {
  muatData()
})

async function kirimTerima() {
  sedangSimpan.value = true
  pesanError.value = ''
  pesanSukses.value = ''
  try {
    await panggilApi('/stock/receive', {
      method: 'POST',
      body: JSON.stringify(formTerima.value)
    })
    pesanSukses.value = 'Penerimaan barang berhasil dicatat ke stok'
    formTerima.value.kuantitas = 1
    formTerima.value.catatan = ''
    await muatData()
  } catch (err) {
    pesanError.value = err.message || 'Gagal mencatat penerimaan barang'
  } finally {
    sedangSimpan.value = false
  }
}

async function kirimSesuaikan() {
  if (formSesuaikan.value.perubahan_stok === 0) {
    pesanError.value = 'Perubahan stok tidak boleh 0'
    return
  }
  if (!formSesuaikan.value.alasan.trim()) {
    pesanError.value = 'Alasan penyesuaian stok wajib diisi'
    return
  }

  sedangSimpan.value = true
  pesanError.value = ''
  pesanSukses.value = ''
  try {
    await panggilApi('/stock/adjust', {
      method: 'POST',
      body: JSON.stringify(formSesuaikan.value)
    })
    pesanSukses.value = 'Penyesuaian stok berhasil disimpan'
    formSesuaikan.value.perubahan_stok = 0
    formSesuaikan.value.alasan = ''
    await muatData()
  } catch (err) {
    pesanError.value = err.message || 'Gagal menyimpan penyesuaian stok'
  } finally {
    sedangSimpan.value = false
  }
}

async function kirimOpname() {
  sedangSimpan.value = true
  pesanError.value = ''
  pesanSukses.value = ''
  try {
    await panggilApi('/stock/opname', {
      method: 'POST',
      body: JSON.stringify(formOpname.value)
    })
    pesanSukses.value = 'Hasil Stock Opname fisik berhasil disinkronkan'
    await muatData()
  } catch (err) {
    pesanError.value = err.message || 'Gagal menyimpan stock opname'
  } finally {
    sedangSimpan.value = false
  }
}

function padaGantiProdukOpname() {
  const p = daftarProduk.value.find(prod => prod.id === formOpname.value.id_produk)
  if (p) {
    formOpname.value.stok_fisik = p.stok
  }
}

function teksTipePergerakan(tipe) {
  switch (tipe) {
    case 'receive': return 'Barang Masuk'
    case 'initial': return 'Stok Awal'
    case 'sale': return 'Penjualan POS'
    case 'adjust': return 'Penyesuaian'
    case 'opname': return 'Stock Opname'
    case 'return': return 'Retur Barang'
    case 'void': return 'Void Batal'
    default: return tipe ? tipe.toUpperCase() : '-'
  }
}
</script>

<template>
  <div class="halaman-stok">
    <div class="panel-kartu">
      <!-- Header Halaman -->
      <div class="header-stok">
        <div class="header-info">
          <div>
            <h1 class="judul-halaman">Manajemen Stok</h1>
            <p class="sub-halaman">Pantau ketersediaan barang, penerimaan pasokan baru, koreksi kerusakan, dan stock opname fisik.</p>
          </div>
        </div>
        <button type="button" class="tombol-segarkan" @click="muatData" :disabled="sedangMemuat" title="Segarkan data stok terbaru">
          <RotateCcw :size="14" :class="{ 'animasi-putar': sedangMemuat }" />
          <span>{{ sedangMemuat ? 'Memuat...' : 'Segarkan Data' }}</span>
        </button>
      </div>

      <!-- Tab Navigasi Stok -->
      <div class="tab-stok mt-4">
        <button 
          type="button"
          class="btn-tab tab-daftar" 
          :class="{ 'aktif': tabAktif === 'daftar' }" 
          @click="tabAktif = 'daftar'"
        >
          <Boxes :size="15" />
          <span>Daftar Stok</span>
          <span class="badge-tab-hitung font-angka">{{ daftarProduk.length }}</span>
        </button>

        <button 
          type="button"
          class="btn-tab tab-terima" 
          :class="{ 'aktif': tabAktif === 'terima' }" 
          @click="tabAktif = 'terima'"
        >
          <ArrowDownToLine :size="15" />
          <span>Terima Barang</span>
        </button>

        <button 
          type="button"
          class="btn-tab tab-sesuaikan" 
          :class="{ 'aktif': tabAktif === 'sesuaikan' }" 
          @click="tabAktif = 'sesuaikan'"
        >
          <Sliders :size="15" />
          <span>Penyesuaian Stok</span>
        </button>

        <button 
          type="button"
          class="btn-tab tab-opname" 
          :class="{ 'aktif': tabAktif === 'opname' }" 
          @click="tabAktif = 'opname'"
        >
          <ClipboardCheck :size="15" />
          <span>Stock Opname</span>
        </button>

        <button 
          type="button"
          class="btn-tab tab-riwayat" 
          :class="{ 'aktif': tabAktif === 'riwayat' }" 
          @click="tabAktif = 'riwayat'"
        >
          <History :size="15" />
          <span>Riwayat Mutasi</span>
        </button>
      </div>

      <!-- Pesan Notifikasi -->
      <div v-if="pesanSukses" class="pesan-sukses-box mt-3">
        {{ pesanSukses }}
      </div>
      <div v-if="pesanError" class="peringatan-error mt-3">{{ pesanError }}</div>

      <!-- TAB 0: DAFTAR STOK BARANG & KOLOM PENCARIAN UTAMA -->
      <div v-if="tabAktif === 'daftar'" class="konten-tab mt-4">
        <!-- Bar Pencarian Stok Cepat & Filter Status -->
        <div class="bar-pencarian-stok">
          <div class="input-cari-stok-wrap">
            <Search :size="16" class="ikon-cari-stok" />
            <input 
              v-model="kueriCariStok" 
              type="text" 
              class="input-cari-stok" 
              placeholder="Cari nama barang, barcode, SKU, atau kategori..." 
            />
            <button v-if="kueriCariStok" class="btn-bersih-cari" @click="kueriCariStok = ''" title="Hapus pencarian">✕</button>
          </div>

          <!-- Filter Status Stok Pills -->
          <div class="filter-stok-pills">
            <button 
              type="button"
              class="pill-stok" 
              :class="{ 'aktif': filterStatusStok === 'semua' }"
              @click="filterStatusStok = 'semua'"
            >
              <span>Semua</span>
              <span class="badge-hitung-stok font-angka">{{ hitungStok.semua }}</span>
            </button>
            <button 
              type="button"
              class="pill-stok pill-habis" 
              :class="{ 'aktif': filterStatusStok === 'habis' }"
              @click="filterStatusStok = 'habis'"
            >
              <span>Stok Habis</span>
              <span class="badge-hitung-stok font-angka">{{ hitungStok.habis }}</span>
            </button>
            <button 
              type="button"
              class="pill-stok pill-menipis" 
              :class="{ 'aktif': filterStatusStok === 'menipis' }"
              @click="filterStatusStok = 'menipis'"
            >
              <span>Menipis</span>
              <span class="badge-hitung-stok font-angka">{{ hitungStok.menipis }}</span>
            </button>
            <button 
              type="button"
              class="pill-stok pill-aman" 
              :class="{ 'aktif': filterStatusStok === 'aman' }"
              @click="filterStatusStok = 'aman'"
            >
              <span>Stok Aman</span>
              <span class="badge-hitung-stok font-angka">{{ hitungStok.aman }}</span>
            </button>
          </div>
        </div>

        <!-- Tabel Ringkasan Stok Produk -->
        <div class="tabel-wadah mt-3">
          <table class="tabel-data">
            <thead>
              <tr>
                <th style="width: 48px;">No</th>
                <th>Produk</th>
                <th>SKU & Barcode</th>
                <th>Kategori</th>
                <th class="text-right">Sisa Stok</th>
                <th class="text-right">Min. Stok</th>
                <th class="text-center">Status</th>
                <th class="text-center">Aksi Cepat</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(p, index) in produkStokTersaring" :key="p.id" class="baris-stok-item">
                <td class="teks-redup font-angka">{{ index + 1 }}</td>
                <td>
                  <div class="flex items-center gap-3">
                    <div class="foto-mini-stok">
                      <img v-if="p.foto" :src="p.foto" :alt="p.nama" class="img-mini-stok" />
                      <div v-else class="foto-mini-placeholder font-angka">
                        {{ (p.nama || 'P').charAt(0).toUpperCase() }}
                      </div>
                    </div>
                    <div>
                      <div class="nama-produk-tabel">{{ p.nama }}</div>
                      <div class="harga-tabel font-angka">{{ formatRupiah(p.harga) }}</div>
                    </div>
                  </div>
                </td>
                <td>
                  <div class="font-angka teks-sku">{{ p.sku || '-' }}</div>
                  <div v-if="p.barcode" class="teks-barcode font-angka">{{ p.barcode }}</div>
                </td>
                <td>
                  <span class="badge-kategori-tabel">{{ p.kategori || 'Umum' }}</span>
                </td>
                <td class="text-right">
                  <span 
                    class="font-angka angka-stok-utama" 
                    :class="{ 
                      'habis': p.stok <= 0, 
                      'menipis': p.stok > 0 && p.stok <= (p.min_stok || 5),
                      'aman': p.stok > (p.min_stok || 5)
                    }"
                  >
                    {{ p.stok }}
                  </span>
                </td>
                <td class="text-right font-angka teks-redup">
                  {{ p.min_stok || 0 }}
                </td>
                <td class="text-center">
                  <span 
                    class="badge-status-stok"
                    :class="{
                      'status-habis': p.stok <= 0,
                      'status-menipis': p.stok > 0 && p.stok <= (p.min_stok || 5),
                      'status-aman': p.stok > (p.min_stok || 5)
                    }"
                  >
                    {{ p.stok <= 0 ? 'Habis (0)' : (p.stok <= (p.min_stok || 5) ? 'Menipis' : 'Aman') }}
                  </span>
                </td>
                <td class="text-center">
                  <div class="aksi-cepat-stok">
                    <button 
                      type="button" 
                      class="btn-aksi-cepat btn-cepat-terima"
                      @click="pilihAksiProduk(p, 'terima')"
                      title="Tambah stok dari penerimaan barang"
                    >
                      + Terima
                    </button>
                    <button 
                      type="button" 
                      class="btn-aksi-cepat btn-cepat-sesuaikan"
                      @click="pilihAksiProduk(p, 'sesuaikan')"
                      title="Koreksi stok barang rusak / hilang"
                    >
                      Sesuaikan
                    </button>
                    <button 
                      type="button" 
                      class="btn-aksi-cepat btn-cepat-opname"
                      @click="pilihAksiProduk(p, 'opname')"
                      title="Tetapkan hasil hitung stok fisik"
                    >
                      Opname
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="produkStokTersaring.length === 0">
                <td colspan="8" class="text-center p-8 teks-kosong">
                  <Boxes :size="36" class="mb-2 teks-pudar" />
                  <div class="tebal">Tidak ada produk yang cocok dengan pencarian</div>
                  <div class="sub-kosong">Coba periksa kata kunci pencarian atau ubah filter status stok.</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- TAB 1: TERIMA BARANG -->
      <div v-if="tabAktif === 'terima'" class="konten-tab mt-4">
        <div class="panduan-tab-box panduan-hijau">
          <b>Penerimaan Barang:</b> Catat barang yang masuk dari distributor/supplier untuk menambah stok toko.
        </div>

        <form @submit.prevent="kirimTerima" class="form-stok mt-4">
          <div class="grup-form">
            <div class="flex justify-between items-center mb-1">
              <label class="label-form">Cari & Pilih Produk yang Masuk*</label>
              <span v-if="kueriCariForm" class="teks-info-filter font-angka">
                Ditemukan {{ produkFormTersaring.length }} produk
              </span>
            </div>
            
            <!-- Kolom Search Cepat Produk -->
            <div class="input-cari-wrap-mini mb-2">
              <Search :size="15" class="ikon-cari-mini" />
              <input 
                v-model="kueriCariForm" 
                type="text" 
                class="input-teks input-cari-mini" 
                placeholder="Ketik untuk mencari nama produk, SKU, barcode..." 
              />
              <button v-if="kueriCariForm" type="button" class="btn-bersih-cari" @click="kueriCariForm = ''">✕</button>
            </div>

            <select v-model="formTerima.id_produk" class="input-pilihan select-tebal">
              <option v-for="p in produkFormTersaring" :key="p.id" :value="p.id">
                {{ p.nama }} — [Stok Saat Ini: {{ p.stok }} Unit | SKU: {{ p.sku }}]
              </option>
            </select>
          </div>

          <div class="grid-form mt-3">
            <div class="grup-form">
              <label class="label-form">Jumlah Kuantitas Masuk*</label>
              <input v-model.number="formTerima.kuantitas" type="number" min="1" class="input-teks font-angka input-tebal" required />
            </div>
            <div class="grup-form">
              <label class="label-form">Harga Modal Beli Baru (Opsional)</label>
              <input v-model.number="formTerima.harga_modal" type="number" min="0" class="input-teks font-angka" placeholder="Kosongkan jika tidak berubah" />
            </div>
          </div>

          <div class="grup-form mt-3">
            <label class="label-form">Catatan Penerimaan / Nomor Faktur Distributor</label>
            <input v-model="formTerima.catatan" type="text" class="input-teks" placeholder="Contoh: Faktur No. 1234 dari PT Sumber Makmur Jaya" />
          </div>

          <button type="submit" class="tombol-aksi-simpan tombol-hijau mt-4" :disabled="sedangSimpan">
            <ArrowDownToLine :size="18" />
            <span>{{ sedangSimpan ? 'Menyimpan...' : 'Simpan Penerimaan Barang Masuk' }}</span>
          </button>
        </form>
      </div>

      <!-- TAB 2: PENYESUAIAN STOK -->
      <div v-if="tabAktif === 'sesuaikan'" class="konten-tab mt-4">
        <div class="panduan-tab-box panduan-oranye">
          <b>Penyesuaian Stok:</b> Gunakan formulir ini untuk mengoreksi selisih stok jika ada barang yang rusak, kadaluarsa, atau hilang.
        </div>

        <form @submit.prevent="kirimSesuaikan" class="form-stok mt-4">
          <div class="grup-form">
            <div class="flex justify-between items-center mb-1">
              <label class="label-form">Cari & Pilih Produk yang Disesuaikan*</label>
              <span v-if="kueriCariForm" class="teks-info-filter font-angka">
                Ditemukan {{ produkFormTersaring.length }} produk
              </span>
            </div>
            
            <!-- Kolom Search Cepat Produk -->
            <div class="input-cari-wrap-mini mb-2">
              <Search :size="15" class="ikon-cari-mini" />
              <input 
                v-model="kueriCariForm" 
                type="text" 
                class="input-teks input-cari-mini" 
                placeholder="Ketik untuk mencari nama produk, SKU, barcode..." 
              />
              <button v-if="kueriCariForm" type="button" class="btn-bersih-cari" @click="kueriCariForm = ''">✕</button>
            </div>

            <select v-model="formSesuaikan.id_produk" class="input-pilihan select-tebal">
              <option v-for="p in produkFormTersaring" :key="p.id" :value="p.id">
                {{ p.nama }} — [Stok Saat Ini: {{ p.stok }} Unit | SKU: {{ p.sku }}]
              </option>
            </select>
          </div>

          <div class="grup-form mt-3">
            <label class="label-form">Perubahan Jumlah (+ untuk tambah, - untuk kurang)*</label>
            <input 
              v-model.number="formSesuaikan.perubahan_stok" 
              type="number" 
              class="input-teks font-angka input-tebal" 
              placeholder="Contoh: -2 (jika rusak) atau +5 (jika ada barang tertinggal)" 
              required 
            />
            <span class="teks-keterangan-bawah">Ketik tanda minus (-) bila barang berkurang karena rusak atau hilang.</span>
          </div>

          <div class="grup-form mt-3">
            <label class="label-form">Alasan Penyesuaian (Wajib Diisi)*</label>
            <input 
              v-model="formSesuaikan.alasan" 
              type="text" 
              class="input-teks" 
              placeholder="Contoh: Kemasan sobek / bocor saat penataan rak barang" 
              required 
            />
          </div>

          <button type="submit" class="tombol-aksi-simpan tombol-oranye mt-4" :disabled="sedangSimpan">
            <Sliders :size="18" />
            <span>{{ sedangSimpan ? 'Menyimpan...' : 'Simpan Koreksi Penyesuaian' }}</span>
          </button>
        </form>
      </div>

      <!-- TAB 3: STOCK OPNAME -->
      <div v-if="tabAktif === 'opname'" class="konten-tab mt-4">
        <div class="kotak-peringatan-opname mb-4">
          <AlertTriangle :size="24" />
          <div>
            <b>Panduan Stock Opname Fisik:</b> Lakukan penghitungan fisik nyata saat toko sepi atau sesudah kasir tutup shift agar tidak ada struk penjualan yang mengubah angka sistem secara bersamaan.
          </div>
        </div>

        <form @submit.prevent="kirimOpname" class="form-stok">
          <div class="grup-form">
            <div class="flex justify-between items-center mb-1">
              <label class="label-form">Cari & Pilih Produk yang Dihitung*</label>
              <span v-if="kueriCariForm" class="teks-info-filter font-angka">
                Ditemukan {{ produkFormTersaring.length }} produk
              </span>
            </div>
            
            <!-- Kolom Search Cepat Produk -->
            <div class="input-cari-wrap-mini mb-2">
              <Search :size="15" class="ikon-cari-mini" />
              <input 
                v-model="kueriCariForm" 
                type="text" 
                class="input-teks input-cari-mini" 
                placeholder="Ketik untuk mencari nama produk, SKU, barcode..." 
              />
              <button v-if="kueriCariForm" type="button" class="btn-bersih-cari" @click="kueriCariForm = ''">✕</button>
            </div>

            <select v-model="formOpname.id_produk" class="input-pilihan select-tebal" @change="padaGantiProdukOpname">
              <option v-for="p in produkFormTersaring" :key="p.id" :value="p.id">
                {{ p.nama }} — [Stok Sistem: {{ p.stok }} Unit | SKU: {{ p.sku }}]
              </option>
            </select>
          </div>

          <div class="grup-form mt-3">
            <label class="label-form">Jumlah Stok Nyata di Toko Saat Ini (Hasil Hitung Fisik)*</label>
            <input v-model.number="formOpname.stok_fisik" type="number" min="0" class="input-teks font-angka input-tebal input-stok-besar" required />
          </div>

          <div class="grup-form mt-3">
            <label class="label-form">Keterangan / Alasan Opname</label>
            <input v-model="formOpname.alasan" type="text" class="input-teks" placeholder="Stock Opname Mingguan / Bulanan" />
          </div>

          <button type="submit" class="tombol-aksi-simpan tombol-ungu mt-4" :disabled="sedangSimpan">
            <ClipboardCheck :size="18" />
            <span>{{ sedangSimpan ? 'Menyimpan...' : 'Konfirmasi & Tetapkan Stok Fisik' }}</span>
          </button>
        </form>
      </div>

      <!-- TAB 4: BUKU BESAR PERGERAKAN STOK -->
      <div v-if="tabAktif === 'riwayat'" class="konten-tab mt-4">
        <!-- Kolom Pencarian Riwayat Mutasi -->
        <div class="bar-pencarian-stok mb-3">
          <div class="input-cari-stok-wrap">
            <Search :size="16" class="ikon-cari-stok" />
            <input 
              v-model="kueriCariRiwayat" 
              type="text" 
              class="input-cari-stok" 
              placeholder="Cari riwayat pergerakan berdasarkan nama barang, alasan, atau PIC..." 
            />
            <button v-if="kueriCariRiwayat" class="btn-bersih-cari" @click="kueriCariRiwayat = ''">✕</button>
          </div>
        </div>

        <div class="tabel-wadah">
          <table class="tabel-data">
            <thead>
              <tr>
                <th>Waktu Kejadian</th>
                <th>Nama Produk</th>
                <th>Jenis Aktivitas</th>
                <th>Perubahan (+ / -)</th>
                <th>Alasan / Keterangan</th>
                <th>Petugas / PIC</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in riwayatPergerakanTersaring" :key="m.id" class="baris-mutasi">
                <td class="teks-waktu">{{ new Date(m.dibuat_pada).toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' }) }}</td>
                <td><span class="tebal teks-nama-item">{{ m.nama_produk }}</span></td>
                <td>
                  <span 
                    class="badge-mutasi"
                    :class="{
                      'mutasi-masuk': m.tipe === 'receive' || m.tipe === 'initial',
                      'mutasi-keluar': m.tipe === 'sale',
                      'mutasi-koreksi': m.tipe === 'adjust',
                      'mutasi-opname': m.tipe === 'opname',
                      'mutasi-retur': m.tipe === 'return' || m.tipe === 'void'
                    }"
                  >
                    {{ teksTipePergerakan(m.tipe) }}
                  </span>
                </td>
                <td>
                  <span class="font-angka tebal badge-delta" :class="m.perubahan_stok > 0 ? 'delta-plus' : 'delta-minus'">
                    {{ m.perubahan_stok > 0 ? `+${m.perubahan_stok}` : m.perubahan_stok }}
                  </span>
                </td>
                <td class="teks-alasan">{{ m.alasan || '-' }}</td>
                <td>
                  <span class="badge-pic">{{ m.dibuat_oleh || 'Sistem' }}</span>
                </td>
              </tr>
              <tr v-if="riwayatPergerakanTersaring.length === 0">
                <td colspan="6" class="text-center p-8 teks-kosong">
                  <History :size="40" class="mb-2 teks-pudar" />
                  <div class="tebal">Belum Ada Riwayat Pergerakan Stok yang Cocok</div>
                  <div class="sub-kosong">Aktivitas penjualan, penerimaan, dan opname barang akan tercatat otomatis di sini.</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.halaman-stok {
  padding: 24px;
}

.panel-kartu {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
}

.header-stok {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  padding-bottom: 20px;
  border-bottom: 1px solid #f1f5f9;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.ikon-header {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: #2563eb;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: none;
}

.judul-halaman {
  font-size: 1.5rem;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.02em;
}

.sub-halaman {
  font-size: 0.9rem;
  color: #475569;
  margin-top: 2px;
}

/* Tab Navigation with Colorful Identities */
.tab-stok {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding-bottom: 16px;
  border-bottom: 2px solid #f1f5f9;
}

.btn-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: #f8fafc;
  border: 1.5px solid #cbd5e1;
  border-radius: var(--radius-md);
  color: #334155;
  cursor: pointer;
  font-weight: 700;
  font-size: 0.875rem;
  transition: all 0.2s ease;
}

.btn-tab:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.tab-daftar.aktif {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.badge-tab-hitung {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.08);
  color: inherit;
  padding: 2px 7px;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 700;
}

.tab-daftar.aktif .badge-tab-hitung {
  background: rgba(255, 255, 255, 0.25);
  color: #ffffff;
}

.tombol-segarkan {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #f1f5f9;
  border: 1.5px solid #cbd5e1;
  border-radius: var(--radius-md);
  color: #334155;
  font-weight: 700;
  font-size: 0.8125rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tombol-segarkan:hover:not(:disabled) {
  background: #e2e8f0;
  color: #0f172a;
  border-color: #94a3b8;
}

.tombol-segarkan:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.animasi-putar {
  animation: putar 1s linear infinite;
}

@keyframes putar {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.tab-terima.aktif {
  background: #15803d;
  border-color: #15803d;
  color: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.tab-sesuaikan.aktif {
  background: #d97706;
  border-color: #d97706;
  color: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.tab-opname.aktif {
  background: #7c3aed;
  border-color: #7c3aed;
  color: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.tab-riwayat.aktif {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

/* Informational Guides */
.panduan-tab-box {
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  line-height: 1.5;
}

.panduan-hijau {
  background: #f0fdf4;
  border: 1.5px solid #bbf7d0;
  color: #166534;
}

.panduan-oranye {
  background: #fffbeb;
  border: 1.5px solid #fde68a;
  color: #92400e;
}

.kotak-peringatan-opname {
  display: flex;
  align-items: center;
  gap: 14px;
  background: #fef2f2;
  border: 1.5px solid #fecaca;
  color: #991b1b;
  padding: 14px 18px;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  line-height: 1.45;
}

.pesan-sukses-box {
  background: #f0fdf4;
  border: 1.5px solid #86efac;
  color: #15803d;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  font-weight: 700;
}

/* Form Styles */
.form-stok {
  max-width: 600px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-md);
  padding: 20px;
}

.grid-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.select-tebal, .input-tebal {
  font-weight: 600;
  background: #ffffff;
  border: 1.5px solid #cbd5e1;
}

.input-stok-besar {
  font-size: 1.2rem;
  font-weight: 800;
  color: #7c3aed;
}

.teks-keterangan-bawah {
  font-size: 0.78rem;
  color: #64748b;
  display: block;
  margin-top: 4px;
}

/* Tombol Aksi Form */
.tombol-aksi-simpan {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 12px 24px;
  border: none;
  border-radius: var(--radius-md);
  color: #ffffff;
  font-weight: 800;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tombol-hijau {
  background: #059669;
  box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3);
}
.tombol-hijau:hover {
  background: #047857;
}

.tombol-oranye {
  background: #d97706;
  box-shadow: 0 4px 12px rgba(217, 119, 6, 0.3);
}
.tombol-oranye:hover {
  background: #b45309;
}

.tombol-ungu {
  background: #7c3aed;
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
}
.tombol-ungu:hover {
  background: #6d28d9;
}

/* Tabel Data Mutasi */
.tabel-wadah {
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-md);
}

.tabel-data {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
  text-align: left;
}

.tabel-data th {
  padding: 14px 16px;
  background: #f1f5f9;
  color: #1e293b;
  font-weight: 800;
  border-bottom: 2px solid #e2e8f0;
}

.tabel-data td {
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.baris-mutasi:hover {
  background-color: #f8fafc;
}

.teks-waktu {
  color: #475569;
  font-size: 0.85rem;
}

.teks-nama-item {
  color: #0f172a;
}

.teks-alasan {
  color: #475569;
  font-size: 0.85rem;
}

.badge-mutasi {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 700;
}

.mutasi-masuk {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #86efac;
}

.mutasi-keluar {
  background: #fee2e2;
  color: #b91c1c;
  border: 1px solid #fca5a5;
}

.mutasi-koreksi {
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fcd34d;
}

.mutasi-opname {
  background: #f3e8ff;
  color: #7c3aed;
  border: 1px solid #d8b4fe;
}

.mutasi-retur {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.badge-delta {
  display: inline-block;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.95rem;
}

.delta-plus {
  background: #f0fdf4;
  color: #15803d;
}

.delta-minus {
  background: #fef2f2;
  color: #dc2626;
}

.badge-pic {
  display: inline-block;
  padding: 3px 8px;
  background: #f1f5f9;
  border-radius: var(--radius-sm);
  color: #475569;
  font-size: 0.8rem;
}

.teks-kosong {
  color: #64748b;
}

.sub-kosong {
  font-size: 0.85rem;
  color: #94a3b8;
  margin-top: 4px;
}

.font-angka { font-family: var(--font-angka); }
.tebal { font-weight: 700; }
.teks-pudar { color: #94a3b8; }
.mt-4 { margin-top: 16px; }
.mt-3 { margin-top: 12px; }
.mb-2 { margin-bottom: 8px; }
.mb-4 { margin-bottom: 16px; }
.p-8 { padding: 32px; }
.text-center { text-align: center; }

/* Bar Pencarian Stok & Filter */
.bar-pencarian-stok {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.input-cari-stok-wrap {
  position: relative;
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 280px;
  background: #ffffff;
  border: 1.5px solid #cbd5e1;
  border-radius: var(--radius-md);
  padding: 0 12px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.input-cari-stok-wrap:focus-within {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.ikon-cari-stok {
  color: #64748b;
  flex-shrink: 0;
  margin-right: 8px;
}

.input-cari-stok {
  width: 100%;
  padding: 10px 0;
  border: none;
  background: transparent;
  outline: none;
  font-size: 0.875rem;
  color: #0f172a;
}

.input-cari-stok::placeholder {
  color: #94a3b8;
}

.btn-bersih-cari {
  border: none;
  background: #e2e8f0;
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  flex-shrink: 0;
  margin-left: 6px;
}

.btn-bersih-cari:hover {
  background: #cbd5e1;
  color: #0f172a;
}

/* Filter Status Stok Pills */
.filter-stok-pills {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.pill-stok {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  background: #ffffff;
  border: 1.5px solid #cbd5e1;
  border-radius: 9999px;
  font-size: 0.8125rem;
  font-weight: 700;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s ease;
}

.pill-stok:hover {
  background: #f8fafc;
  border-color: #94a3b8;
  color: #0f172a;
}

.pill-stok.aktif {
  background: #0f172a;
  border-color: #0f172a;
  color: #ffffff;
}

.pill-habis.aktif {
  background: #dc2626;
  border-color: #dc2626;
  color: #ffffff;
}

.pill-menipis.aktif {
  background: #d97706;
  border-color: #d97706;
  color: #ffffff;
}

.pill-aman.aktif {
  background: #16a34a;
  border-color: #16a34a;
  color: #ffffff;
}

.badge-hitung-stok {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 6px;
  border-radius: 9999px;
  font-size: 0.72rem;
  font-weight: 800;
  background: #f1f5f9;
  color: #475569;
}

.pill-stok.aktif .badge-hitung-stok {
  background: rgba(255, 255, 255, 0.25);
  color: #ffffff;
}

/* Mini Thumbnail & Cell details in Stock Table */
.baris-stok-item:hover {
  background-color: #f8fafc;
}

.foto-mini-stok {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.img-mini-stok {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.foto-mini-placeholder {
  font-weight: 800;
  font-size: 0.95rem;
  color: #64748b;
}

.nama-produk-tabel {
  font-weight: 700;
  color: #0f172a;
  font-size: 0.875rem;
}

.harga-tabel {
  font-size: 0.78rem;
  color: #64748b;
}

.teks-sku {
  font-size: 0.82rem;
  color: #334155;
  font-weight: 600;
}

.teks-barcode {
  font-size: 0.75rem;
  color: #64748b;
}

.badge-kategori-tabel {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #e2e8f0;
}

.angka-stok-utama {
  font-size: 1.05rem;
  font-weight: 800;
}

.angka-stok-utama.habis {
  color: #dc2626;
}

.angka-stok-utama.menipis {
  color: #d97706;
}

.angka-stok-utama.aman {
  color: #16a34a;
}

.badge-status-stok {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 700;
}

.status-habis {
  background: #fee2e2;
  color: #b91c1c;
  border: 1px solid #fca5a5;
}

.status-menipis {
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fcd34d;
}

.status-aman {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #86efac;
}

/* Quick Action Buttons in Stock Table */
.aksi-cepat-stok {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.btn-aksi-cepat {
  padding: 5px 9px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.btn-cepat-terima {
  background: #f0fdf4;
  color: #15803d;
  border-color: #bbf7d0;
}

.btn-cepat-terima:hover {
  background: #dcfce7;
  border-color: #86efac;
}

.btn-cepat-sesuaikan {
  background: #fffbeb;
  color: #b45309;
  border-color: #fde68a;
}

.btn-cepat-sesuaikan:hover {
  background: #fef3c7;
  border-color: #fcd34d;
}

.btn-cepat-opname {
  background: #f3e8ff;
  color: #7c3aed;
  border-color: #e9d5ff;
}

.btn-cepat-opname:hover {
  background: #ede9fe;
  border-color: #c4b5fd;
}

/* Mini Quick Search in Operation Forms */
.input-cari-wrap-mini {
  display: flex;
  align-items: center;
  background: #ffffff;
  border: 1.5px solid #cbd5e1;
  border-radius: var(--radius-sm);
  padding: 0 10px;
  transition: border-color 0.2s ease;
}

.input-cari-wrap-mini:focus-within {
  border-color: #2563eb;
}

.ikon-cari-mini {
  color: #94a3b8;
  flex-shrink: 0;
  margin-right: 6px;
}

.input-cari-mini {
  width: 100%;
  padding: 8px 0;
  border: none;
  background: transparent;
  outline: none;
  font-size: 0.8125rem;
  color: #0f172a;
}

.input-cari-mini::placeholder {
  color: #94a3b8;
}

.teks-info-filter {
  font-size: 0.75rem;
  color: #2563eb;
  font-weight: 700;
}

.peringatan-error {
  background: #fef2f2;
  border: 1.5px solid #fca5a5;
  color: #b91c1c;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  font-weight: 700;
}

.teks-redup {
  color: #94a3b8;
}

.text-right {
  text-align: right;
}

.gap-3 {
  gap: 12px;
}

.items-center {
  align-items: center;
}

.justify-between {
  justify-content: space-between;
}
</style>
