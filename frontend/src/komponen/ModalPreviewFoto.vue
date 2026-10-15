<script setup>
import { onMounted, onUnmounted } from 'vue'
import { X, ShoppingBag, Tag, Barcode, Check, AlertCircle, Package } from 'lucide-vue-next'

const props = defineProps({
  foto: {
    type: String,
    default: null
  },
  nama: {
    type: String,
    required: true
  },
  sku: {
    type: String,
    default: ''
  },
  barcode: {
    type: String,
    default: ''
  },
  kategori: {
    type: String,
    default: 'Umum'
  },
  harga: {
    type: Number,
    default: 0
  },
  stok: {
    type: Number,
    default: 0
  },
  minStok: {
    type: Number,
    default: 5
  },
  tampilkanAksiKeranjang: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['tutup', 'tambah'])

const formatRupiah = (val) => 'Rp ' + Number(val || 0).toLocaleString('id-ID')

function tanganiKeydown(e) {
  if (e.key === 'Escape') {
    emit('tutup')
  }
}

onMounted(() => {
  window.addEventListener('keydown', tanganiKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', tanganiKeydown)
})
</script>

<template>
  <div class="latar-modal-preview" @click.self="emit('tutup')">
    <div class="kartu-modal-preview">
      <!-- Tombol Tutup Silang -->
      <button class="btn-tutup-silang" @click="emit('tutup')" title="Tutup pratinjau (Esc)">
        <X :size="22" />
      </button>

      <!-- Wadah Gambar Utama -->
      <div class="wadah-gambar-besar">
        <img 
          v-if="foto" 
          :src="foto" 
          :alt="nama" 
          class="img-preview-utama" 
        />
        <div v-else class="img-preview-kosong">
          <Package :size="64" class="ikon-kosong-preview" />
          <span class="teks-belum-ada-foto">Belum Ada Foto Produk</span>
        </div>
      </div>

      <!-- Rincian Produk di Bawah Gambar -->
      <div class="konten-detail-preview">
        <div class="baris-kategori-stok">
          <span class="badge-kategori-preview">
            <Tag :size="13" />
            <span>{{ kategori || 'Umum' }}</span>
          </span>

          <span 
            class="badge-stok-preview"
            :class="stok <= 0 ? 'stok-habis' : (stok <= minStok ? 'stok-menipis' : 'stok-aman')"
          >
            <AlertCircle v-if="stok <= minStok" :size="13" />
            <Check v-else :size="13" />
            <span>{{ stok <= 0 ? 'Stok Habis' : `Stok: ${stok} Unit` }}</span>
          </span>
        </div>

        <h3 class="nama-produk-preview">{{ nama }}</h3>

        <div class="baris-kode-produk">
          <span v-if="sku" class="kode-sku">SKU: <strong>{{ sku }}</strong></span>
          <span v-if="barcode" class="kode-barcode">
            <Barcode :size="14" />
            <span>{{ barcode }}</span>
          </span>
        </div>

        <div class="harga-produk-preview">
          {{ formatRupiah(harga) }}
        </div>

        <!-- Tombol Aksi di Bawah -->
        <div class="baris-tombol-preview">
          <button class="tombol-tutup-preview" @click="emit('tutup')">
            Tutup
          </button>
          <button 
            v-if="tampilkanAksiKeranjang" 
            class="tombol-tambah-preview" 
            :disabled="stok <= 0"
            @click="emit('tambah')"
          >
            <ShoppingBag :size="18" />
            <span>{{ stok <= 0 ? 'Stok Habis' : '+ Masukkan ke Keranjang' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.latar-modal-preview {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.78);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
  animation: fadeIn 0.2s ease-out;
}

.kartu-modal-preview {
  background: #ffffff;
  border-radius: 18px;
  max-width: 480px;
  width: 100%;
  overflow: hidden;
  position: relative;
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.8);
  animation: popIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.btn-tutup-silang {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  color: #334155;
  border: 1px solid #cbd5e1;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  transition: all 0.2s ease;
}
.btn-tutup-silang:hover {
  background: #fee2e2;
  color: #dc2626;
  border-color: #fca5a5;
  transform: scale(1.08);
}

.wadah-gambar-besar {
  width: 100%;
  height: 280px;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-bottom: 2px solid #e2e8f0;
}

.img-preview-utama {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  transition: transform 0.3s ease;
}
.img-preview-utama:hover {
  transform: scale(1.04);
}

.img-preview-kosong {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #94a3b8;
}
.ikon-kosong-preview {
  opacity: 0.6;
}
.teks-belum-ada-foto {
  font-size: 0.9rem;
  font-weight: 700;
}

.konten-detail-preview {
  padding: 20px;
}

.baris-kategori-stok {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.badge-kategori-preview {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 800;
  text-transform: uppercase;
}

.badge-stok-preview {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 800;
}
.stok-aman {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}
.stok-menipis {
  background: #fffbeb;
  color: #b45309;
  border: 1px solid #fde68a;
}
.stok-habis {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.nama-produk-preview {
  font-size: 1.25rem;
  font-weight: 900;
  color: #0f172a;
  line-height: 1.35;
  margin-bottom: 6px;
}

.baris-kode-produk {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.85rem;
  color: #64748b;
  margin-bottom: 14px;
}
.kode-barcode {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.harga-produk-preview {
  font-size: 1.7rem;
  font-weight: 900;
  color: #059669;
  font-family: var(--font-angka, sans-serif);
  margin-bottom: 18px;
}

.baris-tombol-preview {
  display: flex;
  gap: 12px;
}

.tombol-tutup-preview {
  flex: 1;
  padding: 12px;
  background: #f1f5f9;
  color: #334155;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
}
.tombol-tutup-preview:hover {
  background: #e2e8f0;
}

.tombol-tambah-preview {
  flex: 2;
  padding: 12px 18px;
  background: #2563eb;
  color: #ffffff;
  border: none;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);
  transition: all 0.2s ease;
}
.tombol-tambah-preview:hover:not(:disabled) {
  background: #1d4ed8;
  transform: translateY(-1px);
}
.tombol-tambah-preview:disabled {
  background: #94a3b8;
  cursor: not-allowed;
  box-shadow: none;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes popIn {
  from { opacity: 0; transform: scale(0.92); }
  to { opacity: 1; transform: scale(1); }
}
</style>
