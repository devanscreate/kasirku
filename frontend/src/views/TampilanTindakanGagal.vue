<script setup>
import { ref, onMounted } from 'vue'
import { useKoneksiStore } from '../stores/koneksi'
import { AlertTriangle, RotateCcw, Trash2, CheckCircle2 } from 'lucide-vue-next'

const koneksiStore = useKoneksiStore()
const alasanBuang = ref('')
const idSedangDibuang = ref(null)

onMounted(() => {
  koneksiStore.perbaruiStatus()
})

async function kirimUlang(id) {
  if (confirm('Kirim ulang transaksi ini ke server?')) {
    await koneksiStore.kirimUlangEventGagal(id)
    alert('Event dijadwalkan ulang untuk dikirim ke server')
  }
}

async function buangEvent(id) {
  const alasan = prompt('Masukkan alasan wajib membuang event ini (F-05):')
  if (!alasan || alasan.trim().length < 5) {
    alert('Alasan pembuangan minimal 5 karakter!')
    return
  }
  await koneksiStore.buangEventGagal(id, alasan)
  alert('Event telah dibuang dan dicatat.')
}
</script>

<template>
  <div class="halaman-tindakan">
    <div class="panel-kartu">
      <div class="header-halaman">
        <div class="flex items-center gap-4">
          <div class="ikon-header-peringatan">
            <AlertTriangle :size="28" />
          </div>
          <div>
            <h1 class="judul-halaman">Daftar Perlu Tindakan (Event Outbox Gagal)</h1>
            <p class="sub-halaman">Daftar transaksi lokal yang ditolak oleh cloud server (Error 422) karena format data tidak sesuai atau bentrok integritas.</p>
          </div>
        </div>
      </div>

      <div class="daftar-gagal mt-5">
        <div v-if="koneksiStore.daftarGagal.length === 0" class="state-bersih p-8 text-center">
          <CheckCircle2 :size="56" class="teks-sukses mb-3" />
          <h3 class="tebal judul-bersih">Semua Antrean Sinkronisasi Bersih</h3>
          <p class="teks-redup">Alhamdulillah, tidak ada transaksi kasir yang gagal dikirim ke cloud saat ini.</p>
        </div>

        <div v-for="item in koneksiStore.daftarGagal" :key="item.id" class="kartu-gagal">
          <div class="info-gagal">
            <div class="judul-event">
              <span class="badge-tipe-event">{{ item.tipe_peristiwa.toUpperCase() }}</span>
              <span class="tebal teks-id-event font-angka">ID Event: {{ item.id }}</span>
            </div>
            <div class="pesan-error-teks mt-2">
              ⚠️ <b>Penyebab Penolakan Server:</b> {{ item.pesan_kesalahan || 'Validasi skema data gagal' }}
            </div>
            <div class="teks-waktu-gagal mt-1">
              Dibuat pada: {{ new Date(item.dibuat_pada).toLocaleString('id-ID') }} | Percobaan Sinkron: {{ item.percobaan }}x
            </div>
          </div>

          <div class="tombol-aksi-gagal">
            <button class="tombol-kirim-ulang" @click="kirimUlang(item.id)">
              <RotateCcw :size="15" />
              <span>Kirim Ulang ke Cloud</span>
            </button>
            <button class="tombol-buang" @click="buangEvent(item.id)">
              <Trash2 :size="15" />
              <span>Buang dengan Catatan</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.halaman-tindakan {
  padding: 24px;
}

.panel-kartu {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
}

.header-halaman {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 20px;
  border-bottom: 1px solid #f1f5f9;
}

.ikon-header-peringatan {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: #fef2f2;
  border: 1.5px solid #fca5a5;
  color: #dc2626;
  display: flex;
  align-items: center;
  justify-content: center;
}

.judul-halaman {
  font-size: 1.45rem;
  font-weight: 800;
  color: #0f172a;
}

.sub-halaman {
  font-size: 0.9rem;
  color: #475569;
  margin-top: 2px;
}

.state-bersih {
  background: #f0fdf4;
  border: 1.5px dashed #86efac;
  border-radius: var(--radius-lg);
  padding: 40px;
}

.judul-bersih {
  font-size: 1.2rem;
  color: #15803d;
}

.kartu-gagal {
  background: #fffafa;
  border: 1.5px solid #fecaca;
  border-radius: var(--radius-md);
  padding: 18px;
  margin-bottom: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.badge-tipe-event {
  display: inline-block;
  padding: 3px 8px;
  background: #fee2e2;
  color: #b91c1c;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  font-weight: 800;
}

.teks-id-event {
  color: #0f172a;
  font-size: 0.9rem;
}

.pesan-error-teks {
  font-size: 0.875rem;
  color: #dc2626;
  background: #ffffff;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid #fecaca;
  display: inline-block;
}

.teks-waktu-gagal {
  font-size: 0.8rem;
  color: #64748b;
}

.tombol-aksi-gagal {
  display: flex;
  gap: 10px;
}

.tombol-kirim-ulang {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: #1e3a8a;
  color: #ffffff;
  border: none;
  border-radius: var(--radius-sm);
  font-weight: 700;
  font-size: 0.825rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tombol-kirim-ulang:hover {
  background: #1d4ed8;
}

.tombol-buang {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: #fef2f2;
  border: 1.5px solid #fecaca;
  color: #dc2626;
  border-radius: var(--radius-sm);
  font-weight: 700;
  font-size: 0.825rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tombol-buang:hover {
  background: #dc2626;
  color: #ffffff;
}

.font-angka { font-family: var(--font-angka); }
.tebal { font-weight: 700; }
.teks-sukses { color: #16a34a; }
.teks-redup { color: #64748b; font-size: 0.875rem; }
.mt-5 { margin-top: 20px; }
.mt-2 { margin-top: 8px; }
.mt-1 { margin-top: 4px; }
.mb-3 { margin-bottom: 12px; }
.p-8 { padding: 32px; }
.flex { display: flex; }
.items-center { align-items: center; }
.gap-4 { gap: 16px; }
.text-center { text-align: center; }
</style>
