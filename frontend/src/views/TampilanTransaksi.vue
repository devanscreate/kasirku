<script setup>
import { ref, onMounted, computed } from 'vue'
import { dbLokal } from '../basis_data'
import { panggilApi } from '../layanan/api'
import { useAuthStore } from '../stores/auth'
import { useShiftStore } from '../stores/shift'
import { cetakStrukTransaksi } from '../layanan/pencetak_struk'

import { 
  Receipt, 
  Search, 
  Printer, 
  Ban, 
  RotateCcw, 
  Eye, 
  X, 
  Check, 
  AlertCircle 
} from 'lucide-vue-next'

const authStore = useAuthStore()
const shiftStore = useShiftStore()

const daftarTransaksi = ref([])
const sedangMemuat = ref(false)
const kueriCari = ref('')
const filterStatus = ref('semua')

const transaksiTerpilih = ref(null)
const tampilModalDetail = ref(false)
const tampilModalVoid = ref(false)
const tampilModalRetur = ref(false)

const alasanVoid = ref('')
const alasanRetur = ref('')
const metodeRefund = ref('tunai')
const itemReturDipilih = ref([])
const pesanError = ref('')
const sedangAksi = ref(false)

const formatRupiah = (val) => 'Rp ' + Number(val || 0).toLocaleString('id-ID')

async function muatTransaksi() {
  sedangMemuat.value = true
  try {
    if (navigator.onLine) {
      const dataServer = await panggilApi('/sales')
      daftarTransaksi.value = dataServer
    } else {
      // Ambil transaksi lokal IndexedDB jika offline
      const dataLokal = await dbLokal.penjualan.orderBy('dibuat_pada').reverse().toArray()
      daftarTransaksi.value = dataLokal
    }
  } catch (err) {
    console.warn('Menggunakan data transaksi lokal:', err)
    const dataLokal = await dbLokal.penjualan.orderBy('dibuat_pada').reverse().toArray()
    daftarTransaksi.value = dataLokal
  } finally {
    sedangMemuat.value = false
  }
}

onMounted(() => {
  muatTransaksi()
})

const transaksiTerfilter = computed(() => {
  let list = daftarTransaksi.value
  if (filterStatus.value !== 'semua') {
    list = list.filter(t => t.status === filterStatus.value)
  }
  if (kueriCari.value.trim()) {
    const q = kueriCari.value.toLowerCase().trim()
    list = list.filter(t => t.nomor_struk.toLowerCase().includes(q))
  }
  return list
})

function bukaDetail(tx) {
  transaksiTerpilih.value = tx
  tampilModalDetail.value = true
}

function cetakSalinan(tx) {
  cetakStrukTransaksi(tx, {}, true)
}

function bukaModalVoid(tx) {
  transaksiTerpilih.value = tx
  alasanVoid.value = ''
  pesanError.value = ''
  tampilModalVoid.value = true
}

async function eksekusiVoid() {
  if (alasanVoid.value.trim().length < 5) {
    pesanError.value = 'Alasan void minimal 5 karakter (F-07)'
    return
  }

  sedangAksi.value = true
  pesanError.value = ''

  try {
    const hasil = await panggilApi(`/sales/${transaksiTerpilih.value.id}/void`, {
      method: 'POST',
      body: JSON.stringify({ alasan: alasanVoid.value })
    })

    // Update status lokal
    transaksiTerpilih.value.status = 'voided'
    tampilModalVoid.value = false
    await muatTransaksi()
    alert('Transaksi berhasil dibatalkan (VOID)')
  } catch (err) {
    pesanError.value = err.message || 'Gagal membatalkan transaksi'
  } finally {
    sedangAksi.value = false
  }
}

function bukaModalRetur(tx) {
  transaksiTerpilih.value = tx
  alasanRetur.value = ''
  pesanError.value = ''
  
  // Inisialisasi item retur
  itemReturDipilih.value = (tx.item || []).map(it => ({
    id_produk: it.id_produk,
    nama: it.nama_produk_snapshot || it.nama,
    harga: it.harga_snapshot || it.harga,
    qty_maks: it.kuantitas,
    qty_retur: 1,
    apakah_stok_kembali: true,
    dipilih: false
  }))

  tampilModalRetur.value = true
}

