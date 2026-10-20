<script setup>
import { ref, onMounted, computed } from 'vue'
import { useShiftStore } from '../stores/shift'
import { panggilApi } from '../layanan/api'
import { CheckCircle2, AlertCircle, X, Lock, FileText } from 'lucide-vue-next'

const emit = defineEmits(['tutup', 'sukses'])
const shiftStore = useShiftStore()

const ringkasan = ref(null)
const sedangMemuat = ref(true)
const sedangTutup = ref(false)
const kasFisik = ref(0)
const catatan = ref('')
const pesanError = ref('')

const blindClose = ref(true) // Pengaturan blind close
const ambangSelisih = 50000 // Ambang selisih wajib catatan (F-09)

const formatRupiah = (val) => 'Rp ' + Number(val || 0).toLocaleString('id-ID')

function tanganiInputKasFisik(e) {
  const digitOnly = e.target.value.replace(/\D/g, '')
  const num = digitOnly ? parseInt(digitOnly, 10) : 0
  kasFisik.value = num
  e.target.value = num > 0 ? num.toLocaleString('id-ID') : ''
}

onMounted(async () => {
  if (!shiftStore.shiftAktif) return
  try {
    const data = await panggilApi(`/shifts/${shiftStore.shiftAktif.id}/ringkasan`)
    ringkasan.value = data
    kasFisik.value = data.kas_ekspektasi || 0
  } catch (err) {
    pesanError.value = 'Gagal mengambil ringkasan shift server, menggunakan perkiraan lokal.'
  } finally {
    sedangMemuat.value = false
  }
})

const selisihKas = computed(() => {
  if (!ringkasan.value) return 0
  return kasFisik.value - ringkasan.value.kas_ekspektasi
})

const wajibCatatan = computed(() => {
  return Math.abs(selisihKas.value) > ambangSelisih
})

async function konfirmasiTutupShift() {
  if (wajibCatatan.value && !catatan.value.trim()) {
    pesanError.value = `Selisih kas melebihi ambang batas (${formatRupiah(ambangSelisih)}). Catatan penjelasan wajib diisi!`
    return
  }

  sedangTutup.value = true
  pesanError.value = ''

  try {
    await shiftStore.tutupShift(kasFisik.value, catatan.value)
    emit('sukses')
  } catch (err) {
    pesanError.value = err.message || 'Gagal menutup shift'
  } finally {
    sedangTutup.value = false
  }
}
</script>

