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

      <!-- Kotak Uang Kembalian Besar -->
      <div class="kartu-kembalian">
        <div class="label-kembalian">UANG KEMBALIAN PELANGGAN</div>
        <div class="angka-kembalian">{{ formatRupiah(props.kembalian) }}</div>
      </div>

      <!-- Panduan Lembaran Uang Otomatis (Sangat Membantu Kasir 40-an) -->
      <div v-if="rincianLembaranUang.length > 0" class="panduan-lembaran">
        <div class="judul-panduan">
          <Banknote :size="18" class="ikon-uang" />
          <span>Panduan Ambil Uang Kembalian di Laci:</span>
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
        <div class="flex-between">
          <span class="label-info">Total Belanja:</span>
          <span class="tebal angka-info">{{ formatRupiah(props.transaksi.total) }}</span>
        </div>
        <div class="flex-between">
          <span class="label-info">Status Sinkronisasi:</span>
          <span class="lencana lencana-online">{{ props.transaksi.status_sinkron === 'synced' ? 'Tersinkron ke Server' : 'Tersimpan Aman di Outbox' }}</span>
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
</style>
