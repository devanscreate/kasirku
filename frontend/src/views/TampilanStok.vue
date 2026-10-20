<script setup>
import { ref, onMounted } from 'vue'
import { panggilApi } from '../layanan/api'
import { 
  Boxes, 
  ArrowDownToLine, 
  Sliders, 
  ClipboardCheck, 
  History, 
  X, 
  AlertTriangle 
} from 'lucide-vue-next'

const tabAktif = ref('terima') // 'terima' | 'sesuaikan' | 'opname' | 'riwayat'
const daftarProduk = ref([])
const riwayatPergerakan = ref([])
const sedangMemuat = ref(false)
const sedangSimpan = ref(false)
const pesanSukses = ref('')
const pesanError = ref('')

// Form Terima Barang
const formTerima = ref({ id_produk: '', kuantitas: 1, harga_modal: null, catatan: '' })

// Form Penyesuaian
const formSesuaikan = ref({ id_produk: '', perubahan_stok: 0, alasan: '' })

// Form Opname Fisik
const formOpname = ref({ id_produk: '', stok_fisik: 0, alasan: 'Stock Opname Rutin' })

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
      formTerima.value.id_produk = prod[0].id
      formSesuaikan.value.id_produk = prod[0].id
      formOpname.value.id_produk = prod[0].id
      formOpname.value.stok_fisik = prod[0].stok
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
            <p class="sub-halaman">Penerimaan pasokan barang baru, penyesuaian barang rusak/hilang, dan stock opname fisik.</p>
          </div>
        </div>
      </div>

      <!-- Tab Navigasi Stok -->
      <div class="tab-stok mt-4">
        <button 
          class="btn-tab tab-terima" 
          :class="{ 'aktif': tabAktif === 'terima' }" 
          @click="tabAktif = 'terima'"
        >
          <ArrowDownToLine :size="15" />
          <span>Terima Barang</span>
        </button>

        <button 
          class="btn-tab tab-sesuaikan" 
          :class="{ 'aktif': tabAktif === 'sesuaikan' }" 
          @click="tabAktif = 'sesuaikan'"
        >
          <Sliders :size="15" />
          <span>Penyesuaian Stok</span>
        </button>

        <button 
          class="btn-tab tab-opname" 
          :class="{ 'aktif': tabAktif === 'opname' }" 
          @click="tabAktif = 'opname'"
        >
          <ClipboardCheck :size="15" />
          <span>Stock Opname</span>
        </button>

        <button 
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

      <!-- TAB 1: TERIMA BARANG -->
      <div v-if="tabAktif === 'terima'" class="konten-tab mt-4">
        <div class="panduan-tab-box panduan-hijau">
          <b>Penerimaan Barang:</b> Catat barang yang masuk dari distributor/supplier untuk menambah stok toko.
        </div>

        <form @submit.prevent="kirimTerima" class="form-stok mt-4">
          <div class="grup-form">
            <label class="label-form">Pilih Produk yang Masuk*</label>
            <select v-model="formTerima.id_produk" class="input-pilihan select-tebal">
              <option v-for="p in daftarProduk" :key="p.id" :value="p.id">
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
            <label class="label-form">Pilih Produk yang Disesuaikan*</label>
            <select v-model="formSesuaikan.id_produk" class="input-pilihan select-tebal">
              <option v-for="p in daftarProduk" :key="p.id" :value="p.id">
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
            <label class="label-form">Pilih Produk yang Dihitung*</label>
            <select v-model="formOpname.id_produk" class="input-pilihan select-tebal" @change="padaGantiProdukOpname">
              <option v-for="p in daftarProduk" :key="p.id" :value="p.id">
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
              <tr v-for="m in riwayatPergerakan" :key="m.id" class="baris-mutasi">
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
              <tr v-if="riwayatPergerakan.length === 0">
                <td colspan="6" class="text-center p-8 teks-kosong">
                  <History :size="40" class="mb-2 teks-pudar" />
                  <div class="tebal">Belum Ada Riwayat Pergerakan Stok</div>
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
</style>
