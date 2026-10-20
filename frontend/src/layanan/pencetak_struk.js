/**
 * Layanan Cetak Struk Kasir (F-06)
 * Mendukung format kertas 58mm dan 80mm via browser print dialog
 */

export function cetakStrukTransaksi(dataTransaksi, dataToko = {}, apakahSalinan = false) {
  // Buat atau bersihkan kontainer cetak di DOM
  let kontainer = document.getElementById('struk-cetak')
  if (!kontainer) {
    kontainer = document.createElement('div')
    kontainer.id = 'struk-cetak'
    document.body.appendChild(kontainer)
  }

  const namaToko = dataToko.nama || 'TOKO BERKAH SEJAHTERA'
  const alamatToko = dataToko.alamat || 'Jl. Merdeka No. 45'
  const telpToko = dataToko.telepon || '0812-3456-7890'
  const lebarKertas = dataToko.pengaturan?.lebar_kertas || 58

  const formatRupiah = (angka) => 'Rp ' + Number(angka || 0).toLocaleString('id-ID')
  const waktuStr = new Date(dataTransaksi.waktu_transaksi).toLocaleString('id-ID', {
    dateStyle: 'short',
    timeStyle: 'medium'
  })

  let daftarItemHtml = ''
  const items = dataTransaksi.item || []
  for (const it of items) {
    const nama = it.nama_produk_snapshot || it.nama || 'Item'
    const qty = it.kuantitas || 1
    const harga = it.harga_snapshot || it.harga || 0
    const subtotal = it.subtotal_baris || (qty * harga)

    daftarItemHtml += `
      <div style="margin-bottom: 4px;">
        <div style="font-weight: 600;">${nama}</div>
        <div style="display: flex; justify-content: space-between; font-size: 0.85em;">
          <span>${qty} x ${formatRupiah(harga)}</span>
          <span>${formatRupiah(subtotal)}</span>
        </div>
      </div>
    `
  }

  const bayar = dataTransaksi.pembayaran?.[0] || { metode: 'tunai', diterima: dataTransaksi.total, kembalian: 0 }
  const adaPotonganDonasi = Boolean((dataTransaksi.potongan_donasi && dataTransaksi.potongan_donasi > 0) || (dataTransaksi.potonganDonasi && dataTransaksi.potonganDonasi.nominal > 0))
  const isLunasTabungan = adaPotonganDonasi && (dataTransaksi.total === 0 || bayar.metode === 'tabungan')

  kontainer.innerHTML = `
    <div style="
      width: ${lebarKertas === 80 ? '76mm' : '54mm'};
      margin: 0 auto;
      padding: 6px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #000;
      line-height: 1.35;
    ">
      ${apakahSalinan ? '<div style="text-align: center; border: 1px dashed #000; padding: 2px; margin-bottom: 6px; font-weight: bold; font-size: 12px;">*** SALINAN STRUK ***</div>' : ''}
      
      <div style="text-align: center; margin-bottom: 8px;">
        <div style="font-size: 14px; font-weight: bold;">${namaToko}</div>
        <div style="font-size: 10px;">${alamatToko}</div>
        <div style="font-size: 10px;">Telp: ${telpToko}</div>
      </div>

      <div style="border-top: 1px dashed #000; margin: 4px 0;"></div>
      
      <div style="font-size: 10px; margin-bottom: 6px;">
        <div>No. Struk: ${dataTransaksi.nomor_struk}</div>
        <div>Waktu    : ${waktuStr}</div>
        <div>Kasir    : ${dataTransaksi.nama_kasir || 'Kasir'}</div>
      </div>

      <div style="border-top: 1px dashed #000; margin: 4px 0;"></div>
      
      <div style="margin: 6px 0;">
        ${daftarItemHtml}
      </div>

      <div style="border-top: 1px dashed #000; margin: 4px 0;"></div>

      <div style="display: flex; justify-content: space-between;">
        <span>Subtotal:</span>
        <span>${formatRupiah(dataTransaksi.subtotal)}</span>
      </div>

      ${dataTransaksi.diskon > 0 ? `
      <div style="display: flex; justify-content: space-between; color: #000;">
        <span>Diskon:</span>
        <span>-${formatRupiah(dataTransaksi.diskon)}</span>
      </div>` : ''}

      ${dataTransaksi.pajak > 0 ? `
      <div style="display: flex; justify-content: space-between;">
        <span>Pajak:</span>
        <span>+${formatRupiah(dataTransaksi.pajak)}</span>
      </div>` : ''}

      ${adaPotonganDonasi ? `
      <div style="display: flex; justify-content: space-between; font-size: 11px;">
        <span>Total Belanja:</span>
        <span>${formatRupiah(dataTransaksi.total_sebelum_potongan || dataTransaksi.subtotal)}</span>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 11px;">
        <span>Potong Saldo Tabungan:</span>
        <span>-${formatRupiah(dataTransaksi.potongan_donasi || dataTransaksi.potonganDonasi?.nominal)}</span>
      </div>` : ''}

      <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 13px; margin: 4px 0; border-top: 1px solid #000; padding-top: 3px;">
        <span>TOTAL DIBAYAR:</span>
        <span>${isLunasTabungan ? 'Rp 0 (LUNAS TABUNGAN)' : formatRupiah(dataTransaksi.total)}</span>
      </div>

      <div style="display: flex; justify-content: space-between; font-size: 10px;">
        <span>Metode Bayar:</span>
        <span>${isLunasTabungan ? 'TABUNGAN DONASI' : (bayar.metode || 'tunai').toUpperCase()}</span>
      </div>

      ${!isLunasTabungan ? `
      <div style="display: flex; justify-content: space-between; font-size: 10px;">
        <span>Uang Diterima:</span>
        <span>${formatRupiah(bayar.diterima)}</span>
      </div>

      <div style="display: flex; justify-content: space-between; font-size: 10px;">
        <span>Kembalian Fisik:</span>
        <span>${formatRupiah(bayar.kembalian)}</span>
      </div>` : ''}

      ${(dataTransaksi.sisaSaldoDonasi !== undefined && dataTransaksi.sisaSaldoDonasi !== null) ? `
      <div style="display: flex; justify-content: space-between; font-size: 10px; font-weight: bold; margin-top: 2px;">
        <span>Sisa Saldo Tabungan:</span>
        <span>${formatRupiah(dataTransaksi.sisaSaldoDonasi)}</span>
      </div>` : ''}

      ${(isLunasTabungan && (dataTransaksi.potonganDonasi?.nomorHp || dataTransaksi.hp_pelanggan)) ? `
      <div style="font-size: 9px; margin-top: 2px; color: #333;">
        Pembeli: ${dataTransaksi.potonganDonasi?.namaPelanggan || dataTransaksi.nama_pelanggan || 'Pelanggan'} (${dataTransaksi.potonganDonasi?.nomorHp || dataTransaksi.hp_pelanggan})
      </div>` : ''}

      ${dataTransaksi.donasi ? `
      <div style="border-top: 1px dotted #000; margin: 4px 0; padding-top: 4px; font-size: 9.5px;">
        <div style="display: flex; justify-content: space-between; font-weight: bold;">
          <span>Donasi Kembalian Ditabung:</span>
          <span>+${formatRupiah(dataTransaksi.donasi.nominal)}</span>
        </div>
        <div>No. HP Pembeli : ${dataTransaksi.donasi.nomorHp}</div>
        ${dataTransaksi.donasi.totalSaldoBaru ? `<div>Total Saldo Anda : ${formatRupiah(dataTransaksi.donasi.totalSaldoBaru)}</div>` : ''}
        <div style="font-style: italic; font-size: 8.5px; margin-top: 2px;">*Dapat dicairkan uang cash / belanja setelah 1 bulan</div>
      </div>` : ''}

      <div style="border-top: 1px dashed #000; margin: 8px 0 4px 0;"></div>

      <div style="text-align: center; font-size: 10px; margin-top: 6px;">
        <div>Terima Kasih atas Kunjungan Anda</div>
        <div>Barang yang dibeli tidak dapat ditukar kecuali perjanjian</div>
      </div>
    </div>
  `

  // Panggil dialog cetak browser
  setTimeout(() => {
    window.print()
  }, 100)
}

