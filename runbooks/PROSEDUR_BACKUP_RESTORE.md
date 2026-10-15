# Runbook F-13: Prosedur Backup & Restore Basis Data Kasirku POS

Dokumen ini merupakan panduan operasional standar (**SOP**) untuk menjamin integritas data transaksi dan ketersediaan sistem sesuai target **RPO ≤ 24 jam** dan **RTO ≤ 2 jam**.

---

## 1. Arsitektur & Kebijakan Backup

- **Format Dump**: `pg_dump -Fc` (format kustom PostgreSQL terkompresi dengan metadata integritas).
- **Enkripsi**: Berkas dump dienkripsi secara simetris menggunakan AES-256 (`gpg` atau `openssl`) sebelum ditransmisikan.
- **Penyimpanan**: Bucket Cloudflare R2 (kompatibel S3 dengan biaya keluar Rp0).
- **Jadwal Eksekusi**: Otomatis setiap hari pukul **02:00 WIB** (saat toko tutup dan tidak ada aktivitas kasir).
- **Kebijakan Retensi**:
  - 7 cadangan harian terakhir.
  - 4 cadangan mingguan terakhir.

---

## 2. Skrip Backup Otomatis Harian (`backup_harian.sh`)

Simpan skrip berikut di server backend:

```bash
#!/usr/bin/env bash
set -euo pipefail

WAKTU=$(date +"%Y%m%d_%H%M%S")
NAMA_BERKAS="kasirku_backup_${WAKTU}.dump"
KUNCI_ENKRIPSI="${PASSPHRASE_BACKUP}"
BUCKET_R2="r2://kasirku-backups"

echo "[$(date)] Memulai proses pencadangan basis data..."

# 1. Eksekusi pg_dump dari container PostgreSQL
docker exec -t kasirku_db pg_dump -U kasirku_user -d kasirku_db -Fc > "/tmp/${NAMA_BERKAS}"

# 2. Enkripsi berkas menggunakan GPG
gpg --batch --yes --passphrase "${KUNCI_ENKRIPSI}" -c "/tmp/${NAMA_BERKAS}"
rm -f "/tmp/${NAMA_BERKAS}"

# 3. Unggah ke Cloudflare R2 via rclone / AWS CLI
aws s3 cp "/tmp/${NAMA_BERKAS}.gpg" "${BUCKET_R2}/${NAMA_BERKAS}.gpg" \
    --endpoint-url "https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

rm -f "/tmp/${NAMA_BERKAS}.gpg"
echo "[$(date)] Pencadangan dan pengunggahan ke R2 berhasil."
```

---

## 3. Latihan Restore Bulanan (Wajib Dilakukan)

> **Prinsip Utama:** *«Backup yang belum pernah dites restore belum dianggap backup.»*

Latihan restore dilakukan setiap tanggal 1 setiap bulan ke lingkungan uji coba (staging/local):

### Langkah-langkah:

1. **Siapkan Database Kosong Pengujian**:
   ```bash
   docker exec -it kasirku_db psql -U kasirku_user -c "DROP DATABASE IF EXISTS kasirku_restore_test;"
   docker exec -it kasirku_db psql -U kasirku_user -c "CREATE DATABASE kasirku_restore_test;"
   ```

2. **Unduh Dump Terbaru dari R2 & Dekripsi**:
   ```bash
   aws s3 cp "${BUCKET_R2}/kasirku_backup_terbaru.dump.gpg" ./ --endpoint-url ...
   gpg --batch --passphrase "${PASSPHRASE_BACKUP}" -d kasirku_backup_terbaru.dump.gpg > kasirku_restore.dump
   ```

3. **Jalankan `pg_restore`**:
   ```bash
   docker cp kasirku_restore.dump kasirku_db:/tmp/
   docker exec -it kasirku_db pg_restore -U kasirku_user -d kasirku_restore_test /tmp/kasirku_restore.dump
   ```

4. **Verifikasi Integritas Data & Invarian Stok**:
   Jalankan query SQL berikut di database hasil restore:
   ```sql
   -- Verifikasi 1: Pastikan transaksi penjualan ada
   SELECT count(*) AS total_transaksi FROM sales;

   -- Verifikasi 2: Cek Invarian Stok (Stok = Jumlah Pergerakan Stok)
   SELECT 
       p.id, 
       p.sku, 
       p.stock AS stok_di_tabel_produk,
       COALESCE(SUM(sm.qty_delta), 0) AS total_delta_pergerakan,
       (p.stock - COALESCE(SUM(sm.qty_delta), 0)) AS selisih
   FROM products p
   LEFT JOIN stock_movements sm ON p.id = sm.product_id
   GROUP BY p.id, p.sku, p.stock
   HAVING p.stock != COALESCE(SUM(sm.qty_delta), 0);
   ```
   *Jika query di atas menghasilkan 0 baris, maka invarian stok 100% konsisten.*

5. **Catat Waktu & Durasi Restore**:
   Pastikan total durasi dari unduh hingga verifikasi tidak melebihi **2 jam (RTO tercapai)**.
