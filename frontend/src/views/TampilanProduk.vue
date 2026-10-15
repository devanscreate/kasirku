<script setup>
import { ref, onMounted, computed } from 'vue'
import { panggilApi } from '../layanan/api'
import { dbLokal } from '../basis_data'
import { sinkronkanKatalogProduk } from '../layanan/sinkronisasi'
import { kompresFotoProduk } from '../layanan/utilitas_gambar'
import { 
  Package, 
  Plus, 
  Upload, 
  Edit, 
  Trash2, 
  Search, 
  X, 
  FileSpreadsheet, 
  Check, 
  AlertCircle,
  Camera,
  Image as ImageIcon
} from 'lucide-vue-next'

const daftarProduk = ref([])
const sedangMemuat = ref(false)
const kueriCari = ref('')
const filterKategori = ref('semua')

const tampilModalForm = ref(false)
const tampilModalImpor = ref(false)
const isEdit = ref(false)
const idProdukEdit = ref(null)

const inputFotoRef = ref(null)
const sedangKompresFoto = ref(false)
const infoFoto = ref(null)

const formProduk = ref({
  sku: '',
  barcode: '',
  nama: '',
  kategori: '',
  foto: null,
  harga: 0,
  harga_modal: 0,
  stok_awal: 0,
  min_stok: 5,
  status_aktif: true
})

const fileCSV = ref(null)
const hasilImpor = ref(null)
const sedangSimpan = ref(false)
const pesanError = ref('')

const formatRupiah = (val) => 'Rp ' + Number(val || 0).toLocaleString('id-ID')

async function muatProduk() {
  sedangMemuat.value = true
  try {
    if (navigator.onLine) {
      const data = await panggilApi('/products?termasuk_nonaktif=true')
      daftarProduk.value = data
      // Update juga Dexie secara lokal agar konsisten
      if (Array.isArray(data)) {
        await dbLokal.produk.bulkPut(data.map(p => ({
          id: p.id,
          sku: p.sku,
          barcode: p.barcode,
          nama: p.nama,
          kategori: p.kategori,
          foto: p.foto || null,
          harga: p.harga,
          harga_modal: p.harga_modal,
          stok: p.stok,
          min_stok: p.min_stok,
          status_aktif: p.status_aktif && !p.apakah_dihapus,
          terakhir_diperbarui: p.diperbarui_pada
        })))
      }
    } else {
      const dataLokal = await dbLokal.produk.toArray()
      daftarProduk.value = dataLokal
    }
  } catch (err) {
    const dataLokal = await dbLokal.produk.toArray()
    daftarProduk.value = dataLokal
  } finally {
    sedangMemuat.value = false
  }
}

onMounted(() => {
  muatProduk()
})

const produkTerfilter = computed(() => {
  let list = daftarProduk.value
  if (filterKategori.value !== 'semua') {
    list = list.filter(p => p.kategori === filterKategori.value)
  }
  if (kueriCari.value.trim()) {
    const q = kueriCari.value.toLowerCase().trim()
    list = list.filter(p => 
      p.nama.toLowerCase().includes(q) || 
      p.sku.toLowerCase().includes(q) ||
      (p.barcode && p.barcode.toLowerCase().includes(q))
    )
  }
  return list
})

const daftarKategoriUnik = computed(() => {
  const setKat = new Set(daftarProduk.value.map(p => p.kategori).filter(Boolean))
  return ['semua', ...Array.from(setKat)]
})


// Menangani kompresi foto otomatis di sisi browser (hemat memori ~3-8 KB WebP)
async function tanganiPilihFoto(e) {
  const file = e.target.files?.[0]
  if (!file) return

  sedangKompresFoto.value = true
  pesanError.value = ''
  try {
    const hasil = await kompresFotoProduk(file, 200, 0.7)
    formProduk.value.foto = hasil.dataUrl
    infoFoto.value = {
      kb: hasil.perkiraanKb,
      dimensi: `${hasil.lebar}x${hasil.tinggi}`
    }
  } catch (err) {
    pesanError.value = 'Gagal memproses gambar: ' + (err.message || 'Format tidak didukung')
  } finally {
    sedangKompresFoto.value = false
  }
}

function hapusFoto() {
  formProduk.value.foto = null
  infoFoto.value = null
  if (inputFotoRef.value) {
    inputFotoRef.value.value = ''
  }
}

