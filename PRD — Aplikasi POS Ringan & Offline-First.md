# PRD — Aplikasi POS Ringan & Offline-First

**Versi:** 0.1 (Draft) · **Tanggal:** 15 Oktober 2026 · **Status:** untuk review manual alur kerja

**Label:** \[FAKTA\] = spesifikasi atau hasil verifikasi · \[ASUMSI\] = perlu dikonfirmasi klien · \[TARGET\] = angka yang wajib diukur sebelum dianggap tercapai.

## TL;DR

POS berbasis web (PWA) untuk toko kecil dengan biaya infrastruktur Rp0: kasir tetap bisa berjualan saat internet putus, data tersinkron otomatis saat online kembali, dan update dari klien dirilis lewat satu pipeline Docker. Stack: **Vue 3 PWA + FastAPI + PostgreSQL + Caddy + Docker Compose**. Prinsip utama: transaksi **tidak boleh hilang dan tidak boleh tercatat ganda** (idempotency + outbox), stok diubah secara atomik, uang disimpan sebagai integer rupiah.

## 1. Latar Belakang & Tujuan

**Masalah:** klien membutuhkan program kasir dengan modal nol, ringan di perangkat murah, mudah diubah saat ada permintaan baru, dan tidak melambat ketika banyak kasir memakainya.

**Tujuan (Goals)**

- G1. Kasir menyelesaikan transaksi tanpa bergantung pada koneksi internet.
- G2. Tidak ada transaksi hilang atau ganda, walau jaringan putus di tengah pengiriman.
- G3. Stok akurat meski beberapa kasir menjual produk yang sama bersamaan.
- G4. Biaya infrastruktur Rp0 untuk MVP, dengan jalur upgrade yang jelas.
- G5. Update dirilis dan bisa di-rollback dengan prosedur baku (F-14).

**Bukan tujuan (MVP):** integrasi payment gateway, multi-cabang, akuntansi lengkap, e-commerce, loyalitas/member, cetak ESC/POS langsung, aplikasi native.

## 2. Asumsi

| ID  | Asumsi                                                                                | Dampak bila salah                                                |
| --- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| A1  | \[ASUMSI\] 1 tenant = 1 toko. Kolom tenant_id tetap ada di semua tabel                | Multi-cabang butuh stok per toko                                 |
| A2  | \[ASUMSI\] 1–5 kasir aktif bersamaan per toko                                         | Mengubah target performa dan pilihan DB                          |
| A3  | \[ASUMSI\] Pembayaran: Tunai, QRIS manual, Transfer manual (kasir konfirmasi sendiri) | Gateway = fitur baru                                             |
| A4  | \[ASUMSI\] Pajak berupa persentase yang bisa diatur (inklusif/eksklusif), default 0   | Perhitungan total berubah                                        |
| A5  | \[ASUMSI\] Stok boleh minus (barang fisik sudah terjual) dan transaksi diberi flag    | Kebijakan blokir stok = Fase 2                                   |
| A6  | \[ASUMSI\] Struk dicetak via dialog cetak browser (58/80 mm)                          | Printer langsung butuh pengembangan tambahan                     |
| A7  | \[ASUMSI\] Barcode scanner USB yang bekerja seperti keyboard                          | Scanner Bluetooth/kamera = pengujian tambahan                    |
| A8  | \[ASUMSI\] Mata uang IDR tanpa desimal                                                | Desimal mengubah tipe data                                       |
| A9  | \[ASUMSI\] Internet toko kadang putus                                                 | Jika selalu stabil, offline tetap dipertahankan sebagai pengaman |

## 3. Pengguna & Hak Akses

RBAC ditegakkan di **server** (UI hanya menyembunyikan menu).

| Kemampuan                | Kasir | Manajer | Owner |
| ------------------------ | ----- | ------- | ----- |
| Buka/tutup shift sendiri | Ya    | Ya      | Ya    |
| Transaksi penjualan      | Ya    | Ya      | Ya    |
| Diskon ≤ batas kasir     | Ya    | Ya      | Ya    |
| Diskon > batas kasir     | Tidak | Ya      | Ya    |
| Void / Retur             | Tidak | Ya      | Ya    |
| Kelola produk & stok     | Tidak | Ya      | Ya    |
| Laporan                  | Tidak | Ya      | Ya    |
| Kelola user & pengaturan | Tidak | Tidak   | Ya    |

## 4. Ruang Lingkup

**MVP:** login & RBAC, shift & kas, penjualan (online/offline), sinkronisasi, struk, void, retur, produk (+impor CSV), stok (terima, penyesuaian, opname), laporan dasar, backup/restore, pipeline rilis.

**Fase 2:** multi-cabang, cetak ESC/POS, payment gateway, member/promo, kebijakan blokir stok, pembelian ke supplier.

## 5. Arsitektur

### 5.1 Tech stack

| Komponen          | Pilihan                                            | Alasan                                                    |
| ----------------- | -------------------------------------------------- | --------------------------------------------------------- |
| Frontend          | Vue 3 + Vite + Pinia + vite-plugin-pwa             | Build statis, ringan di server, pengembang sudah familiar |
| Penyimpanan lokal | IndexedDB via Dexie                                | Katalog, keranjang, dan outbox bertahan saat offline      |
| Backend           | FastAPI (async) + SQLAlchemy 2 + asyncpg + Alembic | Cepat dikembangkan, migrasi terkontrol                    |
| Database          | PostgreSQL                                         | Transaksi, row-level locking, constraint kuat             |
| Reverse proxy     | Caddy                                              | HTTPS otomatis, kompresi, konfigurasi minim               |
| Deploy            | Docker Compose + GitHub Actions                    | Update satu perintah, rollback via tag image              |
| Backup            | pg_dump → Cloudflare R2                            | Ruang gratis untuk backup (verifikasi kuota terbaru)      |

