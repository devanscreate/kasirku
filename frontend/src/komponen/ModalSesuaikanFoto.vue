<script setup>
import { ref, onMounted, watch } from 'vue'
import { bacaBerkasKeImage, sesuaikanBingkaiPersegi } from '../layanan/utilitas_gambar'
import { X, ZoomIn, ZoomOut, Move, Check, RotateCcw } from 'lucide-vue-next'

const props = defineProps({
  berkas: {
    type: [Object, String],
    required: true
  }
})

const emit = defineEmits(['selesai', 'batal'])

const imgElement = ref(null)
const kanvasRef = ref(null)

const zoom = ref(1)
const panX = ref(0)
const panY = ref(0)
const sedangMuat = ref(true)
const pesanError = ref('')
const perkiraanKb = ref(0)

const sedangGeser = ref(false)
const titikAwal = ref({ x: 0, y: 0, panX: 0, panY: 0 })

function mulaiGeser(e) {
  sedangGeser.value = true
  const clientX = e.touches ? e.touches[0].clientX : e.clientX
  const clientY = e.touches ? e.touches[0].clientY : e.clientY
  titikAwal.value = {
    x: clientX,
    y: clientY,
    panX: panX.value,
    panY: panY.value
  }
}

function lakukanGeser(e) {
  if (!sedangGeser.value) return
  const clientX = e.touches ? e.touches[0].clientX : e.clientX
  const clientY = e.touches ? e.touches[0].clientY : e.clientY
  const deltaX = clientX - titikAwal.value.x
  const deltaY = clientY - titikAwal.value.y

  // Konversi pergeseran piksel ke persentase pan (-50 sampai 50)
  const shiftX = Math.round(deltaX / 2.4)
  const shiftY = Math.round(deltaY / 2.4)

  panX.value = Math.max(-50, Math.min(50, titikAwal.value.panX + shiftX))
  panY.value = Math.max(-50, Math.min(50, titikAwal.value.panY + shiftY))
}

function hentiGeser() {
  sedangGeser.value = false
}

async function inisialisasiGambar() {
  sedangMuat.value = true
  pesanError.value = ''
  try {
    const { img } = await bacaBerkasKeImage(props.berkas)
    imgElement.value = img
    gambarKeKanvas()
  } catch (err) {
    pesanError.value = err.message || 'Gagal membaca berkas gambar'
  } finally {
    sedangMuat.value = false
  }
}

function gambarKeKanvas() {
  if (!imgElement.value || !kanvasRef.value) return

  const hasil = sesuaikanBingkaiPersegi(
    imgElement.value, 
    zoom.value, 
    panX.value, 
    panY.value, 
    240, 
    0.8
  )
  perkiraanKb.value = hasil.perkiraanKb

  const ctx = kanvasRef.value.getContext('2d')
  const imgHasil = new Image()
  imgHasil.src = hasil.dataUrl
  imgHasil.onload = () => {
    ctx.clearRect(0, 0, 240, 240)
    ctx.drawImage(imgHasil, 0, 0, 240, 240)
  }
}

watch([zoom, panX, panY], () => {
  gambarKeKanvas()
})

function resetPosisi() {
  zoom.value = 1
  panX.value = 0
  panY.value = 0
}

function terapkanFoto() {
  if (!imgElement.value) return
  // Ekspor final standar bingkai 1:1 persegi 200x200 WebP hemat memori
  const final = sesuaikanBingkaiPersegi(
    imgElement.value, 
    zoom.value, 
    panX.value, 
    panY.value, 
    200, 
    0.7
  )
  emit('selesai', final)
}

onMounted(() => {
  inisialisasiGambar()
})
</script>

