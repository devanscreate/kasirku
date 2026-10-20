import { panggilApi } from './api'
import { dbLokal } from '../basis_data'

/**
 * Layanan Fitur Donasi & Tabungan Kembalian Pembeli
 * Mendukung pencatatan donasi kembalian, akumulasi saldo,
 * serta pencairan tunai atau potong belanjaan.
 */

export function bersihkanNomorHp(noHp) {
  if (!noHp) return ''
  return noHp.replace(/[^\d+]/g, '').trim()
}

/**
 * Setor donasi kembalian dari transaksi kasir
 */
export async function setorDonasiKembalian({ nomorHp, namaPelanggan, nominal, nomorStruk, idPenjualan, idShift }) {
  const noHp = bersihkanNomorHp(nomorHp)
  if (!noHp || nominal <= 0) {
    throw new Error('Nomor HP dan nominal donasi wajib diisi')
  }

  const payload = {
    nomor_hp: noHp,
    nama_pelanggan: namaPelanggan || 'Pelanggan',
    nominal: Number(nominal),
    nomor_struk: nomorStruk || null,
    id_penjualan: idPenjualan || null,
    id_shift: idShift || null
  }

  // Simpan catatan lokal di Dexie
  const idLokal = crypto.randomUUID()
  const waktuSekarang = new Date().toISOString()

  await dbLokal.tabungan_donasi.put({
    id: idLokal,
    nomor_hp: noHp,
    nama_pelanggan: namaPelanggan || 'Pelanggan',
    tipe: 'setor_kembalian',
    nominal: Number(nominal),
    nomor_struk: nomorStruk,
    dibuat_pada: waktuSekarang
  })

  // Perbarui saldo pelanggan di Dexie
  const dataPelanggan = await dbLokal.pelanggan_donasi.get(noHp)
  const saldoBaru = (dataPelanggan?.saldo || 0) + Number(nominal)
  await dbLokal.pelanggan_donasi.put({
    nomor_hp: noHp,
    nama: namaPelanggan || dataPelanggan?.nama || 'Pelanggan',
    saldo: saldoBaru,
    terakhir_donasi: waktuSekarang
  })

  // Jika online, kirim ke server backend
  if (navigator.onLine) {
    try {
      const hasil = await panggilApi('/donations/setor', {
        method: 'POST',
        body: JSON.stringify(payload)
      })
      return hasil
    } catch (err) {
      console.warn('Gagal sinkron donasi ke server (disimpan lokal):', err)
    }
  }

  return {
    status: 'success',
    pesan: `Donasi kembalian Rp ${nominal.toLocaleString('id-ID')} berhasil dicatat secara lokal.`,
    nomor_hp: noHp,
    nama_pelanggan: namaPelanggan || 'Pelanggan',
    nominal_disetor: Number(nominal),
    total_saldo: saldoBaru,
    total_donasi_bulan_ini: Number(nominal)
  }
}

/**
 * Cek saldo dan riwayat donasi pembeli berdasarkan Nomor HP
 */
export async function cekSaldoPelanggan(nomorHp) {
  const noHp = bersihkanNomorHp(nomorHp)
  if (!noHp) return null

  if (navigator.onLine) {
    try {
      const data = await panggilApi(`/donations/saldo/${encodeURIComponent(noHp)}`)
      // Sinkronkan ke Dexie
      if (data) {
        await dbLokal.pelanggan_donasi.put({
          nomor_hp: noHp,
          nama: data.nama_pelanggan,
          saldo: data.total_saldo,
          terakhir_donasi: new Date().toISOString()
        })
      }
      return data
    } catch (err) {
      console.warn('Fallback cek saldo donasi lokal Dexie:', err)
    }
  }

  // Fallback Dexie lokal
  const itemLokal = await dbLokal.tabungan_donasi.where('nomor_hp').equals(noHp).toArray()
  let totalSetor = 0
  let totalCair = 0
  for (const it of itemLokal) {
    if (it.tipe === 'setor_kembalian') totalSetor += it.nominal
    else totalCair += it.nominal
  }

  const pel = await dbLokal.pelanggan_donasi.get(noHp)
  const totalSaldo = Math.max(0, totalSetor - totalCair)

  return {
    nomor_hp: noHp,
    nama_pelanggan: pel?.nama || 'Pelanggan',
    total_saldo: totalSaldo,
    total_donasi_bulan_ini: totalSaldo,
    jumlah_transaksi: itemLokal.length,
    riwayat: itemLokal.sort((a, b) => new Date(b.dibuat_pada) - new Date(a.dibuat_pada))
  }
}

