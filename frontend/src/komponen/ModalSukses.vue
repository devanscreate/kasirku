<script setup>
import { computed } from 'vue'
import { Printer, PlusCircle, CheckCircle2, Banknote, Sparkles } from 'lucide-vue-next'
import { cetakStrukTransaksi } from '../layanan/pencetak_struk'

const props = defineProps({
  transaksi: {
    type: Object,
    required: true
  },
  kembalian: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['transaksiBaru'])

const formatRupiah = (val) => 'Rp ' + Number(val || 0).toLocaleString('id-ID')

// Cek apakah transaksi lunas sepenuhnya dari potongan tabungan donasi pembeli
const apakahLunasTabungan = computed(() => {
  const t = props.transaksi
  if (!t) return false
  const adaPotongan = Boolean((t.potongan_donasi && t.potongan_donasi > 0) || (t.potonganDonasi && t.potonganDonasi.nominal > 0))
  const totalNol = Number(t.total || 0) === 0
  const metodeTabungan = t.pembayaran?.[0]?.metode === 'tabungan'
  return adaPotongan && (totalNol || metodeTabungan)
})

const namaPelangganTabungan = computed(() => {
  return props.transaksi?.potonganDonasi?.namaPelanggan || 
         props.transaksi?.nama_pelanggan || 
         'Pelanggan'
})

const noHpPelangganTabungan = computed(() => {
  return props.transaksi?.potonganDonasi?.nomorHp || 
         props.transaksi?.hp_pelanggan || 
         ''
})

const sisaSaldoTabungan = computed(() => {
  if (props.transaksi?.sisaSaldoDonasi !== undefined && props.transaksi?.sisaSaldoDonasi !== null) {
    return props.transaksi.sisaSaldoDonasi
  }
  const saldoAwal = props.transaksi?.potonganDonasi?.saldoAwal
  const nominal = props.transaksi?.potonganDonasi?.nominal || props.transaksi?.potongan_donasi || 0
  if (saldoAwal !== undefined && saldoAwal !== null) {
    return Math.max(0, Number(saldoAwal) - Number(nominal))
  }
  return 0
})

// Panduan hitung pecahan lembaran uang kembalian otomatis untuk persona 40 tahun
const rincianLembaranUang = computed(() => {
  let sisa = props.kembalian
  if (sisa <= 0) return []

  const pecahan = [
    { nilai: 100000, label: 'Rp 100.000', warnaBg: '#fff1f2', warnaTeks: '#be123c', border: '#f43f5e' },
    { nilai: 50000,  label: 'Rp 50.000',  warnaBg: '#f0f9ff', warnaTeks: '#0369a1', border: '#38bdf8' },
    { nilai: 20000,  label: 'Rp 20.000',  warnaBg: '#f0fdf4', warnaTeks: '#15803d', border: '#4ade80' },
    { nilai: 10000,  label: 'Rp 10.000',  warnaBg: '#faf5ff', warnaTeks: '#7e22ce', border: '#c084fc' },
    { nilai: 5000,   label: 'Rp 5.000',   warnaBg: '#fffbeb', warnaTeks: '#b45309', border: '#fde68a' },
    { nilai: 2000,   label: 'Rp 2.000',   warnaBg: '#f8fafc', warnaTeks: '#334155', border: '#cbd5e1' },
    { nilai: 1000,   label: 'Rp 1.000',   warnaBg: '#f8fafc', warnaTeks: '#475569', border: '#cbd5e1' }
  ]

  const hasil = []
  for (const p of pecahan) {
    if (sisa >= p.nilai) {
      const lembar = Math.floor(sisa / p.nilai)
      sisa = sisa % p.nilai
      hasil.push({ ...p, jumlah: lembar })
    }
  }
  return hasil
})

function cetakStruk() {
  cetakStrukTransaksi(props.transaksi, {}, false)
}
</script>

<template>
  <div class="latar-modal" @keydown.enter="emit('transaksiBaru')">
    <div class="kotak-modal p-6 text-center">
      <div class="ikon-sukses">
        <CheckCircle2 :size="54" />
      </div>

      <h2 class="judul-sukses">Transaksi Berhasil!</h2>
      <p class="sub-sukses">Nomor Struk: <span class="tebal nomor-struk-teks">{{ props.transaksi.nomor_struk }}</span></p>

      <!-- JIKA LUNAS 100% OLEH SALDO TABUNGAN (PEMBELI TIDAK MEMBAYAR TUNAI) -->
      <div v-if="apakahLunasTabungan" class="kartu-lunas-sukses">
        <div class="ikon-lunas-badge">
          <Sparkles :size="24" class="teks-emas" />
        </div>
        <div class="label-lunas-sukses">LUNAS DENGAN SALDO TABUNGAN</div>
        <div class="angka-lunas-sukses font-angka">Rp 0</div>
        <div class="sub-lunas-sukses">Pembeli tidak membayar — saldo tabungan telah terpotong</div>

        <div class="ledger-lunas-sukses mt-3">
          <div class="baris-ledger-sukses">
            <span>Total Belanja Asli:</span>
            <strong class="font-angka">{{ formatRupiah(props.transaksi.total_sebelum_potongan || props.transaksi.subtotal) }}</strong>
          </div>
          <div class="baris-ledger-sukses teks-hijau-sukses">
            <span>Dipotong dari Saldo Tabungan:</span>
            <strong class="font-angka">-{{ formatRupiah(props.transaksi.potonganDonasi?.nominal || props.transaksi.potongan_donasi) }}</strong>
          </div>
          <div class="garis-pemisah-sukses"></div>
          <div class="baris-ledger-sukses baris-sisa-saldo">
            <span>Sisa Saldo Tabungan Pelanggan:</span>
            <strong class="font-angka teks-hijau-tebal">{{ formatRupiah(sisaSaldoTabungan) }}</strong>
          </div>
        </div>

        <div class="info-pembeli-lunas mt-2">
          Pembeli: <strong>{{ namaPelangganTabungan }}</strong> <span v-if="noHpPelangganTabungan">({{ noHpPelangganTabungan }})</span>
        </div>
      </div>

      <!-- Kotak Uang Kembalian Biasa (Hanya Tampil Jika Bukan Lunas Tabungan Penuh) -->
      <div v-else class="kartu-kembalian">
        <div class="label-kembalian">UANG KEMBALIAN UNTUK PEMBELI</div>
        <div class="angka-kembalian font-angka">{{ formatRupiah(props.kembalian) }}</div>
      </div>

      <!-- Info Donasi Kembalian Jika Ada -->
      <div v-if="props.transaksi.donasi" class="kartu-donasi-sukses mt-3">
        <div class="flex items-center justify-between mb-1">
          <span class="label-donasi-sukses">
            <strong>Ditabung ke Celengan Donasi:</strong>
          </span>
          <span class="font-angka tebal teks-hijau-sukses">+{{ formatRupiah(props.transaksi.donasi.nominal) }}</span>
        </div>
        <div class="flex items-center justify-between text-xs sub-donasi-sukses">
          <span>No. HP Pembeli: <strong>{{ props.transaksi.donasi.nomorHp }}</strong></span>
          <span v-if="props.transaksi.donasi.totalSaldoBaru">Total Tabungan: <strong class="font-angka">{{ formatRupiah(props.transaksi.donasi.totalSaldoBaru) }}</strong></span>
        </div>
        <div class="petunjuk-pencairan-struk mt-1">
          Saldo celengan ini dapat digunakan untuk potongan belanja atau dicairkan kapan saja.
        </div>
      </div>

      <!-- Info Potongan Donasi Jika Ada (Sebagian/Parsial) -->
      <div v-if="!apakahLunasTabungan && (props.transaksi.potonganDonasi || props.transaksi.potongan_donasi)" class="kartu-potongan-sukses mt-2">
        <div class="flex items-center justify-between">
          <span>Saldo Celengan Tabungan Dipakai:</span>
          <span class="font-angka tebal teks-hijau-sukses">-{{ formatRupiah(props.transaksi.potonganDonasi?.nominal || props.transaksi.potongan_donasi) }}</span>
        </div>
        <div v-if="props.transaksi.sisaSaldoDonasi !== undefined" class="flex items-center justify-between text-xs mt-1">
          <span>Sisa Saldo Tabungan:</span>
          <strong class="font-angka">{{ formatRupiah(props.transaksi.sisaSaldoDonasi) }}</strong>
        </div>
      </div>

      <!-- Panduan Lembaran Uang Otomatis (Hanya Tampil Jika Ada Uang Kembalian Tunai) -->
      <div v-if="!apakahLunasTabungan && rincianLembaranUang.length > 0" class="panduan-lembaran">
        <div class="judul-panduan">
          <Banknote :size="18" class="ikon-uang" />
          <span>Panduan Uang Kembalian di Laci Kasir:</span>
        </div>
        <div class="daftar-lembar">
          <div 
            v-for="lembar in rincianLembaranUang" 
            :key="lembar.nilai"
            class="pill-lembar"
            :style="{ background: lembar.warnaBg, color: lembar.warnaTeks, borderColor: lembar.border }"
          >
            <span class="qty-lembar">{{ lembar.jumlah }}x</span>
            <span class="nama-pecahan">{{ lembar.label }}</span>
          </div>
        </div>
      </div>

      <!-- Ringkasan Singkat -->
      <div class="info-struk">
        <div v-if="props.transaksi.potonganDonasi || props.transaksi.potongan_donasi" class="flex-between">
          <span class="label-info">Total Belanja Asli:</span>
          <span class="tebal angka-info font-angka">{{ formatRupiah(props.transaksi.total_sebelum_potongan || props.transaksi.subtotal) }}</span>
        </div>
        <div v-if="props.transaksi.potonganDonasi || props.transaksi.potongan_donasi" class="flex-between">
          <span class="label-info teks-hijau-sukses">Potongan Tabungan Donasi:</span>
          <span class="tebal angka-info teks-hijau-sukses font-angka">-{{ formatRupiah(props.transaksi.potonganDonasi?.nominal || props.transaksi.potongan_donasi) }}</span>
        </div>
        <div class="flex-between">
          <span class="label-info">{{ (props.transaksi.potonganDonasi || props.transaksi.potongan_donasi) ? 'Total yang Dibayar Pembeli:' : 'Total Belanja:' }}</span>
          <span class="tebal angka-info font-angka" :class="{ 'teks-hijau-sukses': apakahLunasTabungan }">
            {{ formatRupiah(props.transaksi.total) }} {{ apakahLunasTabungan ? '(Lunas Tabungan)' : '' }}
          </span>
        </div>

        <template v-if="!apakahLunasTabungan">
          <div v-if="props.transaksi.pembayaran && props.transaksi.pembayaran[0]" class="flex-between">
            <span class="label-info">Uang Diterima ({{ (props.transaksi.pembayaran[0].metode || 'tunai').toUpperCase() }}):</span>
            <span class="tebal angka-info font-angka">{{ formatRupiah(props.transaksi.pembayaran[0].diterima) }}</span>
          </div>
          <div v-if="props.transaksi.pembayaran && props.transaksi.pembayaran[0] && props.transaksi.pembayaran[0].metode === 'tunai'" class="flex-between">
            <span class="label-info">Uang Kembalian:</span>
            <span class="tebal angka-info font-angka">{{ formatRupiah(props.kembalian) }}</span>
          </div>
        </template>

        <template v-else>
          <div class="flex-between">
            <span class="label-info">Metode Pembayaran:</span>
            <span class="tebal angka-info teks-hijau-sukses">TABUNGAN DONASI</span>
          </div>
          <div class="flex-between">
            <span class="label-info">Sisa Saldo Tabungan:</span>
            <span class="tebal angka-info font-angka teks-hijau-sukses">{{ formatRupiah(sisaSaldoTabungan) }}</span>
          </div>
        </template>

        <div class="flex-between">
          <span class="label-info">Status Data:</span>
          <span class="lencana lencana-online">{{ props.transaksi.status_sinkron === 'synced' ? 'Tersimpan & Sinkron ke Server' : 'Tersimpan Aman di Kasir' }}</span>
        </div>
      </div>

      <!-- Tombol Aksi Bawah -->
      <div class="aksi-grid mt-6">
        <button class="tombol tombol-sekunder tombol-lg tombol-cetak" @click="cetakStruk">
          <Printer :size="22" />
          <span>Cetak Struk [P]</span>
        </button>
        <button class="tombol tombol-sukses tombol-lg tombol-transaksi-baru" @click="emit('transaksiBaru')">
          <PlusCircle :size="22" />
          <span>Transaksi Baru [Enter]</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.p-6 { padding: 32px 28px; }
.text-center { text-align: center; }
.mt-2 { margin-top: 8px; }
.mt-3 { margin-top: 12px; }
.mt-6 { margin-top: 24px; }
.flex-between { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }

.ikon-sukses {
  width: 84px;
  height: 84px;
  background: #ecfdf5;
  color: #059669;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 18px auto;
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.25);
  border: 3px solid #a7f3d0;
}

