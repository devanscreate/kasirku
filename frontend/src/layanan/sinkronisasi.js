import { dbLokal, dapatkanWaktuSinkronTerakhir, simpanWaktuSinkronTerakhir } from '../basis_data'
import { panggilApi } from './api'

let sedangMemprosesOutbox = false

/**
 * F-03: Sinkronisasi Katalog Produk dari Server ke IndexedDB (Dexie)
 */
export async function sinkronkanKatalogProduk() {
  if (!navigator.onLine) return { sukses: false, alasan: 'offline' }

  try {
    const waktuTerakhir = await dapatkanWaktuSinkronTerakhir()
    let parameterSince = ''
    
    // Tumpang-tindih 60 detik untuk menjamin transaksi commit lambat tidak tertinggal (F-03)
    if (waktuTerakhir) {
      const tanggalKurang60Detik = new Date(new Date(waktuTerakhir).getTime() - 60000)
      parameterSince = `?since=${encodeURIComponent(tanggalKurang60Detik.toISOString())}`
    }

    let kursor = null
    let waktuServerTerakhir = null

    do {
      const urlKueri = `/sync/products${parameterSince}${kursor ? `&cursor=${kursor}` : ''}`
      const respons = await panggilApi(urlKueri)

      if (respons && respons.produk) {
        waktuServerTerakhir = respons.waktu_server

        // Upsert atomik ke Dexie
        await dbLokal.transaction('rw', dbLokal.produk, async () => {
          for (const item of respons.produk) {
            await dbLokal.produk.put({
              id: item.id,
              sku: item.sku,
              barcode: item.barcode,
              nama: item.nama,
              kategori: item.kategori,
              foto: item.foto || null,
              harga: item.harga,
              harga_modal: item.harga_modal,
              stok: item.stok,
              min_stok: item.min_stok,
              status_aktif: item.status_aktif && !item.apakah_dihapus,
              terakhir_diperbarui: item.diperbarui_pada
            })
          }
        })

        kursor = respons.kursor_berikutnya
      } else {
        kursor = null
      }
    } while (kursor)

    if (waktuServerTerakhir) {
      await simpanWaktuSinkronTerakhir(waktuServerTerakhir)
    }

    window.dispatchEvent(new CustomEvent('katalog:diperbarui'))
    return { sukses: true }
  } catch (err) {
    console.warn('Gagal sinkron katalog (menggunakan cache lokal):', err)
    return { sukses: false, error: err.message }
  }
}

/**
 * F-05: Menambahkan event baru ke antrean keluar (Outbox) secara atomik
 */
export async function tambahKeAntreanKeluar(tipePeristiwa, payload) {
  const eventBaru = {
    id: payload.id,
    tipe_peristiwa: tipePeristiwa,
    payload,
    status: 'pending',
    percobaan: 0,
    pesan_kesalahan: null,
    dibuat_pada: new Date().toISOString()
  }

  await dbLokal.antrean_keluar.put(eventBaru)
  
  // Picu proses pengiriman di latar belakang jika online
  if (navigator.onLine) {
    prosesAntreanKeluar()
  }
  
  window.dispatchEvent(new CustomEvent('outbox:berubah'))
  return eventBaru
}

/**
 * F-05: Pemroses Antrean Keluar (Outbox Processor) secara FIFO & Idempoten
 */
export async function prosesAntreanKeluar() {
  if (sedangMemprosesOutbox || !navigator.onLine) return
  sedangMemprosesOutbox = true

  try {
    const daftarEvent = await dbLokal.antrean_keluar
      .where('status')
      .equals('pending')
      .sortBy('dibuat_pada')

    for (const event of daftarEvent) {
      // Tandai sedang dikirim
      await dbLokal.antrean_keluar.update(event.id, {
        status: 'sending',
        percobaan: event.percobaan + 1
      })

      try {
        if (event.tipe_peristiwa === 'sale') {
          // Kirim transaksi penjualan dengan header Idempotency-Key
          await panggilApi('/sales', {
            method: 'POST',
            body: JSON.stringify(event.payload),
            headers: {
              'Idempotency-Key': event.payload.id
            }
          })

          // Sukses: tandai done dan update status penjualan lokal
          await dbLokal.antrean_keluar.update(event.id, {
            status: 'done',
            disinkronkan_pada: new Date().toISOString()
          })

          await dbLokal.penjualan.update(event.payload.id, {
            status_sinkron: 'synced'
          })

        } else if (event.tipe_peristiwa === 'shift_open') {
          // Kirim pembukaan shift
          await panggilApi('/shifts/open', {
            method: 'POST',
            body: JSON.stringify(event.payload)
          })

          await dbLokal.antrean_keluar.update(event.id, {
            status: 'done',
            disinkronkan_pada: new Date().toISOString()
          })

        } else if (event.tipe_peristiwa === 'shift_close') {
          // Aturan F-05 butir 7: Shift close DITAHAN sampai semua transaksi shift tersebut selesai dikirim!
          const transaksiShiftPending = await dbLokal.antrean_keluar
            .where('tipe_peristiwa')
            .equals('sale')
            .and(ev => ev.payload.id_shift === event.payload.id_shift && ev.status !== 'done' && ev.status !== 'failed')
            .count()

          if (transaksiShiftPending > 0) {
            // Tahan event tutup shift, kembalikan ke status pending
            await dbLokal.antrean_keluar.update(event.id, { status: 'pending' })
            continue
          }

          // Semua penjualan shift sudah aman terkirim, sekarang tutup shift di server
          await panggilApi(`/shifts/${event.payload.id_shift}/close`, {
            method: 'POST',
            body: JSON.stringify({
              kas_fisik: event.payload.kas_fisik,
              catatan: event.payload.catatan
            })
          })

          await dbLokal.antrean_keluar.update(event.id, {
            status: 'done',
            disinkronkan_pada: new Date().toISOString()
          })
        }
      } catch (err) {
        if (err.status === 422) {
          // Error validasi struktur: tandai failed untuk ditindaklanjuti Manajer (F-05 butir 6)
          await dbLokal.antrean_keluar.update(event.id, {
            status: 'failed',
            pesan_kesalahan: err.message || 'Kesalahan validasi data'
          })
          if (event.tipe_peristiwa === 'sale') {
            await dbLokal.penjualan.update(event.payload.id, {
              status_sinkron: 'failed'
            })
          }
        } else {
          // Gangguan jaringan/timeout/5xx: kembalikan ke pending untuk dicoba lagi nanti
          await dbLokal.antrean_keluar.update(event.id, {
            status: 'pending',
            pesan_kesalahan: err.message
          })
          // Hentikan iterasi sementara jika koneksi internet terputus
          if (!navigator.onLine) break
        }
      }
    }
  } finally {
    sedangMemprosesOutbox = false
    window.dispatchEvent(new CustomEvent('outbox:berubah'))
  }
}

// Inisialisasi pendengar event koneksi online/offline
if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    sinkronkanKatalogProduk()
    prosesAntreanKeluar()
  })

  // Timer berkala tiap 30 detik untuk pengiriman outbox dan sinkronisasi
  setInterval(() => {
    if (navigator.onLine) {
      prosesAntreanKeluar()
    }
  }, 30000)
}
