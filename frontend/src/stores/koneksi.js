import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dbLokal, dapatkanWaktuSinkronTerakhir } from '../basis_data'
import { prosesAntreanKeluar, sinkronkanKatalogProduk } from '../layanan/sinkronisasi'

export const useKoneksiStore = defineStore('koneksi', () => {
  const apakahOnline = ref(navigator.onLine)
  const jumlahPending = ref(0)
  const jumlahGagal = ref(0)
  const daftarGagal = ref([])
  const waktuSinkronTerakhir = ref(null)
  const sedangSinkron = ref(false)

  async function perbaruiStatus() {
    apakahOnline.value = navigator.onLine

    // Hitung antrean pending & sending
    const pending = await dbLokal.antrean_keluar
      .where('status')
      .anyOf(['pending', 'sending'])
      .count()
    jumlahPending.value = pending

    // Ambil antrean failed (perlu tindakan)
    const gagal = await dbLokal.antrean_keluar
      .where('status')
      .equals('failed')
      .toArray()
    jumlahGagal.value = gagal.length
    daftarGagal.value = gagal

    // Waktu sinkron terakhir
    waktuSinkronTerakhir.value = await dapatkanWaktuSinkronTerakhir()
  }

  async function picuSinkronManual() {
    if (!navigator.onLine) return
    sedangSinkron.value = true
    try {
      await sinkronkanKatalogProduk()
      await prosesAntreanKeluar()
      await perbaruiStatus()
    } finally {
      sedangSinkron.value = false
    }
  }

  // Aksi Manajer: Kirim ulang event yang gagal setelah masalah diperbaiki (F-05)
  async function kirimUlangEventGagal(idEvent) {
    await dbLokal.antrean_keluar.update(idEvent, {
      status: 'pending',
      pesan_kesalahan: null
    })
    await perbaruiStatus()
    if (navigator.onLine) {
      prosesAntreanKeluar()
    }
  }

  // Aksi Manajer: Buang event yang gagal dengan catatan (F-05)
  async function buangEventGagal(idEvent, alasan) {
    await dbLokal.antrean_keluar.delete(idEvent)
    await perbaruiStatus()
  }

  // Inisialisasi event listener
  if (typeof window !== 'undefined') {
    window.addEventListener('online', () => perbaruiStatus())
    window.addEventListener('offline', () => perbaruiStatus())
    window.addEventListener('outbox:berubah', () => perbaruiStatus())
    window.addEventListener('katalog:diperbarui', () => perbaruiStatus())
  }

  // Panggilan awal
  perbaruiStatus()

  return {
    apakahOnline,
    jumlahPending,
    jumlahGagal,
    daftarGagal,
    waktuSinkronTerakhir,
    sedangSinkron,
    perbaruiStatus,
    picuSinkronManual,
    kirimUlangEventGagal,
    buangEventGagal
  }
})
