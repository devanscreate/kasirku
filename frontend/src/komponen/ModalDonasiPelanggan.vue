<script setup>
import { ref, onMounted, computed } from 'vue'
import { 
  HeartHandshake, 
  Search, 
  Banknote, 
  ShoppingBag, 
  Printer, 
  X, 
  Check, 
  Sparkles, 
  History, 
  User, 
  Phone, 
  Calendar,
  AlertCircle,
  Coins
} from 'lucide-vue-next'
import { 
  ambilDaftarPelangganDonasi, 
  cekSaldoPelanggan, 
  cairkanDonasiPelanggan, 
  ambilRingkasanDonasiToko,
  bersihkanNomorHp 
} from '../layanan/donasi'
import { useShiftStore } from '../stores/shift'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  apakahDariPOS: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['tutup', 'terapkanPotongBelanja'])

const shiftStore = useShiftStore()
const authStore = useAuthStore()

const kueriCari = ref('')
const sedangMemuat = ref(false)
const daftarPelanggan = ref([])
const ringkasanToko = ref({
  total_donasi_terkumpul: 0,
  total_dicairkan: 0,
  saldo_aktif_keseluruhan: 0,
  jumlah_pelanggan_aktif: 0
})

const pelangganTerpilih = ref(null)
const riwayatTerpilih = ref([])
const pesanSukses = ref('')
const pesanError = ref('')

// State Dialog Pencairan Tunai
const tampilDialogCairTunai = ref(false)
const nominalCairTunai = ref(0)
const sedangProsesCair = ref(false)
const formatRupiah = (val) => 'Rp ' + Number(val || 0).toLocaleString('id-ID')

function tanganiInputNominalCair(e) {
  const digitOnly = e.target.value.replace(/\D/g, '')
  const num = digitOnly ? parseInt(digitOnly, 10) : 0
  nominalCairTunai.value = num
  e.target.value = num > 0 ? num.toLocaleString('id-ID') : ''
}

async function muatData() {
  sedangMemuat.value = true
  pesanError.value = ''
  try {
    const [ringkasan, list] = await Promise.all([
      ambilRingkasanDonasiToko(),
      ambilDaftarPelangganDonasi(kueriCari.value)
    ])
    ringkasanToko.value = ringkasan || ringkasanToko.value
    daftarPelanggan.value = list || []
  } catch (err) {
    pesanError.value = 'Gagal memuat data donasi: ' + (err.message || 'Error jaringan')
  } finally {
    sedangMemuat.value = false
  }
}

async function cariPelanggan() {
  if (!kueriCari.value.trim()) {
    await muatData()
    return
  }
  sedangMemuat.value = true
  try {
    const list = await ambilDaftarPelangganDonasi(kueriCari.value)
    daftarPelanggan.value = list || []

    // Jika pencarian berupa nomor HP lengkap dan ada kecocokan persis
    const exact = list.find(p => p.nomor_hp === bersihkanNomorHp(kueriCari.value))
    if (exact) {
      await pilihPelanggan(exact.nomor_hp)
    } else if (list.length === 1) {
      await pilihPelanggan(list[0].nomor_hp)
    }
  } catch (err) {
    pesanError.value = 'Gagal mencari pelanggan'
  } finally {
    sedangMemuat.value = false
  }
}

async function pilihPelanggan(nomorHp) {
  pesanSukses.value = ''
  pesanError.value = ''
  sedangMemuat.value = true
  try {
    const data = await cekSaldoPelanggan(nomorHp)
    pelangganTerpilih.value = data
    riwayatTerpilih.value = data?.riwayat || []
  } catch (err) {
    pesanError.value = 'Gagal memuat rincian saldo pelanggan: ' + err.message
  } finally {
    sedangMemuat.value = false
  }
}

function bukaDialogCairTunai() {
  if (!pelangganTerpilih.value || pelangganTerpilih.value.total_saldo <= 0) {
    alert('Saldo tabungan pelanggan masih 0 atau tidak mencukupi untuk dicairkan.')
    return
  }
  nominalCairTunai.value = pelangganTerpilih.value.total_saldo
  tampilDialogCairTunai.value = true
}

