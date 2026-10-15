import pytest
from httpx import AsyncClient, ASGITransport
import uuid
from datetime import datetime, timezone, timedelta
from app.utama import aplikasi, masa_hidup_aplikasi

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture(autouse=True)
async def persiapkan_aplikasi():
    async with masa_hidup_aplikasi(aplikasi):
        yield

@pytest.mark.asyncio
async def test_health_dan_ready():
    async with AsyncClient(transport=ASGITransport(app=aplikasi), base_url="http://test") as klien:
        res_h = await klien.get("/health")
        assert res_h.status_code == 200
        assert res_h.json()["status"] == "sehat"

        res_r = await klien.get("/ready")
        assert res_r.status_code == 200
        assert res_r.json()["status"] == "siap"

@pytest.mark.asyncio
async def test_alur_penuh_kasirku():
    async with AsyncClient(transport=ASGITransport(app=aplikasi), base_url="http://test") as klien:
        # 1. Login Kasir
        res_kasir = await klien.post("/api/v1/auth/login", json={"nama_pengguna": "kasir", "kata_sandi": "password123"})
        assert res_kasir.status_code == 200
        token_kasir = res_kasir.json()["token_akses"]
        header_kasir = {"Authorization": f"Bearer {token_kasir}"}

        # 2. Login Manajer
        res_mgr = await klien.post("/api/v1/auth/login", json={"nama_pengguna": "manajer", "kata_sandi": "password123"})
        assert res_mgr.status_code == 200
        token_mgr = res_mgr.json()["token_akses"]
        header_mgr = {"Authorization": f"Bearer {token_mgr}"}

        # Tutup shift kasir jika masih ada yang terbuka
        shift_aktif_res = await klien.get("/api/v1/shifts/aktif", headers=header_kasir)
        if shift_aktif_res.status_code == 200 and shift_aktif_res.json():
            id_lama = shift_aktif_res.json()["id"]
            await klien.post(f"/api/v1/shifts/{id_lama}/close", json={"kas_fisik": 100000}, headers=header_kasir)

        # 3. U02: Buka Shift Kasir Baru
        id_shift = str(uuid.uuid4())
        res_shift = await klien.post("/api/v1/shifts/open", json={
            "id": id_shift,
            "kas_awal": 100000
        }, headers=header_kasir)
        assert res_shift.status_code == 200
        assert res_shift.json()["status"] == "open"
        assert res_shift.json()["kas_awal"] == 100000

        # Coba buka shift lagi saat masih open -> harus ditolak (409 SHIFT_ALREADY_OPEN)
        res_shift2 = await klien.post("/api/v1/shifts/open", json={
            "id": str(uuid.uuid4()),
            "kas_awal": 50000
        }, headers=header_kasir)
        assert res_shift2.status_code == 409
        assert res_shift2.json()["detail"]["code"] == "SHIFT_ALREADY_OPEN"

        # 4. Ambil Katalog Produk
        res_sync = await klien.get("/api/v1/sync/products", headers=header_kasir)
        assert res_sync.status_code == 200
        produk_list = res_sync.json()["produk"]
        assert len(produk_list) >= 1
        p_beras = next(p for p in produk_list if p["sku"] == "BRS-001")
        stok_awal_beras = p_beras["stok"]

        # 5. U03: Transaksi Penjualan Tunai Online
        id_sale = str(uuid.uuid4())
        payload_sale = {
            "id": id_sale,
            "id_shift": id_shift,
            "nomor_struk": f"KASIR-01-{id_sale[:8]}",
            "subtotal": 72000,
            "diskon": 0,
            "pajak": 0,
            "pembulatan": 0,
            "total": 72000,
            "waktu_transaksi": datetime.now(timezone.utc).isoformat(),
            "item": [
                {
                    "id_produk": p_beras["id"],
                    "nama_produk_snapshot": p_beras["nama"],
                    "harga_snapshot": p_beras["harga"],
                    "kuantitas": 2,
                    "alokasi_diskon": 0,
                    "subtotal_baris": 72000
                }
            ],
            "pembayaran": [
                {
                    "metode": "tunai",
                    "jumlah": 72000,
                    "diterima": 100000,
                    "kembalian": 28000
                }
            ]
        }

        res_sale = await klien.post("/api/v1/sales", json=payload_sale, headers={
            **header_kasir,
            "Idempotency-Key": id_sale
        })
        assert res_sale.status_code == 201
        data_sale = res_sale.json()
        assert data_sale["status"] == "completed"

        # 6. U06: Retry Idempoten (Kirim ulang payload yang sama persis)
        res_sale_retry = await klien.post("/api/v1/sales", json=payload_sale, headers={
            **header_kasir,
            "Idempotency-Key": id_sale
        })
        assert res_sale_retry.status_code == 200 # Idempotent 200 OK
        assert res_sale_retry.json()["id"] == id_sale

        # 7. Verifikasi Pengurangan Stok Atomik (stok awal - 2)
        res_prod_cek = await klien.get(f"/api/v1/products?cari=BRS-001", headers=header_kasir)
        p_beras_terbaru = res_prod_cek.json()[0]
        assert p_beras_terbaru["stok"] == stok_awal_beras - 2

        # 8. U08: Stok Minus (Jual melebihi stok yang ada -> transaksi tetap sukses dengan flag negative_stock)
        id_sale_minus = str(uuid.uuid4())
        payload_sale_minus = {
            "id": id_sale_minus,
            "id_shift": id_shift,
            "nomor_struk": f"KASIR-01-{id_sale_minus[:8]}",
            "subtotal": 7200000,
            "diskon": 0,
            "pajak": 0,
            "pembulatan": 0,
            "total": 7200000,
            "waktu_transaksi": datetime.now(timezone.utc).isoformat(),
            "item": [
                {
                    "id_produk": p_beras["id"],
                    "nama_produk_snapshot": p_beras["nama"],
                    "harga_snapshot": p_beras["harga"],
                    "kuantitas": 1000,
                    "alokasi_diskon": 0,
                    "subtotal_baris": 7200000
                }
            ],
            "pembayaran": [
                {
                    "metode": "transfer",
                    "jumlah": 7200000,
                    "diterima": 7200000,
                    "kembalian": 0
                }
            ]
        }
        res_sale_minus = await klien.post("/api/v1/sales", json=payload_sale_minus, headers=header_kasir)
        assert res_sale_minus.status_code == 201
        assert res_sale_minus.json()["flag"].get("negative_stock") is True

        # 9. U10: Void Transaksi oleh Manajer saat Shift Terbuka
        res_void = await klien.post(f"/api/v1/sales/{id_sale_minus}/void", json={
            "alasan": "Pelanggan membatalkan pesanan"
        }, headers=header_mgr)
        assert res_void.status_code == 200
        assert res_void.json()["status"] == "voided"

        # 10. U12: Retur Parsial dengan Restock
        id_retur = str(uuid.uuid4())
        res_retur = await klien.post("/api/v1/returns", json={
            "id": id_retur,
            "id_penjualan": id_sale,
            "id_shift": id_shift,
            "alasan": "Salah beli varian",
            "metode_pengembalian": "tunai",
            "item": [
                {
                    "id_produk": p_beras["id"],
                    "kuantitas": 1,
                    "apakah_stok_kembali": True
                }
            ]
        }, headers=header_mgr)
        assert res_retur.status_code == 201
        assert res_retur.json()["total_pengembalian"] == 36000

        # Coba retur melebihi kuota sisa (sisa 1, minta 2) -> harus 422
        res_retur_lebih = await klien.post("/api/v1/returns", json={
            "id": str(uuid.uuid4()),
            "id_penjualan": id_sale,
            "id_shift": id_shift,
            "alasan": "Retur lagi",
            "metode_pengembalian": "tunai",
            "item": [
                {
                    "id_produk": p_beras["id"],
                    "kuantitas": 2,
                    "apakah_stok_kembali": True
                }
            ]
        }, headers=header_mgr)
        assert res_retur_lebih.status_code == 422
        assert res_retur_lebih.json()["detail"]["code"] == "RETURN_QTY_EXCEEDED"

        # 11. U13: Tutup Shift Kasir
        res_tutup = await klien.post(f"/api/v1/shifts/{id_shift}/close", json={
            "kas_fisik": 136000,
            "catatan": "Uang fisik pas"
        }, headers=header_kasir)
        assert res_tutup.status_code == 200
        assert res_tutup.json()["status"] == "closed"

        # 12. U11: Void setelah shift ditutup harus ditolak (409 SHIFT_CLOSED)
        res_void_tutup = await klien.post(f"/api/v1/sales/{id_sale}/void", json={
            "alasan": "Mencoba void setelah shift closed"
        }, headers=header_mgr)
        assert res_void_tutup.status_code == 409
        assert res_void_tutup.json()["detail"]["code"] == "SHIFT_CLOSED"

