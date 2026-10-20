"""
Script untuk menambahkan data dummy pembeli dan tabungan kembalian ke database Kasirku.
Jalankan di terminal backend:
    python tambah_dummy_pelanggan.py
"""
import asyncio
from sqlalchemy import select
from app.basis_data import PembuatSesiAsync
from app.model.entitas import ModelToko, ModelTabunganDonasi, waktu_sekarang_utc

DAFTAR_DUMMY_PELANGGAN = [
    {
        "hp": "081234567891",
        "nama": "Ibu Siti Rahmawati",
        "mutasi": [
            {"tipe": "setor_kembalian", "nominal": 2500, "struk": "TRX-DEMO-001", "catatan": "Donasi kembalian beras"},
            {"tipe": "setor_kembalian", "nominal": 5000, "struk": "TRX-DEMO-002", "catatan": "Donasi kembalian minyak"},
            {"tipe": "setor_kembalian", "nominal": 15000, "struk": "TRX-DEMO-005", "catatan": "Tabungan kembalian sembako"}
        ]
    },
    {
        "hp": "081388776655",
        "nama": "Pak Hendra Wijaya",
        "mutasi": [
            {"tipe": "setor_kembalian", "nominal": 10000, "struk": "TRX-DEMO-003", "catatan": "Tabungan kembalian belanja"},
            {"tipe": "setor_kembalian", "nominal": 25000, "struk": "TRX-DEMO-007", "catatan": "Tabungan kembalian sembako"},
            {"tipe": "potong_belanja", "nominal": 10000, "struk": "TRX-DEMO-009", "catatan": "Potongan belanjaan kasir POS"}
        ]
    },
    {
        "hp": "085712349988",
        "nama": "Ahmad Fauzi",
        "mutasi": [
            {"tipe": "setor_kembalian", "nominal": 3000, "struk": "TRX-DEMO-004", "catatan": "Donasi kembalian belanja mie"},
            {"tipe": "setor_kembalian", "nominal": 1500, "struk": "TRX-DEMO-006", "catatan": "Donasi kembalian kopi"}
        ]
    },
    {
        "hp": "082199887766",
        "nama": "Dewi Lestari",
        "mutasi": [
            {"tipe": "setor_kembalian", "nominal": 50000, "struk": "TRX-DEMO-008", "catatan": "Tabungan kembalian belanja bulanan"},
            {"tipe": "cair_tunai", "nominal": 20000, "struk": None, "catatan": "Pencairan tunai saldo tabungan di kasir"}
        ]
    },
    {
        "hp": "087855443322",
        "nama": "Budi Prasetyo",
        "mutasi": [
            {"tipe": "setor_kembalian", "nominal": 8000, "struk": "TRX-DEMO-010", "catatan": "Donasi kembalian belanja deterjen"},
            {"tipe": "setor_kembalian", "nominal": 7000, "struk": "TRX-DEMO-011", "catatan": "Donasi kembalian susu kotak"}
        ]
    },
    {
        "hp": "081912345678",
        "nama": "Rina Marlina",
        "mutasi": [
            {"tipe": "setor_kembalian", "nominal": 12000, "struk": "TRX-DEMO-012", "catatan": "Donasi kembalian belanja camilan"},
            {"tipe": "setor_kembalian", "nominal": 6500, "struk": "TRX-DEMO-013", "catatan": "Donasi kembalian gula"}
        ]
    }
]

async def tambah_data_dummy():
    async with PembuatSesiAsync() as sesi:
        # Dapatkan ID Toko
        kueri_toko = select(ModelToko)
        toko = (await sesi.execute(kueri_toko)).scalars().first()
        if not toko:
            print("[ERROR] Toko belum terdaftar di database. Silakan jalankan backend terlebih dahulu.")
            return

        total_item = 0
        for p in DAFTAR_DUMMY_PELANGGAN:
            for m in p["mutasi"]:
                baru = ModelTabunganDonasi(
                    id_toko=toko.id,
                    nomor_hp=p["hp"],
                    nama_pelanggan=p["nama"],
                    tipe=m["tipe"],
                    nominal=m["nominal"],
                    nomor_struk=m["struk"],
                    catatan=m["catatan"],
                    dibuat_pada=waktu_sekarang_utc()
                )
                sesi.add(baru)
                total_item += 1

        await sesi.commit()
        print(f"[SUKSES] Berhasil menambahkan {len(DAFTAR_DUMMY_PELANGGAN)} pembeli ({total_item} mutasi donasi & tabungan).")
        print("\nDaftar Pembeli Dummy yang ditambahkan:")
        for idx, p in enumerate(DAFTAR_DUMMY_PELANGGAN, 1):
            saldo = sum(m["nominal"] if m["tipe"] == "setor_kembalian" else -m["nominal"] for m in p["mutasi"])
            print(f" {idx}. {p['nama']} ({p['hp']}) - Saldo: Rp {saldo:,}")

if __name__ == "__main__":
    asyncio.run(tambah_data_dummy())