### 5.2 Topologi

```
Perangkat kasir: Vue 3 PWA + IndexedDB (katalog, keranjang, outbox)
      │ HTTPS, satu origin
Caddy ─ /       → file statis PWA
      └ /api/*  → FastAPI → PostgreSQL → pg_dump harian → R2
```

Satu origin (PWA dan API di Caddy yang sama) menghilangkan konfigurasi CORS dan mengurangi satu hop.

### 5.3 Opsi hosting (pilih saat setup)

- **A. VPS gratis** (mis. Oracle Always Free): publik, HTTPS otomatis jika punya domain/hostname. Risiko: kuota free tier bisa berubah (Oracle memangkas A1 menjadi 2 OCPU/12 GB pada 2026), kapasitas sering habis, tanpa support.
- **B. Server di toko** (PC/mini PC Linux): latensi LAN, tetap hidup saat internet putus. Tantangan: HTTPS dan update jarak jauh.

**\[FAKTA\]** Service worker (dasar PWA offline) hanya jalan di _secure context_ (HTTPS atau localhost). Maka `http://IP-LAN` **tidak** bisa dipakai untuk PWA offline. Solusi HTTPS untuk opsi B harus divalidasi dulu (lihat R3 dan Q6). Batas free tier selalu **diverifikasi ulang** sebelum deploy.

### 5.4 Prinsip offline-first

- **Bisa offline:** login dengan sesi yang masih valid, pencarian produk, penjualan, buka shift, tutup shift, cetak struk.
- **Hanya online:** void, retur, kelola produk, stok, laporan, kelola user. Alasan: mengurangi konflik data, karena operasi ini mengubah data yang dibagi antar perangkat.
- Semua perubahan dari kasir dikirim lewat **outbox** (antrean lokal berurutan) dan diproses server secara **idempotent**.

## 6. Model Data

Aturan umum: uang = `BIGINT` rupiah (tanpa float); waktu = `timestamptz` UTC, tampil WIB; semua tabel punya `tenant_id`; ID = UUID (disarankan v7); data master memakai soft delete.

| Tabel                  | Field kunci                                                                                                                                                         | Constraint / Index                                                                                                |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| tenants                | id, name, settings (jsonb)                                                                                                                                          | settings: pajak, pembulatan, max_discount_pct_cashier, cash_diff_threshold, blind_close, paper_width, device_code |
| users                  | id, tenant_id, username, password_hash, role, is_active                                                                                                             | UNIQUE (tenant_id, username)                                                                                      |
| products               | id, tenant_id, sku, barcode, name, price, cost_price, stock, min_stock, is_active, is_deleted, updated_at                                                           | UNIQUE (tenant_id, sku); UNIQUE parsial (tenant_id, barcode); index (tenant_id, updated_at)                       |
| price_history          | product_id, old_price, new_price, changed_by, changed_at                                                                                                            | index product_id                                                                                                  |
| shifts                 | id (UUID klien), tenant_id, cashier_id, opened_at, closed_at, opening_cash, expected_cash, counted_cash, difference, status, has_unresolved_sales                   | status open/closed; UNIQUE parsial 1 shift open per kasir                                                         |
| sales                  | id (UUID klien), tenant_id, shift_id, cashier_id, receipt_no, status, subtotal, discount, tax, total, sold_at (waktu klien), synced_at, payload_hash, flags (jsonb) | UNIQUE (tenant_id, receipt_no); index (tenant_id, sold_at); index shift_id                                        |
| sale_items             | id, sale_id, product_id, name_snapshot, price_snapshot, qty, discount_alloc, line_total                                                                             | index sale_id                                                                                                     |
| payments               | id, sale_id, method, amount, received, change                                                                                                                       | index sale_id                                                                                                     |
| returns / return_items | id (UUID klien), sale_id, shift_id, reason, refund_method, refund_amount / item, qty, restock                                                                       | qty kumulatif retur ≤ qty terjual                                                                                 |
| stock_movements        | id, tenant_id, product_id, qty_delta, type, ref_id, reason, created_by, created_at                                                                                  | type: initial/sale/void/return/receive/adjust/opname; index (product_id, created_at)                              |
| audit_logs             | id, tenant_id, actor_id, action, entity, entity_id, detail, created_at                                                                                              | append-only (role DB aplikasi tanpa UPDATE/DELETE)                                                                |

**Invarian:** `products.stock` = Σ `stock_movements.qty_delta` per produk. Dicek oleh job harian; selisih dicatat ke log.

**Flag transaksi (sales.flags):** `negative_stock`, `price_mismatch` (harga klien ≠ harga server saat sync), `total_mismatch` (total klien ≠ hitung ulang server), `clock_skew` (|sold_at − waktu server saat sync| > 10 menit \[ASUMSI\]).

## 7. Alur Detail (Workflow)

Format tiap alur: **Aktor · Prasyarat · Alur utama (bernomor) · Alternatif/Error · Pasca-kondisi**. Gunakan saat review manual: tiap langkah harus bisa diperagakan dan hasilnya terlihat di UI atau database.

### F-01 Login & Sesi

**Aktor:** semua peran · **Prasyarat:** akun aktif.

