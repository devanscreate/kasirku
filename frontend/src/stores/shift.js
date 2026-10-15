import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { dbLokal } from '../basis_data'
import { tambahKeAntreanKeluar } from '../layanan/sinkronisasi'
import { panggilApi } from '../layanan/api'

export const useShiftStore = defineStore('shift', () => {
  const shiftAktif = ref(null)
  const sedangMemuat = ref(false)

  const apakahShiftTerbuka = computed(() => {
    return shiftAktif.value && shiftAktif.value.status === 'open'
  })

  // Memuat data shift dari IndexedDB atau server
  async function muatShiftAktif(idKasir) {
    sedangMemuat.value = true
    try {
      // 1. Cek basis data lokal Dexie
      const lokal = await dbLokal.shift.where('id_kasir').equals(idKasir).and(s => s.status === 'open').first()
      if (lokal) {
        shiftAktif.value = lokal
        return lokal
      }

      // 2. Jika online, periksa dari server
      if (navigator.onLine) {
        const dariServer = await panggilApi('/shifts/aktif')
        if (dariServer) {
          shiftAktif.value = dariServer
          await dbLokal.shift.put(dariServer)
          return dariServer
        }
      }

      shiftAktif.value = null
      return null
    } catch (err) {
      console.warn('Gagal memuat status shift:', err)
      return null
    } finally {
      sedangMemuat.value = false
    }
  }

  // F-02: Buka Shift Kasir Baru
  async function bukaShift(idKasir, kasAwal) {
    const shiftId = crypto.randomUUID()
    const shiftBaru = {
      id: shiftId,
      id_kasir: idKasir,
      kas_awal: parseInt(kasAwal, 10) || 0,
      kas_ekspektasi: parseInt(kasAwal, 10) || 0,
      status: 'open',
      dibuka_pada: new Date().toISOString()
    }

    // Simpan ke IndexedDB lokal
    await dbLokal.shift.put(shiftBaru)
    shiftAktif.value = shiftBaru

    // Tambahkan event shift_open ke outbox
    await tambahKeAntreanKeluar('shift_open', {
      id: shiftId,
      kas_awal: shiftBaru.kas_awal
    })

    return shiftBaru
  }

  // F-09: Tutup Shift Kasir
  async function tutupShift(kasFisik, catatan = '') {
    if (!shiftAktif.value) return

    const idShift = shiftAktif.value.id
    const waktuTutup = new Date().toISOString()

    // Perbarui shift lokal di Dexie
    await dbLokal.shift.update(idShift, {
      status: 'closed',
      kas_fisik: parseInt(kasFisik, 10) || 0,
      catatan,
      ditutup_pada: waktuTutup
    })

    // Tambahkan event shift_close ke outbox
    await tambahKeAntreanKeluar('shift_close', {
      id: crypto.randomUUID(),
      id_shift: idShift,
      kas_fisik: parseInt(kasFisik, 10) || 0,
      catatan
    })

    shiftAktif.value = null
  }

  return {
    shiftAktif,
    sedangMemuat,
    apakahShiftTerbuka,
    muatShiftAktif,
    bukaShift,
    tutupShift
  }
})