async function konfirmasiCairTunai() {
  if (nominalCairTunai.value <= 0 || nominalCairTunai.value > pelangganTerpilih.value.total_saldo) {
    alert('Nominal pencairan tidak valid!')
    return
  }

  sedangProsesCair.value = true
  try {
    const hasil = await cairkanDonasiPelanggan({
      nomorHp: pelangganTerpilih.value.nomor_hp,
      nominal: nominalCairTunai.value,
      tipe: 'tunai',
      idShift: shiftStore.shiftAktif?.id,
      catatan: `Penarikan tunai laci oleh kasir ${authStore.namaLengkap}`
    })

    buktiCairTerakhir.value = {
      ...hasil,
      namaKasir: authStore.namaLengkap,
      waktu: new Date().toLocaleString('id-ID')
    }

    pesanSukses.value = `Uang tunai Rp ${Number(nominalCairTunai.value).toLocaleString('id-ID')} berhasil dicairkan kepada pelanggan. Silakan berikan uang dari laci kasir.`
    tampilDialogCairTunai.value = false
    await pilihPelanggan(pelangganTerpilih.value.nomor_hp)
    await muatData()
  } catch (err) {
    alert('Gagal mencairkan donasi: ' + (err.message || 'Kesalahan server'))
  } finally {
    sedangProsesCair.value = false
  }
}

function gunakanUntukPotongBelanja() {
  if (!pelangganTerpilih.value || pelangganTerpilih.value.total_saldo <= 0) {
    alert('Saldo tabungan pelanggan masih 0.')
    return
  }
  emit('terapkanPotongBelanja', {
    nomorHp: pelangganTerpilih.value.nomor_hp,
    namaPelanggan: pelangganTerpilih.value.nama_pelanggan,
    saldoMaksimal: pelangganTerpilih.value.total_saldo
  })
  emit('tutup')
}

function cetakStrukPencairan() {
  if (!buktiCairTerakhir.value) return
  window.print()
}

onMounted(() => {
  muatData()
})
</script>