.judul-sukses {
  font-size: 1.7rem;
  font-weight: 900;
  color: #0f172a;
}
.sub-sukses {
  color: #64748b;
  font-size: 1rem;
  margin-top: 6px;
  font-weight: 600;
}
.nomor-struk-teks {
  color: #1d4ed8;
  font-family: var(--font-angka);
  font-size: 1.05rem;
}
.tebal { font-weight: 800; color: #0f172a; }

/* KARTU LUNAS DENGAN TABUNGAN (PEMBELI TIDAK BAYAR TUNAI) */
.kartu-lunas-sukses {
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  border: 2px solid #10b981;
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  margin: 18px 0;
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.16);
  text-align: center;
}
.ikon-lunas-badge {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #ffffff;
  color: #059669;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 8px auto;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);
}
.label-lunas-sukses {
  font-size: 0.88rem;
  font-weight: 900;
  color: #065f46;
  letter-spacing: 0.05em;
}
.angka-lunas-sukses {
  font-size: 2.2rem;
  font-weight: 900;
  color: #047857;
  font-family: var(--font-angka);
  margin: 4px 0 2px 0;
}
.sub-lunas-sukses {
  font-size: 0.82rem;
  color: #059669;
  font-weight: 700;
}
.ledger-lunas-sukses {
  background: #ffffff;
  border: 1px solid #a7f3d0;
  border-radius: 10px;
  padding: 12px 14px;
  text-align: left;
}
.baris-ledger-sukses {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  color: #475569;
  margin-bottom: 4px;
}
.garis-pemisah-sukses {
  border-top: 1px dashed #cbd5e1;
  margin: 8px 0;
}
.baris-sisa-saldo {
  color: #065f46;
  font-size: 0.9rem;
  font-weight: 800;
  margin-bottom: 0;
}
.teks-hijau-tebal {
  color: #059669;
  font-size: 1.05rem;
}
.info-pembeli-lunas {
  font-size: 0.78rem;
  color: #047857;
  font-weight: 600;
}