/**
 * Cetak Struk Bukti Penarikan Uang Tunai Tabungan Donasi
 */
export function cetakStrukPencairanDonasi(bukti, dataToko = {}) {
  let kontainer = document.getElementById('struk-cetak')
  if (!kontainer) {
    kontainer = document.createElement('div')
    kontainer.id = 'struk-cetak'
    document.body.appendChild(kontainer)
  }

  const namaToko = dataToko.nama || 'TOKO BERKAH SEJAHTERA'
  const formatRupiah = (angka) => 'Rp ' + Number(angka || 0).toLocaleString('id-ID')

  kontainer.innerHTML = `
    <div style="
      width: 54mm;
      margin: 0 auto;
      padding: 6px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #000;
      line-height: 1.35;
    ">
      <div style="text-align: center; font-weight: bold; font-size: 13px; margin-bottom: 4px;">
        ${namaToko}
      </div>
      <div style="text-align: center; font-weight: bold; border-top: 1px dashed #000; border-bottom: 1px dashed #000; padding: 3px 0; margin-bottom: 6px;">
        BUKTI PENARIKAN UANG TUNAI
        TABUNGAN DONASI PEMBELI
      </div>
      <div style="font-size: 10px; margin-bottom: 6px;">
        <div>Waktu    : ${new Date().toLocaleString('id-ID')}</div>
        <div>Kasir    : ${bukti.namaKasir || 'Kasir'}</div>
        <div>Pembeli  : ${bukti.nama_pelanggan || 'Pelanggan'}</div>
        <div>No. HP   : ${bukti.nomor_hp}</div>
      </div>
      <div style="border-top: 1px solid #000; padding: 6px 0; font-size: 13px; font-weight: bold; display: flex; justify-content: space-between;">
        <span>DICAIRKAN:</span>
        <span>${formatRupiah(bukti.nominal_dicairkan)}</span>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 10px;">
        <span>Sisa Saldo:</span>
        <span>${formatRupiah(bukti.sisa_saldo)}</span>
      </div>
      <div style="border-top: 1px dashed #000; margin: 8px 0 6px 0;"></div>
      <div style="text-align: center; font-size: 9px;">
        <div>Uang tunai telah diserahkan dari kasir kepada pembeli.</div>
        <div>Terima kasih atas kebaikan Anda menabung kembalian.</div>
      </div>
    </div>
  `

  setTimeout(() => {
    window.print()
  }, 100)
}