@pytest.mark.asyncio
async def test_u01_login_dan_rate_limit():
    async with AsyncClient(transport=ASGITransport(app=aplikasi), base_url="http://test") as klien:
        # Login benar
        res_ok = await klien.post("/api/v1/auth/login", json={"nama_pengguna": "owner", "kata_sandi": "password123"})
        assert res_ok.status_code == 200
        assert res_ok.json()["peran"] == "owner"

        # Uji Rate Limit: percobaan salah berturut-turut
        nama_pengguna_uji = f"user_gagal_{uuid.uuid4().hex[:6]}"
        for _ in range(5):
            res_salah = await klien.post("/api/v1/auth/login", json={
                "nama_pengguna": nama_pengguna_uji,
                "kata_sandi": "salah123"
            })
            assert res_salah.status_code == 401
            assert res_salah.json()["detail"]["code"] == "UNAUTHORIZED"

        # Percobaan ke-6 harus kena rate limit 429
        res_limit = await klien.post("/api/v1/auth/login", json={
            "nama_pengguna": nama_pengguna_uji,
            "kata_sandi": "salah123"
        })
        assert res_limit.status_code == 429
        assert res_limit.json()["detail"]["code"] == "TOO_MANY_REQUESTS"

@pytest.mark.asyncio
async def test_u14_hak_akses_rbac():
    async with AsyncClient(transport=ASGITransport(app=aplikasi), base_url="http://test") as klien:
        res_kasir = await klien.post("/api/v1/auth/login", json={"nama_pengguna": "kasir", "kata_sandi": "password123"})
        header_kasir = {"Authorization": f"Bearer {res_kasir.json()['token_akses']}"}

        # Kasir mencoba akses endpoint Laporan -> 403 Forbidden
        res_lap = await klien.get("/api/v1/reports/summary", headers=header_kasir)
        assert res_lap.status_code == 403
        assert res_lap.json()["detail"]["code"] == "FORBIDDEN"

        # Kasir mencoba menambah produk -> 403 Forbidden
        res_prod = await klien.post("/api/v1/products", json={
            "sku": "TEST-RBAC",
            "nama": "Produk Ilegal",
            "harga": 10000
        }, headers=header_kasir)
        assert res_prod.status_code == 403

        # Kasir mencoba mencatat penerimaan stok -> 403 Forbidden
        res_stok = await klien.post("/api/v1/stock/receive", json={
            "id_produk": "dummy",
            "kuantitas": 10
        }, headers=header_kasir)
        assert res_stok.status_code == 403

        # Kasir mencoba melakukan retur -> 403 Forbidden
        res_retur = await klien.post("/api/v1/returns", json={
            "id": str(uuid.uuid4()),
            "id_penjualan": "dummy",
            "id_shift": "dummy",
            "alasan": "Retur",
            "metode_pengembalian": "tunai",
            "item": [{"id_produk": "dummy", "kuantitas": 1, "apakah_stok_kembali": True}]
        }, headers=header_kasir)
        assert res_retur.status_code == 403

