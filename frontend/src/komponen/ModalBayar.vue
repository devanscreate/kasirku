<script setup>
import { ref, computed } from 'vue'
import { Banknote, QrCode, ArrowRightLeft, X, Check, AlertCircle, Coins } from 'lucide-vue-next'

const props = defineProps({
  total: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['tutup', 'bayar'])

const metode = ref('tunai') // 'tunai' | 'qris' | 'transfer'
const uangDiterima = ref(props.total)
const pesanError = ref('')

const formatRupiah = (val) => 'Rp ' + Number(val || 0).toLocaleString('id-ID')

// Pecahan uang kertas Indonesia standar
const pecahanCepat = [10000, 20000, 50000, 100000]

// Hitung nominal bulat di atas total
const opsiBulat = computed(() => {
  const daftar = [{ label: 'UANG PAS', nilai: props.total, tipe: 'pas' }]
  
  pecahanCepat.forEach(pecahan => {
    if (pecahan > props.total) {
      daftar.push({ label: formatRupiah(pecahan), nilai: pecahan, tipe: pecahan })
    }
  })

  // Nominal kelipatan 50rb / 100rb terdekat
  const bulat50 = Math.ceil(props.total / 50000) * 50000
  if (bulat50 > props.total && !daftar.some(d => d.nilai === bulat50)) {
    daftar.push({ label: formatRupiah(bulat50), nilai: bulat50, tipe: 50000 })
  }
  const bulat100 = Math.ceil(props.total / 100000) * 100000
  if (bulat100 > props.total && !daftar.some(d => d.nilai === bulat100)) {
    daftar.push({ label: formatRupiah(bulat100), nilai: bulat100, tipe: 100000 })
  }
  return daftar
})

// Fungsi gaya tombol pecahan sesuai warna lembaran uang Rupiah asli
function gayaTombolPecahan(opsi) {
  if (opsi.tipe === 'pas') {
    return { bg: '#ecfdf5', color: '#047857', border: '#10b981', aktifBg: '#059669', aktifColor: '#ffffff' }
  }
  if (opsi.tipe === 100000) {
    return { bg: '#fff1f2', color: '#be123c', border: '#f43f5e', aktifBg: '#be123c', aktifColor: '#ffffff' }
  }
  if (opsi.tipe === 50000) {
    return { bg: '#f0f9ff', color: '#0369a1', border: '#38bdf8', aktifBg: '#0284c7', aktifColor: '#ffffff' }
  }
  if (opsi.tipe === 20000) {
    return { bg: '#f0fdf4', color: '#15803d', border: '#4ade80', aktifBg: '#16a34a', aktifColor: '#ffffff' }
  }
  if (opsi.tipe === 10000) {
    return { bg: '#faf5ff', color: '#7e22ce', border: '#c084fc', aktifBg: '#9333ea', aktifColor: '#ffffff' }
  }
  return { bg: '#f8fafc', color: '#334155', border: '#cbd5e1', aktifBg: '#1e40af', aktifColor: '#ffffff' }
}

const kembalian = computed(() => {
  if (metode.value !== 'tunai') return 0
  return Math.max(0, uangDiterima.value - props.total)
})

const apakahCukup = computed(() => {
  if (metode.value !== 'tunai') return true
  return uangDiterima.value >= props.total
})

function konfirmasiBayar() {
  if (metode.value === 'tunai' && uangDiterima.value < props.total) {
    pesanError.value = 'Uang yang diterima kurang dari total belanja!'
    return
  }

  emit('bayar', {
    metode: metode.value,
    diterima: metode.value === 'tunai' ? uangDiterima.value : props.total,
    kembalian: kembalian.value
  })
}
</script>

<template>
  <div class="latar-modal" @keydown.esc="emit('tutup')">
    <div class="kotak-modal p-6">
      <div class="header-modal">
        <div>
          <h2 class="judul-modal">Proses Pembayaran Kasir</h2>
          <p class="sub-modal">Pilih cara bayar dan masukkan nominal uang pelanggan</p>
        </div>
        <button class="tombol-tutup" @click="emit('tutup')" title="Tutup Modal">
          <X :size="24" />
        </button>
      </div>

      <!-- Tagihan Total Besar & Jelas -->
      <div class="kotak-total">
        <div>
          <div class="label-total">TOTAL YANG HARUS DIBAYAR</div>
          <div class="petunjuk-tagihan">Pastikan tagihan sudah sesuai keranjang</div>
        </div>
        <div class="angka-total">{{ formatRupiah(props.total) }}</div>
      </div>

      <!-- Pilihan Metode Pembayaran Berwarna & Menarik -->
      <div class="label-bagian">Pilih Cara Pembayaran:</div>
      <div class="metode-pilihan">
        <button 
          type="button"
          class="metode-btn metode-tunai"
          :class="{ 'aktif': metode === 'tunai' }"
          @click="metode = 'tunai'; uangDiterima = props.total"
        >
          <div class="ikon-metode">
            <Banknote :size="28" />
          </div>
          <span class="nama-metode">Uang Tunai</span>
          <span class="sub-metode">Bayar Cash</span>
        </button>

        <button 
          type="button"
          class="metode-btn metode-qris"
          :class="{ 'aktif': metode === 'qris' }"
          @click="metode = 'qris'; uangDiterima = props.total"
        >
          <div class="ikon-metode">
            <QrCode :size="28" />
          </div>
          <span class="nama-metode">QRIS Toko</span>
          <span class="sub-metode">Scan Barcode</span>
        </button>

        <button 
          type="button"
          class="metode-btn metode-transfer"
          :class="{ 'aktif': metode === 'transfer' }"
          @click="metode = 'transfer'; uangDiterima = props.total"
        >
          <div class="ikon-metode">
            <ArrowRightLeft :size="28" />
          </div>
          <span class="nama-metode">Transfer Bank</span>
          <span class="sub-metode">m-Banking</span>
        </button>
      </div>

      <!-- Form Metode Tunai -->
      <div v-if="metode === 'tunai'" class="bagian-tunai">
        <div class="grup-form">
          <div class="flex justify-between items-center mb-2">
            <label class="label-form">Uang Tunai yang Diterima:</label>
            <span class="petunjuk-input">Ketik angka atau klik tombol pecahan di bawah</span>
          </div>
          <div class="input-wrap-besar">
            <span class="awalan-rp">Rp</span>
            <input 
              v-model.number="uangDiterima"
              type="number"
              class="input-teks input-bayar-besar"
              step="1000"
              autofocus
              @keydown.enter="konfirmasiBayar"
            />
          </div>
        </div>

        <!-- Tombol Cepat Pecahan Uang Rupiah Asli -->
        <div class="label-cepat">Tombol Cepat Pecahan Uang:</div>
        <div class="grid-nominal">
          <button 
            v-for="opsi in opsiBulat" 
            :key="opsi.nilai"
            type="button"
            class="btn-pecahan"
            :style="{
              backgroundColor: uangDiterima === opsi.nilai ? gayaTombolPecahan(opsi).aktifBg : gayaTombolPecahan(opsi).bg,
              color: uangDiterima === opsi.nilai ? gayaTombolPecahan(opsi).aktifColor : gayaTombolPecahan(opsi).color,
              borderColor: gayaTombolPecahan(opsi).border
            }"
            @click="uangDiterima = opsi.nilai"
          >
            {{ opsi.label }}
          </button>
        </div>

        <!-- Kotak Kembalian Jelas -->
        <div class="kotak-kembalian" :class="{ 'kurang': uangDiterima < props.total }">
          <div class="flex-between">
            <span class="label-kembalian">Uang Kembalian:</span>
            <span class="angka-kembalian">{{ formatRupiah(kembalian) }}</span>
          </div>
          <div v-if="uangDiterima < props.total" class="pesan-kurang">
            <AlertCircle :size="18" />
            <span>Uang Kurang: <strong>{{ formatRupiah(props.total - uangDiterima) }}</strong></span>
          </div>
        </div>
      </div>

      <!-- Info QRIS / Transfer Manual -->
      <div v-else class="bagian-non-tunai">
        <div class="kotak-instruksi" :class="metode === 'qris' ? 'instruksi-qris' : 'instruksi-transfer'">
          <div v-if="metode === 'qris'">
            <div class="judul-instruksi">📱 Petunjuk Pembayaran QRIS:</div>
            <p>1. Arahkan pelanggan untuk scan QRIS toko di kasir.</p>
            <p>2. Pastikan nominal pembayaran pas sebesar <strong>{{ formatRupiah(props.total) }}</strong>.</p>
            <p>3. Setelah notifikasi masuk, tekan tombol hijau di bawah.</p>
          </div>
          <div v-else>
            <div class="judul-instruksi">🏦 Petunjuk Pembayaran Transfer:</div>
            <p>1. Pelanggan mentransfer dana via m-Banking/ATM.</p>
            <p>2. Periksa bukti mutasi dana rekening toko.</p>
            <p>3. Jika dana sudah masuk, tekan tombol hijau di bawah.</p>
          </div>
        </div>
      </div>

      <!-- Tombol Aksi Bawah -->
      <div class="footer-aksi flex gap-3 mt-4">
        <button class="tombol tombol-sekunder flex-1 tombol-batal-bayar" @click="emit('tutup')">
          <span>❌ Batal (Esc)</span>
        </button>
        <button 
          class="tombol tombol-sukses flex-2 tombol-konfirmasi-bayar"
          :disabled="!apakahCukup"
          @click="konfirmasiBayar"
        >
          <Check :size="22" />
          <span>SELESAIKAN PEMBAYARAN [F9]</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.p-6 { padding: 26px; }