<template>
  <div class="latar-modal-donasi" @click.self="emit('tutup')">
    <div class="kartu-modal-donasi">
      <!-- Header Modal -->
      <div class="header-modal-donasi">
        <div class="flex items-center gap-3">
          <div class="ikon-donasi-header">
            <HeartHandshake :size="26" />
          </div>
          <div>
            <h2 class="judul-donasi-header">Tabungan & Donasi Kembalian Pelanggan</h2>
            <p class="sub-donasi-header">
              Akumulasi kembalian belanja pembeli selama 1 bulan yang dapat dicairkan tunai atau ditukarkan belanja.
            </p>
          </div>
        </div>
        <button class="btn-tutup-donasi" @click="emit('tutup')" title="Tutup Modal (Esc)">
          <X :size="22" />
        </button>
      </div>

      <!-- Ringkasan Statistik Toko (Berwarna Menarik & Jelas) -->
      <div class="grid-ringkasan-donasi">
        <div class="kartu-stat stat-hijau">
          <div class="label-stat">TOTAL TERKUMPUL</div>
          <div class="angka-stat font-angka">{{ formatRupiah(ringkasanToko.total_donasi_terkumpul) }}</div>
          <div class="sub-stat">Dari seluruh kembalian pembeli</div>
        </div>
        <div class="kartu-stat stat-biru">
          <div class="label-stat">SALDO AKTIF BELUM DICAIRKAN</div>
          <div class="angka-stat font-angka">{{ formatRupiah(ringkasanToko.saldo_aktif_keseluruhan) }}</div>
          <div class="sub-stat">Siap ditukarkan uang cash / belanja</div>
        </div>
        <div class="kartu-stat stat-kuning">
          <div class="label-stat">SUDAH DICAIRKAN</div>
          <div class="angka-stat font-angka">{{ formatRupiah(ringkasanToko.total_dicairkan) }}</div>
          <div class="sub-stat">Telah dikembalikan ke pembeli</div>
        </div>
        <div class="kartu-stat stat-ungu">
          <div class="label-stat">JUMLAH PELANGGAN</div>
          <div class="angka-stat font-angka">{{ ringkasanToko.jumlah_pelanggan_aktif }} Orang</div>
          <div class="sub-stat">Terdaftar menabung kembalian</div>
        </div>
      </div>

      <!-- Bilah Pencarian Pembeli -->
      <div class="bar-pencarian-donasi mt-4">
        <div class="wrap-input-cari-donasi">
          <Search :size="20" class="ikon-cari-donasi" />
          <input 
            v-model="kueriCari" 
            type="text" 
            class="input-cari-donasi" 
            placeholder="Cari nomor HP pembeli (contoh: 08123456789) atau nama..."
            @keydown.enter="cariPelanggan"
          />
        </div>
        <button class="tombol tombol-primer btn-cari-aksi" @click="cariPelanggan">
          <span>Cari Pembeli</span>
        </button>
      </div>

      <!-- Pesan Notifikasi Sukses / Error -->
      <div v-if="pesanSukses" class="pesan-notif-sukses mt-3">
        <Check :size="18" />
        <span>{{ pesanSukses }}</span>
      </div>
      <div v-if="pesanError" class="pesan-notif-error mt-3">
        <AlertCircle :size="18" />
        <span>{{ pesanError }}</span>
      </div>

      <!-- Konten Utama: 2 Kolom (Detail Pelanggan Terpilih & Daftar Pelanggan) -->
      <div class="grid-konten-donasi mt-4">
        <!-- Kolom Kiri: Kartu Rincian Saldo & Aksi Pencairan Pelanggan Terpilih -->
        <div class="kolom-detail-pelanggan">
          <div v-if="pelangganTerpilih" class="kartu-detail-saldo">
            <div class="header-pelanggan-terpilih">
              <div class="flex items-center gap-3">
                <div class="avatar-pelanggan">
                  <User :size="24" />
                </div>
                <div>
                  <h3 class="nama-pelanggan-teks">{{ pelangganTerpilih.nama_pelanggan || 'Pelanggan Toko' }}</h3>
                  <div class="hp-pelanggan-teks">
                    <Phone :size="14" />
                    <span>{{ pelangganTerpilih.nomor_hp }}</span>
                  </div>
                </div>
              </div>
              <span class="badge-status-tabungan">
                ⭐ Aktif Menabung
              </span>
            </div>

            <!-- Kotak Saldo Besar & Bersih -->
            <div class="kotak-saldo-akumulasi mt-4">
              <div class="info-saldo-kiri">
                <div class="label-saldo-besar">TOTAL SALDO TERKUMPUL</div>
                <div class="angka-saldo-besar font-angka">{{ formatRupiah(pelangganTerpilih.total_saldo) }}</div>
                <div class="sub-saldo-bulan">
                  Akumulasi Bulan Ini: <strong>{{ formatRupiah(pelangganTerpilih.total_donasi_bulan_ini) }}</strong>
                </div>
              </div>
              <div class="ikon-koin-hias">
                <Coins :size="48" />
              </div>
            </div>

            <!-- Tombol Aksi Pencairan Sesuai Flowchart User -->
            <div class="area-tombol-pencairan mt-4">
              <div class="label-pencairan-pilihan">Pilihan Penukaran / Pencairan Saldo:</div>
              <div class="grid-tombol-pencairan">
                <!-- Pilihan A: Ditukarkan Uang Cash -->
                <button 
                  type="button" 
                  class="btn-aksi-cair btn-cair-cash"
                  :disabled="pelangganTerpilih.total_saldo <= 0"
                  @click="bukaDialogCairTunai"
                >
                  <Banknote :size="22" />
                  <div class="teks-btn-aksi">
                    <span class="judul-aksi">A. Tukarkan Uang Cash</span>
                    <span class="sub-aksi">Berikan uang tunai dari laci kasir</span>
                  </div>
                </button>

                <!-- Pilihan B: Potong Belanjaan -->
                <button 
                  type="button" 
                  class="btn-aksi-cair btn-cair-belanja"
                  :disabled="pelangganTerpilih.total_saldo <= 0"
                  @click="gunakanUntukPotongBelanja"
                >
                  <ShoppingBag :size="22" />
                  <div class="teks-btn-aksi">
                    <span class="judul-aksi">B. Potong Belanjaan</span>
                    <span class="sub-aksi">Gunakan saldo untuk bayar belanja POS</span>
                  </div>
                </button>
              </div>
            </div>

            <!-- Riwayat Mutasi Donasi Pelanggan Terpilih -->
            <div class="area-riwayat-pelanggan mt-4">
              <div class="judul-riwayat-pelanggan">
                <History :size="16" />
                <span>Riwayat Setoran Kembalian & Pencairan</span>
              </div>
              <div class="tabel-mini-riwayat">
                <div 
                  v-for="r in riwayatTerpilih" 
                  :key="r.id"
                  class="baris-riwayat-item"
                  :class="r.tipe === 'setor_kembalian' ? 'item-setor' : 'item-cair'"
                >
                  <div class="info-riwayat-kiri">
                    <div class="tipe-riwayat">
                      {{ r.tipe === 'setor_kembalian' ? 'Donasi Kembalian Belanja' : (r.tipe === 'cair_tunai' ? 'Penarikan Uang Tunai' : 'Potongan Belanja POS') }}
                    </div>
                    <div class="waktu-riwayat">
                      {{ new Date(r.dibuat_pada).toLocaleString('id-ID') }}
                      <span v-if="r.nomor_struk" class="struk-info">• Struk: {{ r.nomor_struk }}</span>
                    </div>
                  </div>
                  <div class="nominal-riwayat font-angka">
                    {{ r.tipe === 'setor_kembalian' ? '+' : '-' }}{{ formatRupiah(r.nominal) }}
                  </div>
                </div>

                <div v-if="riwayatTerpilih.length === 0" class="state-riwayat-kosong">
                  Belum ada riwayat mutasi donasi untuk nomor ini.
                </div>
              </div>
            </div>
          </div>

          <!-- Placeholder Jika Belum Ada Pelanggan yang Dipilih -->
          <div v-else class="placeholder-pilih-pelanggan">
            <HeartHandshake :size="54" class="ikon-placeholder-redup" />
            <h3 class="judul-placeholder">Pilih atau Cari Pembeli</h3>
            <p class="sub-placeholder">
              Ketik nomor HP pembeli di atas atau pilih dari daftar pelanggan di sebelah kanan untuk melihat total saldo tabungan donasi yang terkumpul.
            </p>
          </div>
        </div>

        <!-- Kolom Kanan: Daftar Pembeli yang Memiliki Saldo Tabungan -->
        <div class="kolom-daftar-pelanggan">
          <div class="header-daftar-kanan">
            <h3 class="judul-daftar-kanan">Daftar Pembeli Terdaftar ({{ daftarPelanggan.length }})</h3>
            <span class="sub-daftar-kanan">Klik pembeli untuk melihat saldo</span>
          </div>

          <div class="daftar-pelanggan-scroll">
            <div 
              v-for="p in daftarPelanggan" 
              :key="p.nomor_hp"
              class="kartu-item-pelanggan"
              :class="{ 'aktif': pelangganTerpilih?.nomor_hp === p.nomor_hp }"
              @click="pilihPelanggan(p.nomor_hp)"
            >
              <div class="item-pelanggan-kiri">
                <div class="nama-item-p">{{ p.nama_pelanggan || 'Pelanggan' }}</div>
                <div class="hp-item-p">{{ p.nomor_hp }}</div>
              </div>
              <div class="item-pelanggan-kanan text-right">
                <div class="saldo-item-p font-angka">{{ formatRupiah(p.total_saldo) }}</div>
                <div class="bulan-item-p">Bulan ini: {{ formatRupiah(p.total_donasi_bulan_ini) }}</div>
              </div>
            </div>

            <div v-if="daftarPelanggan.length === 0" class="kosong-daftar-kanan">
              <span v-if="sedangMemuat">Sedang memuat data...</span>
              <span v-else>Tidak ada pembeli yang cocok dengan pencarian.</span>
            </div>
          </div>
        </div>
      </div>

      <!-- MODAL DIALOG PENCAIRAN TUNAI -->
      <div v-if="tampilDialogCairTunai" class="latar-submodal" @click.self="tampilDialogCairTunai = false">
        <div class="kartu-submodal">
          <div class="header-submodal">
            <h3 class="judul-submodal">Konfirmasi Penarikan Uang Tunai</h3>
            <button class="btn-tutup-sub" @click="tampilDialogCairTunai = false"><X :size="18" /></button>
          </div>

          <div class="p-4">
            <p class="petunjuk-cair">
              Kasir akan menyerahkan uang tunai dari laci kasir kepada pembeli:
            </p>
            <div class="kotak-info-cair-pelanggan mt-2">
              <div>Pembeli: <strong>{{ pelangganTerpilih.nama_pelanggan }}</strong> ({{ pelangganTerpilih.nomor_hp }})</div>
              <div>Saldo Maksimal: <strong class="font-angka teks-hijau">{{ formatRupiah(pelangganTerpilih.total_saldo) }}</strong></div>
            </div>

            <div class="grup-input-cair mt-3">
              <label class="label-cair">Nominal Uang Tunai yang Dicairkan (Rp):</label>
              <input 
                :value="nominalCairTunai > 0 ? Number(nominalCairTunai).toLocaleString('id-ID') : ''" 
                type="text" 
                inputmode="numeric"
                class="input-teks input-cair-besar font-angka"
                placeholder="0"
                @focus="$event.target.select()"
                @input="tanganiInputNominalCair"
              />
            </div>

            <div class="flex gap-2 mt-2">
              <button 
                type="button" 
                class="btn-pilih-semua-cair" 
                @click="nominalCairTunai = pelangganTerpilih.total_saldo"
              >
                Cairkan Seluruh Saldo ({{ formatRupiah(pelangganTerpilih.total_saldo) }})
              </button>
            </div>

            <div class="footer-submodal mt-4 flex gap-2">
              <button 
                type="button" 
                class="tombol tombol-sekunder flex-1" 
                @click="tampilDialogCairTunai = false"
              >
                Batal
              </button>
              <button 
                type="button" 
                class="tombol tombol-sukses flex-2"
                :disabled="sedangProsesCair || nominalCairTunai <= 0 || nominalCairTunai > pelangganTerpilih.total_saldo"
                @click="konfirmasiCairTunai"
              >
                <Check :size="18" />
                <span>{{ sedangProsesCair ? 'Memproses...' : 'Serahkan Uang Cash' }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.latar-modal-donasi {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
  padding: 16px;
}

.kartu-modal-donasi {
  background: #ffffff;
  border-radius: 20px;
  max-width: 960px;
  width: 100%;
  max-height: 92vh;
  display: flex;
  flex-direction: column;
  padding: 24px;
  box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.35);
  border: 1.5px solid #e2e8f0;
  overflow: hidden;
}

