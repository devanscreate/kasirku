<script setup>
import { ref, onMounted } from 'vue'
import { panggilApi } from '../layanan/api'
import { 
  BarChart3, 
  TrendingUp, 
  Download, 
  Calendar, 
  AlertTriangle, 
  CreditCard, 
  Users, 
  Package 
} from 'lucide-vue-next'

const ringkasan = ref(null)
const produkTerlaris = ref([])
const metodeBayar = ref([])
const performaKasir = ref([])
const stokMenipis = ref([])
const transaksiFlag = ref([])
const sedangMemuat = ref(false)

const formatRupiah = (val) => 'Rp ' + Number(val || 0).toLocaleString('id-ID')

async function muatLaporan() {
  sedangMemuat.value = true
  try {
    const [ring, prod, bayar, kasir, low, flag] = await Promise.all([
      panggilApi('/reports/summary'),
      panggilApi('/reports/products'),
      panggilApi('/reports/payments'),
      panggilApi('/reports/cashiers'),
      panggilApi('/reports/low-stock'),
      panggilApi('/reports/flagged')
    ])
    ringkasan.value = ring
    produkTerlaris.value = prod
    metodeBayar.value = bayar
    performaKasir.value = kasir
    stokMenipis.value = low
    transaksiFlag.value = flag
  } catch (err) {
    console.error('Gagal memuat laporan:', err)
  } finally {
    sedangMemuat.value = false
  }
}

onMounted(() => {
  muatLaporan()
})

function unduhCSV(tipe) {
  const token = localStorage.getItem('token_akses')
  window.open(`/api/v1/reports/export/csv?tipe=${tipe}`, '_blank')
}
</script>

