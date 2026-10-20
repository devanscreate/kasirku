import Dexie from 'dexie'

/**
 * Basis Data Lokal Kasirku (IndexedDB via Dexie)
 * Dirancang untuk mendukung arsitektur Offline-First
 * Data tetap tersimpan aman di peramban saat jaringan internet terputus.
 */
export const dbLokal = new Dexie('KasirkuDB')

dbLokal.version(1).stores({
  // Katalog produk lokal untuk pencarian super cepat (<100ms untuk 10.000 item)
  produk: 'id, sku, barcode, nama, kategori, status_aktif, terakhir_diperbarui',
  
  // Transaksi penjualan lokal
  penjualan: 'id, nomor_struk, shift_id, id_kasir, status_sinkron, dibuat_pada',
  
  // Antrean keluar (Outbox) untuk pengiriman data asinkron & idempoten
  antrean_keluar: 'id, tipe_peristiwa, status, percobaan, dibuat_pada',
  
  // Shift lokal kasir
  shift: 'id, id_kasir, status, dibuka_pada',
  
  // Konfigurasi dan pengaturan perangkat lokal (kode_perangkat, sync_cursor, dll)
  pengaturan_lokal: 'kunci'
})

dbLokal.version(2).stores({
  // Tabungan donasi kembalian pelanggan lokal & offline
  tabungan_donasi: 'id, nomor_hp, tipe, nomor_struk, dibuat_pada',
  pelanggan_donasi: 'nomor_hp, nama, saldo, terakhir_donasi'
})

/**
 * Helper untuk mengambil atau menginisialisasi kode unik perangkat kasir (mis. KSR01)
 */
export async function dapatkanKodePerangkat() {
  const item = await dbLokal.pengaturan_lokal.get('kode_perangkat')
  if (item && item.nilai) {
    return item.nilai
  }
  const kodeBaru = 'KASIR-' + Math.floor(100 + Math.random() * 900)
  await dbLokal.pengaturan_lokal.put({ kunci: 'kode_perangkat', nilai: kodeBaru })
  return kodeBaru
}

/**
 * Helper untuk membuat nomor struk lokal yang unik dan berurutan:
 * Format: <KODE_PERANGKAT>-<YYYYMMDD>-<URUTAN>
 * Contoh: KASIR-101-20261015-0001
 */
export async function buatNomorStrukLokal() {
  const kodePerangkat = await dapatkanKodePerangkat()
  const sekarang = new Date()
  const tahun = sekarang.getFullYear()
  const bulan = String(sekarang.getMonth() + 1).padStart(2, '0')
  const tanggal = String(sekarang.getDate()).padStart(2, '0')
  const kunciHariIni = `${tahun}${bulan}${tanggal}`

  const catatanUrutan = await dbLokal.pengaturan_lokal.get(`urutan_struk_${kunciHariIni}`)
  let urutan = 1
  if (catatanUrutan && typeof catatanUrutan.nilai === 'number') {
    urutan = catatanUrutan.nilai + 1
  }

  await dbLokal.pengaturan_lokal.put({ kunci: `urutan_struk_${kunciHariIni}`, nilai: urutan })
  const urutanTeks = String(urutan).padStart(4, '0')
  return `${kodePerangkat}-${kunciHariIni}-${urutanTeks}`
}

/**
 * Ambil waktu sinkronisasi terakhir
 */
export async function dapatkanWaktuSinkronTerakhir() {
  const item = await dbLokal.pengaturan_lokal.get('terakhir_sinkron_katalog')
  return item ? item.nilai : null
}

/**
 * Simpan waktu sinkronisasi terakhir
 */
export async function simpanWaktuSinkronTerakhir(waktuISO) {
  await dbLokal.pengaturan_lokal.put({ kunci: 'terakhir_sinkron_katalog', nilai: waktuISO })
}