.header-modal-donasi {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding-bottom: 16px;
  border-bottom: 2px solid #f1f5f9;
}
.ikon-donasi-header {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #f1f5f9;
  color: #0f172a;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.judul-donasi-header {
  font-size: 1.25rem;
  font-weight: 800;
  color: #0f172a;
}
.sub-donasi-header {
  font-size: 0.82rem;
  color: #64748b;
  margin-top: 2px;
}
.btn-tutup-donasi {
  background: #f1f5f9;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  transition: all 0.2s ease;
}
.btn-tutup-donasi:hover {
  background: #fee2e2;
  color: #dc2626;
}

/* 4 Kotak Ringkasan Statistik */
.grid-ringkasan-donasi {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 16px;
}
@media (max-width: 768px) {
  .grid-ringkasan-donasi {
    grid-template-columns: repeat(2, 1fr);
  }
}
.kartu-stat {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}
.stat-hijau, .stat-biru, .stat-kuning, .stat-ungu { 
  background: #f8fafc; 
  border-color: #e2e8f0; 
  color: #0f172a; 
}

.label-stat {
  font-size: 0.68rem;
  font-weight: 700;
  color: #64748b;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.angka-stat {
  font-size: 1.25rem;
  font-weight: 900;
  margin: 4px 0 2px 0;
}
.sub-stat {
  font-size: 0.68rem;
  opacity: 0.85;
}