<template>
  <div class="latar-modal-atur-foto" @click.self="emit('batal')">
    <div class="kartu-modal-atur">
      <!-- Header -->
      <div class="header-atur">
        <div>
          <h3 class="judul-atur">Atur Bingkai Foto Produk</h3>
          <p class="sub-atur">Sesuaikan ukuran dan posisi foto agar pas dan seragam di layar kasir POS.</p>
        </div>
        <button class="btn-tutup-atur" @click="emit('batal')"><X :size="20" /></button>
      </div>

      <div v-if="pesanError" class="pesan-error-atur">{{ pesanError }}</div>

      <!-- Area Pratinjau Bingkai Persegi 1:1 -->
      <div class="area-bingkai-preview">
        <div 
          class="wadah-kanvas-bingkai"
          :class="{ 'sedang-geser': sedangGeser }"
          @mousedown="mulaiGeser"
          @mousemove="lakukanGeser"
          @mouseup="hentiGeser"
          @mouseleave="hentiGeser"
          @touchstart.passive="mulaiGeser"
          @touchmove.passive="lakukanGeser"
          @touchend="hentiGeser"
          title="Klik & tahan untuk menggeser posisi foto"
        >
          <canvas ref="kanvasRef" width="240" height="240" class="kanvas-preview"></canvas>
          <div class="garis-bantu-tengah"></div>
          <div class="sudut-bingkai sudut-tl"></div>
          <div class="sudut-bingkai sudut-tr"></div>
          <div class="sudut-bingkai sudut-bl"></div>
          <div class="sudut-bingkai sudut-br"></div>
          <div class="overlay-petunjuk-geser">
            <Move :size="14" />
            <span>Geser langsung atau gunakan kontrol</span>
          </div>
        </div>
        <div class="keterangan-bingkai">
          <span>Format Bingkai Seragam (1:1 Persegi) • ~{{ perkiraanKb }} KB</span>
        </div>
      </div>

      <!-- Kontrol Penyesuaian (Zoom & Geser) -->
      <div class="kontrol-penyesuaian">
        <!-- Slider Zoom -->
        <div class="grup-slider">
          <div class="label-slider">
            <span class="flex items-center gap-1.5 font-bold">
              <ZoomIn :size="15" class="teks-primer" />
              <span>Ukuran Zoom (Perbesar / Perkecil)</span>
            </span>
            <span class="nilai-slider">{{ Math.round(zoom * 100) }}%</span>
          </div>
          <div class="baris-slider">
            <button class="btn-step" @click="zoom = Math.max(1, +(zoom - 0.1).toFixed(2))">
              <ZoomOut :size="16" />
            </button>
            <input 
              v-model.number="zoom" 
              type="range" 
              min="1" 
              max="2.5" 
              step="0.05" 
              class="input-range" 
            />
            <button class="btn-step" @click="zoom = Math.min(2.5, +(zoom + 0.1).toFixed(2))">
              <ZoomIn :size="16" />
            </button>
          </div>
        </div>

        <!-- Slider Geser Horisontal (X) -->
        <div class="grup-slider mt-2">
          <div class="label-slider">
            <span class="flex items-center gap-1.5 font-bold">
              <Move :size="15" class="teks-primer" />
              <span>Geser Kiri / Kanan</span>
            </span>
            <span class="nilai-slider">{{ panX > 0 ? `+${panX}%` : `${panX}%` }}</span>
          </div>
          <input 
            v-model.number="panX" 
            type="range" 
            min="-50" 
            max="50" 
            step="1" 
            class="input-range" 
          />
        </div>

        <!-- Slider Geser Vertikal (Y) -->
        <div class="grup-slider mt-2">
          <div class="label-slider">
            <span class="flex items-center gap-1.5 font-bold">
              <Move :size="15" class="teks-primer" />
              <span>Geser Atas / Bawah</span>
            </span>
            <span class="nilai-slider">{{ panY > 0 ? `+${panY}%` : `${panY}%` }}</span>
          </div>
          <input 
            v-model.number="panY" 
            type="range" 
            min="-50" 
            max="50" 
            step="1" 
            class="input-range" 
          />
        </div>

        <button class="btn-reset-posisi mt-2" @click="resetPosisi">
          <RotateCcw :size="14" />
          <span>Kembalikan ke Tengah</span>
        </button>
      </div>

      <!-- Footer Tombol Aksi -->
      <div class="footer-atur">
        <button class="tombol-batal-atur" @click="emit('batal')">
          Batal
        </button>
        <button class="tombol-terapkan-atur" @click="terapkanFoto">
          <Check :size="18" />
          <span>Terapkan & Simpan Foto</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.latar-modal-atur-foto {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.78);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
  padding: 16px;
}