@pytest.mark.asyncio
async def test_u15_sinkron_katalog_dan_perubahan_harga():
    async with AsyncClient(transport=ASGITransport(app=aplikasi), base_url="http://test") as klien:
        res_mgr = await klien.post("/api/v1/auth/login", json={"nama_pengguna": "manajer", "kata_sandi": "password123"})
        header_mgr = {"Authorization": f"Bearer {res_mgr.json()['token_akses']}"}

        # Ambil produk untuk diubah harganya
        res_prod = await klien.get("/api/v1/products?cari=GLA-003", headers=header_mgr)
        produk = res_prod.json()[0]
        id_produk = produk["id"]
        harga_baru = produk["harga"] + 2500

        # Ubah harga
        res_ubah = await klien.put(f"/api/v1/products/{id_produk}", json={
            "harga": harga_baru
        }, headers=header_mgr)
        assert res_ubah.status_code == 200
        assert res_ubah.json()["harga"] == harga_baru

        # Periksa katalog sinkronisasi mengembalikan harga baru
        res_sync = await klien.get("/api/v1/sync/products", headers=header_mgr)
        assert res_sync.status_code == 200
        p_sync = next(p for p in res_sync.json()["produk"] if p["id"] == id_produk)
        assert p_sync["harga"] == harga_baru