1. Pengguna membuka PWA. Jika sesi masih valid, langsung ke beranda sesuai peran.
2. Input username + password → `POST /api/v1/auth/login`.
3. Server cek rate limit (maks 5 gagal/menit per username+IP \[ASUMSI\]), verifikasi hash argon2id.
4. Server mengembalikan access token (JWT, 15 menit) di body, dan refresh token (rotating, disimpan ter-hash di DB, berlaku 12 jam \[ASUMSI\]) sebagai cookie httpOnly + Secure + SameSite=Strict. Alasan cookie: refresh token tidak bisa dibaca JavaScript, sehingga lebih tahan XSS.
5. Klien memicu sinkron katalog (F-03) lalu menampilkan beranda.

**Alternatif/Error**

- a. Kredensial salah → 401 pesan generik (tidak membocorkan username mana yang salah) + audit log.
- b. Akun nonaktif → 403.
- c. Offline dan sesi lokal masih berlaku → tetap bisa masuk dan berjualan sampai masa refresh habis.
- d. Offline dan sesi habis → tidak bisa login; data outbox tetap aman di IndexedDB.
- e. Refresh token ditolak saat online → logout paksa; outbox **tidak dihapus** dan disinkronkan setelah login berikutnya.

**Pasca:** audit log login berhasil/gagal.

### F-02 Buka Shift

**Aktor:** Kasir · **Prasyarat:** login; belum ada shift terbuka milik kasir ini.

1. Layar POS terkunci; tombol **Buka Shift** tampil.
2. Kasir mengisi kas awal (bilangan bulat ≥ 0).
3. Klien membuat `shift_id` (UUID), menyimpan shift lokal berstatus `open`, dan menambahkan event `shift_open` ke outbox (atomik dalam satu transaksi IndexedDB).
4. Jika online, outbox dikirim segera (F-05): `POST /shifts/open`, idempotent berdasarkan `shift_id`.
5. Layar POS terbuka.

**Alternatif/Error**

- a. Server sudah punya shift `open` milik kasir yang sama (perangkat lain) → 409 `SHIFT_ALREADY_OPEN`; klien menawarkan melanjutkan shift tersebut. \[ASUMSI: 1 kasir = 1 shift terbuka\]
- b. Kas awal negatif/bukan angka → ditolak di form.

**Pasca:** baris `shifts` status `open` dengan `opening_cash`.

### F-03 Sinkronisasi Katalog

**Aktor:** sistem · **Prasyarat:** token valid atau cache lokal tersedia.

1. Pemicu: setelah login, tiap 5 menit saat online \[ASUMSI\], saat koneksi kembali, dan tombol manual.
2. Klien memanggil `GET /sync/products?since=<last_sync_at − 60 detik>&limit=500` (sinkron pertama tanpa `since`).
3. Server mengembalikan produk berubah (termasuk yang nonaktif/terhapus) urut `updated_at, id`, plus `next_cursor` dan `server_time`.
4. Klien meng-upsert ke Dexie berdasarkan `id`, menyembunyikan produk terhapus/nonaktif, mengulang sampai tidak ada `next_cursor`, lalu menyimpan `last_sync_at = server_time`.
5. Indeks lokal pada barcode, SKU, dan nama dipakai untuk pencarian.

**Alasan tumpang-tindih 60 detik:** transaksi yang commit terlambat bisa punya `updated_at` lebih lama dari cursor. Karena upsert idempotent, data yang terambil dua kali tidak merusak apa pun.

**Alternatif/Error**

- a. Jaringan gagal → pakai cache lama; badge menampilkan waktu sinkron terakhir.
- b. Cache kosong dan offline (pertama kali dipakai) → POS tidak bisa dipakai; tampilkan pesan jelas.

**Catatan:** stok di klien hanya indikatif. Server adalah sumber kebenaran stok.

### F-04 Penjualan (UI sama untuk online dan offline)

**Aktor:** Kasir · **Prasyarat:** shift terbuka; katalog lokal ada.

1. Kasir di layar POS; fokus otomatis ke kolom cari/scan.
2. Tambah item: scan barcode (scanner mengetik kode + Enter) atau cari nama/SKU lalu pilih. Barcode tak dikenal → pesan «Produk tidak ditemukan», keranjang tidak berubah.
3. Item masuk keranjang, qty awal 1; scan produk sama → qty +1. Qty bisa diubah (bilangan bulat ≥ 1) atau baris dihapus.
4. Saat item pertama masuk, klien membuat `sale_id` (UUID) dan `receipt_no` lokal berformat `<device_code>-<yyyymmdd>-<urut>`; urutan berasal dari counter IndexedDB yang naik atomik. Alasan: nomor struk harus unik walau offline.
5. Opsional: diskon transaksi (nominal atau %), dibatasi `max_discount_pct_cashier`; lebih dari batas ditolak di form.
6. Hitung: subtotal = Σ(harga × qty); dikurangi diskon; pajak sesuai pengaturan; pembulatan sesuai pengaturan; hasilnya total.
7. Kasir menekan **Bayar** (F9) dan memilih metode: **Tunai** (input uang diterima; kembalian = diterima − total; tombol nominal cepat) atau **QRIS manual / Transfer** (kasir menekan «Pembayaran diterima» setelah mengecek notifikasi sendiri).
8. Validasi klien: keranjang tidak kosong; tunai diterima ≥ total.
9. Klien membekukan transaksi: menyimpan `sales` lokal berstatus `pending_sync` **dan** event `sale` ke outbox dalam satu transaksi IndexedDB; keranjang dikosongkan.
10. Layar sukses menampilkan kembalian, tombol **Cetak Struk** (F-06) dan **Transaksi Baru**.
11. Jika online, outbox dikirim di latar belakang (F-05) tanpa menghalangi kasir.

