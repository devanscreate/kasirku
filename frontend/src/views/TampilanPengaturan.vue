<script setup>
import { ref, onMounted } from 'vue'
import { panggilApi } from '../layanan/api'
import { Settings, Users, Store, Plus, Edit, Shield, Save, Check } from 'lucide-vue-next'

const tabPengaturan = ref('toko') // 'toko' | 'pengguna'
const toko = ref({
  nama: '',
  alamat: '',
  telepon: '',
  pengaturan: {
    pajak_persen: 0,
    tipe_pajak: 'inklusif',
    pembulatan: 0,
    max_diskon_kasir: 10,
    cash_diff_threshold: 50000,
    blind_close: true,
    lebar_kertas: 58
  }
})

const daftarUser = ref([])
const tampilModalUser = ref(false)
const sedangSimpan = ref(false)
const pesanSukses = ref('')
const pesanError = ref('')

const formUser = ref({
  nama_pengguna: '',
  kata_sandi: '',
  nama_lengkap: '',
  peran: 'kasir'
})

async function muatPengaturan() {
  try {
    const [dataToko, dataUser] = await Promise.all([
      panggilApi('/settings'),
      panggilApi('/users')
    ])
    toko.value = dataToko
    daftarUser.value = dataUser
  } catch (err) {
    pesanError.value = 'Gagal memuat pengaturan toko'
  }
}

onMounted(() => {
  muatPengaturan()
})

async function simpanToko() {
  sedangSimpan.value = true
  pesanSukses.value = ''
  pesanError.value = ''
  try {
    await panggilApi('/settings', {
      method: 'PUT',
      body: JSON.stringify(toko.value)
    })
    pesanSukses.value = 'Pengaturan toko berhasil disimpan'
  } catch (err) {
    pesanError.value = err.message || 'Gagal menyimpan profil toko'
  } finally {
    sedangSimpan.value = false
  }
}

async function simpanUserBaru() {
  if (!formUser.value.nama_pengguna || !formUser.value.kata_sandi || !formUser.value.nama_lengkap) {
    alert('Semua kolom pengguna wajib diisi!')
    return
  }

  try {
    await panggilApi('/users', {
      method: 'POST',
      body: JSON.stringify(formUser.value)
    })
    tampilModalUser.value = false
    formUser.value = { nama_pengguna: '', kata_sandi: '', nama_lengkap: '', peran: 'kasir' }
    await muatPengaturan()
    alert('Akun pengguna baru berhasil dibuat')
  } catch (err) {
    alert('Gagal membuat akun: ' + err.message)
  }
}
</script>