@pytest.mark.asyncio
async def test_u16_clock_skew_dan_u04_qris():
    async with AsyncClient(transport=ASGITransport(app=aplikasi), base_url="http://test") as klien:
        res_kasir = await klien.post("/api/v1/auth/login", json={"nama_pengguna": "kasir", "kata_sandi": "password123"})
        header_kasir = {"Authorization": f"Bearer {res_kasir.json()['token_akses']}"}

        # Buka Shift Kasir
        id_shift = str(uuid.uuid4())
        await klien.post("/api/v1/shifts/open", json={"id": id_shift, "kas_awal": 50000}, headers=header_kasir)

        # Ambil produk
        res_prod = await klien.get("/api/v1/products?cari=AIR-007", headers=header_kasir)
        p_air = res_prod.json()[0]

        # U04: Jual QRIS Manual dengan Clock Skew (dimajukan 30 menit)
        id_sale = str(uuid.uuid4())
        waktu_miring = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
        payload_qris = {
            "id": id_sale,
            "id_shift": id_shift,
            "nomor_struk": f"QRIS-01-{id_sale[:8]}",
            "subtotal": 8000,
            "diskon": 0,
            "pajak": 0,
            "pembulatan": 0,
            "total": 8000,
            "waktu_transaksi": waktu_miring,
            "item": [
                {
                    "id_produk": p_air["id"],
                    "nama_produk_snapshot": p_air["nama"],
                    "harga_snapshot": p_air["harga"],
                    "kuantitas": 2,
                    "alokasi_diskon": 0,
                    "subtotal_baris": 8000
                }
            ],
            "pembayaran": [
                {
                    "metode": "qris",
                    "jumlah": 8000,
                    "diterima": 8000,
                    "kembalian": 0
                }
            ]
        }
        res_sale = await klien.post("/api/v1/sales", json=payload_qris, headers=header_kasir)
        assert res_sale.status_code == 201
        data = res_sale.json()
        assert data["status"] == "completed"
        # Verifikasi flag clock_skew aktif dan mencatat selisih detik
        assert "clock_skew" in data["flag"]
        assert data["flag"]["clock_skew"]["selisih_detik"] >= 600

        # Tutup shift
        res_tutup = await klien.post(f"/api/v1/shifts/{id_shift}/close", json={
            "kas_fisik": 50000,
            "catatan": "Shift ditutup setelah penjualan QRIS"
        }, headers=header_kasir)
        assert res_tutup.status_code == 200
        assert res_tutup.json()["status"] == "closed"