async function eksekusiRetur() {
  const itemAktif = itemReturDipilih.value.filter(it => it.dipilih && it.qty_retur > 0)
  if (itemAktif.length === 0) {
    pesanError.value = 'Pilih minimal satu item yang ingin diretur'
    return
  }
  if (!alasanRetur.value.trim()) {
    pesanError.value = 'Alasan retur wajib diisi'
    return
  }
  if (!shiftStore.shiftAktif) {
    pesanError.value = 'Anda harus memiliki shift kasir yang terbuka untuk memproses refund tunai'
    return
  }

  sedangAksi.value = true
  pesanError.value = ''

  try {
    const payload = {
      id: crypto.randomUUID(),
      id_penjualan: transaksiTerpilih.value.id,
      id_shift: shiftStore.shiftAktif.id,
      alasan: alasanRetur.value,
      metode_pengembalian: metodeRefund.value,
      item: itemAktif.map(it => ({
        id_produk: it.id_produk,
        kuantitas: it.qty_retur,
        apakah_stok_kembali: it.apakah_stok_kembali
      }))
    }

    const hasil = await panggilApi('/returns', {
      method: 'POST',
      body: JSON.stringify(payload)
    })

    tampilModalRetur.value = false
    await muatTransaksi()
    alert(`Retur berhasil diproses. Total pengembalian: ${formatRupiah(hasil.total_pengembalian)}`)
  } catch (err) {
    pesanError.value = err.message || 'Gagal memproses retur'
  } finally {
    sedangAksi.value = false
  }
}

const countStatus = computed(() => {
  const counts = { semua: daftarTransaksi.value.length, completed: 0, voided: 0, retur: 0 }
    for (const t of daftarTransaksi.value) {
      if (t.status === 'completed') counts.completed++
      else if (t.status === 'voided') counts.voided++
      else if (t.status === 'partially_refunded' || t.status === 'refunded') counts.retur++
    }
    return counts
  })

  function teksStatus(status) {
    switch (status) {
      case 'completed': return 'Selesai'
      case 'voided': return 'Batal (Void)'
      case 'partially_refunded': return 'Retur Sebagian'
      case 'refunded': return 'Retur Total'
      default: return status ? status.toUpperCase() : '-'
    }
  }

  function teksSinkron(status) {
    switch (status) {
      case 'synced': return 'Tersinkron'
      case 'pending': return 'Menunggu'
      case 'failed': return 'Gagal Sinkron'
      default: return 'Tersinkron'
    }
  }
</script>