/* KARTU KEMBALIAN TUNAI */
.kartu-kembalian {
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  border: 2px solid #10b981;
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  margin: 20px 0;
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.15);
}
.label-kembalian {
  font-size: 0.9rem;
  font-weight: 900;
  color: #065f46;
  letter-spacing: 0.05em;
}
.angka-kembalian {
  font-size: 2.3rem;
  font-weight: 900;
  color: #047857;
  font-family: var(--font-angka);
  margin-top: 4px;
}

/* Panduan Uang Kembalian */
.panduan-lembaran {
  background: #eff6ff;
  border: 1.5px solid #bfdbfe;
  border-radius: var(--radius-md);
  padding: 14px 16px;
  margin-bottom: 20px;
  text-align: left;
}
.judul-panduan {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
  font-weight: 800;
  color: #1e40af;
  margin-bottom: 10px;
}
.ikon-uang { color: #2563eb; }
.daftar-lembar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.pill-lembar {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1.5px solid;
  font-size: 0.85rem;
  font-weight: 800;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.qty-lembar {
  background: rgba(0, 0, 0, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 900;
}
.nama-pecahan {
  font-family: var(--font-angka);
}

.info-struk {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-md);
  padding: 14px 18px;
  margin-bottom: 20px;
  font-size: 0.95rem;
}
.label-info { color: #64748b; font-weight: 600; }
.angka-info { font-family: var(--font-angka); font-size: 1.05rem; }

.aksi-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.tombol-cetak {
  border: 2px solid #cbd5e1;
  font-weight: 800;
  color: #1e40af;
}
.tombol-cetak:hover {
  background: #eff6ff;
  border-color: #3b82f6;
}
.tombol-transaksi-baru {
  background: linear-gradient(135deg, #059669, #10b981);
  font-weight: 900;
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.35);
}
.tombol-transaksi-baru:hover {
  background: linear-gradient(135deg, #047857, #059669);
}

.kartu-donasi-sukses {
  background: #f0fdf4;
  border: 1.5px solid #86efac;
  border-radius: var(--radius-md);
  padding: 12px 16px;
  text-align: left;
}
.label-donasi-sukses {
  font-size: 0.88rem;
  color: #166534;
}
.teks-emas {
  color: #d97706;
}
.teks-hijau-sukses {
  color: #15803d;
  font-size: 1.1rem;
}
.sub-donasi-sukses {
  color: #334155;
  margin-top: 4px;
}
.petunjuk-pencairan-struk {
  font-size: 0.72rem;
  color: #64748b;
  font-style: italic;
}

.kartu-potongan-sukses {
  background: #eff6ff;
  border: 1.5px solid #bfdbfe;
  border-radius: var(--radius-md);
  padding: 10px 14px;
  font-size: 0.85rem;
  color: #1e40af;
  font-weight: 700;
}
</style>
