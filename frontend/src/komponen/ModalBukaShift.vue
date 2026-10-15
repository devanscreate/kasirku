<script setup>
import { ref } from 'vue'
import { useShiftStore } from '../stores/shift'
import { useAuthStore } from '../stores/auth'
import { Landmark, ArrowRight, Wallet, Check } from 'lucide-vue-next'

const emit = defineEmits(['tutup', 'sukses'])
const shiftStore = useShiftStore()
const authStore = useAuthStore()

const kasAwal = ref(100000)
const sedangProses = ref(false)
const pesanError = ref('')

const nominalCepat = [
  { nilai: 50000, label: 'Rp 50.000', warna: '#0284c7', bg: '#f0f9ff', border: '#bae6fd' },
  { nilai: 100000, label: 'Rp 100.000', warna: '#be123c', bg: '#fff1f2', border: '#fecdd3' },
  { nilai: 200000, label: 'Rp 200.000', warna: '#15803d', bg: '#f0fdf4', border: '#bbf7d0' },
  { nilai: 500000, label: 'Rp 500.000', warna: '#7e22ce', bg: '#faf5ff', border: '#e9d5ff' },
]

async function simpanBukaShift() {
  if (kasAwal.value < 0) {
    pesanError.value = 'Modal kas awal tidak boleh bernilai negatif!'
    return
  }

  sedangProses.value = true
  pesanError.value = ''

  try {
    await shiftStore.bukaShift(authStore.idPengguna, kasAwal.value)
    emit('sukses')
  } catch (err) {
    pesanError.value = err.message || 'Gagal membuka shift'
  } finally {
    sedangProses.value = false
  }
}
</script>

<template>
  <div class="latar-modal">
    <div class="kotak-modal p-6">
      <div class="header-modal">
        <div class="ikon-lingkaran">
          <Wallet :size="32" />
        </div>
        <div>
          <h2 class="judul-modal">Buka Shift Kasir Baru</h2>
          <p class="sub-modal">Masukkan uang modal receh di laci kasir untuk uang kembalian.</p>
        </div>
      </div>

      <div v-if="pesanError" class="peringatan-error">
        {{ pesanError }}
      </div>

      <div class="grup-form mt-4">
        <label class="label-form">Jumlah Modal Kas Awal di Laci:</label>
        <div class="input-wrap-besar">
          <span class="awalan-rp">Rp</span>
          <input 
            v-model.number="kasAwal"
            type="number"
            min="0"
            step="1000"
            class="input-teks input-uang-besar"
            autofocus
            placeholder="0"
            @keydown.enter="simpanBukaShift"
          />
        </div>
      </div>

      <!-- Tombol Nominal Cepat Berwarna -->
      <div class="label-cepat">Pilihan Cepat Nominal Modal:</div>
      <div class="pilihan-nominal">
        <button 
          v-for="nom in nominalCepat" 
          :key="nom.nilai"
          type="button"
          class="btn-nominal-modal"
          :style="{
            backgroundColor: kasAwal === nom.nilai ? nom.warna : nom.bg,
            color: kasAwal === nom.nilai ? '#ffffff' : nom.warna,
            borderColor: nom.border
          }"
          @click="kasAwal = nom.nilai"
        >
          {{ nom.label }}
        </button>
      </div>

      <div class="footer-aksi mt-6">
        <button 
          class="tombol tombol-primer tombol-lg w-full tombol-buka"
          :disabled="sedangProses || kasAwal < 0"
          @click="simpanBukaShift"
        >
          <span>{{ sedangProses ? 'Membuka Shift...' : 'Buka Shift & Masuk Layar Kasir' }}</span>
          <ArrowRight :size="20" />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.p-6 {
  padding: 30px 26px;
}
.w-full {
  width: 100%;
}
.mt-4 { margin-top: 16px; }
.mt-6 { margin-top: 24px; }

.header-modal {
  display: flex;
  align-items: center;
  gap: 16px;
  border-bottom: 2px solid #f1f5f9;
  padding-bottom: 16px;
}
.ikon-lingkaran {
  width: 58px;
  height: 58px;
  background: #eff6ff;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #1d4ed8;
  border: 2px solid #bfdbfe;
  flex-shrink: 0;
}
.judul-modal {
  font-size: 1.4rem;
  font-weight: 900;
  color: #0f172a;
}
.sub-modal {
  font-size: 0.9rem;
  color: #64748b;
  margin-top: 4px;
  font-weight: 600;
}

.peringatan-error {
  background: #fef2f2;
  border: 2px solid #fecaca;
  color: #dc2626;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  font-weight: 700;
  margin-top: 14px;
}

.label-form {
  font-weight: 800;
  font-size: 1rem;
  color: #0f172a;
  display: block;
  margin-bottom: 8px;
}

.input-wrap-besar {
  position: relative;
  display: flex;
  align-items: center;
}
.awalan-rp {
  position: absolute;
  left: 18px;
  font-size: 1.3rem;
  font-weight: 900;
  color: #2563eb;
  font-family: var(--font-angka);
}
.input-uang-besar {
  padding-left: 56px;
  font-size: 1.6rem;
  font-weight: 900;
  height: 58px;
  font-family: var(--font-angka);
  color: #0f172a;
  border: 2.5px solid #2563eb;
  background: #ffffff;
}

.label-cepat {
  font-size: 0.85rem;
  font-weight: 800;
  color: #475569;
  margin: 16px 0 10px 0;
}
.pilihan-nominal {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}
.btn-nominal-modal {
  padding: 12px;
  font-size: 1.05rem;
  font-weight: 900;
  border-radius: var(--radius-md);
  border: 2px solid;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: var(--font-angka);
  text-align: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.04);
}
.btn-nominal-modal:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}

.tombol-buka {
  height: 56px;
  font-size: 1.15rem;
  font-weight: 900;
  background: linear-gradient(135deg, #1d4ed8, #2563eb);
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.35);
}
</style>
