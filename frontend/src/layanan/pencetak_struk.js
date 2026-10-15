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

      <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 13px; margin: 4px 0; border-top: 1px solid #000; padding-top: 3px;">
        <span>TOTAL:</span>
        <span>${formatRupiah(dataTransaksi.total)}</span>
      </div>

      <div style="display: flex; justify-content: space-between; font-size: 10px;">
        <span>Bayar (${bayar.metode.toUpperCase()}):</span>
        <span>${formatRupiah(bayar.diterima)}</span>
      </div>

      <div style="display: flex; justify-content: space-between; font-size: 10px;">
        <span>Kembalian:</span>
        <span>${formatRupiah(bayar.kembalian)}</span>
      </div>

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
