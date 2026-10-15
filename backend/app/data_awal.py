import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.model.entitas import (
    ModelToko,
    ModelPengguna,
    ModelProduk,
    ModelPergerakanStok,
    waktu_sekarang_utc
)
from app.keamanan.autentikasi import buat_hash_kata_sandi

async def inisialisasi_data_awal(sesi: AsyncSession):
    """
    Mengisi data awal demo: Toko, Pengguna (kasir, manajer, owner), dan Produk ritel
    """
    # 1. Cek Toko
    kueri_toko = select(ModelToko)
    toko = (await sesi.execute(kueri_toko)).scalars().first()

    if not toko:
        pengaturan_awal = {
            "pajak_persen": 0,
            "tipe_pajak": "inklusif",
            "pembulatan": 0,
            "max_diskon_kasir": 10,
            "cash_diff_threshold": 50000,
            "blind_close": True,
            "lebar_kertas": 58,
            "kode_perangkat": "KASIR-01"
        }
        toko = ModelToko(
            nama="Toko Berkah Sejahtera",
            alamat="Jl. Merdeka No. 45, Jakarta",
            telepon="0812-3456-7890",
            pengaturan=json.dumps(pengaturan_awal)
        )
        sesi.add(toko)
        await sesi.flush()

    # 2. Pengguna Awal
    daftar_pengguna_awal = [
        {"username": "owner", "pass": "password123", "nama": "Budi Santoso (Owner)", "peran": "owner"},
        {"username": "manajer", "pass": "password123", "nama": "Siti Rahma (Manajer)", "peran": "manajer"},
        {"username": "kasir", "pass": "password123", "nama": "Rian Pratama (Kasir)", "peran": "kasir"},
    ]

    for p in daftar_pengguna_awal:
        kueri_p = select(ModelPengguna).where(
            ModelPengguna.id_toko == toko.id,
            ModelPengguna.nama_pengguna == p["username"]
        )
        ada = (await sesi.execute(kueri_p)).scalar_one_or_none()
        if not ada:
            baru = ModelPengguna(
                id_toko=toko.id,
                nama_pengguna=p["username"],
                kata_sandi_hash=buat_hash_kata_sandi(p["pass"]),
                nama_lengkap=p["nama"],
                peran=p["peran"],
                status_aktif=True
            )
            sesi.add(baru)

    # 3. Produk Ritel Awal
    daftar_produk_awal = [
        {"sku": "BRS-001", "barcode": "8991001001", "nama": "Beras Premium 5kg", "kategori": "Sembako", "harga": 72000, "modal": 65000, "stok": 50, "min": 10},
        {"sku": "MYK-002", "barcode": "8991001002", "nama": "Minyak Goreng 2 Liter", "kategori": "Sembako", "harga": 36000, "modal": 32000, "stok": 40, "min": 10},
        {"sku": "GLA-003", "barcode": "8991001003", "nama": "Gula Pasir 1kg", "kategori": "Sembako", "harga": 17500, "modal": 15500, "stok": 35, "min": 8},
        {"sku": "KPI-004", "barcode": "8991001004", "nama": "Kopi Bubuk Robusta 150g", "kategori": "Minuman", "harga": 12000, "modal": 9500, "stok": 60, "min": 10},
        {"sku": "TEH-005", "barcode": "8991001005", "nama": "Teh Celup Kotak 25s", "kategori": "Minuman", "harga": 8500, "modal": 6500, "stok": 45, "min": 10},
        {"sku": "MIE-006", "barcode": "8991001006", "nama": "Mie Instan Goreng", "kategori": "Makanan", "harga": 3500, "modal": 2800, "stok": 120, "min": 24},
        {"sku": "AIR-007", "barcode": "8991001007", "nama": "Air Mineral Botol 600ml", "kategori": "Minuman", "harga": 4000, "modal": 2500, "stok": 80, "min": 15},
        {"sku": "SSU-008", "barcode": "8991001008", "nama": "Susu UHT Plain 1 Liter", "kategori": "Minuman", "harga": 21000, "modal": 18000, "stok": 25, "min": 5},
        {"sku": "SBN-009", "barcode": "8991001009", "nama": "Sabun Mandi Batang 80g", "kategori": "Kebersihan", "harga": 5000, "modal": 3800, "stok": 50, "min": 10},
        {"sku": "DTG-010", "barcode": "8991001010", "nama": "Deterjen Bubuk 800g", "kategori": "Kebersihan", "harga": 19500, "modal": 16500, "stok": 3, "min": 5}, # Stok menipis demo
    ]

    for p in daftar_produk_awal:
        kueri_pr = select(ModelProduk).where(
            ModelProduk.id_toko == toko.id,
            ModelProduk.sku == p["sku"]
        )
        ada_pr = (await sesi.execute(kueri_pr)).scalar_one_or_none()
        if not ada_pr:
            pr_baru = ModelProduk(
                id_toko=toko.id,
                sku=p["sku"],
                barcode=p["barcode"],
                nama=p["nama"],
                kategori=p["kategori"],
                harga=p["harga"],
                harga_modal=p["modal"],
                stok=p["stok"],
                min_stok=p["min"],
                status_aktif=True,
                diperbarui_pada=waktu_sekarang_utc()
            )
            sesi.add(pr_baru)
            await sesi.flush()

            # Catat pergerakan stok awal
            pergerakan = ModelPergerakanStok(
                id_toko=toko.id,
                id_produk=pr_baru.id,
                perubahan_stok=p["stok"],
                tipe="initial",
                alasan="Inisialisasi katalog awal toko",
                dibuat_pada=waktu_sekarang_utc()
            )
            sesi.add(pergerakan)

    await sesi.commit()