/**
 * Cairkan saldo donasi pembeli (uang tunai / potong belanja)
 */
export async function cairkanDonasiPelanggan({ nomorHp, nominal, tipe, idShift, catatan, saldoAwal }) {
  const noHp = bersihkanNomorHp(nomorHp)
  const payload = {
    nomor_hp: noHp,
    nominal: Number(nominal),
    tipe: tipe || 'tunai',
    id_shift: idShift || null,
    catatan: catatan || null
  }

  // Update Dexie lokal
  const idLokal = crypto.randomUUID()
  const waktuSekarang = new Date().toISOString()
  const tipeMutasi = tipe === 'tunai' ? 'cair_tunai' : 'potong_belanja'

  await dbLokal.tabungan_donasi.put({
    id: idLokal,
    nomor_hp: noHp,
    tipe: tipeMutasi,
    nominal: Number(nominal),
    catatan: catatan || `Pencairan ${tipe}`,
    dibuat_pada: waktuSekarang
  })

  const pel = await dbLokal.pelanggan_donasi.get(noHp)
  const basisSaldo = (saldoAwal !== undefined && saldoAwal !== null) ? Number(saldoAwal) : Number(pel?.saldo || 0)
  const saldoSisa = Math.max(0, basisSaldo - Number(nominal))
  await dbLokal.pelanggan_donasi.put({
    nomor_hp: noHp,
    nama: pel?.nama || 'Pelanggan',
    saldo: saldoSisa,
    terakhir_donasi: waktuSekarang
  })

  if (navigator.onLine) {
    try {
      const hasil = await panggilApi('/donations/cairkan', {
        method: 'POST',
        body: JSON.stringify(payload)
      })
      if (hasil?.sisa_saldo !== undefined) {
        await dbLokal.pelanggan_donasi.put({
          nomor_hp: noHp,
          nama: hasil.nama_pelanggan || pel?.nama || 'Pelanggan',
          saldo: hasil.sisa_saldo,
          terakhir_donasi: waktuSekarang
        })
      }
      return hasil
    } catch (err) {
      console.warn('Gagal sinkron pencairan donasi ke server (tersimpan lokal):', err)
    }
  }

  return {
    status: 'success',
    pesan: `Pencairan ${tipe} sebesar Rp ${nominal.toLocaleString('id-ID')} berhasil dicatat secara lokal.`,
    nomor_hp: noHp,
    nama_pelanggan: pel?.nama || 'Pelanggan',
    tipe_pencairan: tipe,
    nominal_dicairkan: Number(nominal),
    sisa_saldo: saldoSisa,
    waktu: waktuSekarang
  }
}

/**
 * Ambil daftar pelanggan donasi
 */
export async function ambilDaftarPelangganDonasi(q = '') {
  if (navigator.onLine) {
    try {
      const url = q ? `/donations/pelanggan?q=${encodeURIComponent(q)}` : '/donations/pelanggan'
      return await panggilApi(url)
    } catch (err) {
      console.warn('Fallback ambil pelanggan donasi Dexie:', err)
    }
  }

  const list = await dbLokal.pelanggan_donasi.toArray()
  return list.map(p => ({
    nomor_hp: p.nomor_hp,
    nama_pelanggan: p.nama,
    total_saldo: p.saldo,
    total_donasi_bulan_ini: p.saldo,
    terakhir_transaksi: p.terakhir_donasi
  })).filter(p => {
    if (!q) return true
    const cari = q.toLowerCase()
    return p.nomor_hp.includes(cari) || (p.nama_pelanggan && p.nama_pelanggan.toLowerCase().includes(cari))
  })
}

/**
 * Ambil ringkasan toko
 */
export async function ambilRingkasanDonasiToko() {
  if (navigator.onLine) {
    try {
      return await panggilApi('/donations/ringkasan')
    } catch (e) {
      console.warn('Gagal ambil ringkasan toko:', e)
    }
  }
  return {
    total_donasi_terkumpul: 0,
    total_dicairkan: 0,
    saldo_aktif_keseluruhan: 0,
    jumlah_pelanggan_aktif: 0
  }
}
