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

      <!-- Akses Demo Cepat Berwarna Menarik -->
      <div class="akses-demo">
        <div class="label-demo">Klik 1 Tombol untuk Isi Akun Demo:</div>
        <div class="tombol-demo-wrap">
          <button type="button" class="tombol-demo demo-kasir" @click="isiCepat('kasir')" title="Login sebagai Kasir">
            👤 Kasir
          </button>
          <button type="button" class="tombol-demo demo-manajer" @click="isiCepat('manajer')" title="Login sebagai Manajer">
            💼 Manajer
          </button>
          <button type="button" class="tombol-demo demo-owner" @click="isiCepat('owner')" title="Login sebagai Pemilik Toko">
            👑 Pemilik (Owner)
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
  background: linear-gradient(135deg, #e0e7ff 0%, #f0f4f9 50%, #dbeafe 100%);
}
.kotak-login {
  width: 100%;
  max-width: 460px;
  padding: 42px 36px;
  background: #ffffff;
  border-radius: var(--radius-xl);
  border: 2px solid #bfdbfe;
  box-shadow: 0 12px 36px rgba(30, 64, 175, 0.12);
}
.logo-header {
  text-align: center;
  margin-bottom: 28px;
}
.ikon-logo {
  width: 72px;
  height: 72px;
  background: linear-gradient(135deg, #1d4ed8, #2563eb);
  color: white;
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px auto;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.35);
}
.judul-aplikasi {
  font-size: 1.8rem;
  font-weight: 900;
  color: #0f172a;
  letter-spacing: -0.02em;
}
.tagline {
  font-size: 0.95rem;
  color: #475569;
  font-weight: 600;
  margin-top: 4px;
}
.peringatan-error {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fef2f2;
  border: 2px solid #fecaca;
  color: #b91c1c;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  font-weight: 700;
  margin-bottom: 20px;
}
.grup-form {
  margin-bottom: 20px;
}
.label-form {
  display: block;
  font-size: 0.95rem;
  font-weight: 800;
  margin-bottom: 8px;
  color: #0f172a;
}
.input-ikon-wrap {
  position: relative;
  display: flex;
  align-items: center;
}
.ikon-input {
  position: absolute;
  left: 16px;
  color: #2563eb;
}
.input-dengan-ikon {
  padding-left: 48px;
  height: 52px;
  font-size: 1.05rem;
  font-weight: 600;
  border: 2px solid #cbd5e1;
  background: #f8fafc;
}
.input-dengan-ikon:focus {
  background: #ffffff;
  border-color: #2563eb;
}
.w-full {
  width: 100%;
}
.mt-4 {
  margin-top: 16px;
}
.tombol-masuk {
  height: 56px;
  font-size: 1.15rem;
  font-weight: 900;
  letter-spacing: 0.02em;
}

.akses-demo {
  margin-top: 28px;
  padding-top: 22px;
  border-top: 2px dashed #cbd5e1;
  text-align: center;
}
.label-demo {
  font-size: 0.85rem;
  color: #475569;
  font-weight: 800;
  margin-bottom: 12px;
}
.tombol-demo-wrap {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.tombol-demo {
  padding: 10px 8px;
  border-radius: 10px;
  font-size: 0.875rem;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid;
  box-shadow: 0 2px 4px rgba(0,0,0,0.04);
}
.tombol-demo:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.08);
}
.demo-kasir {
  background: #eff6ff;
  color: #1d4ed8;
  border-color: #bfdbfe;
}
.demo-manajer {
  background: #f5f3ff;
  color: #7c3aed;
  border-color: #ddd6fe;
}
.demo-owner {
  background: #fffbeb;
  color: #b45309;
  border-color: #fde68a;
}
</style>