/* Bilah Pencarian */
.bar-pencarian-donasi {
  display: flex;
  gap: 10px;
}
.wrap-input-cari-donasi {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
}
.ikon-cari-donasi {
  position: absolute;
  left: 14px;
  color: #2563eb;
}
.input-cari-donasi {
  width: 100%;
  padding-left: 44px;
  padding-right: 14px;
  height: 46px;
  border-radius: 10px;
  border: 1.5px solid #cbd5e1;
  font-size: 0.95rem;
  font-weight: 700;
  color: #0f172a;
}
.input-cari-donasi:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}
.btn-cari-aksi {
  height: 46px;
  padding: 0 20px;
  border-radius: 10px;
  font-weight: 800;
}

/* Grid Konten 2 Kolom */
.grid-konten-donasi {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
  gap: 16px;
  overflow-y: auto;
  flex: 1;
  padding-right: 4px;
}
@media (max-width: 800px) {
  .grid-konten-donasi {
    grid-template-columns: 1fr;
  }
}

.kolom-detail-pelanggan {
  display: flex;
  flex-direction: column;
}

.kartu-detail-saldo {
  background: #ffffff;
  border: 1.5px solid #e2e8f0;
  border-radius: 14px;
  padding: 16px;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
}

.header-pelanggan-terpilih {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}
.avatar-pelanggan {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: #eff6ff;
  color: #2563eb;
  display: flex;
  align-items: center;
  justify-content: center;
}
.nama-pelanggan-teks {
  font-size: 1.1rem;
  font-weight: 800;
  color: #0f172a;
}
.hp-pelanggan-teks {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.85rem;
  color: #64748b;
  font-family: var(--font-angka);
}
.badge-status-tabungan {
  background: #ecfdf5;
  color: #059669;
  border: 1px solid #a7f3d0;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 800;
}