function bukaTambah() {
  isEdit.value = false
  idProdukEdit.value = null
  pesanError.value = ''
  infoFoto.value = null
  formProduk.value = {
    sku: '',
    barcode: '',
    nama: '',
    kategori: 'Sembako',
    foto: null,
    harga: 0,
    harga_modal: 0,
    stok_awal: 10,
    min_stok: 5,
    status_aktif: true
  }
  tampilModalForm.value = true
}

function bukaUbah(p) {
  isEdit.value = true
  idProdukEdit.value = p.id
  pesanError.value = ''
  formProduk.value = {
    sku: p.sku,
    barcode: p.barcode || '',
    nama: p.nama,
    kategori: p.kategori || '',
    foto: p.foto || null,
    harga: p.harga,
    harga_modal: p.harga_modal,
    stok_awal: p.stok,
    min_stok: p.min_stok,
    status_aktif: p.status_aktif
  }
  if (p.foto) {
    const perkiraanKb = Math.max(1, Math.round((p.foto.length * 3) / 4 / 1024))
    infoFoto.value = {
      kb: perkiraanKb,
      dimensi: 'Tersimpan'
    }
  } else {
    infoFoto.value = null
  }
  tampilModalForm.value = true
}

async function simpanProduk() {
  if (!formProduk.value.sku || !formProduk.value.nama) {
    pesanError.value = 'SKU dan Nama Produk wajib diisi'
    return
  }

  sedangSimpan.value = true
  pesanError.value = ''

  try {
    if (isEdit.value) {
      await panggilApi(`/products/${idProdukEdit.value}`, {
        method: 'PUT',
        body: JSON.stringify(formProduk.value)
      })
    } else {
      await panggilApi('/products', {
        method: 'POST',
        body: JSON.stringify(formProduk.value)
      })
    }

    tampilModalForm.value = false
    await muatProduk()
    await sinkronkanKatalogProduk()
  } catch (err) {
    pesanError.value = err.message || 'Gagal menyimpan produk'
  } finally {
    sedangSimpan.value = false
  }
}

async function hapusProduk(p) {
  if (confirm(`Apakah Anda yakin ingin menghapus produk ${p.nama}?`)) {
    try {
      await panggilApi(`/products/${p.id}`, { method: 'DELETE' })
      await muatProduk()
      await sinkronkanKatalogProduk()
    } catch (err) {
      alert('Gagal menghapus produk: ' + err.message)
    }
  }
}

function tanganiPilihBerkasCSV(e) {
  fileCSV.value = e.target.files[0]
}

async function unggahCSV() {
  if (!fileCSV.value) return
  sedangSimpan.value = true
  pesanError.value = ''
  hasilImpor.value = null

  try {
    const formData = new FormData()
    formData.append('berkas', fileCSV.value)

    const token = localStorage.getItem('token_akses')
    const res = await fetch('/api/v1/products/import', {
      method: 'POST',
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: formData
    })
    const data = await res.json()
    hasilImpor.value = data
    await muatProduk()
    await sinkronkanKatalogProduk()
  } catch (err) {
    pesanError.value = err.message || 'Gagal mengimpor file CSV'
  } finally {
  sedangSimpan.value = false
  }
}

function dapatkanKelasKategori(kat) {
  if (!kat) return 'kategori-lain'
  const k = kat.toLowerCase()
  if (k.includes('sembako') || k.includes('beras') || k.includes('minyak')) return 'kategori-sembako'
  if (k.includes('minum')) return 'kategori-minuman'
  if (k.includes('makan') || k.includes('snack')) return 'kategori-makanan'
  if (k.includes('bersih') || k.includes('sabun')) return 'kategori-kebersihan'
  return 'kategori-lain'
}
</script>