<template>
  <div class="latar-modal">
    <div class="kotak-modal p-6">
      <div class="header-modal">
        <div>
          <h2 class="judul-modal">Tutup Shift Kasir</h2>
          <p class="sub-modal">Hitung uang fisik di laci kasir dan lakukan rekonsiliasi kas.</p>
        </div>
        <button class="tombol-tutup" @click="emit('tutup')" title="Tutup Dialog">
          <X :size="20" />
        </button>
      </div>

      <div v-if="pesanError" class="peringatan-error">
        {{ pesanError }}
      </div>

      <!-- Ringkasan Shift Berwarna & Terang -->
      <div v-if="ringkasan" class="kartu-ringkasan">
        <div class="baris-ringkasan">
          <span class="label-ringkasan">Modal Kas Awal:</span>
          <span class="nilai-ringkasan">{{ formatRupiah(ringkasan.kas_awal) }}</span>
        </div>
        <div class="baris-ringkasan">
          <span class="label-ringkasan">Penjualan Uang Tunai:</span>
          <span class="nilai-ringkasan teks-sukses">+{{ formatRupiah(ringkasan.total_penjualan_tunai) }}</span>
        </div>
        <div class="baris-ringkasan">
          <span class="label-ringkasan">Penjualan QRIS:</span>
          <span class="nilai-ringkasan teks-info">{{ formatRupiah(ringkasan.total_penjualan_qris) }}</span>
        </div>
        <div class="baris-ringkasan">
          <span class="label-ringkasan">Penjualan Transfer:</span>
          <span class="nilai-ringkasan teks-ungu">{{ formatRupiah(ringkasan.total_penjualan_transfer) }}</span>
        </div>
        <div v-if="ringkasan.total_refund_tunai > 0" class="baris-ringkasan">
          <span class="label-ringkasan">Refund / Pengembalian Tunai:</span>
          <span class="nilai-ringkasan teks-bahaya">-{{ formatRupiah(ringkasan.total_refund_tunai) }}</span>
        </div>
        <div class="baris-ringkasan pembatas-atas tebal">
          <span class="label-ringkasan">Total Transaksi Selesai:</span>
          <span class="nilai-ringkasan teks-primer">{{ ringkasan.jumlah_transaksi }} Struk Pembelian</span>
        </div>
      </div>

      <!-- Input Uang Fisik Besar -->
      <div class="grup-form mt-4">
        <label class="label-form">Hitungan Nyata Uang Fisik di Laci Kasir (Rp):</label>
        <div class="input-wrap-besar">
          <span class="awalan-rp">Rp</span>
          <input 
            :value="kasFisik > 0 ? Number(kasFisik).toLocaleString('id-ID') : ''"
            type="text"
            inputmode="numeric"
            class="input-teks input-uang-besar"
            placeholder="0"
            autofocus
            @focus="$event.target.select()"
            @input="tanganiInputKasFisik"
          />
        </div>
      </div>

      <!-- Info Selisih Kas Berwarna Kontras -->
      <div v-if="ringkasan" class="info-selisih" :class="{ 'selisih-aman': selisihKas === 0, 'selisih-bahaya': selisihKas !== 0 }">
        <div class="flex-between">
          <span class="tebal">Status Selisih Kas Fisik:</span>
          <span class="angka-selisih tebal">
            {{ selisihKas === 0 ? 'Sesuai / Pas (Rp 0)' : (selisihKas > 0 ? `Lebih ${formatRupiah(selisihKas)}` : `Kurang ${formatRupiah(Math.abs(selisihKas))}`) }}
          </span>
        </div>
      </div>

      <!-- Catatan Penjelasan jika Selisih -->
      <div class="grup-form mt-4">
        <label class="label-form">
          Catatan Rekonsiliasi Kasir
          <span v-if="wajibCatatan" class="teks-bahaya">* (Wajib diisi karena selisih > Rp 50.000)</span>
        </label>
        <textarea 
          v-model="catatan"
          class="input-teks area-catatan"
          rows="2"
          placeholder="Tuliskan keterangan singkat jika ada uang kas lebih/kurang..."
        ></textarea>
      </div>

      <div class="footer-aksi flex gap-3 mt-6">
        <button class="tombol tombol-sekunder flex-1" @click="emit('tutup')">Batal</button>
        <button 
          class="tombol tombol-bahaya flex-2 tombol-tutup-konfirmasi"
          :disabled="sedangTutup"
          @click="konfirmasiTutupShift"
        >
          <span>{{ sedangTutup ? 'Memproses...' : 'Tutup Shift & Simpan Laporan' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.p-6 { padding: 28px 24px; }
.mt-4 { margin-top: 16px; }
.mt-6 { margin-top: 22px; }
.flex { display: flex; }
.flex-1 { flex: 1; }
.flex-2 { flex: 2; }
.gap-3 { gap: 12px; }
.flex-between { display: flex; justify-content: space-between; align-items: center; }

.header-modal {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
  border-bottom: 2px solid #f1f5f9;
  padding-bottom: 14px;
}
.ikon-tutup-shift {
  width: 44px;
  height: 44px;
  background: #fee2e2;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #dc2626;
}
.judul-modal { font-size: 1.35rem; font-weight: 900; color: #0f172a; }
.sub-modal { font-size: 0.85rem; color: #64748b; font-weight: 600; margin-top: 2px; }

.tombol-tutup {
  background: #f1f5f9;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
}
.tombol-tutup:hover { background: #fee2e2; color: #dc2626; }

.kartu-ringkasan {
  background: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: var(--radius-md);
  padding: 16px;
  font-size: 0.95rem;
}
.baris-ringkasan {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}
.label-ringkasan { color: #475569; font-weight: 600; }
.nilai-ringkasan { font-family: var(--font-angka); font-weight: 800; color: #0f172a; }
.teks-sukses { color: #059669; }
.teks-info { color: #0284c7; }
.teks-ungu { color: #7c3aed; }
.teks-bahaya { color: #dc2626; }
.teks-primer { color: #1d4ed8; }

.pembatas-atas {
  border-top: 2px dashed #cbd5e1;
  padding-top: 10px;
  margin-top: 10px;
}

.label-form {
  font-weight: 800;
  font-size: 0.95rem;
  color: #0f172a;
  display: block;
  margin-bottom: 6px;
}

.input-wrap-besar {
  position: relative;
  display: flex;
  align-items: center;
}
.awalan-rp {
  position: absolute;
  left: 18px;
  font-size: 1.2rem;
  font-weight: 800;
  color: #64748b;
  font-family: var(--font-angka);
}
.input-uang-besar {
  padding-left: 56px;
  font-size: 1.5rem;
  font-weight: 800;
  height: 54px;
  font-family: var(--font-angka);
  color: #0f172a;
  border: 1.5px solid #0f172a;
  background: #ffffff;
  border-radius: var(--radius-md);
}

.info-selisih {
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: 0.95rem;
  margin-top: 14px;
}
.selisih-aman {
  background: #ecfdf5;
  border: 1.5px solid #10b981;
  color: #065f46;
}
.selisih-bahaya {
  background: #fef2f2;
  border: 1.5px solid #ef4444;
  color: #991b1b;
}
.angka-selisih { font-family: var(--font-angka); font-size: 1rem; }

.area-catatan {
  resize: vertical;
}

.peringatan-error {
  background: #fef2f2;
  border: 1.5px solid #fecaca;
  color: #dc2626;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  font-weight: 700;
  margin-bottom: 14px;
}

.tombol-tutup-konfirmasi {
  font-weight: 900;
  font-size: 1.05rem;
}
</style>
