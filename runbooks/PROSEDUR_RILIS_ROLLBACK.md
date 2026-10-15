# Runbook F-14: Prosedur Rilis & Rollback Aplikasi Kasirku POS

Dokumen ini menjelaskan alur rilis versi baru ke server produksi dan prosedur rollback darurat untuk memastikan **zero downtime** dan data transaksi tidak mengalami korupsi.

---

## 1. Alur Rilis Versi Baru (Release Pipeline)

1. **Permintaan Klien & Pengembangan**:
   - Setiap fitur atau perbaikan dicatat pada issue GitHub.
   - Dikembangkan pada branch fitur dan diuji secara lokal.
2. **Pengujian Otomatis (CI)**:
   - Saat pull request di-merge ke branch `main`, GitHub Actions menjalankan pengujian backend (`pytest`) dan build frontend (`pnpm build`).
3. **Build & Tagging Image Docker**:
   - Image Docker backend dibuild dengan tag semver (contoh: `v1.2.0`) dan `latest`.
   - Diunggah ke registry container.

---

## 2. Prosedur Deploy ke Server Produksi (Oracle Free Tier / VPS)

Jalankan perintah berikut di server produksi:

```bash
# 1. Masuk ke direktori aplikasi
cd /opt/kasirku

# 2. PRA-DEPLOY: Backup database seketika sebelum melakukan update
docker exec -t kasirku_db pg_dump -U kasirku_user -d kasirku_db -Fc > "/tmp/pre_deploy_$(date +%Y%m%d_%H%M%S).dump"

# 3. Ambil kode dan image terbaru
git pull origin main
docker compose pull api

# 4. Restart container API dengan image baru
docker compose up -d --no-deps api

# 5. Verifikasi Pemeriksaan Kesehatan (Health Checks)
sleep 5
STATUS_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
STATUS_READY=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ready)

if [ "$STATUS_HEALTH" = "200" ] && [ "$STATUS_READY" = "200" ]; then
    echo "✅ Rilis BERHASIL! Layanan sehat dan siap melayani transaksi."
else
    echo "❌ Health check GAGAL! Memulai prosedur ROLLBACK otomatis..."
    ./scripts/rollback.sh
fi
```

---

## 3. Prosedur Rollback Darurat (Jika Health Check Gagal)

Jika versi baru gagal boot atau mengalami crash loop:

1. **Kembalikan Container ke Image Versi Sebelumnya**:
   ```bash
   # Ganti tag image ke versi stabil sebelumnya
   export TAG_API="v1.1.9"
   docker compose up -d --no-deps api
   ```
2. **Kebijakan Skema Database (Expand and Contract)**:
   - Skema database Kasirku dirancang backward-compatible (kolom baru nullable atau memiliki nilai default).
   - Migrasi database **tidak di-rollback ke bawah** secara terburu-buru, sehingga versi API lama tetap dapat membaca dan menulis data tanpa galat.
3. **Pemberitahuan Tim**:
   - Periksa log container penyebab kegagalan:
     ```bash
     docker logs kasirku_api --tail 100
     ```

---

## 4. Siklus Pembaruan Frontend PWA di Perangkat Kasir

- Service Worker di browser secara berkala memeriksa pembaruan berkas `/sw.js`.
- Ketika versi baru terdeteksi:
  - Cache baru diunduh di latar belakang tanpa mengganggu transaksi kasir yang sedang berjalan.
  - Saat kasir selesai transaksi atau merefresh tab, aplikasi otomatis aktif menggunakan bundle terbaru.