**Alternatif/Error**

- a. Stok lokal 0 atau kurang → peringatan saja; transaksi tidak diblokir (A5).
- b. Tab ditutup/refresh di tengah transaksi → draf keranjang dipulihkan dari IndexedDB.
- c. Batal sebelum bayar → keranjang dikosongkan; tidak ada data terkirim.
- d. Salah input setelah bayar → Void (F-07) atau Retur (F-08) oleh Manajer.

**Pasca lokal:** sale `pending_sync` + 1 event outbox `pending`.

### F-05 Outbox & Sinkronisasi Transaksi (alur paling kritis)

**Aktor:** sistem (klien + server) · **Prasyarat:** ada event `pending`; token valid.

1. Pemicu: event baru masuk outbox, koneksi kembali, interval 30 detik, atau tombol **Sinkron sekarang**.
2. Klien mengambil event `pending` berurutan (FIFO) dan mengirim satu per satu (batching = Fase 2). Untuk event `sale`: `POST /sales` dengan header `Idempotency-Key = sale_id`; status event menjadi `sending`.
3. Server memproses `POST /sales`:
   - a. Autentikasi; pengirim harus kasir yang sama dengan `cashier_id`, atau berperan ≥ Manajer.
   - b. Validasi struktur (item ≥ 1, qty > 0, `product_id` dan `shift_id` ada). Gagal → 422 (lihat langkah 6).
   - c. `BEGIN`; `INSERT INTO sales ... ON CONFLICT (id) DO NOTHING RETURNING id`.
   - d. Jika tidak ada baris dikembalikan (sudah pernah diproses): bandingkan `payload_hash`. Sama → balas 200 dengan sale yang ada (idempotent). Beda → 409 `IDEMPOTENCY_CONFLICT`. Lalu `COMMIT` dan berhenti.
   - e. `INSERT` sale_items dan payments.
   - f. Untuk tiap item **urut `product_id` naik** (mencegah deadlock antar transaksi): `UPDATE products SET stock = stock - :qty WHERE id = :id AND tenant_id = :t`. Jika stok menjadi < 0 → set flag `negative_stock`.
   - g. `INSERT stock_movements` (type=sale, qty_delta=−qty, ref_id=sale_id) per item.
   - h. Hitung ulang total dan bandingkan dengan klien: beda → flag `total_mismatch`. Bandingkan harga dengan harga server saat ini: beda → flag `price_mismatch`. Cek selisih jam → flag `clock_skew`.
   - i. Set status `completed`, `synced_at = now()`; `COMMIT`.
4. Server membalas 201 `{sale_id, status, flags}`.
5. Klien menandai event `done` dan sale lokal `synced`.
6. Penanganan error klien:
   - Timeout/jaringan/5xx → event kembali `pending`; retry dengan exponential backoff (5 dtk, 15 dtk, 60 dtk, maks 5 menit). Jika server sebenarnya sudah commit, retry jatuh ke langkah 3d dan aman.
   - 401 → coba refresh token; gagal → hentikan sync, minta login; outbox tetap utuh.
   - 422 → event menjadi `failed`; muncul di daftar **Perlu Tindakan** untuk Manajer; event lain tetap berjalan.
7. Event `shift_close` ditahan sampai semua `sale` pada shift itu berstatus `done` atau `failed`.

**Alasan desain:** transaksi yang sudah terjadi di meja kasir adalah fakta fisik. Server **tidak menolaknya** karena stok minus atau harga berbeda; server mencatat dan memberi flag agar Manajer meninjau. Hanya data yang rusak secara struktur yang ditolak.

**Pasca:** sales, sale_items, payments, stock_movements tertulis atomik dalam satu transaksi database; flag terisi bila ada anomali.

### F-06 Cetak Struk

**Aktor:** Kasir/Manajer · **Prasyarat:** transaksi ada di IndexedDB (online maupun offline).

1. Kasir menekan **Cetak Struk** di layar sukses atau di Riwayat Transaksi.
2. Klien merender template struk dari data lokal: nama toko, alamat, `receipt_no`, waktu, kasir, daftar item, subtotal, diskon, pajak, total, bayar, kembalian, footer.
3. Klien memanggil dialog cetak browser dengan CSS `@page` selebar 58 atau 80 mm (pengaturan `paper_width`).
4. Cetak ulang diberi label **SALINAN** dan dicatat di audit log (ditunda sampai online bila offline).

**Alternatif/Error**

- a. Printer tidak tersedia → tampilkan struk di layar atau simpan sebagai PDF.
- b. Cetak langsung ke printer thermal (ESC/POS via USB/Bluetooth) **bukan MVP**; dukungan browser bervariasi dan harus divalidasi sebelum dijanjikan ke klien (R4).

**Pasca:** tidak ada perubahan data transaksi.

### F-07 Void Transaksi (online saja)

**Aktor:** Manajer/Owner · **Prasyarat:** online; sale berstatus `completed`; shift sale tersebut **masih terbuka**; belum ada retur pada sale itu.

1. Manajer membuka Riwayat Transaksi, mencari `receipt_no`, membuka Detail.
2. Menekan **Void** dan mengisi alasan (minimal 5 karakter \[ASUMSI\]).
3. Klien memanggil `POST /sales/{id}/void` `{reason}`.
4. Server: `BEGIN`; kunci baris sale (`SELECT ... FOR UPDATE`); validasi status dan shift; `UPDATE` status menjadi `voided` beserta `voided_by`, `voided_at`, `void_reason`; untuk tiap item (urut `product_id`) kembalikan stok; `INSERT stock_movements` (type=void, qty_delta=+qty); `INSERT audit_logs`; `COMMIT`.
5. UI menampilkan status **VOID**; transaksi tidak dihitung pada omzet maupun kas shift.

