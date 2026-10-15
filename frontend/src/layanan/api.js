/**
 * Layanan HTTP Client Kasirku
 * Menghubungkan Frontend ke Backend FastAPI
 */
const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

export async function panggilApi(titikAkhir, opsi = {}) {
  const url = `${BASE_URL}${titikAkhir}`
  const token = localStorage.getItem('token_akses')

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(opsi.headers || {})
  }

  try {
    const respons = await fetch(url, {
      ...opsi,
      headers
    })

    if (respons.status === 401) {
      // Jika token tidak valid / kedaluwarsa saat online
      localStorage.removeItem('token_akses')
      localStorage.removeItem('pengguna')
      window.dispatchEvent(new CustomEvent('auth:kadaluarsa'))
    }

    const data = await respons.json().catch(() => null)

    if (!respons.ok) {
      const pesanError = data?.detail?.message || data?.message || `Terjadi kesalahan (Kode: ${respons.status})`
      const errorObj = new Error(pesanError)
      errorObj.status = respons.status
      errorObj.detail = data?.detail || data
      throw errorObj
    }

    return data
  } catch (err) {
    if (!window.navigator.onLine || err.name === 'TypeError') {
      const errorJaringan = new Error('Koneksi internet offline atau server tidak dapat dijangkau')
      errorJaringan.status = 0
      errorJaringan.isOffline = true
      throw errorJaringan
    }
    throw err
  }
}