/* Kotak Saldo Besar */
.kotak-saldo-akumulasi {
  background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%);
  border-radius: 14px;
  padding: 18px 22px;
  color: #ffffff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.3);
}
.label-saldo-besar {
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.5px;
  opacity: 0.9;
}
.angka-saldo-besar {
  font-size: 2rem;
  font-weight: 900;
  margin: 4px 0;
  letter-spacing: -0.5px;
}
.sub-saldo-bulan {
  font-size: 0.8rem;
  opacity: 0.9;
}
.ikon-koin-hias {
  opacity: 0.3;
}

/* Tombol Pilihan Pencairan A dan B */
.area-tombol-pencairan {
  background: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
}
.label-pencairan-pilihan {
  font-size: 0.78rem;
  font-weight: 800;
  color: #334155;
  margin-bottom: 10px;
}
.grid-tombol-pencairan {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
@media (max-width: 500px) {
  .grid-tombol-pencairan {
    grid-template-columns: 1fr;
  }
}
.btn-aksi-cair {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1.5px solid;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s ease;
}
.btn-aksi-cair:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
}
.btn-aksi-cair:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-cair-cash {
  background: #ffffff;
  border-color: #10b981;
  color: #047857;
}
.btn-cair-cash:hover:not(:disabled) {
  background: #059669;
  color: #ffffff;
}

.btn-cair-belanja {
  background: #ffffff;
  border-color: #3b82f6;
  color: #1d4ed8;
}
.btn-cair-belanja:hover:not(:disabled) {
  background: #2563eb;
  color: #ffffff;
}

.teks-btn-aksi {
  display: flex;
  flex-direction: column;
}
.judul-aksi {
  font-size: 0.85rem;
  font-weight: 800;
}
.sub-aksi {
  font-size: 0.7rem;
  opacity: 0.85;
}

