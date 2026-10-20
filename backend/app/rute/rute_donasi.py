from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from typing import Optional, List
from datetime import datetime, timezone

from app.basis_data import dapatkan_sesi_db
from app.model.entitas import (
    ModelTabunganDonasi,
    ModelPengguna,
    ModelShiftKasir,
    ModelPenjualan,
    waktu_sekarang_utc
)
from app.skema.skema_donasi import (
    InputSetorDonasi,
    InputCairkanDonasi,
    ResponsSaldoPelanggan,
    ItemRiwayatDonasi,
    ItemPelangganDonasi,
    RingkasanDonasiToko
)
from app.keamanan.autentikasi import dapatkan_pengguna_saat_ini

router = APIRouter(prefix="/donations", tags=["Donasi & Tabungan Kembalian"])

def bersihkan_nomor_hp(no_hp: str) -> str:
    """Bersihkan karakter non-digit kecuali tanda plus"""
    no_bersih = "".join(c for c in no_hp if c.isdigit() or c == "+")
    return no_bersih.strip()

@router.post("/setor", status_code=status.HTTP_201_CREATED)
async def setor_donasi_kembalian(
    data: InputSetorDonasi,
    pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Mencatat donasi kembalian pembeli dari transaksi kasir.
    Nominal donasi diakumulasikan ke nomor HP pembeli.
    """
    no_hp = bersihkan_nomor_hp(data.nomor_hp)
    if not no_hp:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "VALIDATION_ERROR", "message": "Nomor HP pembeli tidak valid"}
        )

    catatan_baru = ModelTabunganDonasi(
        id_toko=pengguna.id_toko,
        nomor_hp=no_hp,
        nama_pelanggan=data.nama_pelanggan or None,
        tipe="setor_kembalian",
        nominal=data.nominal,
        id_penjualan=data.id_penjualan,
        nomor_struk=data.nomor_struk,
        id_shift=data.id_shift,
        id_kasir=pengguna.id,
        catatan="Donasi kembalian belanja",
        dibuat_pada=waktu_sekarang_utc()
    )
    sesi.add(catatan_baru)
    await sesi.commit()

    # Hitung saldo akumulasi terkini
    saldo_info = await dapatkan_saldo_pelanggan_internal(no_hp, pengguna.id_toko, sesi)

    return {
        "status": "success",
        "pesan": f"Donasi kembalian Rp {data.nominal:,} berhasil ditambahkan ke tabungan pelanggan.",
        "nomor_hp": no_hp,
        "nama_pelanggan": saldo_info["nama_pelanggan"],
        "nominal_disetor": data.nominal,
        "total_saldo": saldo_info["total_saldo"],
        "total_donasi_bulan_ini": saldo_info["total_donasi_bulan_ini"]
    }

async def dapatkan_saldo_pelanggan_internal(nomor_hp: str, id_toko: str, sesi: AsyncSession):
    kueri = select(ModelTabunganDonasi).where(
        ModelTabunganDonasi.id_toko == id_toko,
        ModelTabunganDonasi.nomor_hp == nomor_hp
    ).order_by(desc(ModelTabunganDonasi.dibuat_pada))

    hasil = (await sesi.execute(kueri)).scalars().all()

    total_setor = 0
    total_cair = 0
    total_bulan_ini = 0
    nama_pelanggan = None

    sekarang = datetime.now(timezone.utc)
    awal_bulan = datetime(sekarang.year, sekarang.month, 1, tzinfo=timezone.utc)

    for item in hasil:
        if not nama_pelanggan and item.nama_pelanggan:
            nama_pelanggan = item.nama_pelanggan

        if item.tipe == "setor_kembalian":
            total_setor += item.nominal
            # Hitung donasi bulan kalender berjalan
            item_waktu = item.dibuat_pada
            if item_waktu and item_waktu.tzinfo is None:
                item_waktu = item_waktu.replace(tzinfo=timezone.utc)
            if item_waktu and item_waktu >= awal_bulan:
                total_bulan_ini += item.nominal
        elif item.tipe in ("cair_tunai", "potong_belanja"):
            total_cair += item.nominal

    total_saldo = max(0, total_setor - total_cair)

    return {
        "nomor_hp": nomor_hp,
        "nama_pelanggan": nama_pelanggan or "Pelanggan",
        "total_saldo": total_saldo,
        "total_donasi_bulan_ini": total_bulan_ini,
        "jumlah_transaksi": len(hasil),
        "riwayat": hasil
    }

@router.get("/saldo/{nomor_hp}", response_model=ResponsSaldoPelanggan)
async def ambil_saldo_pelanggan(
    nomor_hp: str,
    pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Cek saldo tabungan donasi pembeli berdasarkan Nomor HP.
    Menampilkan akumulasi saldo, total donasi bulan ini, dan riwayat mutasi.
    """
    no_hp = bersihkan_nomor_hp(nomor_hp)
    info = await dapatkan_saldo_pelanggan_internal(no_hp, pengguna.id_toko, sesi)

    return ResponsSaldoPelanggan(
        nomor_hp=info["nomor_hp"],
        nama_pelanggan=info["nama_pelanggan"],
        total_saldo=info["total_saldo"],
        total_donasi_bulan_ini=info["total_donasi_bulan_ini"],
        jumlah_transaksi=info["jumlah_transaksi"],
        riwayat=[
            ItemRiwayatDonasi(
                id=r.id,
                tipe=r.tipe,
                nominal=r.nominal,
                nomor_struk=r.nomor_struk,
                catatan=r.catatan,
                dibuat_pada=r.dibuat_pada
            ) for r in info["riwayat"][:30]
        ]
    )

@router.post("/cairkan")
async def cairkan_donasi_pelanggan(
    data: InputCairkanDonasi,
    pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Mencairkan saldo donasi/tabungan pembeli:
    - Pilihan A: Ditukarkan uang cash (tunai dari laci)
    - Pilihan B: Potong belanjaan (digunakan sebagai metode bayar belanja)
    """
    no_hp = bersihkan_nomor_hp(data.nomor_hp)
    info = await dapatkan_saldo_pelanggan_internal(no_hp, pengguna.id_toko, sesi)

    if data.nominal > info["total_saldo"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INSUFFICIENT_BALANCE",
                "message": f"Saldo tabungan donasi tidak mencukupi. Saldo tersedia: Rp {info['total_saldo']:,}, diminta: Rp {data.nominal:,}."
            }
        )

    tipe_mutasi = "cair_tunai" if data.tipe == "tunai" else "potong_belanja"
    catatan_teks = data.catatan or (
        f"Pencairan tunai donasi pelanggan Rp {data.nominal:,}"
        if data.tipe == "tunai"
        else f"Potongan belanja kasir Rp {data.nominal:,}"
    )

    pencairan = ModelTabunganDonasi(
        id_toko=pengguna.id_toko,
        nomor_hp=no_hp,
        nama_pelanggan=info["nama_pelanggan"],
        tipe=tipe_mutasi,
        nominal=data.nominal,
        id_shift=data.id_shift,
        id_kasir=pengguna.id,
        catatan=catatan_teks,
        dibuat_pada=waktu_sekarang_utc()
    )
    sesi.add(pencairan)
    await sesi.commit()

    sisa_saldo = info["total_saldo"] - data.nominal

    return {
        "status": "success",
        "pesan": f"Pencairan {data.tipe} sebesar Rp {data.nominal:,} berhasil diproses.",
        "nomor_hp": no_hp,
        "nama_pelanggan": info["nama_pelanggan"],
        "tipe_pencairan": data.tipe,
        "nominal_dicairkan": data.nominal,
        "sisa_saldo": sisa_saldo,
        "waktu": pencairan.dibuat_pada.isoformat()
    }

@router.get("/pelanggan", response_model=List[ItemPelangganDonasi])
async def daftar_pelanggan_donasi(
    q: Optional[str] = Query(None, description="Pencarian nama atau nomor HP"),
    pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Menampilkan daftar pembeli yang memiliki riwayat tabungan donasi kembalian di toko.
    """
    kueri = select(ModelTabunganDonasi).where(
        ModelTabunganDonasi.id_toko == pengguna.id_toko
    ).order_by(desc(ModelTabunganDonasi.dibuat_pada))

    semua = (await sesi.execute(kueri)).scalars().all()

    pelanggan_map = {}
    sekarang = datetime.now(timezone.utc)
    awal_bulan = datetime(sekarang.year, sekarang.month, 1, tzinfo=timezone.utc)

    for item in semua:
        hp = item.nomor_hp
        if hp not in pelanggan_map:
            pelanggan_map[hp] = {
                "nomor_hp": hp,
                "nama_pelanggan": item.nama_pelanggan or "Pelanggan",
                "total_saldo": 0,
                "total_donasi_bulan_ini": 0,
                "terakhir_transaksi": item.dibuat_pada
            }
        
        if not pelanggan_map[hp]["nama_pelanggan"] and item.nama_pelanggan:
            pelanggan_map[hp]["nama_pelanggan"] = item.nama_pelanggan

        if item.tipe == "setor_kembalian":
            pelanggan_map[hp]["total_saldo"] += item.nominal
            item_waktu = item.dibuat_pada
            if item_waktu and item_waktu.tzinfo is None:
                item_waktu = item_waktu.replace(tzinfo=timezone.utc)
            if item_waktu and item_waktu >= awal_bulan:
                pelanggan_map[hp]["total_donasi_bulan_ini"] += item.nominal
        elif item.tipe in ("cair_tunai", "potong_belanja"):
            pelanggan_map[hp]["total_saldo"] -= item.nominal

    hasil = []
    for data in pelanggan_map.values():
        if q:
            kueri_cari = q.lower().strip()
            if kueri_cari not in data["nomor_hp"].lower() and kueri_cari not in data["nama_pelanggan"].lower():
                continue
        hasil.append(ItemPelangganDonasi(
            nomor_hp=data["nomor_hp"],
            nama_pelanggan=data["nama_pelanggan"],
            total_saldo=max(0, data["total_saldo"]),
            total_donasi_bulan_ini=data["total_donasi_bulan_ini"],
            terakhir_transaksi=data["terakhir_transaksi"]
        ))

    # Urutkan berdasarkan saldo terbanyak
    hasil.sort(key=lambda x: x.total_saldo, reverse=True)
    return hasil

@router.get("/ringkasan", response_model=RingkasanDonasiToko)
async def ringkasan_donasi_toko(
    pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Ringkasan metrik donasi & tabungan kembalian untuk toko
    """
    kueri = select(ModelTabunganDonasi).where(
        ModelTabunganDonasi.id_toko == pengguna.id_toko
    )
    semua = (await sesi.execute(kueri)).scalars().all()

    total_setor = sum(i.nominal for i in semua if i.tipe == "setor_kembalian")
    total_cair = sum(i.nominal for i in semua if i.tipe in ("cair_tunai", "potong_belanja"))
    saldo_aktif = max(0, total_setor - total_cair)

    pelanggan_unik = set(i.nomor_hp for i in semua)

    return RingkasanDonasiToko(
        total_donasi_terkumpul=total_setor,
        total_dicairkan=total_cair,
        saldo_aktif_keseluruhan=saldo_aktif,
        jumlah_pelanggan_aktif=len(pelanggan_unik)
    )