**Alasan batasan shift terbuka:** shift yang sudah ditutup bersifat final agar rekonsiliasi kas tidak berubah diam-diam. Koreksi setelah tutup shift dilakukan lewat Retur.

**Alternatif/Error**

- a. Shift sudah ditutup → 409 `SHIFT_CLOSED`; gunakan Retur (F-08).
- b. Sale sudah `voided` → 409 `ALREADY_VOIDED` (UI cukup menampilkan status saat ini).
- c. Kasir mencoba mengakses → 403.
- d. Offline → tombol Void dinonaktifkan dengan penjelasan.

**Pasca:** sale `voided`, stok kembali, movement dan audit log tercatat.

### F-08 Retur (online saja)

**Aktor:** Manajer/Owner · **Prasyarat:** online; sale `completed` atau `partially_refunded`.

1. Manajer membuka Detail transaksi asal → **Retur**.
2. Memilih item dan qty (≤ qty terjual − qty yang sudah diretur), memilih `restock` ya/tidak per item (tidak = barang rusak), mengisi alasan, memilih metode refund. Untuk refund tunai, memilih shift terbuka yang kasnya dipakai.
3. Klien memanggil `POST /returns` dengan `id` UUID buatan klien (idempotent).
4. Server: kunci sale; validasi kuota retur; hitung `refund = (line_total ÷ qty_terjual) × qty_retur`, pembulatan ke rupiah (selisih pembulatan masuk item terakhir); `INSERT returns` dan `return_items`; jika `restock` → tambah stok + movement (type=return); perbarui status sale menjadi `partially_refunded` atau `refunded`; `INSERT audit_logs`; `COMMIT`.
5. UI menampilkan nilai refund yang harus diserahkan.

**Alternatif/Error**

- a. Qty melebihi kuota → 422 `RETURN_QTY_EXCEEDED`.
- b. Sale `voided` → 409.
- c. Refund tunai tanpa shift terbuka → 422 `NO_OPEN_SHIFT`.
- d. Request terkirim dua kali (timeout) → `id` sama → respons hasil sebelumnya, tidak ada retur ganda.

**Pasca:** refund tunai mengurangi `expected_cash` pada shift yang dipilih.

### F-09 Tutup Shift

**Aktor:** Kasir · **Prasyarat:** shift terbuka milik kasir.

1. Kasir menekan **Tutup Shift**. Jika online dan masih ada sale `pending`, sistem mengirimnya dulu (F-05). Jika offline, tutup shift tetap boleh; event `shift_close` ditahan sampai sale terkirim.
2. Layar ringkasan: jumlah transaksi, omzet, total per metode bayar, refund tunai, kas awal.
3. Kasir menghitung uang fisik dan mengisi `counted_cash`. Bila `blind_close` aktif, `expected_cash` disembunyikan dari kasir agar hitungan tidak «disesuaikan».
4. `selisih = counted_cash − expected_cash`, dengan `expected_cash = kas awal + Σ pembayaran tunai (sale completed) − Σ refund tunai`. Jika |selisih| > `cash_diff_threshold`, catatan wajib diisi.
5. Event `shift_close` dikirim (idempotent berdasarkan `shift_id`). Server **menghitung ulang** `expected_cash` dari data server (otoritatif), menyimpan `difference`, dan mengubah status menjadi `closed`.
6. Ringkasan shift tampil dan bisa dicetak; kasir logout.

**Alternatif/Error**

- a. Ada sale `failed` pada shift → shift tetap bisa ditutup, ditandai `has_unresolved_sales`, dan muncul di laporan Manajer.
- b. Shift sudah `closed` → respons idempotent.

**Pasca:** shift `closed` dan final; transaksi di dalamnya tidak bisa di-void.

### F-10 Kelola Produk (online saja)

**Aktor:** Manajer/Owner.

**Tambah produk**

1. Menu Produk → **Tambah**; isi nama\*, SKU\*, barcode (opsional), kategori, harga jual\* (bilangan bulat ≥ 0), harga modal, stok awal, stok minimum, status aktif.
2. `POST /products`. Server memvalidasi keunikan (tenant, SKU) dan (tenant, barcode), menyimpan; bila stok awal > 0 menulis movement `initial`; menulis audit log.
3. Produk muncul di perangkat lain pada sinkron katalog berikutnya (F-03).

**Ubah produk:** perubahan harga menulis `price_history`; transaksi lama tidak berubah karena memakai `price_snapshot`.

**Hapus produk:** soft delete (`is_deleted`) agar riwayat transaksi tetap utuh.

**Impor CSV:** unggah → validasi per baris → pratinjau baris bermasalah → konfirmasi → upsert berdasarkan SKU dalam satu transaksi → laporan hasil. Batas 5.000 baris per berkas \[ASUMSI\].

**Alternatif/Error:** SKU/barcode duplikat → 409 dengan nama field; harga negatif atau bukan angka → 422.

### F-11 Kelola Stok (online saja)

**Aktor:** Manajer/Owner. Setiap operasi mengubah `products.stock` **dan** menulis `stock_movements` dalam satu transaksi database.

