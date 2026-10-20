/**
 * Utilitas Kompresi & Penyesuaian Foto Produk (Format Bingkai Persegi 1:1 Seragam)
 * Menghasilkan data URI WebP berdimensi presisi 200x200 pixel (persegi 1:1)
 * dengan bobot sangat minimal (~3 KB - 8 KB) agar tidak menghabiskan memori RAM maupun IndexedDB/SQLite.
 */

/**
 * Membaca File berkas gambar menjadi HTMLImageElement
 */
export function bacaBerkasKeImage(berkas) {
  return new Promise((resolve, reject) => {
    if (!berkas) {
      return reject(new Error('Berkas gambar tidak ditemukan'))
    }

    // Jika sudah berupa data URL atau URL string
    if (typeof berkas === 'string') {
      const img = new Image()
      img.onload = () => resolve({ img, dataUrlAsli: berkas })
      img.onerror = () => reject(new Error('Gagal memuat gambar dari URL/DataURL'))
      img.src = berkas
      return
    }

    if (!berkas.type || !berkas.type.startsWith('image/')) {
      return reject(new Error('Berkas harus berupa file gambar (JPG, PNG, WebP)'))
    }

    const pembaca = new FileReader()
    pembaca.readAsDataURL(berkas)
    pembaca.onload = (event) => {
      const img = new Image()
      img.src = event.target.result
      img.onload = () => resolve({ img, dataUrlAsli: event.target.result })
      img.onerror = () => reject(new Error('Gagal memuat format gambar'))
    }
    pembaca.onerror = () => reject(new Error('Gagal membaca berkas gambar'))
  })
}

/**
 * Memotong dan menyesuaikan gambar ke bingkai 1:1 persegi seragam (200x200)
 * berdasarkan nilai zoom (skala) dan panX / panY (geser)
 */
export function sesuaikanBingkaiPersegi(img, zoom = 1, panX = 0, panY = 0, ukuranBingkai = 200, kualitas = 0.7) {
  const kanvas = document.createElement('canvas')
  kanvas.width = ukuranBingkai
  kanvas.height = ukuranBingkai
  const ctx = kanvas.getContext('2d')

  // Latar belakang netral putih
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, ukuranBingkai, ukuranBingkai)

  // Hitung skala dasar agar mengisi bingkai persegi (cover)
  const aspect = img.width / img.height
  let drawWidth, drawHeight

  if (aspect >= 1) {
    // Landscape: tinggi paskan bingkai, lebar menyesuaikan
    drawHeight = ukuranBingkai * zoom
    drawWidth = drawHeight * aspect
  } else {
    // Portrait: lebar paskan bingkai, tinggi menyesuaikan
    drawWidth = ukuranBingkai * zoom
    drawHeight = drawWidth / aspect
  }

  // Posisi tengah + offset geser (pan)
  const posX = (ukuranBingkai - drawWidth) / 2 + (panX * drawWidth / 100)
  const posY = (ukuranBingkai - drawHeight) / 2 + (panY * drawHeight / 100)

  ctx.drawImage(img, posX, posY, drawWidth, drawHeight)

  // Ekspor ke WebP (fallback JPEG)
  let dataUrl = kanvas.toDataURL('image/webp', kualitas)
  if (!dataUrl.startsWith('data:image/webp')) {
    dataUrl = kanvas.toDataURL('image/jpeg', kualitas)
  }

  const perkiraanKb = Math.max(1, Math.round((dataUrl.length * 3) / 4 / 1024))

  return {
    dataUrl,
    perkiraanKb,
    lebar: ukuranBingkai,
    tinggi: ukuranBingkai
  }
}

/**
 * Kompres otomatis ke persegi 1:1 tengah (Center-Crop Cover 200x200)
 */
export async function kompresFotoProduk(berkas, maxDimensi = 200, kualitas = 0.7) {
  const { img } = await bacaBerkasKeImage(berkas)
  return sesuaikanBingkaiPersegi(img, 1, 0, 0, maxDimensi, kualitas)
}
