# 🛒 Kasirku — Aplikasi POS Ringan & Offline-First

Aplikasi Point of Sale (POS) modern, ringan, dan siap beroperasi saat internet terputus (**Offline-First**) yang dirancang khusus sesuai spesifikasi lengkap **PRD Aplikasi POS Ringan & Offline-First**.

---

## 🌟 Keunggulan Utama & Fitur Unggulan

1. **Offline-First Nyata (PWA + IndexedDB)**:
   - Kasir tetap dapat membuka shift, mencari produk, melakukan scan barcode, menambah keranjang, dan mencetak struk saat internet putus.
   - Menggunakan **Outbox Pattern** dan penyimpanan lokal IndexedDB (Dexie).
   - Pengiriman antrean otomatis (FIFO) dengan `Idempotency-Key = sale_id` saat online kembali sehingga transaksi **tidak akan pernah hilang dan tidak akan pernah tercatat ganda**.
2. **Integritas Stok & Keuangan Terjamin**:
   - Stok dipotong secara atomik dengan pengurutan `product_id` naik untuk mencegah *deadlock*.
   - Nilai uang disimpan dalam bilangan bulat Rupiah murni (`BIGINT`), bebas dari galat desimal (*floating point rounding errors*).
   - Deteksi anomali otomatis (*Flagging*): `negative_stock`, `clock_skew`, `price_mismatch`, dan `total_mismatch`.
3. **Kontrol Shift & Rekonsiliasi Kas (F-02 & F-09)**:
   - Fitur *Blind Close* untuk mencegah kasir memanipulasi hitungan kas fisik.
   - Peringatan dan catatan wajib jika selisih kas fisik melebihi ambang batas (`cash_diff_threshold`).
4. **Void & Retur Terkontrol (F-07 & F-08)**:
   - **Void**: Membatalkan transaksi selama shift kasir masih terbuka, otomatis memulihkan stok dan mencatat audit log.
   - **Retur**: Mendukung pengembalian parsial atau penuh dengan opsi apakah barang dimasukkan kembali ke stok (*restock*).
5. **Bahasa Indonesia 100% Sesuai Bagian 15 PRD**:
   - Seluruh teks tampilan, pesan kesalahan, nama variabel, dan sintaks kode menggunakan istilah Bahasa Indonesia untuk kemudahan pemeliharaan (*maintenance*).

---

## 🛠️ Stack Teknologi

- **Frontend**: Vue 3 (Composition API) + Vite + Pinia + Dexie (IndexedDB) + PWA + Lucide Icons.
- **Backend**: FastAPI (Python async) + SQLAlchemy 2 + Pydantic v2 + Argon2id + JWT Token.
- **Basis Data**: SQLite async (`sqlite+aiosqlite`) untuk pengembangan lokal cepat, dan PostgreSQL 16 untuk produksi.
- **Infrastruktur & Deploy**: Docker Compose + Caddy (Reverse Proxy & kompresi aset PWA satu origin).
- **Paket Manajer**: `pnpm` (eksklusif untuk frontend).

---

## 🚀 Panduan Menjalankan Aplikasi

### 1. Menjalankan Backend (FastAPI)

Pastikan Python 3.12+ telah terpasang di komputer Anda:

```bash
# Masuk ke folder backend
cd backend

# Aktifkan virtual environment yang sudah tersedia
# Di Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Atau jika di Command Prompt (CMD):
.\venv\Scripts\activate.bat

# Pasang dependensi jika belum terpasang:
pip install -r requirements.txt

# Jalankan server FastAPI
uvicorn app.utama:aplikasi --reload --port 8000
```