1. **Penerimaan barang:** pilih produk, qty > 0, harga modal (opsional), catatan → `POST /stock/receive` → movement `receive`.
2. **Penyesuaian:** delta (+/−) dengan alasan wajib (rusak, hilang, koreksi) → movement `adjust`.
3. **Opname:** input stok fisik per produk → sistem menampilkan pratinjau selisih → konfirmasi → server mengunci baris produk dan menulis movement `opname` dengan delta = fisik − stok sistem saat commit.

**Peringatan opname:** kasir offline yang belum sinkron akan menggeser stok setelah opname. Lakukan opname di luar jam operasional atau setelah semua perangkat tersinkron (UI menampilkan peringatan ini).

### F-12 Laporan (online saja)

**Aktor:** Manajer/Owner.

1. Pilih laporan dan filter (rentang tanggal zona WIB, shift, kasir).
2. Server menjalankan query berindeks `(tenant_id, sold_at)` dengan paginasi; rentang maksimum 92 hari per permintaan \[ASUMSI\].
3. Tampil di layar; tombol **Export CSV**.

**Daftar laporan MVP:** ringkasan harian; penjualan per produk; per metode bayar; per kasir; stok menipis (`stock` ≤ `min_stock`); transaksi berflag (`negative_stock`, `price_mismatch`, `total_mismatch`, `clock_skew`) beserta transaksi `failed`; rekap shift dan selisih kas.

**Definisi:** omzet bersih = Σ total sale (`completed` dan `partially_refunded`) − Σ refund. Sale `voided` tidak dihitung.

### F-13 Backup & Restore

**Backup harian (otomatis)**

1. Cron menjalankan `pg_dump -Fc`.
2. Berkas dienkripsi sebelum diunggah.
3. Unggah ke R2; retensi 7 harian + 4 mingguan \[ASUMSI\].
4. Hasil (sukses/gagal, ukuran) ditulis ke log; kegagalan memicu notifikasi sederhana (mis. webhook).

**Latihan restore (bulanan, wajib)**

1. Siapkan database kosong.
2. Unduh dump terbaru dan dekripsi.
3. `pg_restore` ke database kosong.
4. Jalankan aplikasi ke database tersebut.
5. Verifikasi: jumlah `sales` wajar, dan invarian stok (stok = Σ movement) terpenuhi.
6. Catat hasil dan durasi.

**Target:** RPO ≤ 24 jam, RTO ≤ 2 jam \[TARGET — buktikan lewat latihan restore\]. Backup yang belum pernah dites restore belum dianggap backup.

### F-14 Rilis & Update dari Klien

1. Klien mengirim permintaan → dicatat sebagai issue (label: bug/fitur) → masuk backlog.
2. Pengembang merge ke `main` → GitHub Actions menjalankan lint + test → build image → push ke registry dengan tag `vX.Y.Z` (verifikasi kuota registry yang dipakai).
3. **Pra-deploy:** backup database.
4. Server menarik image baru → `alembic upgrade head` → restart API → cek `/health` dan `/ready`.
5. Jika health check gagal → kembali ke tag sebelumnya. Migrasi **tidak** di-downgrade otomatis; karena itu migrasi harus backward-compatible (pola expand → contract).
6. PWA mendeteksi versi baru lewat service worker → banner **Update tersedia** → aktif setelah transaksi berjalan selesai atau saat refresh.
7. API diberi versi `/api/v1`; klien lama tetap harus didukung minimal satu rilis, karena kasir offline mungkin masih memakai versi lama.

## 8. State Machine

**Status transaksi (sales.status)**

| Dari               | Ke                 | Pemicu                    | Syarat                                         |
| ------------------ | ------------------ | ------------------------- | ---------------------------------------------- |
| (lokal) draft      | pending_sync       | Bayar dikonfirmasi (F-04) | Keranjang valid                                |
| pending_sync       | completed          | Server 201/200 (F-05)     | —                                              |
| pending_sync       | failed             | Server 422 (F-05)         | Struktur data rusak; butuh tindakan Manajer    |
| completed          | voided             | F-07                      | Shift terbuka, belum ada retur, peran Manajer+ |
| completed          | partially_refunded | F-08                      | Sebagian qty diretur                           |
| partially_refunded | refunded           | F-08                      | Seluruh qty sudah diretur                      |
| completed          | refunded           | F-08                      | Seluruh qty diretur sekaligus                  |

**Shift:** `open` → `closed` (F-09). Tidak bisa dibuka kembali.

**Event outbox:** `pending` → `sending` → `done`; `sending` → `pending` (jaringan/5xx); `sending` → `failed` (422).

**Penanganan event `failed`:** Manajer membuka daftar **Perlu Tindakan**, melihat penyebab, lalu memilih **Kirim ulang** (setelah masalah diperbaiki, mis. produk dipulihkan) atau **Buang** dengan alasan wajib (tercatat di audit log). Tidak ada event yang dihapus diam-diam.

## 9. Kontrak API Ringkas

Prefix `/api/v1`. Format error seragam: `{code, message, details}`.