/* Riwayat Mutasi */
.area-riwayat-pelanggan {
  border-top: 1px dashed #e2e8f0;
  padding-top: 14px;
}
.judul-riwayat-pelanggan {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  font-weight: 800;
  color: #334155;
  margin-bottom: 8px;
}
.tabel-mini-riwayat {
  max-height: 180px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.baris-riwayat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
}
.item-setor { border-left: 3px solid #10b981; }
.item-cair { border-left: 3px solid #f59e0b; }

.tipe-riwayat {
  font-size: 0.78rem;
  font-weight: 700;
  color: #0f172a;
}
.waktu-riwayat {
  font-size: 0.68rem;
  color: #64748b;
}
.struk-info {
  font-weight: 700;
}
.nominal-riwayat {
  font-size: 0.88rem;
  font-weight: 800;
}
.item-setor .nominal-riwayat { color: #059669; }
.item-cair .nominal-riwayat { color: #d97706; }

.placeholder-pilih-pelanggan {
  background: #f8fafc;
  border: 2px dashed #cbd5e1;
  border-radius: 14px;
  padding: 40px 20px;
  text-align: center;
  color: #64748b;
}
.ikon-placeholder-redup {
  color: #94a3b8;
  margin-bottom: 10px;
}
.judul-placeholder {
  font-size: 1.1rem;
  font-weight: 800;
  color: #0f172a;
}
.sub-placeholder {
  font-size: 0.82rem;
  max-width: 380px;
  margin: 6px auto 0 auto;
}

/* Kolom Kanan: Daftar Pembeli */
.kolom-daftar-pelanggan {
  background: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: 14px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.header-daftar-kanan {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}
.judul-daftar-kanan {
  font-size: 0.85rem;
  font-weight: 800;
  color: #0f172a;
}
.sub-daftar-kanan {
  font-size: 0.7rem;
  color: #64748b;
}

.daftar-pelanggan-scroll {
  overflow-y: auto;
  max-height: 380px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.kartu-item-pelanggan {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.15s ease;
}
.kartu-item-pelanggan:hover {
  border-color: #2563eb;
  background: #eff6ff;
  transform: translateX(2px);
}
.kartu-item-pelanggan.aktif {
  background: #eff6ff;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}
.nama-item-p {
  font-size: 0.85rem;
  font-weight: 800;
  color: #0f172a;
}
.hp-item-p {
  font-size: 0.72rem;
  color: #64748b;
  font-family: var(--font-angka);
}
.saldo-item-p {
  font-size: 0.95rem;
  font-weight: 800;
  color: #059669;
}
.bulan-item-p {
  font-size: 0.65rem;
  color: #64748b;
}

/* Submodal Pencairan */
.latar-submodal {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1300;
  padding: 16px;
}
.kartu-submodal {
  background: #ffffff;
  border-radius: 16px;
  max-width: 440px;
  width: 100%;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  border: 1px solid #e2e8f0;
}
.header-submodal {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}
.judul-submodal { font-size: 1.05rem; font-weight: 800; color: #0f172a; }
.btn-tutup-sub { background: none; border: none; cursor: pointer; color: #94a3b8; }
.btn-tutup-sub:hover { color: #dc2626; }
.petunjuk-cair { font-size: 0.85rem; color: #475569; }
.kotak-info-cair-pelanggan {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 10px;
  border-radius: 8px;
  font-size: 0.82rem;
  color: #1e40af;
}
.input-cair-besar {
  font-size: 1.3rem;
  font-weight: 900;
  height: 48px;
  color: #059669;
  border: 2px solid #a7f3d0;
}
.btn-pilih-semua-cair {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 700;
  cursor: pointer;
}
.btn-pilih-semua-cair:hover { background: #d1fae5; }
.pesan-notif-sukses {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}
.pesan-notif-error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}
.p-4 { padding: 18px; }
.mt-2 { margin-top: 8px; }
.mt-3 { margin-top: 12px; }
.mt-4 { margin-top: 16px; }
.flex { display: flex; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.flex-1 { flex: 1; }
.flex-2 { flex: 2; }
.font-angka { font-family: var(--font-angka); }
.text-right { text-align: right; }
.teks-hijau { color: #059669; }
</style>
