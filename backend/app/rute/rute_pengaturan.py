from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Dict, Any, Optional
import json

from app.basis_data import dapatkan_sesi_db
from app.model.entitas import ModelToko, ModelPengguna, ModelCatatanAudit, waktu_sekarang_utc
from app.skema.skema_auth import ResponsPengguna, PermintaanBuatPengguna, PermintaanUbahPengguna
from app.keamanan.autentikasi import dapatkan_pengguna_saat_ini, wajib_peran, buat_hash_kata_sandi

router = APIRouter(tags=["Pengaturan Toko & Pengguna"])

@router.get("/settings")
async def ambil_pengaturan_toko(
    pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Mengambil data profil toko dan konfigurasi POS
    """
    kueri = select(ModelToko).where(ModelToko.id == pengguna.id_toko)
    toko = (await sesi.execute(kueri)).scalar_one_or_none()
    if not toko:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Data toko tidak ditemukan"}
        )

    pengaturan_json = json.loads(toko.pengaturan) if toko.pengaturan else {}
    return {
        "id": toko.id,
        "nama": toko.nama,
        "alamat": toko.alamat,
        "telepon": toko.telepon,
        "pengaturan": pengaturan_json
    }

@router.put("/settings")
async def perbarui_pengaturan_toko(
    data: Dict[str, Any],
    pengguna: ModelPengguna = Depends(wajib_peran("owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Memperbarui profil toko dan aturan bisnis POS (Khusus Owner)
    """
    kueri = select(ModelToko).where(ModelToko.id == pengguna.id_toko)
    toko = (await sesi.execute(kueri)).scalar_one_or_none()
    if not toko:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Data toko tidak ditemukan"}
        )

    if "nama" in data:
        toko.nama = data["nama"]
    if "alamat" in data:
        toko.alamat = data["alamat"]
    if "telepon" in data:
        toko.telepon = data["telepon"]
    if "pengaturan" in data:
        toko.pengaturan = json.dumps(data["pengaturan"])

    audit = ModelCatatanAudit(
        id_toko=toko.id,
        id_aktor=pengguna.id,
        aksi="UBAH_PENGATURAN_TOKO",
        entitas="toko",
        id_entitas=toko.id,
        rincian=f"Pengaturan toko diubah oleh Owner {pengguna.nama_pengguna}"
    )
    sesi.add(audit)
    await sesi.commit()
    await sesi.refresh(toko)

    return {
        "id": toko.id,
        "nama": toko.nama,
        "alamat": toko.alamat,
        "telepon": toko.telepon,
        "pengaturan": json.loads(toko.pengaturan) if toko.pengaturan else {}
    }

@router.get("/users", response_model=List[ResponsPengguna])
async def daftar_pengguna(
    pengguna: ModelPengguna = Depends(wajib_peran("owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Mengambil daftar seluruh pengguna/karyawan toko (Khusus Owner)
    """
    kueri = select(ModelPengguna).where(
        ModelPengguna.id_toko == pengguna.id_toko
    ).order_by(ModelPengguna.nama_lengkap.asc())
    daftar = (await sesi.execute(kueri)).scalars().all()
    return daftar

@router.post("/users", response_model=ResponsPengguna, status_code=status.HTTP_201_CREATED)
async def buat_pengguna_baru(
    permintaan: PermintaanBuatPengguna,
    pengguna: ModelPengguna = Depends(wajib_peran("owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Membuat akun kasir atau manajer baru (Khusus Owner)
    """
    kueri_cek = select(ModelPengguna).where(
        ModelPengguna.id_toko == pengguna.id_toko,
        ModelPengguna.nama_pengguna == permintaan.nama_pengguna
    )
    ada = (await sesi.execute(kueri_cek)).scalar_one_or_none()
    if ada:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DUPLICATE_USERNAME", "message": f"Nama pengguna '{permintaan.nama_pengguna}' sudah digunakan."}
        )

    pengguna_baru = ModelPengguna(
        id_toko=pengguna.id_toko,
        nama_pengguna=permintaan.nama_pengguna,
        kata_sandi_hash=buat_hash_kata_sandi(permintaan.kata_sandi),
        nama_lengkap=permintaan.nama_lengkap,
        peran=permintaan.peran,
        status_aktif=True
    )
    sesi.add(pengguna_baru)

    audit = ModelCatatanAudit(
        id_toko=pengguna.id_toko,
        id_aktor=pengguna.id,
        aksi="BUAT_PENGGUNA",
        entitas="pengguna",
        id_entitas=pengguna_baru.id,
        rincian=f"Akun baru {pengguna_baru.nama_pengguna} ({pengguna_baru.peran}) dibuat oleh Owner {pengguna.nama_pengguna}"
    )
    sesi.add(audit)
    await sesi.commit()
    await sesi.refresh(pengguna_baru)
    return pengguna_baru

@router.put("/users/{id_target}", response_model=ResponsPengguna)
async def perbarui_pengguna(
    id_target: str,
    permintaan: PermintaanUbahPengguna,
    pengguna: ModelPengguna = Depends(wajib_peran("owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Mengubah info akun atau peran pengguna (Khusus Owner)
    """
    kueri = select(ModelPengguna).where(
        ModelPengguna.id == id_target,
        ModelPengguna.id_toko == pengguna.id_toko
    )
    target = (await sesi.execute(kueri)).scalar_one_or_none()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Pengguna tidak ditemukan."}
        )

    if permintaan.nama_lengkap is not None:
        target.nama_lengkap = permintaan.nama_lengkap
    if permintaan.peran is not None:
        target.peran = permintaan.peran
    if permintaan.status_aktif is not None:
        target.status_aktif = permintaan.status_aktif
    if permintaan.kata_sandi:
        target.kata_sandi_hash = buat_hash_kata_sandi(permintaan.kata_sandi)

    audit = ModelCatatanAudit(
        id_toko=pengguna.id_toko,
        id_aktor=pengguna.id,
        aksi="UBAH_PENGGUNA",
        entitas="pengguna",
        id_entitas=target.id,
        rincian=f"Akun {target.nama_pengguna} diperbarui oleh Owner {pengguna.nama_pengguna}"
    )
    sesi.add(audit)
    await sesi.commit()
    await sesi.refresh(target)
    return target