<template>
  <div class="halaman-pengaturan">
    <div class="panel-kartu">
      <!-- Header Pengaturan -->
      <div class="header-pengaturan">
        <div class="header-info">
          <div class="ikon-header">
            <Settings :size="26" />
          </div>
          <div>
            <h1 class="judul-halaman">Pengaturan Toko & Manajemen Pengguna</h1>
            <p class="sub-halaman">Konfigurasi profil toko, aturan pajak, batas diskon kasir, printer struk, dan manajemen hak akses karyawan.</p>
          </div>
        </div>
      </div>

      <!-- Tab Navigasi -->
      <div class="tab-pengaturan mt-4">
        <button 
          class="btn-tab tab-toko" 
          :class="{ 'aktif': tabPengaturan === 'toko' }" 
          @click="tabPengaturan = 'toko'"
        >
          <Store :size="18" />
          <span>Profil Toko & Aturan POS</span>
        </button>
        <button 
          class="btn-tab tab-karyawan" 
          :class="{ 'aktif': tabPengaturan === 'pengguna' }" 
          @click="tabPengaturan = 'pengguna'"
        >
          <Users :size="18" />
          <span>Kelola Akun Karyawan & Kasir</span>
        </button>
      </div>

      <div v-if="pesanSukses" class="pesan-sukses-box mt-3">✅ {{ pesanSukses }}</div>
      <div v-if="pesanError" class="peringatan-error mt-3">{{ pesanError }}</div>

      <!-- TAB PROFIL & ATURAN TOKO -->
      <div v-if="tabPengaturan === 'toko'" class="konten-tab mt-4">
        <form @submit.prevent="simpanToko" class="form-pengaturan">
          <div class="kartu-sub-pengaturan">
            <h3 class="judul-sub">🏪 Profil Usaha / Toko</h3>
            <div class="grup-form mt-3">
              <label class="label-form">Nama Toko (Tercetak di Kepala Struk)*</label>
              <input v-model="toko.nama" type="text" class="input-teks input-tebal" placeholder="Contoh: Toko Berkah Jaya" required />
            </div>
            <div class="grid-form mt-3">
              <div class="grup-form">
                <label class="label-form">Alamat Lengkap Toko</label>
                <input v-model="toko.alamat" type="text" class="input-teks" placeholder="Jl. Pasar Baru No. 12" />
              </div>
              <div class="grup-form">
                <label class="label-form">Nomor Telepon / WhatsApp Toko</label>
                <input v-model="toko.telepon" type="text" class="input-teks" placeholder="0812-3456-7890" />
              </div>
            </div>
          </div>

          <div class="kartu-sub-pengaturan mt-4">
            <h3 class="judul-sub">⚙️ Aturan Kasir & Transaksi POS</h3>
            <div class="grid-form mt-3">
              <div class="grup-form">
                <label class="label-form">Pajak Penjualan PPN (%)</label>
                <input v-model.number="toko.pengaturan.pajak_persen" type="number" min="0" max="100" class="input-teks font-angka input-tebal" />
                <span class="teks-keterangan">Contoh: 11 untuk PPN 11% (isi 0 jika bebas pajak)</span>
              </div>
              <div class="grup-form">
                <label class="label-form">Batas Maksimal Diskon Kasir (%)</label>
                <input v-model.number="toko.pengaturan.max_diskon_kasir" type="number" min="0" max="100" class="input-teks font-angka input-tebal" />
                <span class="teks-keterangan">Kasir tidak dapat memberi diskon melebihi persentase ini tanpa otorisasi.</span>
              </div>
            </div>

            <div class="grid-form mt-3">
              <div class="grup-form">
                <label class="label-form">Ambang Selisih Kas Laci Wajib Catatan (Rp)</label>
                <input v-model.number="toko.pengaturan.cash_diff_threshold" type="number" min="0" step="1000" class="input-teks font-angka input-tebal" />
                <span class="teks-keterangan">Jika selisih uang fisik saat tutup shift melewati angka ini, kasir wajib menuliskan alasan.</span>
              </div>
              <div class="grup-form">
                <label class="label-form">Lebar Kertas Cetak Struk Kasir</label>
                <select v-model.number="toko.pengaturan.lebar_kertas" class="input-pilihan select-tebal">
                  <option :value="58">58 mm (Printer Thermal Mini / Bluetooth)</option>
                  <option :value="80">80 mm (Printer Thermal Lebar / POS Kasir)</option>
                </select>
              </div>
            </div>

            <div class="grup-form mt-4 kotak-opsi-blind">
              <label class="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" v-model="toko.pengaturan.blind_close" class="checkbox-besar" />
                <div>
                  <span class="tebal teks-judul-opsi">Aktifkan Fitur Blind Close pada Tutup Shift</span>
                  <div class="teks-keterangan mt-1">Sistem menyembunyikan angka ekspektasi uang kas saat tutup shift, sehingga kasir wajib menghitung uang fisik secara jujur dan objektif.</div>
                </div>
              </label>
            </div>
          </div>

          <button type="submit" class="tombol-simpan-pengaturan mt-4" :disabled="sedangSimpan">
            <Save :size="18" />
            <span>{{ sedangSimpan ? 'Menyimpan...' : 'Simpan Semua Pengaturan Toko' }}</span>
          </button>
        </form>
      </div>

      <!-- TAB KELOLA PENGGUNA -->
      <div v-if="tabPengaturan === 'pengguna'" class="konten-tab mt-4">
        <div class="flex justify-between items-center mb-4">
          <div>
            <h3 class="judul-sub">Daftar Akun Pengguna & Karyawan</h3>
            <p class="sub-halaman">Kelola akun kasir, manajer, dan owner toko.</p>
          </div>
          <button class="tombol-tambah-user" @click="tampilModalUser = true">
            <Plus :size="16" />
            <span>+ Tambah Akun Karyawan</span>
          </button>
        </div>

        <div class="tabel-wadah">
          <table class="tabel-data">
            <thead>
              <tr>
                <th>Username Login</th>
                <th>Nama Lengkap</th>
                <th>Peran / Hak Akses</th>
                <th>Status Akun</th>
                <th>Terdaftar Sejak</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in daftarUser" :key="u.id" class="baris-user">
                <td><span class="font-angka tebal teks-username">👤 {{ u.nama_pengguna }}</span></td>
                <td><span class="tebal teks-nama-user">{{ u.nama_lengkap }}</span></td>
                <td>
                  <span 
                    class="badge-peran"
                    :class="{
                      'peran-owner': u.peran === 'owner',
                      'peran-manajer': u.peran === 'manajer',
                      'peran-kasir': u.peran === 'kasir'
                    }"
                  >
                    {{ u.peran === 'owner' ? '👑 Owner (Pemilik)' : (u.peran === 'manajer' ? '💼 Manajer' : '👤 Kasir') }}
                  </span>
                </td>
                <td>
                  <span class="badge-status-aktif" :class="u.status_aktif ? 'status-aktif' : 'status-nonaktif'">
                    {{ u.status_aktif ? 'Aktif' : 'Nonaktif' }}
                  </span>
                </td>
                <td class="teks-waktu">{{ new Date(u.dibuat_pada).toLocaleDateString('id-ID', { dateStyle: 'long' }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- MODAL BUAT PENGGUNA BARU -->
    <div v-if="tampilModalUser" class="latar-modal">
      <div class="kotak-modal p-6 modal-putih" style="max-width: 520px;">
        <div class="header-modal">
          <div>
            <div class="lencana-info mb-1">Manajemen Karyawan</div>
            <h2 class="judul-modal">Tambah Akun Karyawan Baru</h2>
          </div>
          <button class="tombol-tutup" @click="tampilModalUser = false"><X :size="20" /></button>
        </div>

        <div class="grup-form mt-4">
          <label class="label-form">Username Login Kasir*</label>
          <input v-model="formUser.nama_pengguna" type="text" class="input-teks input-tebal" placeholder="Contoh: kasir_sore" required />
        </div>
        <div class="grup-form mt-3">
          <label class="label-form">Kata Sandi (Password)*</label>
          <input v-model="formUser.kata_sandi" type="password" class="input-teks" placeholder="Minimal 6 huruf atau angka" required />
        </div>
        <div class="grup-form mt-3">
          <label class="label-form">Nama Lengkap Petugas*</label>
          <input v-model="formUser.nama_lengkap" type="text" class="input-teks input-tebal" placeholder="Contoh: Ahmad Fauzi" required />
        </div>
        <div class="grup-form mt-3">
          <label class="label-form">Peran & Tingkat Hak Akses*</label>
          <select v-model="formUser.peran" class="input-pilihan select-tebal">
            <option value="kasir">👤 Kasir (Buka/Tutup Shift, Transaksi Penjualan POS)</option>
            <option value="manajer">💼 Manajer (Void, Retur, Kelola Produk & Stok, Laporan)</option>
            <option value="owner">👑 Owner (Hak Akses Penuh & Kelola Semua Akun)</option>
          </select>
        </div>

        <div class="footer-aksi flex gap-3 mt-6">
          <button class="tombol tombol-sekunder flex-1" @click="tampilModalUser = false">Batal</button>
          <button class="tombol tombol-simpan-user flex-1" @click="simpanUserBaru">
            <Check :size="18" />
            <span>Buat Akun Sekarang</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.halaman-pengaturan {
  padding: 24px;
}

.panel-kartu {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
}

.header-pengaturan {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

/* Tabs */
.tab-pengaturan {
  display: flex;
  gap: 10px;
  border-bottom: 2px solid #f1f5f9;
  padding-bottom: 16px;
}

.btn-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
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

.tab-toko.aktif {
  background: #1e3a8a;
  border-color: #1e3a8a;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(30, 58, 138, 0.3);
}

.tab-karyawan.aktif {
  background: #7c3aed;
  border-color: #7c3aed;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
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
.form-pengaturan {
  max-width: 680px;
}

.kartu-sub-pengaturan {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-md);
  padding: 20px;
}

.judul-sub {
  font-size: 1.1rem;
  font-weight: 800;
  color: #0f172a;
}

.grid-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.input-tebal, .select-tebal {
  font-weight: 600;
  background: #ffffff;
  border: 1.5px solid #cbd5e1;
}

.teks-keterangan {
  font-size: 0.78rem;
  color: #64748b;
  display: block;
  margin-top: 4px;
  line-height: 1.4;
}

.kotak-opsi-blind {
  background: #ffffff;
  border: 1.5px solid #cbd5e1;
  border-radius: var(--radius-md);
  padding: 14px;
}

.checkbox-besar {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.teks-judul-opsi {
  color: #0f172a;
  font-size: 0.925rem;
}

.tombol-simpan-pengaturan {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 24px;
  background: #059669;
  border: none;
  border-radius: var(--radius-md);
  color: #ffffff;
  font-weight: 800;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3);
}

.tombol-simpan-pengaturan:hover {
  background: #047857;
}

/* User management */
.tombol-tambah-user {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 16px;
  background: #7c3aed;
  border: none;
  border-radius: var(--radius-md);
  color: #ffffff;
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tombol-tambah-user:hover {
  background: #6d28d9;
}

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

.baris-user:hover {
  background-color: #f8fafc;
}

.teks-username {
  color: #1e3a8a;
}

.teks-nama-user {
  color: #0f172a;
}

.badge-peran {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: 0.82rem;
  font-weight: 800;
}

.peran-owner {
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fcd34d;
}

.peran-manajer {
  background: #f3e8ff;
  color: #6b21a8;
  border: 1px solid #d8b4fe;
}

.peran-kasir {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.badge-status-aktif {
  display: inline-block;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.78rem;
  font-weight: 700;
}

.status-aktif {
  background: #f0fdf4;
  color: #16a34a;
}

.status-nonaktif {
  background: #f8fafc;
  color: #94a3b8;
}

.teks-waktu {
  color: #64748b;
  font-size: 0.85rem;
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

.lencana-info {
  display: inline-block;
  padding: 3px 8px;
  background: #eff6ff;
  color: #2563eb;
  font-weight: 700;
  font-size: 0.75rem;
  border-radius: var(--radius-sm);
}

.tombol-simpan-user {
  background: #7c3aed;
  color: #ffffff;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.tombol-simpan-user:hover {
  background: #6d28d9;
}

.font-angka { font-family: var(--font-angka); }
.tebal { font-weight: 700; }
.mt-6 { margin-top: 24px; }
.mt-4 { margin-top: 16px; }
.mt-3 { margin-top: 12px; }
.mt-1 { margin-top: 4px; }
.mb-4 { margin-bottom: 16px; }
.mb-1 { margin-bottom: 4px; }
.p-6 { padding: 24px; }
.flex { display: flex; }
.flex-1 { flex: 1; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.gap-3 { gap: 12px; }
.cursor-pointer { cursor: pointer; }
</style>
