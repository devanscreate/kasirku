import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { dbLokal, buatNomorStrukLokal } from '../basis_data'
import { tambahKeAntreanKeluar } from '../layanan/sinkronisasi'

export const useKeranjangStore = defineStore('keranjang', () => {
  const itemKeranjang = ref([])
  const diskonPersen = ref(0)
  const diskonNominal = ref(0)
  const tipeDiskon = ref('persen') // 'persen' | 'nominal'
  const persenPajak = ref(0)
  const pembulatan = ref(0)

  // Pulihkan draf keranjang dari penyimpanan lokal jika ada (F-04 b)
  function pulihkanDraft() {
    try {
      const draft = localStorage.getItem('draft_keranjang')
      if (draft) {
        const parsed = JSON.parse(draft)
        itemKeranjang.value = parsed.items || []
        diskonPersen.value = parsed.diskonPersen || 0
        diskonNominal.value = parsed.diskonNominal || 0
        tipeDiskon.value = parsed.tipeDiskon || 'persen'
      }
    } catch (e) {
      console.warn('Gagal memulihkan draf keranjang:', e)
    }
  }

  function simpanDraft() {
    localStorage.setItem('draft_keranjang', JSON.stringify({
      items: itemKeranjang.value,
      diskonPersen: diskonPersen.value,
      diskonNominal: diskonNominal.value,
      tipeDiskon: tipeDiskon.value
    }))
  }

  // Perhitungan Subtotal
  const subtotal = computed(() => {
    return itemKeranjang.value.reduce((total, it) => total + (it.harga * it.kuantitas), 0)
  })

  // Nilai Diskon
  const nilaiDiskon = computed(() => {
    if (tipeDiskon.value === 'persen') {
      return Math.round((subtotal.value * diskonPersen.value) / 100)
    }
    return Math.min(diskonNominal.value, subtotal.value)
  })

  // Nilai Pajak
  const nilaiPajak = computed(() => {
    const setelahDiskon = subtotal.value - nilaiDiskon.value
    return Math.round((setelahDiskon * persenPajak.value) / 100)
  })

  // Total Akhir Transaksi
  const totalAkhir = computed(() => {
    const total = subtotal.value - nilaiDiskon.value + nilaiPajak.value + pembulatan.value
    return Math.max(0, total)
  })

  const totalKuantitas = computed(() => {
    return itemKeranjang.value.reduce((total, it) => total + it.kuantitas, 0)
  })

  // F-04: Tambah Produk ke Keranjang (Scan / Pilih)
  function tambahItem(produk, kuantitas = 1) {
    const indeks = itemKeranjang.value.findIndex(it => it.id === produk.id)
    if (indeks > -1) {
      itemKeranjang.value[indeks].kuantitas += kuantitas
    } else {
      itemKeranjang.value.push({
        id: produk.id,
        sku: produk.sku,
        barcode: produk.barcode,
        nama: produk.nama,
        harga: produk.harga,
        harga_modal: produk.harga_modal || 0,
        kuantitas: kuantitas,
        stok_tersedia: produk.stok
      })
    }
    simpanDraft()
  }

  function kurangiItem(idProduk) {
    const indeks = itemKeranjang.value.findIndex(it => it.id === idProduk)
    if (indeks > -1) {
      if (itemKeranjang.value[indeks].kuantitas > 1) {
        itemKeranjang.value[indeks].kuantitas -= 1
      } else {
        itemKeranjang.value.splice(indeks, 1)
      }
      simpanDraft()
    }
  }

  function ubahKuantitas(idProduk, jumlah) {
    const indeks = itemKeranjang.value.findIndex(it => it.id === idProduk)
    if (indeks > -1) {
      const qtyBersih = Math.max(1, parseInt(jumlah, 10) || 1)
      itemKeranjang.value[indeks].kuantitas = qtyBersih
      simpanDraft()
    }
  }

  function hapusItem(idProduk) {
    itemKeranjang.value = itemKeranjang.value.filter(it => it.id !== idProduk)
    simpanDraft()
  }

  function aturDiskon(nilai, tipe = 'persen', batasMaksKasir = 100) {
    if (tipe === 'persen') {
      const persen = Math.min(Math.max(0, Number(nilai)), batasMaksKasir)
      diskonPersen.value = persen
      tipeDiskon.value = 'persen'
    } else {
      diskonNominal.value = Math.max(0, parseInt(nilai, 10) || 0)
      tipeDiskon.value = 'nominal'
    }
    simpanDraft()
  }

  function kosongkanKeranjang() {
    itemKeranjang.value = []
    diskonPersen.value = 0
    diskonNominal.value = 0
    pembulatan.value = 0
    localStorage.removeItem('draft_keranjang')
  }

  // F-04: Selesaikan Transaksi Pembayaran dan Simpan ke Outbox secara Atomik
  async function selesaikanTransaksi({ idShift, idKasir, namaKasir, metodeBayar, jumlahDiterima, potonganDonasi = null }) {
    if (itemKeranjang.value.length === 0) {
      throw new Error('Keranjang belanja masih kosong')
    }

    const idTransaksi = crypto.randomUUID()
    const nomorStruk = await buatNomorStrukLokal()
    const waktuTransaksi = new Date().toISOString()
    const nominalPotonganDonasi = potonganDonasi ? (Number(potonganDonasi.nominal) || 0) : 0
    const totalTagihanAkhir = Math.max(0, totalAkhir.value - nominalPotonganDonasi)
    const isLunasTabungan = totalTagihanAkhir === 0 && nominalPotonganDonasi > 0
    const metodeFinal = isLunasTabungan ? 'tabungan' : (metodeBayar || 'tunai')
    const diterima = isLunasTabungan
      ? 0
      : ((jumlahDiterima !== undefined && jumlahDiterima !== null && !isNaN(Number(jumlahDiterima))) 
          ? Number(jumlahDiterima) 
          : totalTagihanAkhir)
    const kembalian = isLunasTabungan ? 0 : Math.max(0, diterima - totalTagihanAkhir)

    // Alokasi diskon transaksi per item secara proporsional
    const totalSub = subtotal.value
    const totalDisk = nilaiDiskon.value

    const itemsFormatted = itemKeranjang.value.map(it => {
      const subtotalBaris = it.harga * it.kuantitas
      const alokasiDiskon = totalSub > 0 ? Math.round((subtotalBaris / totalSub) * totalDisk) : 0
      return {
        id_produk: it.id,
        nama_produk_snapshot: it.nama,
        harga_snapshot: it.harga,
        kuantitas: it.kuantitas,
        alokasi_diskon: alokasiDiskon,
        subtotal_baris: subtotalBaris - alokasiDiskon
      }
    })

    const payloadPenjualan = {
      id: idTransaksi,
      id_shift: idShift,
      nomor_struk: nomorStruk,
      subtotal: subtotal.value,
      diskon: nilaiDiskon.value,
      pajak: nilaiPajak.value,
      pembulatan: pembulatan.value,
      potongan_donasi: nominalPotonganDonasi,
      total_sebelum_potongan: totalAkhir.value,
      total: totalTagihanAkhir,
      waktu_transaksi: waktuTransaksi,
      item: itemsFormatted,
      pembayaran: [
        {
          metode: metodeFinal,
          jumlah: totalTagihanAkhir,
          diterima: diterima,
          kembalian: kembalian
        }
      ]
    }

    // Rekam penjualan di Dexie lokal
    const catatanLokal = {
      ...payloadPenjualan,
      id_kasir: idKasir,
      nama_kasir: namaKasir,
      potonganDonasi: potonganDonasi || null,
      status_sinkron: 'pending_sync',
      status: 'completed',
      dibuat_pada: waktuTransaksi
    }
    await dbLokal.penjualan.put(catatanLokal)

    // Kurangi stok indikatif lokal di Dexie
    for (const it of itemKeranjang.value) {
      const prod = await dbLokal.produk.get(it.id)
      if (prod) {
        await dbLokal.produk.update(it.id, {
          stok: prod.stok - it.kuantitas
        })
      }
    }

    // Tambah ke Outbox
    await tambahKeAntreanKeluar('sale', payloadPenjualan)

    // Kosongkan keranjang
    kosongkanKeranjang()

    return {
      transaksi: catatanLokal,
      kembalian: kembalian
    }
  }

  // Panggil pemulihan draft saat store diinisialisasi
  pulihkanDraft()

  return {
    itemKeranjang,
    diskonPersen,
    diskonNominal,
    tipeDiskon,
    persenPajak,
    pembulatan,
    subtotal,
    nilaiDiskon,
    nilaiPajak,
    totalAkhir,
    totalKuantitas,
    tambahItem,
    kurangiItem,
    ubahKuantitas,
    hapusItem,
    aturDiskon,
    kosongkanKeranjang,
    selesaikanTransaksi,
    pulihkanDraft
  }
})