| Endpoint                                          | Peran                      | Idempotent                         | Catatan                           |
| ------------------------------------------------- | -------------------------- | ---------------------------------- | --------------------------------- |
| POST /auth/login                                  | Publik                     | —                                  | Rate limit                        |
| POST /auth/refresh, /auth/logout                  | Cookie                     | —                                  | Refresh token berputar (rotating) |
| GET /sync/products                                | Semua                      | —                                  | `since`, `limit`, `cursor`        |
| POST /shifts/open                                 | Kasir                      | Ya (`shift_id`)                    | 409 `SHIFT_ALREADY_OPEN`          |
| POST /shifts/{id}/close                           | Kasir                      | Ya (`shift_id`)                    | Server menghitung ulang kas       |
| POST /sales                                       | Kasir+                     | Ya (`Idempotency-Key` = `sale_id`) | F-05                              |
| GET /sales, /sales/{id}                           | Manajer+ (Kasir: miliknya) | —                                  | Filter tanggal, `receipt_no`      |
| POST /sales/{id}/void                             | Manajer+                   | Berbasis status                    | F-07                              |
| POST /returns                                     | Manajer+                   | Ya (`id`)                          | F-08                              |
| CRUD /products, POST /products/import             | Manajer+                   | —                                  | F-10                              |
| POST /stock/receive, /stock/adjust, /stock/opname | Manajer+                   | —                                  | F-11                              |
| GET /reports/\*                                   | Manajer+                   | —                                  | F-12                              |
| /users, /settings                                 | Owner                      | —                                  | Audit log tiap perubahan          |
| GET /health, /ready                               | Internal                   | —                                  | Dipakai pipeline rilis            |

**Kode error utama:** `VALIDATION_ERROR` (422), `UNAUTHORIZED` (401), `FORBIDDEN` (403), `SHIFT_ALREADY_OPEN`, `SHIFT_CLOSED`, `ALREADY_VOIDED`, `IDEMPOTENCY_CONFLICT`, `DUPLICATE_SKU`, `DUPLICATE_BARCODE` (409), `RETURN_QTY_EXCEEDED`, `NO_OPEN_SHIFT` (422).

## 10. Persyaratan Non-Fungsional

- **Performa \[TARGET\]:** p95 `POST /sales` < 300 ms pada 20 permintaan bersamaan di hardware target (uji dengan k6); pencarian produk lokal < 100 ms untuk 10.000 produk.
- **Memori \[TARGET\]:** seluruh stack (API + DB + proxy) idle ≤ 1 GB; ukur dengan `docker stats`. Gunakan 1–2 worker uvicorn dan pool koneksi kecil.
- **Ketersediaan:** penjualan tetap berjalan saat server atau internet mati (konsekuensi desain offline-first).
- **Keamanan:** argon2id; secret dari environment; refresh cookie httpOnly; RBAC di server; rate limit login; DB tidak terekspos publik (jaringan internal Docker); backup terenkripsi; audit log append-only; TLS wajib.
- **Integritas data:** uang `BIGINT`; waktu UTC; invarian stok; semua operasi multi-tabel dalam satu transaksi DB; semua operasi tulis dari klien idempotent.
- **Observability:** `/health`, `/ready`; log JSON; metrik minimal: jumlah event `failed`, umur event `pending` tertua per perangkat (tampil di UI), kegagalan backup.
- **UX:** Bahasa Indonesia; layar ≥ 360 px; pintasan keyboard (F2 cari, F9 bayar, Esc batal); indikator online/offline dan jumlah transaksi pending selalu terlihat.

## 11. Skenario UAT Manual

Gunakan tabel ini untuk memverifikasi alur. Kolom terakhir menunjuk alur yang diuji.

| ID  | Skenario            | Langkah singkat                                               | Hasil diharapkan                                                                    | Alur       |
| --- | ------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ---------- |
| U01 | Login               | Login benar; lalu salah 6 kali berturut-turut                 | Benar → beranda. Salah → 401 generik; percobaan ke-6 kena rate limit; audit log ada | F-01       |
| U02 | Buka shift          | Online, kas awal 100000; ulangi dengan nilai negatif          | Shift `open`, POS terbuka; nilai negatif ditolak                                    | F-02       |
| U03 | Jual tunai online   | Scan 2 produk, bayar tunai                                    | Sale `completed`; stok turun sesuai qty; movement `sale`; kembalian benar           | F-04, F-05 |
| U04 | Jual QRIS manual    | Pilih QRIS, konfirmasi diterima                               | Payment method QRIS; tidak ada kembalian                                            | F-04       |
| U05 | Offline lalu sync   | Putus jaringan, 3 transaksi, sambungkan kembali               | 3 sale `completed` tanpa duplikat; `receipt_no` unik; stok turun sesuai total       | F-05       |
| U06 | Retry idempotent    | Putus koneksi tepat saat `POST /sales`, kirim ulang           | Tepat 1 sale; stok turun 1×; respons kedua 200                                      | F-05       |
| U07 | Dua kasir bersamaan | 2 perangkat jual produk yang sama (stok 10) qty 3 dan 4       | Stok akhir 3; tidak ada lost update                                                 | F-05       |
| U08 | Stok minus          | Jual qty melebihi stok                                        | Transaksi tetap sukses; flag `negative_stock`; tampil di laporan flag               | F-05, F-12 |
| U09 | Outbox bertahan     | Offline, buat transaksi, tutup browser, buka lagi             | Transaksi masih `pending`; terkirim setelah online                                  | F-05       |
| U10 | Void                | Manajer void saat shift terbuka                               | Status `voided`; stok kembali; kas shift berkurang; audit log ada                   | F-07       |
| U11 | Void ditolak        | Void setelah shift ditutup                                    | 409 `SHIFT_CLOSED`                                                                  | F-07       |
| U12 | Retur parsial       | Retur 1 dari 3 qty dengan restock; lalu coba retur 3 qty lagi | Refund = line_total ÷ 3; stok +1; status `partially_refunded`; percobaan kedua 422  | F-08       |
| U13 | Tutup shift         | Isi uang fisik berbeda dari ekspektasi                        | `difference` = fisik − ekspektasi; catatan wajib bila melewati batas                | F-09       |
| U14 | Hak akses           | Kasir memanggil endpoint laporan/void langsung                | 403 (bukan sekadar menu disembunyikan)                                              | §3         |
| U15 | Sinkron katalog     | Manajer ubah harga; kasir online                              | Harga baru muncul ≤ interval sinkron; transaksi lama tetap harga lama               | F-03, F-10 |
| U16 | Clock skew          | Majukan jam perangkat 1 jam, jual, sinkron                    | Sale tersimpan; flag `clock_skew`                                                   | F-05       |
| U17 | Backup & restore    | Jalankan latihan restore                                      | Restore sukses; invarian stok terpenuhi                                             | F-13       |
| U18 | Rilis & rollback    | Deploy versi dengan health check gagal                        | Kembali ke tag sebelumnya; data utuh                                                | F-14       |