<template>
  <div class="halaman-transaksi">
    <div class="panel-kartu">
      <!-- Header Halaman -->
      <div class="header-transaksi">
        <div class="header-info">
          <div class="ikon-header">
            <Receipt :size="26" />
          </div>
          <div>
            <h1 class="judul-halaman">Riwayat Transaksi Penjualan</h1>
            <p class="sub-halaman">Pantau seluruh struk kasir, cetak ulang struk fisik, proses void, dan retur barang.</p>
          </div>
        </div>
        <button class="tombol-segarkan" @click="muatTransaksi" :disabled="sedangMemuat">
          <RotateCcw :size="16" :class="{ 'animasi-putar': sedangMemuat }" />
          <span>{{ sedangMemuat ? 'Memuat...' : 'Segarkan Data' }}</span>
        </button>
      </div>

      <!-- Quick Filter Pills (Ramah Usia 40: 1 Klik Langsung Paham) -->
      <div class="wadah-filter-cepat mt-4">
        <button 
          class="pill-filter" 
          :class="{ 'aktif': filterStatus === 'semua' }"
          @click="filterStatus = 'semua'"
        >
          <span>Semua Transaksi</span>
          <span class="badge-hitung">{{ countStatus.semua }}</span>
        </button>

        <button 
          class="pill-filter pill-sukses" 
          :class="{ 'aktif': filterStatus === 'completed' }"
          @click="filterStatus = 'completed'"
        >
          <Check :size="16" />
          <span>Selesai</span>
          <span class="badge-hitung">{{ countStatus.completed }}</span>
        </button>

        <button 
          class="pill-filter pill-bahaya" 
          :class="{ 'aktif': filterStatus === 'voided' }"
          @click="filterStatus = 'voided'"
        >
          <Ban :size="16" />
          <span>Batal (Void)</span>
          <span class="badge-hitung">{{ countStatus.voided }}</span>
        </button>

        <button 
          class="pill-filter pill-peringatan" 
          :class="{ 'aktif': filterStatus === 'partially_refunded' || filterStatus === 'refunded' }"
          @click="filterStatus = (filterStatus === 'partially_refunded' ? 'semua' : 'partially_refunded')"
        >
          <RotateCcw :size="16" />
          <span>Retur / Refund</span>
          <span class="badge-hitung">{{ countStatus.retur }}</span>
        </button>
      </div>

      <!-- Filter Pencarian -->
      <div class="bar-filter mt-3">
        <div class="input-cari-wrap">
          <Search :size="18" class="ikon-cari" />
          <input 
            v-model="kueriCari" 
            type="text" 
            class="input-teks input-cari" 
            placeholder="Ketik nomor struk untuk mencari (contoh: STR-2026...)" 
          />
        </div>
      </div>

      <!-- Tabel Transaksi -->
      <div class="tabel-wadah mt-4">
        <table class="tabel-data">
          <thead>
            <tr>
              <th>No. Struk</th>
              <th>Waktu Transaksi</th>
              <th>Kasir Bertugas</th>
              <th>Total Pembayaran</th>
              <th>Status Transaksi</th>
              <th>Sinkron Cloud</th>
              <th class="text-center">Aksi Cepat</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tx in transaksiTerfilter" :key="tx.id" class="baris-transaksi">
              <td>
                <span class="font-angka tebal teks-struk">{{ tx.nomor_struk }}</span>
              </td>
              <td class="teks-waktu">
                {{ new Date(tx.waktu_transaksi).toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' }) }}
              </td>
              <td>
                <span class="badge-kasir">
                  👤 {{ tx.nama_kasir || 'Kasir' }}
                </span>
              </td>
              <td>
                <span class="font-angka tebal teks-total-uang">{{ formatRupiah(tx.total) }}</span>
              </td>
              <td>
                <span 
                  class="lencana-status"
                  :class="{
                    'status-selesai': tx.status === 'completed',
                    'status-batal': tx.status === 'voided',
                    'status-retur': tx.status === 'partially_refunded' || tx.status === 'refunded'
                  }"
                >
                  <Check v-if="tx.status === 'completed'" :size="14" />
                  <Ban v-else-if="tx.status === 'voided'" :size="14" />
                  <RotateCcw v-else :size="14" />
                  <span>{{ teksStatus(tx.status) }}</span>
                </span>
              </td>
              <td>
                <span 
                  class="lencana-sync"
                  :class="tx.status_sinkron === 'synced' || !tx.status_sinkron ? 'sync-oke' : (tx.status_sinkron === 'failed' ? 'sync-gagal' : 'sync-tunggu')"
                >
                  {{ teksSinkron(tx.status_sinkron) }}
                </span>
              </td>
              <td>
                <div class="aksi-baris justify-center">
                  <!-- Detail -->
                  <button class="btn-aksi btn-detail" @click="bukaDetail(tx)" title="Lihat Rincian Struk">
                    <Eye :size="15" />
                    <span>Rincian</span>
                  </button>

                  <!-- Cetak Ulang -->
                  <button class="btn-aksi btn-cetak" @click="cetakSalinan(tx)" title="Cetak Ulang Struk Kertas">
                    <Printer :size="15" />
                    <span>Cetak</span>
                  </button>

                  <!-- Void (Khusus Manajer/Owner) -->
                  <button 
                    v-if="authStore.punyaAkses(['manajer', 'owner']) && tx.status === 'completed'"
                    class="btn-aksi btn-void" 
                    @click="bukaModalVoid(tx)" 
                    title="Batalkan Transaksi Ini (Void)"
                  >
                    <Ban :size="15" />
                    <span>Void</span>
                  </button>

                  <!-- Retur (Khusus Manajer/Owner) -->
                  <button 
                    v-if="authStore.punyaAkses(['manajer', 'owner']) && (tx.status === 'completed' || tx.status === 'partially_refunded')"
                    class="btn-aksi btn-retur" 
                    @click="bukaModalRetur(tx)" 
                    title="Retur / Kembalikan Barang"
                  >
                    <RotateCcw :size="15" />
                    <span>Retur</span>
                  </button>
                </div>
              </td>
            </tr>

            <tr v-if="transaksiTerfilter.length === 0">
              <td colspan="7" class="text-center p-8 teks-kosong">
                <Receipt :size="40" class="mb-2 teks-pudar" />
                <div class="tebal">Tidak Ada Transaksi Ditemukan</div>
                <div class="sub-kosong">Silakan ubah filter status atau kata kunci pencarian Anda.</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- MODAL DETAIL STRUK -->
    <div v-if="tampilModalDetail && transaksiTerpilih" class="latar-modal">
      <div class="kotak-modal p-6 modal-putih">
        <div class="header-modal">
          <div>
            <div class="lencana-info mb-1">Rincian Transaksi Kasir</div>
            <h2 class="judul-modal">{{ transaksiTerpilih.nomor_struk }}</h2>
            <div class="sub-modal">
              {{ new Date(transaksiTerpilih.waktu_transaksi).toLocaleString('id-ID', { dateStyle: 'full', timeStyle: 'medium' }) }}
            </div>
          </div>
          <button class="tombol-tutup" @click="tampilModalDetail = false"><X :size="20" /></button>
        </div>

        <div class="daftar-item-modal">
          <div v-for="it in (transaksiTerpilih.item || [])" :key="it.id" class="baris-detail-item">
            <div>
              <div class="tebal teks-nama-item">{{ it.nama_produk_snapshot || it.nama }}</div>
              <div class="teks-redup">{{ it.kuantitas }} x {{ formatRupiah(it.harga_snapshot || it.harga) }}</div>
            </div>
            <div class="tebal font-angka teks-subtotal">{{ formatRupiah(it.subtotal_baris || (it.kuantitas * it.harga)) }}</div>
          </div>
        </div>

        <div class="kartu-ringkasan mt-4">
          <div class="flex-between"><span>Subtotal Produk:</span><span class="font-angka">{{ formatRupiah(transaksiTerpilih.subtotal) }}</span></div>
          <div v-if="transaksiTerpilih.diskon > 0" class="flex-between teks-peringatan">
            <span>Potongan Diskon:</span><span class="font-angka">-{{ formatRupiah(transaksiTerpilih.diskon) }}</span>
          </div>
          <div v-if="transaksiTerpilih.pajak > 0" class="flex-between"><span>Pajak (PPN):</span><span class="font-angka">+{{ formatRupiah(transaksiTerpilih.pajak) }}</span></div>
          <div class="flex-between tebal pembatas-atas">
            <span>TOTAL DIBAYAR:</span>
            <span class="font-angka teks-total-besar">{{ formatRupiah(transaksiTerpilih.total) }}</span>
          </div>
          <div class="flex-between mt-1 teks-redup" style="font-size: 0.8rem;">
            <span>Metode Bayar:</span>
            <span class="tebal uppercase" style="color: var(--warna-primer);">{{ transaksiTerpilih.metode_pembayaran || 'TUNAI' }}</span>
          </div>
        </div>

        <div class="footer-aksi mt-4 flex gap-3">
          <button class="tombol tombol-sekunder flex-1" @click="tampilModalDetail = false">Tutup</button>
          <button class="tombol tombol-cetak-struk flex-1" @click="cetakSalinan(transaksiTerpilih)">
            <Printer :size="18" />
            <span>Cetak Ulang Struk</span>
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL VOID (F-07) -->
    <div v-if="tampilModalVoid && transaksiTerpilih" class="latar-modal">
      <div class="kotak-modal p-6 modal-putih">
        <div class="header-modal">
          <div>
            <h2 class="judul-modal teks-bahaya flex items-center gap-2">
              <Ban :size="22" />
              <span>Void / Batalkan Transaksi</span>
            </h2>
            <p class="sub-modal">Nomor Struk: <b>{{ transaksiTerpilih.nomor_struk }}</b></p>
          </div>
          <button class="tombol-tutup" @click="tampilModalVoid = false"><X :size="20" /></button>
        </div>

        <div v-if="pesanError" class="peringatan-error">{{ pesanError }}</div>

        <div class="kotak-peringatan-bahaya">
          ⚠️ <b>Perhatian Kasir:</b> Tindakan Void membatalkan transaksi secara permanen. Stok produk akan dikembalikan ke gudang secara otomatis dan nilai transaksi akan dikeluarkan dari omzet penjualan.
        </div>

        <div class="grup-form mt-4">
          <label class="label-form">Alasan Pembatalan / Void (Wajib diisi, min. 5 huruf)*</label>
          <textarea 
            v-model="alasanVoid" 
            class="input-teks input-area" 
            rows="3" 
            placeholder="Contoh: Pelanggan salah membawa barang dan membatalkan transaksi..."
            autofocus
          ></textarea>
        </div>

        <div class="footer-aksi flex gap-3 mt-4">
          <button class="tombol tombol-sekunder flex-1" @click="tampilModalVoid = false">Batal</button>
          <button 
            class="tombol tombol-bahaya flex-1" 
            :disabled="sedangAksi || alasanVoid.trim().length < 5"
            @click="eksekusiVoid"
          >
            {{ sedangAksi ? 'Memproses...' : 'Ya, Batalkan Transaksi (VOID)' }}
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL RETUR (F-08) -->
    <div v-if="tampilModalRetur && transaksiTerpilih" class="latar-modal">
      <div class="kotak-modal p-6 modal-putih" style="max-width: 620px;">
        <div class="header-modal">
          <div>
            <h2 class="judul-modal teks-peringatan flex items-center gap-2">
              <RotateCcw :size="22" />
              <span>Retur Barang Penjualan</span>
            </h2>
            <p class="sub-modal">Struk Referensi: <b>{{ transaksiTerpilih.nomor_struk }}</b></p>
          </div>
          <button class="tombol-tutup" @click="tampilModalRetur = false"><X :size="20" /></button>
        </div>

        <div v-if="pesanError" class="peringatan-error">{{ pesanError }}</div>

        <div class="label-form mb-2">Pilih Item yang Ingin Dikembalikan / Diretur:</div>
        <div class="daftar-item-retur">
          <div v-for="it in itemReturDipilih" :key="it.id_produk" class="item-retur-baris">
            <input type="checkbox" v-model="it.dipilih" class="checkbox-retur" />
            <div class="flex-1 ml-2">
              <div class="tebal teks-nama-item">{{ it.nama }}</div>
              <div class="teks-redup">Maksimal retur: {{ it.qty_maks }} unit</div>
            </div>
            <div class="flex items-center gap-2">
              <label class="teks-redup">Qty:</label>
              <input 
                type="number" 
                v-model.number="it.qty_retur" 
                :max="it.qty_maks" 
                min="1" 
                class="input-teks w-16 text-center input-qty-retur" 
                :disabled="!it.dipilih"
              />
            </div>
            <div class="flex items-center gap-1 ml-3">
              <input type="checkbox" v-model="it.apakah_stok_kembali" :disabled="!it.dipilih" />
              <label class="text-xs teks-redup">Kembalikan ke Stok</label>
            </div>
          </div>
        </div>

        <div class="grup-form mt-4">
          <label class="label-form">Alasan Retur / Pengembalian*</label>
          <input v-model="alasanRetur" type="text" class="input-teks" placeholder="Contoh: Kemasan produk cacat atau sudah kedaluwarsa..." />
        </div>

        <div class="grup-form mt-3">
          <label class="label-form">Metode Pengembalian Uang (Refund)</label>
          <select v-model="metodeRefund" class="input-pilihan">
            <option value="tunai">💵 Tunai dari Kas Laci Kasir Aktif</option>
            <option value="transfer">💳 Transfer Bank / Rekening</option>
          </select>
        </div>

        <div class="footer-aksi flex gap-3 mt-4">
          <button class="tombol tombol-sekunder flex-1" @click="tampilModalRetur = false">Batal</button>
          <button 
            class="tombol tombol-proses-retur flex-1" 
            :disabled="sedangAksi"
            @click="eksekusiRetur"
          >
            {{ sedangAksi ? 'Memproses...' : 'Konfirmasi & Proses Retur' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.halaman-transaksi {
  padding: 24px;
}

.panel-kartu {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
}

.header-transaksi {
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

.tombol-segarkan {
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

.tombol-segarkan:hover {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #1d4ed8;
}

.animasi-putar {
  animation: putar 1s linear infinite;
}

@keyframes putar {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Quick Filter Pills */
.wadah-filter-cepat {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.pill-filter {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #f8fafc;
  border: 1.5px solid #cbd5e1;
  border-radius: 9999px;
  color: #334155;
  font-weight: 700;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pill-filter:hover {
  background: #e2e8f0;
  border-color: #94a3b8;
}

.pill-filter.aktif {
  background: #1e3a8a;
  border-color: #1e3a8a;
  color: #ffffff;
  box-shadow: 0 4px 10px rgba(30, 58, 138, 0.25);
}

.pill-sukses.aktif {
  background: #15803d;
  border-color: #15803d;
  color: #ffffff;
  box-shadow: 0 4px 10px rgba(21, 128, 61, 0.25);
}

.pill-bahaya.aktif {
  background: #b91c1c;
  border-color: #b91c1c;
  color: #ffffff;
  box-shadow: 0 4px 10px rgba(185, 28, 28, 0.25);
}

.pill-peringatan.aktif {
  background: #d97706;
  border-color: #d97706;
  color: #ffffff;
  box-shadow: 0 4px 10px rgba(217, 119, 6, 0.25);
}

.badge-hitung {
  background: rgba(0, 0, 0, 0.08);
  padding: 2px 8px;
  border-radius: 9999px;
  font-size: 0.78rem;
}

.pill-filter.aktif .badge-hitung {
  background: rgba(255, 255, 255, 0.25);
  color: #ffffff;
}

/* Filter bar & input */
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

/* Tabel Data */
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

.baris-transaksi {
  transition: background-color 0.15s ease;
}

.baris-transaksi:hover {
  background-color: #f8fafc;
}

.teks-struk {
  color: #1e3a8a;
  font-size: 0.95rem;
}

.teks-waktu {
  color: #475569;
  font-size: 0.85rem;
}

.badge-kasir {
  display: inline-block;
  padding: 4px 10px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-sm);
  color: #334155;
  font-weight: 600;
  font-size: 0.825rem;
}

.teks-total-uang {
  color: #059669;
  font-size: 1.05rem;
  font-weight: 800;
}

/* Lencana Status Transaksi (Color-coded for 40yo) */
.lencana-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 9999px;
  font-size: 0.82rem;
  font-weight: 800;
}

.status-selesai {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #86efac;
}

.status-batal {
  background: #fee2e2;
  color: #b91c1c;
  border: 1px solid #fca5a5;
}

.status-retur {
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fcd34d;
}

/* Lencana Sync */
.lencana-sync {
  display: inline-block;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: 0.78rem;
  font-weight: 700;
}

.sync-oke {
  background: #f0fdf4;
  color: #16a34a;
  border: 1px solid #bbf7d0;
}

.sync-gagal {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.sync-tunggu {
  background: #fffbeb;
  color: #d97706;
  border: 1px solid #fde68a;
}

/* Tombol Aksi Cepat Berwarna (Very user-friendly) */
.aksi-baris {
  display: flex;
  gap: 8px;
  align-items: center;
}

.btn-aksi {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 11px;
  border-radius: var(--radius-sm);
  font-weight: 700;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-detail {
  background: #eff6ff;
  border: 1.5px solid #bfdbfe;
  color: #1d4ed8;
}
.btn-detail:hover {
  background: #2563eb;
  color: #ffffff;
  border-color: #2563eb;
}

.btn-cetak {
  background: #eef2ff;
  border: 1.5px solid #c7d2fe;
  color: #4338ca;
}
.btn-cetak:hover {
  background: #4f46e5;
  color: #ffffff;
  border-color: #4f46e5;
}

.btn-void {
  background: #fef2f2;
  border: 1.5px solid #fecaca;
  color: #b91c1c;
}
.btn-void:hover {
  background: #dc2626;
  color: #ffffff;
  border-color: #dc2626;
}

.btn-retur {
  background: #fffbeb;
  border: 1.5px solid #fde68a;
  color: #b45309;
}
.btn-retur:hover {
  background: #d97706;
  color: #ffffff;
  border-color: #d97706;
}

.teks-kosong {
  color: #64748b;
}

.sub-kosong {
  font-size: 0.85rem;
  color: #94a3b8;
  margin-top: 4px;
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

.daftar-item-modal {
  max-height: 240px;
  overflow-y: auto;
  margin-top: 14px;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-md);
  padding: 8px 14px;
  background: #f8fafc;
}

.baris-detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #e2e8f0;
}

.baris-detail-item:last-child {
  border-bottom: none;
}

.teks-nama-item {
  color: #0f172a;
  font-size: 0.9rem;
}

.teks-subtotal {
  color: #059669;
  font-size: 0.95rem;
}

.kartu-ringkasan {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  padding: 14px;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  color: #334155;
}

.flex-between {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}

.pembatas-atas {
  border-top: 2px dashed #cbd5e1;
  padding-top: 10px;
  margin-top: 10px;
}

.teks-total-besar {
  font-size: 1.3rem;
  color: #059669;
  font-weight: 800;
}

.tombol-cetak-struk {
  background: #4f46e5;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-weight: 700;
}

.tombol-cetak-struk:hover {
  background: #4338ca;
}

.tombol-proses-retur {
  background: #d97706;
  color: #ffffff;
  font-weight: 700;
}

.tombol-proses-retur:hover {
  background: #b45309;
}

.kotak-peringatan-bahaya {
  background: #fef2f2;
  border: 1.5px solid #fca5a5;
  color: #991b1b;
  padding: 14px;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  line-height: 1.5;
}

.input-area {
  background: #f8fafc;
  border: 1.5px solid #cbd5e1;
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  color: #0f172a;
  padding: 10px;
  width: 100%;
}

.input-area:focus {
  background: #ffffff;
  border-color: #dc2626;
  outline: none;
}

.daftar-item-retur {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-md);
  padding: 10px;
  max-height: 240px;
  overflow-y: auto;
}

.item-retur-baris {
  display: flex;
  align-items: center;
  padding: 10px 8px;
  border-bottom: 1px solid #e2e8f0;
}

.checkbox-retur {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.input-qty-retur {
  background: #ffffff;
  border: 1.5px solid #cbd5e1;
  border-radius: var(--radius-sm);
  padding: 4px;
  font-weight: 700;
  color: #0f172a;
}

.font-angka { font-family: var(--font-angka); }
.tebal { font-weight: 700; }
.teks-redup { color: #64748b; font-size: 0.825rem; }
.teks-bahaya { color: #dc2626; }
.teks-peringatan { color: #d97706; }
.teks-pudar { color: #94a3b8; }
.p-6 { padding: 24px; }
.p-8 { padding: 32px; }
.mt-4 { margin-top: 16px; }
.mt-3 { margin-top: 12px; }
.mt-1 { margin-top: 4px; }
.mb-1 { margin-bottom: 4px; }
.mb-2 { margin-bottom: 8px; }
.flex { display: flex; }
.flex-1 { flex: 1; }
.items-center { align-items: center; }
.justify-center { justify-content: center; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.ml-2 { margin-left: 8px; }
.ml-3 { margin-left: 12px; }
.w-16 { width: 64px; }
.text-center { text-align: center; }
.uppercase { text-transform: uppercase; }
</style>