<template>
  <div class="halaman-laporan">
    <div class="panel-kartu">
      <!-- Header Laporan -->
      <div class="header-laporan">
        <div class="header-info">
          <div class="ikon-header">
            <BarChart3 :size="26" />
          </div>
          <div>
            <h1 class="judul-halaman">Laporan Bisnis & Analitik Penjualan</h1>
            <p class="sub-halaman">Ringkasan pendapatan omzet toko, performa kasir, produk terlaris, dan audit transaksi.</p>
          </div>
        </div>
        <div class="flex gap-3">
          <button class="tombol-ekspor" @click="unduhCSV('penjualan')">
            <Download :size="15" />
            <span>Ekspor CSV</span>
          </button>
          <button class="tombol-perbarui" @click="muatLaporan" :disabled="sedangMemuat">
            <span>{{ sedangMemuat ? 'Memuat Data...' : 'Perbarui' }}</span>
          </button>
        </div>
      </div>

      <!-- KPI KARTU RINGKASAN MINIMALIS -->
      <div v-if="ringkasan" class="grid-kpi mt-5">
        <!-- KPI 1: OMZET BERSIH -->
        <div class="kartu-kpi kpi-hijau">
          <div class="kpi-atas">
            <span class="kpi-label teks-kpi-hijau">Omzet Bersih</span>
            <span class="kpi-tag tag-hijau">Bersih</span>
          </div>
          <div class="kpi-nilai font-angka teks-nilai-hijau">{{ formatRupiah(ringkasan.omzet_bersih) }}</div>
          <div class="kpi-sub">Total omzet kotor dikurangi refund retur</div>
        </div>

        <!-- KPI 2: OMZET KOTOR -->
        <div class="kartu-kpi kpi-biru">
          <div class="kpi-atas">
            <span class="kpi-label teks-kpi-biru">Omzet Kotor</span>
            <span class="kpi-tag tag-biru">{{ ringkasan.total_transaksi_berhasil }} Struk</span>
          </div>
          <div class="kpi-nilai font-angka teks-nilai-biru">{{ formatRupiah(ringkasan.total_omzet_kotor) }}</div>
          <div class="kpi-sub">Total transaksi sebelum refund</div>
        </div>

        <!-- KPI 3: TOTAL DISKON -->
        <div class="kartu-kpi kpi-oranye">
          <div class="kpi-atas">
            <span class="kpi-label teks-kpi-oranye">Potongan Diskon</span>
            <span class="kpi-tag tag-oranye">Promo</span>
          </div>
          <div class="kpi-nilai font-angka teks-nilai-oranye">{{ formatRupiah(ringkasan.total_diskon) }}</div>
          <div class="kpi-sub">Total potongan diskon penjualan</div>
        </div>

        <!-- KPI 4: TOTAL REFUND -->
        <div class="kartu-kpi kpi-merah">
          <div class="kpi-atas">
            <span class="kpi-label teks-kpi-merah">Pengembalian (Refund)</span>
            <span class="kpi-tag tag-merah">{{ ringkasan.total_transaksi_retur }} Retur</span>
          </div>
          <div class="kpi-nilai font-angka teks-nilai-merah">{{ formatRupiah(ringkasan.total_refund) }}</div>
          <div class="kpi-sub">Total uang kas keluar untuk retur</div>
        </div>
      </div>

      <!-- 2 KOLOM: METODE BAYAR & PRODUK TERLARIS -->
      <div class="grid-2-kolom mt-6">
        <!-- Metode Pembayaran -->
        <div class="kartu-bagian">
          <div class="header-bagian">
            <div>
              <h3 class="judul-bagian">Penjualan per Cara Bayar</h3>
              <p class="sub-bagian">Distribusi metode transaksi tunai, QRIS, & transfer</p>
            </div>
          </div>
          <table class="tabel-mini mt-3">
            <thead>
              <tr>
                <th>Metode Bayar</th>
                <th>Total Struk</th>
                <th class="text-right">Nominal Masuk</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in metodeBayar" :key="m.metode" class="baris-tabel">
                <td>
                  <span class="badge-metode" :class="m.metode.toLowerCase()">
                    {{ m.metode === 'tunai' ? 'Tunai' : (m.metode === 'qris' ? 'QRIS' : m.metode.toUpperCase()) }}
                  </span>
                </td>
                <td class="font-angka">{{ m.jumlah_transaksi }} Transaksi</td>
                <td class="font-angka tebal teks-uang-tabel text-right">{{ formatRupiah(m.total_nominal) }}</td>
              </tr>
              <tr v-if="metodeBayar.length === 0">
                <td colspan="3" class="text-center teks-redup p-6">Belum ada transaksi tercatat</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Penjualan per Kasir -->
        <div class="kartu-bagian">
          <div class="header-bagian">
            <div class="ikon-bagian ikon-ungu"><Users :size="18" /></div>
            <div>
              <h3 class="judul-bagian">Performa Penjualan Kasir</h3>
              <p class="sub-bagian">Pencapaian omzet masing-masing petugas kasir</p>
            </div>
          </div>
          <table class="tabel-mini mt-3">
            <thead>
              <tr>
                <th>Nama Petugas</th>
                <th>Struk Dilayani</th>
                <th class="text-right">Total Penjualan</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="k in performaKasir" :key="k.id_kasir" class="baris-tabel">
                <td>
                  <span class="badge-petugas">{{ k.nama_kasir }}</span>
                </td>
                <td class="font-angka">{{ k.total_transaksi }} Struk</td>
                <td class="font-angka tebal teks-sukses text-right">{{ formatRupiah(k.total_omzet) }}</td>
              </tr>
              <tr v-if="performaKasir.length === 0">
                <td colspan="3" class="text-center teks-redup p-6">Belum ada transaksi kasir</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- PRODUK TERLARIS -->
      <div class="kartu-bagian mt-6">
        <div class="header-bagian">
          <div class="ikon-bagian ikon-hijau"><TrendingUp :size="18" /></div>
          <div>
            <h3 class="judul-bagian">Peringkat Produk Terlaris (Top Selling Items)</h3>
            <p class="sub-bagian">Barang dagangan yang paling banyak diminati oleh konsumen</p>
          </div>
        </div>
        <table class="tabel-mini mt-3">
          <thead>
            <tr>
              <th style="width: 50px;">No.</th>
              <th>Kode SKU</th>
              <th>Nama Produk Barang</th>
              <th>Total Terjual</th>
              <th class="text-right">Pendapatan Dihasilkan</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(p, index) in produkTerlaris" :key="p.id_produk" class="baris-tabel">
              <td>
                <span class="badge-peringkat" :class="'peringkat-' + (index + 1)">
                  {{ index === 0 ? '🥇 1' : (index === 1 ? '🥈 2' : (index === 2 ? '🥉 3' : (index + 1))) }}
                </span>
              </td>
              <td><span class="font-angka teks-sku">{{ p.sku }}</span></td>
              <td><span class="tebal teks-nama-item">{{ p.nama_produk }}</span></td>
              <td><span class="pill-terjual font-angka">{{ p.total_kuantitas }} Unit Terjual</span></td>
              <td class="font-angka tebal teks-sukses text-right">{{ formatRupiah(p.total_pendapatan) }}</td>
            </tr>
            <tr v-if="produkTerlaris.length === 0">
              <td colspan="5" class="text-center teks-redup p-6">Belum ada produk yang terjual</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- AUDIT ANOMALI TRANSAKSI BERFLAG -->
      <div class="kartu-bagian mt-6 kartu-anomali" v-if="transaksiFlag.length > 0">
        <div class="header-bagian teks-bahaya">
          <div class="ikon-bagian ikon-merah"><AlertTriangle :size="18" /></div>
          <div>
            <h3 class="judul-bagian">Peringatan Audit Anomali Transaksi (Butuh Tinjauan Manajer)</h3>
            <p class="sub-bagian">Deteksi struk mencurigakan: diskon tinggi, void berulang, atau transaksi janggal</p>
          </div>
        </div>
        <table class="tabel-mini mt-3">
          <thead>
            <tr>
              <th>No. Struk</th>
              <th>Kasir</th>
              <th>Waktu Transaksi</th>
              <th>Penyebab Flag Anomali</th>
              <th class="text-right">Total Transaksi</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in transaksiFlag" :key="f.id" class="baris-tabel">
              <td><span class="font-angka tebal teks-struk-flag">{{ f.nomor_struk }}</span></td>
              <td>{{ f.nama_kasir }}</td>
              <td class="teks-waktu">{{ new Date(f.waktu_transaksi).toLocaleString('id-ID') }}</td>
              <td>
                <span v-for="(v, k) in f.flag" :key="k" class="badge-flag-bahaya mr-1">
                  {{ k }}
                </span>
              </td>
              <td class="font-angka tebal text-right">{{ formatRupiah(f.total) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- STOK MENIPIS -->
      <div class="kartu-bagian mt-6 kartu-stok-menipis" v-if="stokMenipis.length > 0">
        <div class="header-bagian teks-peringatan">
          <div class="ikon-bagian ikon-oranye"><Package :size="18" /></div>
          <div>
            <h3 class="judul-bagian">Peringatan: Stok Barang Menipis (Segera Pesan ke Supplier)</h3>
            <p class="sub-bagian">Daftar produk yang stok fisiknya sudah berada di bawah atau sama dengan batas minimum</p>
          </div>
        </div>
        <table class="tabel-mini mt-3">
          <thead>
            <tr>
              <th>Kode SKU</th>
              <th>Nama Produk</th>
              <th>Kategori</th>
              <th>Sisa Stok Saat Ini</th>
              <th>Batas Min. Stok Toko</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in stokMenipis" :key="s.id_produk" class="baris-tabel">
              <td><span class="font-angka teks-sku">{{ s.sku }}</span></td>
              <td><span class="tebal teks-nama-item">{{ s.nama_produk }}</span></td>
              <td><span class="badge-kategori">{{ s.kategori || 'Umum' }}</span></td>
              <td><span class="badge-stok-habis font-angka">{{ s.stok_sekarang }} Unit</span></td>
              <td class="font-angka">{{ s.min_stok }} Unit</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.halaman-laporan {
  padding: 24px;
}

.panel-kartu {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
}

.header-laporan {
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

.tombol-ekspor {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: #ffffff;
  border: 1.5px solid #e2e8f0;
  border-radius: var(--radius-md);
  color: #475569;
  font-weight: 700;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tombol-ekspor:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #2563eb;
}

.tombol-perbarui {
  padding: 10px 18px;
  background: #2563eb;
  border: 1px solid #1d4ed8;
  border-radius: var(--radius-md);
  color: #ffffff;
  font-weight: 700;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.tombol-perbarui:hover {
  background: #1d4ed8;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
}

/* KPI Cards with High Contrast & Color Coding */
.grid-kpi {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 16px;
}

.kartu-kpi {
  border-radius: var(--radius-lg);
  padding: 20px;
  border: 1.5px solid transparent;
  transition: transform 0.15s ease;
}

.kartu-kpi:hover {
  transform: translateY(-2px);
}

.kpi-hijau {
  background: #f0fdf4;
  border-color: #86efac;
}

.kpi-biru {
  background: #eff6ff;
  border-color: #93c5fd;
}

.kpi-oranye {
  background: #fffbeb;
  border-color: #fde68a;
}

.kpi-merah {
  background: #fef2f2;
  border-color: #fca5a5;
}

.kpi-atas {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.kpi-label {
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.teks-kpi-hijau { color: #166534; }
.teks-kpi-biru { color: #1e40af; }
.teks-kpi-oranye { color: #92400e; }
.teks-kpi-merah { color: #991b1b; }

.kpi-tag {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 9999px;
}

.tag-hijau { background: #dcfce7; color: #15803d; }
.tag-biru { background: #dbeafe; color: #1d4ed8; }
.tag-oranye { background: #fef3c7; color: #b45309; }
.tag-merah { background: #fee2e2; color: #b91c1c; }

.kpi-nilai {
  font-size: 1.7rem;
  font-weight: 800;
  margin: 8px 0 4px;
}

.teks-nilai-hijau { color: #15803d; }
.teks-nilai-biru { color: #1e3a8a; }
.teks-nilai-oranye { color: #d97706; }
.teks-nilai-merah { color: #dc2626; }

.kpi-sub {
  font-size: 0.8rem;
  color: #64748b;
}

/* Sections */
.grid-2-kolom {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 900px) {
  .grid-2-kolom { grid-template-columns: 1fr; }
}

.kartu-bagian {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
}

.kartu-anomali {
  border-color: #fca5a5;
  background: #fffafa;
}

.kartu-stok-menipis {
  border-color: #fde68a;
  background: #fffdfa;
}

.header-bagian {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ikon-bagian {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ikon-biru { background: #eff6ff; color: #2563eb; }
.ikon-ungu { background: #f3e8ff; color: #7c3aed; }
.ikon-hijau { background: #f0fdf4; color: #16a34a; }
.ikon-oranye { background: #fffbeb; color: #d97706; }
.ikon-merah { background: #fef2f2; color: #dc2626; }

.judul-bagian {
  font-size: 1.05rem;
  font-weight: 800;
  color: #0f172a;
}

.sub-bagian {
  font-size: 0.8rem;
  color: #64748b;
}

/* Tables */
.tabel-mini {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.tabel-mini th {
  padding: 12px 14px;
  background: #f1f5f9;
  color: #1e293b;
  font-weight: 800;
  border-bottom: 2px solid #e2e8f0;
  text-align: left;
}

.tabel-mini td {
  padding: 12px 14px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.baris-tabel:hover {
  background-color: #f8fafc;
}

.badge-metode {
  display: inline-block;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-weight: 700;
  font-size: 0.825rem;
  background: #f1f5f9;
  color: #1e293b;
}

.teks-uang-tabel {
  color: #059669;
}

.badge-petugas {
  display: inline-block;
  padding: 4px 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-sm);
  font-weight: 600;
  color: #334155;
}

.badge-peringkat {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 9999px;
  font-weight: 800;
  font-size: 0.85rem;
  background: #f1f5f9;
}

.teks-sku {
  color: #1e3a8a;
  font-weight: 600;
}

.teks-nama-item {
  color: #0f172a;
}

.pill-terjual {
  display: inline-block;
  padding: 3px 10px;
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 9999px;
  font-weight: 700;
  font-size: 0.8rem;
}

.badge-flag-bahaya {
  display: inline-block;
  padding: 2px 8px;
  background: #fee2e2;
  color: #b91c1c;
  border-radius: var(--radius-sm);
  font-size: 0.78rem;
  font-weight: 700;
}

.badge-stok-habis {
  display: inline-block;
  padding: 3px 10px;
  background: #fee2e2;
  color: #b91c1c;
  border-radius: 9999px;
  font-weight: 800;
  font-size: 0.825rem;
}

.badge-kategori {
  display: inline-block;
  padding: 3px 8px;
  background: #f1f5f9;
  border-radius: var(--radius-sm);
  color: #475569;
  font-size: 0.8rem;
}

.teks-struk-flag {
  color: #b91c1c;
}

.teks-waktu {
  color: #64748b;
  font-size: 0.825rem;
}

.font-angka { font-family: var(--font-angka); }
.tebal { font-weight: 700; }
.uppercase { text-transform: uppercase; }
.text-right { text-align: right; }
.teks-sukses { color: #16a34a; }
.teks-peringatan { color: #d97706; }
.teks-bahaya { color: #dc2626; }
.teks-redup { color: #64748b; }
.mt-6 { margin-top: 24px; }
.mt-5 { margin-top: 20px; }
.mt-3 { margin-top: 12px; }
.p-6 { padding: 24px; }
.mr-1 { margin-right: 4px; }
.flex { display: flex; }
.gap-3 { gap: 12px; }
</style>