<template>
  <div class="halaman-produk">
    <div class="panel-kartu">
      <!-- Header Halaman -->
      <div class="header-produk">
        <div class="header-info">
          <div class="ikon-header">
            <Package :size="26" />
          </div>
          <div>
            <h1 class="judul-halaman">Katalog & Manajemen Produk</h1>
            <p class="sub-halaman">Kelola data master barang dagangan toko, harga jual/modal, stok minimum, dan impor massal CSV.</p>
          </div>
        </div>
        <div class="flex gap-3">
          <button class="tombol-sekunder-biru" @click="tampilModalImpor = true">
            <Upload :size="16" />
            <span>Impor Data CSV</span>
          </button>
          <button class="tombol-tambah-produk" @click="bukaTambah">
            <Plus :size="18" />
            <span>+ Tambah Produk Baru</span>
          </button>
        </div>
      </div>

      <!-- Kategori Filter Cepat (Pill Berwarna untuk Persona 40 Tahun) -->
      <div class="kategori-filter-wrap mt-4">
        <button 
          v-for="kat in daftarKategoriUnik" 
          :key="kat"
          class="pill-kategori"
          :class="[
            kat === 'semua' ? 'kategori-semua' : dapatkanKelasKategori(kat),
            { 'aktif': filterKategori === kat }
          ]"
          @click="filterKategori = kat"
        >
          <span>{{ kat === 'semua' ? 'Semua Produk' : kat }}</span>
          <span class="badge-total-kategori">
            {{ kat === 'semua' ? daftarProduk.length : daftarProduk.filter(p => p.kategori === kat).length }}
          </span>
        </button>
      </div>

      <!-- Bar Filter & Pencarian -->
      <div class="bar-filter mt-3">
        <div class="input-cari-wrap">
          <Search :size="18" class="ikon-cari" />
          <input 
            v-model="kueriCari" 
            type="text" 
            class="input-teks input-cari" 
            placeholder="Cari berdasarkan nama produk, kode SKU, atau barcode..." 
          />
        </div>
      </div>

      <!-- Tabel Daftar Produk -->
      <div class="tabel-wadah mt-4">
        <table class="tabel-data">
          <thead>
            <tr>
              <th style="width: 68px;">Foto</th>
              <th>Kode / Barcode</th>
              <th>Nama Produk</th>
              <th>Kategori</th>
              <th>Harga Jual</th>
              <th>Harga Modal</th>
              <th>Stok Tersedia</th>
              <th>Min. Stok</th>
              <th>Status</th>
              <th class="text-center">Aksi</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in produkTerfilter" :key="p.id" class="baris-produk">
              <td>
                <div class="thumb-tabel-wadah">
                  <img v-if="p.foto" :src="p.foto" :alt="p.nama" class="img-thumb-tabel" loading="lazy" />
                  <div v-else class="thumb-tabel-kosong" :class="dapatkanKelasKategori(p.kategori)">
                    <span>{{ (p.nama || 'P').charAt(0).toUpperCase() }}</span>
                  </div>
                </div>
              </td>
              <td>
                <div class="font-angka tebal teks-sku">{{ p.sku }}</div>
                <div class="teks-barcode" v-if="p.barcode">🏷️ {{ p.barcode }}</div>
              </td>
              <td>
                <span class="tebal teks-nama-produk">{{ p.nama }}</span>
              </td>
              <td>
                <span class="pill-kategori-tabel" :class="dapatkanKelasKategori(p.kategori)">
                  {{ p.kategori || 'Umum' }}
                </span>
              </td>
              <td>
                <span class="font-angka tebal teks-harga-jual">{{ formatRupiah(p.harga) }}</span>
              </td>
              <td>
                <span class="font-angka teks-harga-modal">{{ formatRupiah(p.harga_modal) }}</span>
              </td>
              <td>
                <span 
                  class="lencana-stok"
                  :class="p.stok <= 0 ? 'stok-habis' : (p.stok <= p.min_stok ? 'stok-kritis' : 'stok-aman')"
                >
                  <AlertCircle v-if="p.stok <= p.min_stok" :size="14" />
                  <Check v-else :size="14" />
                  <span>{{ p.stok }} Unit</span>
                  <span v-if="p.stok <= 0" class="sub-stok">(Habis)</span>
                  <span v-else-if="p.stok <= p.min_stok" class="sub-stok">(Menipis)</span>
                </span>
              </td>
              <td>
                <span class="font-angka teks-min-stok">{{ p.min_stok }} Unit</span>
              </td>
              <td>
                <span class="lencana-aktif" :class="p.status_aktif ? 'aktif-ya' : 'aktif-tidak'">
                  {{ p.status_aktif ? 'Aktif' : 'Nonaktif' }}
                </span>
              </td>
              <td>
                <div class="flex gap-2 justify-center">
                  <button class="btn-aksi-produk btn-edit" @click="bukaUbah(p)" title="Ubah Data Produk">
                    <Edit :size="15" />
                    <span>Ubah</span>
                  </button>
                  <button class="btn-aksi-produk btn-hapus" @click="hapusProduk(p)" title="Hapus Produk">
                    <Trash2 :size="15" />
                    <span>Hapus</span>
                  </button>
                </div>
              </td>
            </tr>

            <tr v-if="produkTerfilter.length === 0">
              <td colspan="10" class="text-center p-8 teks-kosong">
                <Package :size="40" class="mb-2 teks-pudar" />
                <div class="tebal">Tidak Ada Produk Ditemukan</div>
                <div class="sub-kosong">Silakan periksa filter pencarian Anda atau tambah produk baru.</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- MODAL TAMBAH / UBAH PRODUK -->
    <div v-if="tampilModalForm" class="latar-modal">
      <div class="kotak-modal p-6 modal-putih" style="max-width: 580px;">
        <div class="header-modal">
          <div>
            <div class="lencana-info mb-1">{{ isEdit ? 'Perbarui Produk' : 'Master Data Produk' }}</div>
            <h2 class="judul-modal">{{ isEdit ? 'Ubah Data Produk' : 'Tambah Produk Baru' }}</h2>
          </div>
          <button class="tombol-tutup" @click="tampilModalForm = false"><X :size="20" /></button>
        </div>

        <div v-if="pesanError" class="peringatan-error mt-2">{{ pesanError }}</div>

        <!-- Unggah Foto Produk (Hemat Memori) -->
        <div class="wadah-input-foto mt-4">
          <label class="label-form flex items-center justify-between">
            <span class="flex items-center gap-1.5 font-bold">
              <Camera :size="16" class="teks-primer" />
              <span>Foto Produk</span>
            </span>
            <span v-if="infoFoto" class="badge-hemat-memori">
              ⚡ ~{{ infoFoto.kb }} KB (Sangat Hemat Memori)
            </span>
          </label>

          <div class="kotak-upload-foto-mini">
            <div class="pratinjau-foto-wrap">
              <img v-if="formProduk.foto" :src="formProduk.foto" alt="Foto Produk" class="foto-pratinjau-img" />
              <div v-else class="foto-pratinjau-kosong">
                <ImageIcon :size="28" class="ikon-foto-redup" />
                <span class="teks-foto-kosong">Belum ada</span>
              </div>
            </div>

            <div class="kontrol-foto-aksi">
              <div class="info-kompresi-teks">
                Foto otomatis dikompresi WebP 200px (~3-8 KB). Sangat ringan dan tidak menghabiskan RAM atau database.
              </div>
              <div class="flex items-center gap-2 mt-2">
                <label class="btn-pilih-berkas-foto">
                  <Upload :size="15" />
                  <span>{{ formProduk.foto ? 'Ganti Foto' : 'Pilih Foto' }}</span>
                  <input 
                    ref="inputFotoRef" 
                    type="file" 
                    accept="image/*" 
                    class="input-foto-asli" 
                    @change="tanganiPilihFoto" 
                  />
                </label>
                <button 
                  v-if="formProduk.foto" 
                  type="button" 
                  class="btn-hapus-foto" 
                  @click="hapusFoto"
                  title="Hapus foto produk"
                >
                  <Trash2 :size="15" />
                  <span>Hapus</span>
                </button>
                <span v-if="sedangKompresFoto" class="teks-sedang-kompres">Mengompres...</span>
              </div>
            </div>
          </div>
        </div>

        <div class="grid-form mt-3">
          <div class="grup-form">
            <label class="label-form">SKU (Kode Unik Produk)*</label>
            <input v-model="formProduk.sku" type="text" class="input-teks font-angka input-tebal" placeholder="Contoh: BRS-001" required />
          </div>
          <div class="grup-form">
            <label class="label-form">Barcode Scanner (Opsional)</label>
            <input v-model="formProduk.barcode" type="text" class="input-teks font-angka" placeholder="Contoh: 899123456" />
          </div>
        </div>

        <div class="grup-form mt-3">
          <label class="label-form">Nama Lengkap Produk*</label>
          <input v-model="formProduk.nama" type="text" class="input-teks input-tebal" placeholder="Contoh: Beras Premium Rojolele 5kg" required />
        </div>

        <div class="grid-form mt-3">
          <div class="grup-form">
            <label class="label-form">Kategori Barang</label>
            <input v-model="formProduk.kategori" type="text" class="input-teks" placeholder="Contoh: Sembako, Minuman..." />
          </div>
          <div class="grup-form">
            <label class="label-form">Harga Jual Konsumen (Rp)*</label>
            <input v-model.number="formProduk.harga" type="number" min="0" class="input-teks font-angka input-harga" placeholder="0" required />
          </div>
        </div>

        <div class="grid-form mt-3">
          <div class="grup-form">
            <label class="label-form">Harga Modal Beli (Rp)</label>
            <input v-model.number="formProduk.harga_modal" type="number" min="0" class="input-teks font-angka" placeholder="0" />
          </div>
          <div class="grup-form" v-if="!isEdit">
            <label class="label-form">Stok Awal di Toko</label>
            <input v-model.number="formProduk.stok_awal" type="number" class="input-teks font-angka" placeholder="0" />
          </div>
          <div class="grup-form">
            <label class="label-form">Batas Stok Minimum</label>
            <input v-model.number="formProduk.min_stok" type="number" min="0" class="input-teks font-angka" placeholder="5" />
          </div>
        </div>

        <div class="footer-aksi flex gap-3 mt-6">
          <button class="tombol tombol-sekunder flex-1" @click="tampilModalForm = false">Batal</button>
          <button 
            class="tombol tombol-simpan-produk flex-1" 
            :disabled="sedangSimpan" 
            @click="simpanProduk"
          >
            <Check :size="18" />
            <span>{{ sedangSimpan ? 'Menyimpan...' : (isEdit ? 'Simpan Perubahan' : 'Tambahkan ke Katalog') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL IMPOR CSV -->
    <div v-if="tampilModalImpor" class="latar-modal">
      <div class="kotak-modal p-6 modal-putih" style="max-width: 540px;">
        <div class="header-modal">
          <div>
            <div class="lencana-info mb-1">Impor Massal Excel/CSV</div>
            <h2 class="judul-modal">Impor Produk CSV</h2>
            <p class="sub-modal">Kolom CSV: sku, barcode, nama, kategori, harga, harga_modal, stok, min_stok</p>
          </div>
          <button class="tombol-tutup" @click="tampilModalImpor = false"><X :size="20" /></button>
        </div>

        <div v-if="pesanError" class="peringatan-error mt-2">{{ pesanError }}</div>

        <div class="kotak-unggah mt-4">
          <FileSpreadsheet :size="36" class="teks-primer mb-2" />
          <label class="label-unggah">Pilih File Spreadsheet CSV (.csv)</label>
          <input type="file" accept=".csv" @change="tanganiPilihBerkasCSV" class="input-berkas mt-2" />
        </div>

        <div v-if="hasilImpor" class="hasil-impor-box mt-4">
          <div class="teks-sukses font-bold flex items-center gap-2">
            <Check :size="16" />
            <span>Berhasil Diimpor: {{ hasilImpor.jumlah_diimpor }} produk</span>
          </div>
          <div v-if="hasilImpor.baris_gagal?.length > 0" class="teks-bahaya mt-2">
            ⚠️ Gagal pada baris ke: {{ hasilImpor.baris_gagal.map(b => b.baris).join(', ') }}
          </div>
        </div>

        <div class="footer-aksi flex gap-3 mt-6">
          <button class="tombol tombol-sekunder flex-1" @click="tampilModalImpor = false">Tutup</button>
          <button 
            class="tombol tombol-primer flex-1" 
            :disabled="sedangSimpan || !fileCSV" 
            @click="unggahCSV"
          >
            {{ sedangSimpan ? 'Mengunggah & Memproses...' : 'Mulai Proses Impor' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.halaman-produk {
  padding: 24px;
}

.panel-kartu {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
}

.header-produk {
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
  background: linear-gradient(135deg, #1e3a8a, #2563eb);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.25);
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

.tombol-sekunder-biru {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: #f8fafc;
  border: 1.5px solid #cbd5e1;
  border-radius: var(--radius-md);
  color: #0f172a;
  font-weight: 700;
  font-size: 0.9rem;
  cursor: pointer;
  transition: var(--transisi-halus);
}

.tombol-sekunder-biru:hover {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #1d4ed8;
}

.tombol-tambah-produk {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: #059669;
  border: none;
  border-radius: var(--radius-md);
  color: #ffffff;
  font-weight: 700;
  font-size: 0.925rem;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3);
}

.tombol-tambah-produk:hover {
  background: #047857;
  transform: translateY(-1px);
}

/* Category Filter Pills */
.kategori-filter-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.pill-kategori {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #f8fafc;
  border: 1.5px solid #cbd5e1;
  color: #334155;
}

.pill-kategori:hover {
  background: #e2e8f0;
}

.kategori-semua.aktif {
  background: #1e3a8a;
  border-color: #1e3a8a;
  color: #ffffff;
  box-shadow: 0 4px 10px rgba(30, 58, 138, 0.25);
}

.kategori-sembako.aktif {
  background: #15803d;
  border-color: #15803d;
  color: #ffffff;
  box-shadow: 0 4px 10px rgba(21, 128, 61, 0.25);
}

.kategori-minuman.aktif {
  background: #0284c7;
  border-color: #0284c7;
  color: #ffffff;
  box-shadow: 0 4px 10px rgba(2, 132, 199, 0.25);
}

.kategori-makanan.aktif {
  background: #d97706;
  border-color: #d97706;
  color: #ffffff;
  box-shadow: 0 4px 10px rgba(217, 119, 6, 0.25);
}

.kategori-kebersihan.aktif {
  background: #7c3aed;
  border-color: #7c3aed;
  color: #ffffff;
  box-shadow: 0 4px 10px rgba(124, 58, 237, 0.25);
}

.badge-total-kategori {
  background: rgba(0, 0, 0, 0.08);
  padding: 2px 8px;
  border-radius: 9999px;
  font-size: 0.78rem;
}

.pill-kategori.aktif .badge-total-kategori {
  background: rgba(255, 255, 255, 0.25);
  color: #ffffff;
}

/* Filter bar & Search */
.bar-filter {
  display: flex;
  gap: 12px;
}

.input-cari-wrap {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
}

.ikon-cari {
  position: absolute;
  left: 14px;
  color: #64748b;
}

.input-cari {
  padding-left: 42px;
  height: 44px;
  background: #f8fafc;
  border: 1.5px solid #cbd5e1;
  border-radius: var(--radius-md);
  font-size: 0.925rem;
  color: #0f172a;
}

.input-cari:focus {
  background: #ffffff;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

/* Tabel Data Produk */
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

.baris-produk {
  transition: background-color 0.15s ease;
}

.baris-produk:hover {
  background-color: #f8fafc;
}

.teks-sku {
  color: #1e3a8a;
  font-size: 0.95rem;
}

.teks-barcode {
  color: #64748b;
  font-size: 0.8rem;
  margin-top: 2px;
}

.teks-nama-produk {
  color: #0f172a;
  font-size: 0.925rem;
}

.pill-kategori-tabel {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 700;
}

.kategori-sembako {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #86efac;
}

.kategori-minuman {
  background: #e0f2fe;
  color: #0369a1;
  border: 1px solid #7dd3fc;
}

.kategori-makanan {
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fcd34d;
}

.kategori-kebersihan {
  background: #f3e8ff;
  color: #6b21a8;
  border: 1px solid #d8b4fe;
}

.kategori-lain {
  background: #f1f5f9;
  color: #334155;
  border: 1px solid #cbd5e1;
}

.teks-harga-jual {
  color: #059669;
  font-size: 1rem;
  font-weight: 800;
}

.teks-harga-modal {
  color: #64748b;
  font-size: 0.875rem;
}

.teks-min-stok {
  color: #64748b;
  font-size: 0.875rem;
}

/* Lencana Stok (Color Coded Visual Cue) */
.lencana-stok {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 9999px;
  font-size: 0.825rem;
  font-weight: 800;
}

.stok-aman {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #86efac;
}

.stok-kritis {
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fcd34d;
}

.stok-habis {
  background: #fee2e2;
  color: #b91c1c;
  border: 1px solid #fca5a5;
}

.sub-stok {
  font-size: 0.75rem;
  font-weight: 700;
}

.lencana-aktif {
  display: inline-block;
  padding: 3px 10px;
  border-radius: var(--radius-sm);
  font-size: 0.78rem;
  font-weight: 700;
}

.aktif-ya {
  background: #f0fdf4;
  color: #16a34a;
  border: 1px solid #bbf7d0;
}

.aktif-tidak {
  background: #f8fafc;
  color: #94a3b8;
  border: 1px solid #cbd5e1;
}

/* Tombol Aksi */
.btn-aksi-produk {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-weight: 700;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-edit {
  background: #eff6ff;
  border: 1.5px solid #bfdbfe;
  color: #1d4ed8;
}

.btn-edit:hover {
  background: #2563eb;
  color: #ffffff;
  border-color: #2563eb;
}

.btn-hapus {
  background: #fef2f2;
  border: 1.5px solid #fecaca;
  color: #b91c1c;
}

.btn-hapus:hover {
  background: #dc2626;
  color: #ffffff;
  border-color: #dc2626;
}

/* Modals */
.modal-putih {
  background: #ffffff !important;
  color: #0f172a;
  border: 1px solid #cbd5e1;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.2);
}

.judul-modal {
  font-size: 1.3rem;
  font-weight: 800;
  color: #0f172a;
}

.sub-modal {
  font-size: 0.85rem;
  color: #64748b;
  margin-top: 2px;
}

.lencana-info {
  display: inline-block;
  padding: 3px 8px;
  background: #eff6ff;
  color: #2563eb;
  font-weight: 700;
  font-size: 0.75rem;
  border-radius: var(--radius-sm);
}

.grid-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.input-tebal {
  font-weight: 600;
}

.input-harga {
  color: #059669;
  font-weight: 700;
}

.tombol-simpan-produk {
  background: #059669;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-weight: 700;
}

.tombol-simpan-produk:hover {
  background: #047857;
}

.kotak-unggah {
  background: #f8fafc;
  border: 2px dashed #cbd5e1;
  border-radius: var(--radius-md);
  padding: 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.label-unggah {
  font-weight: 700;
  color: #334155;
  font-size: 0.9rem;
}

.input-berkas {
  font-size: 0.85rem;
  color: #64748b;
}

.hasil-impor-box {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: var(--radius-md);
  padding: 14px;
  font-size: 0.875rem;
}

.font-angka { font-family: var(--font-angka); }
.tebal { font-weight: 700; }
.teks-primer { color: #2563eb; }
.teks-sukses { color: #16a34a; }
.teks-bahaya { color: #dc2626; }
.teks-kosong { color: #64748b; }
.sub-kosong { font-size: 0.85rem; color: #94a3b8; margin-top: 4px; }
.teks-pudar { color: #94a3b8; }
.p-6 { padding: 24px; }
.p-8 { padding: 32px; }
.mt-4 { margin-top: 16px; }
.mt-3 { margin-top: 12px; }
.mt-2 { margin-top: 8px; }
.mt-6 { margin-top: 24px; }
.mb-1 { margin-bottom: 4px; }
.mb-2 { margin-bottom: 8px; }
.flex { display: flex; }
.flex-1 { flex: 1; }
.items-center { align-items: center; }
.justify-center { justify-content: center; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.text-center { text-align: center; }

/* Thumbnail Foto Produk di Tabel */
.thumb-tabel-wadah {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
}
.img-thumb-tabel {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.thumb-tabel-kosong {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 1.1rem;
  background: #f1f5f9;
  color: #475569;
}

/* Upload Foto Produk di Modal (Hemat Memori) */
.wadah-input-foto {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-md);
  padding: 12px 14px;
}
.badge-hemat-memori {
  font-size: 0.72rem;
  font-weight: 800;
  color: #059669;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  padding: 2px 8px;
  border-radius: 9999px;
}
.kotak-upload-foto-mini {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-top: 8px;
}
.pratinjau-foto-wrap {
  width: 76px;
  height: 76px;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid #cbd5e1;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.foto-pratinjau-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.foto-pratinjau-kosong {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
}
.ikon-foto-redup {
  color: #94a3b8;
}
.teks-foto-kosong {
  font-size: 0.65rem;
  color: #94a3b8;
  font-weight: 600;
}
.kontrol-foto-aksi {
  flex: 1;
}
.info-kompresi-teks {
  font-size: 0.78rem;
  color: #64748b;
  line-height: 1.35;
}
.btn-pilih-berkas-foto {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #2563eb;
  color: #ffffff;
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-pilih-berkas-foto:hover {
  background: #1d4ed8;
}
.input-foto-asli {
  display: none;
}
.btn-hapus-foto {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #ffffff;
  color: #dc2626;
  border: 1px solid #fca5a5;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-hapus-foto:hover {
  background: #fee2e2;
}
.teks-sedang-kompres {
  font-size: 0.78rem;
  color: #2563eb;
  font-weight: 600;
}
</style>