.kartu-modal-atur {
  background: #ffffff;
  border-radius: 18px;
  max-width: 460px;
  width: 100%;
  padding: 24px;
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.3);
  border: 1px solid #e2e8f0;
}

.header-atur {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}
.judul-atur {
  font-size: 1.25rem;
  font-weight: 900;
  color: #0f172a;
}
.sub-atur {
  font-size: 0.8rem;
  color: #64748b;
  margin-top: 3px;
}
.btn-tutup-atur {
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
}
.btn-tutup-atur:hover {
  background: #fee2e2;
  color: #dc2626;
}

.area-bingkai-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin: 10px 0 16px 0;
}

.wadah-kanvas-bingkai {
  width: 240px;
  height: 240px;
  position: relative;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.12);
  border: 2px solid #2563eb;
  background: #f8fafc;
  cursor: grab;
  user-select: none;
  touch-action: none;
}

.wadah-kanvas-bingkai.sedang-geser {
  cursor: grabbing;
}

.kanvas-preview {
  width: 100%;
  height: 100%;
  display: block;
  pointer-events: none;
}

.overlay-petunjuk-geser {
  position: absolute;
  bottom: 8px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(15, 23, 42, 0.72);
  color: #ffffff;
  font-size: 0.68rem;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  gap: 5px;
  pointer-events: none;
  white-space: nowrap;
  backdrop-filter: blur(2px);
}

.garis-bantu-tengah {
  position: absolute;
  inset: 0;
  border: 1px dashed rgba(37, 99, 235, 0.25);
  pointer-events: none;
}

.sudut-bingkai {
  position: absolute;
  width: 12px;
  height: 12px;
  border: 2px solid #2563eb;
  pointer-events: none;
}
.sudut-tl { top: 6px; left: 6px; border-right: none; border-bottom: none; }
.sudut-tr { top: 6px; right: 6px; border-left: none; border-bottom: none; }
.sudut-bl { bottom: 6px; left: 6px; border-right: none; border-top: none; }
.sudut-br { bottom: 6px; right: 6px; border-left: none; border-top: none; }

.keterangan-bingkai {
  margin-top: 8px;
  font-size: 0.78rem;
  font-weight: 700;
  color: #059669;
}

.kontrol-penyesuaian {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 20px;
}

.grup-slider {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.label-slider {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
  color: #334155;
}
.nilai-slider {
  font-family: var(--font-angka);
  font-weight: 800;
  color: #2563eb;
  font-size: 0.85rem;
}

.baris-slider {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-step {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #334155;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-step:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1d4ed8;
}

.input-range {
  flex: 1;
  height: 6px;
  border-radius: 4px;
  accent-color: #2563eb;
  cursor: pointer;
}

.btn-reset-posisi {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
  transition: all 0.2s ease;
}
.btn-reset-posisi:hover {
  color: #2563eb;
  background: #eff6ff;
}

.footer-atur {
  display: flex;
  gap: 10px;
}

.tombol-batal-atur {
  flex: 1;
  padding: 12px;
  background: #f1f5f9;
  color: #334155;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  font-weight: 800;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s ease;
}
.tombol-batal-atur:hover {
  background: #e2e8f0;
}

.tombol-terapkan-atur {
  flex: 2;
  padding: 12px;
  background: #059669;
  color: #ffffff;
  border: none;
  border-radius: 10px;
  font-weight: 800;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(5, 150, 105, 0.3);
  transition: all 0.2s ease;
}
.tombol-terapkan-atur:hover {
  background: #047857;
}

.teks-primer { color: #2563eb; }
.mt-2 { margin-top: 8px; }
.flex { display: flex; }
.items-center { align-items: center; }
.gap-1\.5 { gap: 6px; }
.font-bold { font-weight: 700; }
</style>
