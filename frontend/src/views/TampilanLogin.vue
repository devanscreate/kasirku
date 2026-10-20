<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { Lock, User, AlertCircle, ShoppingBag, ShieldCheck } from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()

const namaPengguna = ref('kasir')
const kataSandi = ref('password123')
const sedangMemuat = ref(false)
const pesanKesalahan = ref('')

async function prosesLogin() {
  if (!namaPengguna.value || !kataSandi.value) {
    pesanKesalahan.value = 'Silakan isi nama pengguna dan kata sandi Anda'
    return
  }

  sedangMemuat.value = true
  pesanKesalahan.value = ''

  try {
    await authStore.login(namaPengguna.value, kataSandi.value)
    router.push('/pos')
  } catch (err) {
    pesanKesalahan.value = err.message || 'Login gagal, periksa nama pengguna dan kata sandi Anda'
  } finally {
    sedangMemuat.value = false
  }
}

function isiCepat(peran) {
  if (peran === 'kasir') {
    namaPengguna.value = 'kasir'
    kataSandi.value = 'password123'
  } else if (peran === 'manajer') {
    namaPengguna.value = 'manajer'
    kataSandi.value = 'password123'
  } else if (peran === 'owner') {
    namaPengguna.value = 'owner'
    kataSandi.value = 'password123'
  }
}
</script>

<template>
  <div class="halaman-login">
    <div class="kotak-login panel-kartu">
      <div class="logo-header">
        <div class="ikon-logo">
          <ShoppingBag :size="36" />
        </div>
        <h1 class="judul-aplikasi">Kasirku POS</h1>
        <p class="tagline">Sistem Kasir Pintar, Ringan & Siap Offline</p>
      </div>

      <!-- Pesan Kesalahan / Rate Limit -->
      <div v-if="pesanKesalahan" class="peringatan-error">
        <AlertCircle :size="20" class="flex-shrink-0" />
        <span>{{ pesanKesalahan }}</span>
      </div>

      <form @submit.prevent="prosesLogin" class="form-login">
        <div class="grup-form">
          <label class="label-form">Nama Pengguna (Username):</label>
          <div class="input-ikon-wrap">
            <User :size="20" class="ikon-input" />
            <input 
              v-model="namaPengguna" 
              type="text" 
              class="input-teks input-dengan-ikon" 
              placeholder="Contoh: kasir" 
              required
              autofocus
            />
          </div>
        </div>

        <div class="grup-form">
          <label class="label-form">Kata Sandi (Password):</label>
          <div class="input-ikon-wrap">
            <Lock :size="20" class="ikon-input" />
            <input 
              v-model="kataSandi" 
              type="password" 
              class="input-teks input-dengan-ikon" 
              placeholder="Masukkan kata sandi" 
              required
            />
          </div>
        </div>

        <button 
          type="submit" 
          class="tombol tombol-primer tombol-lg w-full mt-4 tombol-masuk"
          :disabled="sedangMemuat"
        >
          <ShieldCheck :size="22" />
          <span>{{ sedangMemuat ? 'Memverifikasi...' : 'Masuk Aplikasi Kasir' }}</span>
        </button>
      </form>

      <!-- Akses Demo Cepat -->
      <div class="akses-demo">
        <div class="label-demo">Akses Cepat Akun Demo:</div>
        <div class="tombol-demo-wrap">
          <button type="button" class="tombol-demo demo-kasir" @click="isiCepat('kasir')" title="Login sebagai Kasir">
            Kasir
          </button>
          <button type="button" class="tombol-demo demo-manajer" @click="isiCepat('manajer')" title="Login sebagai Manajer">
            Manajer
          </button>
          <button type="button" class="tombol-demo demo-owner" @click="isiCepat('owner')" title="Login sebagai Pemilik Toko">
            Owner
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.halaman-login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: #f8fafc;
}
.kotak-login {
  width: 100%;
  max-width: 440px;
  padding: 36px 32px;
  background: #ffffff;
  border-radius: var(--radius-lg);
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
}
.logo-header {
  text-align: center;
  margin-bottom: 28px;
}
.ikon-logo {
  width: 56px;
  height: 56px;
  background: #0f172a;
  color: white;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 14px auto;
}
.judul-aplikasi {
  font-size: 1.6rem;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.02em;
}
.tagline {
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 500;
  margin-top: 4px;
}
.peringatan-error {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 600;
  margin-bottom: 20px;
}
.grup-form {
  margin-bottom: 18px;
}
.label-form {
  display: block;
  font-size: 0.875rem;
  font-weight: 700;
  margin-bottom: 6px;
  color: #0f172a;
}
.input-ikon-wrap {
  position: relative;
  display: flex;
  align-items: center;
}
.ikon-input {
  position: absolute;
  left: 14px;
  color: #64748b;
}
.input-dengan-ikon {
  padding-left: 44px;
  height: 46px;
  font-size: 0.95rem;
  font-weight: 500;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  border-radius: var(--radius-md);
}
.input-dengan-ikon:focus {
  background: #ffffff;
  border-color: #0f172a;
}
.w-full {
  width: 100%;
}
.mt-4 {
  margin-top: 16px;
}
.tombol-masuk {
  height: 48px;
  font-size: 1rem;
  font-weight: 700;
  border-radius: var(--radius-md);
}

.akses-demo {
  margin-top: 24px;
  padding-top: 18px;
  border-top: 1px dashed #e2e8f0;
  text-align: center;
}
.label-demo {
  font-size: 0.8rem;
  color: #64748b;
  font-weight: 600;
  margin-bottom: 10px;
}
.tombol-demo-wrap {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.tombol-demo {
  padding: 8px 6px;
  border-radius: var(--radius-md);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #0f172a;
}
.tombol-demo:hover {
  background: #ffffff;
  border-color: #0f172a;
}
.demo-kasir, .demo-manajer, .demo-owner {
  background: #f8fafc;
  color: #0f172a;
  border-color: #cbd5e1;
}
</style>
