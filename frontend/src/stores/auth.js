import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { panggilApi } from '../layanan/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token_akses') || null)
  const dataPengguna = ref(JSON.parse(localStorage.getItem('pengguna') || 'null'))

  const apakahLogin = computed(() => !!token.value && !!dataPengguna.value)
  const peran = computed(() => dataPengguna.value?.peran || 'kasir')
  const namaLengkap = computed(() => dataPengguna.value?.nama_lengkap || 'Pengguna')
  const idPengguna = computed(() => dataPengguna.value?.id_pengguna || dataPengguna.value?.id || '')
  const idToko = computed(() => dataPengguna.value?.id_toko || '')

  async function login(namaPengguna, kataSandi) {
    const hasil = await panggilApi('/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        nama_pengguna: namaPengguna,
        kata_sandi: kataSandi
      })
    })

    token.value = hasil.token_akses
    dataPengguna.value = {
      id: hasil.id_pengguna,
      nama_pengguna: hasil.nama_pengguna,
      nama_lengkap: hasil.nama_lengkap,
      peran: hasil.peran,
      id_toko: hasil.id_toko
    }

    localStorage.setItem('token_akses', hasil.token_akses)
    localStorage.setItem('pengguna', JSON.stringify(dataPengguna.value))

    return dataPengguna.value
  }

  function logout() {
    panggilApi('/auth/logout', { method: 'POST' }).catch(() => {})
    token.value = null
    dataPengguna.value = null
    localStorage.removeItem('token_akses')
    localStorage.removeItem('pengguna')
  }

  function punyaAkses(daftarPeranDiizinkan) {
    if (!dataPengguna.value) return false
    return daftarPeranDiizinkan.includes(dataPengguna.value.peran)
  }

  return {
    token,
    dataPengguna,
    apakahLogin,
    peran,
    namaLengkap,
    idPengguna,
    idToko,
    login,
    logout,
    punyaAkses
  }
})