## 12. Milestone

Durasi tidak diestimasi sebelum Q1–Q10 terjawab; estimasi tanpa data kecepatan kerja hanya tebakan.

| Milestone             | Isi                                                                                      | Selesai bila                                                              |
| --------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| M0 Fondasi            | Repo, Docker Compose (caddy, api, db), CI (lint + test + build), migrasi awal, `/health` | `docker compose up` jalan; CI hijau                                       |
| M1 Auth & master data | F-01, F-10, RBAC                                                                         | U01, U14 lulus                                                            |
| M2 Penjualan online   | F-02, F-03, F-04 (online), F-06                                                          | U02–U04, U07, U08 lulus                                                   |
| M3 Offline-first      | Outbox, F-05, flag anomali                                                               | U05, U06, U09, U16 lulus                                                  |
| M4 Kontrol            | F-07, F-08, F-09, F-11                                                                   | U10–U13 lulus                                                             |
| M5 Operasional        | F-12, F-13, F-14, observability                                                          | U15, U17, U18 lulus                                                       |
| M6 UAT & pilot        | UAT penuh di perangkat nyata klien + uji beban k6                                        | Semua U lulus; target NFR terukur; tidak ada bug prioritas tinggi terbuka |

## 13. Risiko

| ID  | Risiko                                                                                      | Mitigasi                                                                                                                                                                                                        |
| --- | ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | Free tier berubah atau dicabut                                                              | Verifikasi sebelum deploy; backup di luar penyedia hosting; siapkan jalur upgrade ke VPS berbayar kecil; hindari lock-in (Docker + Postgres standar)                                                            |
| R2  | Oracle: kapasitas habis; instance beban rendah bisa dianggap idle (hipotesis, belum teruji) | Siapkan opsi B; uji di akun nyata sebelum janji ke klien                                                                                                                                                        |
| R3  | HTTPS/domain: tanpa secure context PWA offline tidak aktif; domain umumnya berbayar         | Putuskan skema sebelum coding sync: hostname gratis dengan sertifikat valid, tunnel, atau beli domain murah. Validasi syarat tiap opsi. Siapkan DNS lokal agar nama host tetap terselesaikan saat internet mati |
| R4  | Klien mengharapkan cetak thermal langsung                                                   | Janjikan hanya cetak browser di MVP; uji printer klien sedini mungkin                                                                                                                                           |
| R5  | Browser membersihkan IndexedDB (storage eviction) sehingga outbox hilang                    | Panggil `navigator.storage.persist()`; sinkron secepat mungkin; indikator pending selalu terlihat; peringatan bila pending lama                                                                                 |
| R6  | Jam perangkat salah                                                                         | Flag `clock_skew`; laporan menampilkan transaksi berflag                                                                                                                                                        |
| R7  | Stok fisik tidak cocok dengan sistem                                                        | Opname berkala; laporan stok menipis dan flag                                                                                                                                                                   |
| R8  | Satu pengembang (bus factor)                                                                | README, runbook F-13/F-14, CI, test untuk inti bisnis                                                                                                                                                           |
| R9  | Pajak/regulasi lokal                                                                        | Konfirmasi ke klien atau konsultan pajak; MVP bukan pembukuan resmi                                                                                                                                             |

## 14. Pertanyaan Terbuka

- Q1. Berapa toko dan berapa kasir aktif bersamaan? bebas, karena ini akan diakses oleh banyak orang
- Q2. Perangkat kasir apa (PC/tablet/HP) dan browser apa? PC dan Chrome
- Q3. Pajak: persentase, inklusif atau eksklusif? Ada pembulatan? ya
- Q4. Ada metode pembayaran lain selain tunai, QRIS manual, transfer? ya
- Q5. Printer dan scanner apa yang dipakai (model, koneksi)? tambahkan dulu dummy, jika klien meminta hardware teresbut, gampang dikonfigurasikan
- Q6. Hosting dan domain: VPS gratis, server di toko, atau hostname gratis? (R3) pakai Vercel untuk front-end, dan Oracle Free Tier untuk back-end yaa
- Q7. Kebijakan stok minus (A5) dan batas diskon kasir? ya
- Q8. Retur: siapa yang boleh dan berapa lama batas waktunya? ya
- Q9. Berapa lama data harus disimpan, dan adakah kewajiban pelaporan? belum terpikirkan, namun saya tetap ingin ketika data tidak ada, bisa di handle dengan baik oleh program
- Q10. Apakah ada rencana multi-cabang? (menentukan desain stok) ya

## 15. Bahasa

Pastikan semua berbahasa Indonesia didalam programnya agar memudahkan user saat menggunakannya

Untuk nama variabel dan syntax pada program itu juga menggunakan istilah bahasa Indonesia ya agar lebih mudah dimaintenance oleh developer, untuk antisipasi jika developernya berbeda-beda orang
