/**
 * Utilitas Kompresi Foto Produk (Ringan & Hemat Memori)
 * Menghasilkan data URI WebP/JPEG berdimensi maksimal 200x200 pixel
 * dengan bobot sangat minimal (~3 KB - 8 KB) agar tidak menghabiskan memori RAM maupun IndexedDB/SQLite.
 */
export async function kompresFotoProduk(berkas, maxDimensi = 200, kualitas = 0.7) {
  return new Promise((resolve, reject) => {
    if (!berkas || !berkas.type.startsWith('image/')) {
      return reject(new Error('Berkas harus berupa file gambar (JPG, PNG, WebP)'))
    }

    const pembaca = new FileReader()
    pembaca.readAsDataURL(berkas)
    pembaca.onload = (event) => {
      const img = new Image()
      img.src = event.target.result
      img.onload = () => {
        let lebar = img.width
        let tinggi = img.height

        // Skala proporsional agar tidak melebihi maxDimensi (200px)
        if (lebar > tinggi) {
          if (lebar > maxDimensi) {
            tinggi = Math.round((tinggi * maxDimensi) / lebar)
            lebar = maxDimensi
          }
        } else {
          if (tinggi > maxDimensi) {
            lebar = Math.round((lebar * maxDimensi) / tinggi)
            tinggi = maxDimensi
          }
        }

        const kanvas = document.createElement('canvas')
        kanvas.width = lebar
        kanvas.height = tinggi
        const ctx = kanvas.getContext('2d')
        ctx.drawImage(img, 0, 0, lebar, tinggi)

        // Utamakan WebP untuk kompresi paling efisien, fallback ke JPEG
        let dataUrl = kanvas.toDataURL('image/webp', kualitas)
        if (!dataUrl.startsWith('data:image/webp')) {
          dataUrl = kanvas.toDataURL('image/jpeg', kualitas)
        }

        // Hitung estimasi ukuran dalam KB
        const perkiraanKb = Math.max(1, Math.round((dataUrl.length * 3) / 4 / 1024))
        resolve({
          dataUrl,
          perkiraanKb,
          lebar,
          tinggi
        })
      }
      img.onerror = () => reject(new Error('Gagal memuat format gambar'))
    }
    pembaca.onerror = () => reject(new Error('Gagal membaca berkas gambar'))
  })
}