> **Endpoint Dokumentasi API Interaktif**:
> - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
> - Redoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
> - Health Check: [http://localhost:8000/health](http://localhost:8000/health)

---

### 2. Menjalankan Frontend (Vue 3 PWA)

Buka jendela terminal baru:

```bash
# Masuk ke folder frontend
cd frontend

# Pasang dependensi menggunakan pnpm
pnpm install

# Jalankan dev server lokal
pnpm dev
```

Buka peramban (Google Chrome) di alamat:
👉 **[http://localhost:5173](http://localhost:5173)**

---

### 3. Menjalankan dengan Docker Compose (Produksi / Full Stack)

Untuk menjalankan seluruh stack (Caddy, FastAPI, PostgreSQL) dalam satu perintah:

```bash
# Pastikan Docker Desktop berjalan, lalu eksekusi:
docker compose up -d --build
```
Aplikasi langsung dapat diakses di: **[http://localhost](http://localhost)**.

---

## 🔑 Akun Demo Default

Saat aplikasi pertama kali dijalankan, sistem otomatis membuatkan toko dan 3 pengguna awal dengan kata sandi bawaan `password123`:

| Peran | Username | Kata Sandi | Hak Akses Utama |
| :--- | :--- | :--- | :--- |
| **Kasir** | `kasir` | `password123` | Buka/tutup shift sendiri, kasir POS, scan barcode, cetak struk |
| **Manajer** | `manajer` | `password123` | Semua fitur kasir + Void, Retur, Kelola Produk, Stok, Laporan |
| **Owner (Pemilik)** | `owner` | `password123` | Akses penuh seluruh sistem + Pengaturan Toko & Pengguna |

---

## 🧪 Menjalankan Pengujian Otomatis (UAT & Unit Test)

Semua skenario pengujian bisnis (U01 sampai U16) dapat dijalankan menggunakan `pytest`:

```bash
# Dari root proyek atau folder backend:
.\backend\venv\Scripts\pytest backend\tests -v
```

Hasil uji coba mencakup:
- ✅ **U01**: Login benar dan proteksi brute-force rate limit (maks 5 gagal/menit).
- ✅ **U02**: Buka shift kasir & validasi pencegahan shift ganda.
- ✅ **U03**: Transaksi penjualan tunai online dan pemotongan stok atomik.
- ✅ **U04**: Transaksi pembayaran QRIS manual.
- ✅ **U06**: Retry transaksi idempoten (*Idempotency-Key*).
- ✅ **U08**: Penjualan stok minus dengan penandaan anomali (*negative_stock flag*).
- ✅ **U10**: Void transaksi oleh Manajer saat shift masih terbuka.
- ✅ **U11**: Penolakan void jika shift kasir sudah ditutup (*409 SHIFT_CLOSED*).
- ✅ **U12**: Retur parsial dan validasi batas kuota retur.
- ✅ **U13**: Tutup shift kasir dan rekonsiliasi kas fisik.
- ✅ **U14**: Penegakan RBAC server (kasir ditolak saat mengakses laporan / void).
- ✅ **U15**: Sinkronisasi perubahan harga katalog (*price_history*).
- ✅ **U16**: Deteksi anomali ketidaksesuaian jam perangkat klien (*clock_skew*).

---

## 📂 Struktur Proyek

```
kasirku/
├── backend/
│   ├── app/
│   │   ├── basis_data.py          # Konfigurasi koneksi Async SQLAlchemy
│   │   ├── konfigurasi.py         # Setelan aplikasi & variabel ENV
│   │   ├── data_awal.py           # Seeder otomatis toko, user, dan produk demo
│   │   ├── utama.py               # Entrypoint FastAPI & middleware CORS
│   │   ├── keamanan/              # Argon2id, JWT, dan pembatas laju (Rate Limit)
│   │   ├── model/                 # Model relasional tabel database
│   │   ├── rute/                  # Router endpoint (/auth, /products, /sales, dll)
│   │   └── skema/                 # Skema validasi Pydantic v2
│   ├── tests/
│   │   └── test_kasirku.py        # Pengujian otomatis skenario UAT
│   ├── Dockerfile                 # Image container FastAPI
│   └── requirements.txt           # Dependensi pustaka Python
├── frontend/
│   ├── public/                    # Web App Manifest & Service Worker PWA
│   ├── src/
│   │   ├── basis_data/            # Skema IndexedDB lokal Dexie
│   │   ├── gaya/                  # Desain CSS tema modern ramah mata
│   │   ├── komponen/              # Komponen dialog (Bayar, Shift, Sukses, Struk)
│   │   ├── layanan/               # Service client API, outbox sync, cetak struk
│   │   ├── router/                # Vue Router dengan RBAC navigation guard
│   │   ├── stores/                # State management Pinia (Auth, Shift, Keranjang, Koneksi)
│   │   ├── views/                 # Halaman POS, Transaksi, Produk, Stok, Laporan, Pengaturan
│   │   ├── App.vue                # Komponen induk
│   │   └── main.js                # Inisialisasi Vue & registrasi Service Worker
│   ├── Dockerfile                 # Image builder aset PWA
│   ├── package.json               # Konfigurasi dependensi pnpm
│   └── vite.config.js             # Konfigurasi build Vite & proxy API
├── runbooks/
│   ├── PROSEDUR_BACKUP_RESTORE.md # Prosedur SOP Backup R2 & Latihan Restore (F-13)
│   └── PROSEDUR_RILIS_ROLLBACK.md # Prosedur Rilis & Rollback Otomatis (F-14)
├── .github/workflows/
│   └── ci.yml                     # Pipeline CI lint, test, dan build otomatis
├── Caddyfile                      # Konfigurasi Caddy reverse proxy satu origin
├── docker-compose.yml             # Orkestrasi Docker container
├── PRD — Aplikasi POS Ringan & Offline-First.md
└── README.md                      # Dokumentasi lengkap proyek
```