.mt-4 { margin-top: 18px; }
.flex { display: flex; }
.flex-1 { flex: 1; }
.flex-2 { flex: 2; }
.gap-3 { gap: 14px; }
.flex-between { display: flex; justify-content: space-between; align-items: center; }
.header-modal { 
  display: flex; 
  justify-content: space-between; 
  align-items: flex-start; 
  margin-bottom: 18px;
  border-bottom: 2px solid #f1f5f9;
  padding-bottom: 14px;
}
.judul-modal { font-size: 1.35rem; font-weight: 900; color: #0f172a; }
.sub-modal { font-size: 0.9rem; color: #64748b; margin-top: 4px; font-weight: 600; }
.tombol-tutup { 
  background: #f1f5f9; 
  border: none; 
  color: #64748b; 
  cursor: pointer; 
  padding: 6px; 
  border-radius: 8px;
  transition: all 0.2s ease;
}
.tombol-tutup:hover { background: #fee2e2; color: #dc2626; }

.kotak-total {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
  border: 2px solid #3b82f6;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08);
}
.label-total { font-size: 0.85rem; color: #1e40af; font-weight: 900; letter-spacing: 0.04em; }
.petunjuk-tagihan { font-size: 0.75rem; color: #2563eb; font-weight: 600; }
.angka-total { font-size: 1.8rem; font-weight: 900; color: #1d4ed8; font-family: var(--font-angka); }

.label-bagian {
  font-size: 0.9rem;
  font-weight: 800;
  color: #334155;
  margin-bottom: 8px;
}

.metode-pilihan {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 18px;
}
.metode-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 14px 10px;
  border-radius: var(--radius-md);
  border: 2px solid #cbd5e1;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}
.ikon-metode {
  margin-bottom: 6px;
}
.nama-metode {
  font-size: 0.95rem;
  font-weight: 800;
}
.sub-metode {
  font-size: 0.75rem;
  color: #64748b;
  font-weight: 600;
}

/* Warna per Metode Bayar */
.metode-tunai .ikon-metode { color: #059669; }
.metode-tunai:hover { border-color: #059669; background: #ecfdf5; }
.metode-tunai.aktif {
  background: #ecfdf5;
  border-color: #059669;
  box-shadow: 0 4px 14px rgba(5, 150, 105, 0.2);
}
.metode-tunai.aktif .nama-metode { color: #047857; }

.metode-qris .ikon-metode { color: #0284c7; }
.metode-qris:hover { border-color: #0284c7; background: #f0f9ff; }
.metode-qris.aktif {
  background: #f0f9ff;
  border-color: #0284c7;
  box-shadow: 0 4px 14px rgba(2, 132, 199, 0.2);
}
.metode-qris.aktif .nama-metode { color: #0369a1; }

.metode-transfer .ikon-metode { color: #7c3aed; }
.metode-transfer:hover { border-color: #7c3aed; background: #f5f3ff; }
.metode-transfer.aktif {
  background: #f5f3ff;
  border-color: #7c3aed;
  box-shadow: 0 4px 14px rgba(124, 58, 237, 0.2);
}
.metode-transfer.aktif .nama-metode { color: #6d28d9; }

.label-form {
  font-weight: 800;
  font-size: 0.95rem;
  color: #0f172a;
}
.petunjuk-input {
  font-size: 0.8rem;
  color: #64748b;
  font-weight: 600;
}

.input-wrap-besar {
  position: relative;
  display: flex;
  align-items: center;
}
.awalan-rp {
  position: absolute;
  left: 16px;
  font-size: 1.3rem;
  font-weight: 900;
  color: #2563eb;
  font-family: var(--font-angka);
}
.input-bayar-besar {
  padding-left: 54px;
  font-size: 1.6rem;
  font-weight: 900;
  height: 58px;
  font-family: var(--font-angka);
  color: #0f172a;
  border: 2.5px solid #2563eb;
  background: #f8fafc;
}
.input-bayar-besar:focus {
  background: #ffffff;
}

.label-cepat {
  font-size: 0.85rem;
  font-weight: 800;
  color: #475569;
  margin: 12px 0 8px 0;
}
.grid-nominal {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 8px;
  margin-bottom: 16px;
}
.btn-pecahan {
  padding: 10px 8px;
  font-size: 0.95rem;
  font-weight: 900;
  border-radius: var(--radius-md);
  border: 2px solid;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: var(--font-angka);
  text-align: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
}
.btn-pecahan:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}

.kotak-kembalian {
  background: #ecfdf5;
  border: 2px solid #10b981;
  border-radius: var(--radius-md);
  padding: 14px 18px;
  margin-top: 14px;
}
.kotak-kembalian.kurang {
  background: #fef2f2;
  border-color: #ef4444;
}
.label-kembalian {
  font-size: 1rem;
  font-weight: 800;
  color: #065f46;
}
.kotak-kembalian.kurang .label-kembalian {
  color: #991b1b;
}
.angka-kembalian {
  font-size: 1.6rem;
  font-weight: 900;
  font-family: var(--font-angka);
  color: #047857;
}
.kotak-kembalian.kurang .angka-kembalian {
  color: #dc2626;
}
.pesan-kurang {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  font-weight: 700;
  color: #dc2626;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed #fca5a5;
}

.kotak-instruksi {
  padding: 18px;
  border-radius: var(--radius-md);
  font-size: 0.95rem;
  line-height: 1.6;
}
.instruksi-qris {
  background: #f0f9ff;
  border: 2px solid #bae6fd;
  color: #0369a1;
}
.instruksi-transfer {
  background: #f5f3ff;
  border: 2px solid #ddd6fe;
  color: #5b21b6;
}
.judul-instruksi {
  font-weight: 900;
  margin-bottom: 6px;
  font-size: 1.05rem;
}

.tombol-batal-bayar {
  font-weight: 800;
  color: #475569;
}
.tombol-konfirmasi-bayar {
  height: 52px;
  font-size: 1.05rem;
  font-weight: 900;
  letter-spacing: 0.02em;
}
</style>
