from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.basis_data import dapatkan_sesi_db
from app.model.entitas import ModelPengguna, ModelCatatanAudit, ModelSesiRefresh, waktu_sekarang_utc
from app.skema.skema_auth import PermintaanLogin, ResponsToken, ResponsPengguna
from app.keamanan.autentikasi import (
    verifikasi_kata_sandi,
    buat_token_akses,
    dapatkan_pengguna_saat_ini,
    buat_hash_kata_sandi
)
from app.keamanan.pembatas_laju import periksa_apakah_dibatasi, catat_percobaan_gagal, reset_percobaan
import secrets
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["Autentikasi"])

@router.post("/login", response_model=ResponsToken)
async def masuk(
    permintaan: PermintaanLogin,
    request: Request,
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-01: Login dengan pembatasan laju (maks 5 gagal/menit) dan verifikasi kata sandi
    """
    ip_klien = request.client.host if request.client else "127.0.0.1"
    kunci_pembatas = f"{permintaan.nama_pengguna}:{ip_klien}"

    # Cek pembatasan laju (Rate Limit)
    if periksa_apakah_dibatasi(kunci_pembatas):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "TOO_MANY_REQUESTS", "message": "Terlalu banyak percobaan login yang gagal. Silakan tunggu 1 menit."}
        )

    # Cari data pengguna
    kueri = select(ModelPengguna).where(ModelPengguna.nama_pengguna == permintaan.nama_pengguna)
    hasil = await sesi.execute(kueri)
    pengguna = hasil.scalar_one_or_none()

    # Validasi pengguna dan kata sandi (pesan generik untuk keamanan)
    if not pengguna or not verifikasi_kata_sandi(permintaan.kata_sandi, pengguna.kata_sandi_hash):
        catat_percobaan_gagal(kunci_pembatas)
        # Catat audit kegagalan login
        if pengguna:
            audit = ModelCatatanAudit(
                id_toko=pengguna.id_toko,
                id_aktor=pengguna.id,
                aksi="LOGIN_GAGAL",
                entitas="pengguna",
                id_entitas=pengguna.id,
                rincian=f"Percobaan login gagal dari IP: {ip_klien}"
            )
            sesi.add(audit)
            await sesi.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Nama pengguna atau kata sandi tidak valid"}
        )

    # Cek apakah akun aktif
    if not pengguna.status_aktif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Akun Anda telah dinonaktifkan oleh pemilik toko"}
        )

    # Reset counter gagal
    reset_percobaan(kunci_pembatas)

    # Buat JWT Access Token
    token_jwt = buat_token_akses({
        "sub": pengguna.id,
        "peran": pengguna.peran,
        "nama_pengguna": pengguna.nama_pengguna,
        "id_toko": pengguna.id_toko
    })

    # Buat Refresh Token unik
    token_refresh_acak = secrets.token_hex(32)
    hash_refresh = buat_hash_kata_sandi(token_refresh_acak)
    kadaluarsa_refresh = waktu_sekarang_utc() + timedelta(hours=12)

    sesi_refresh = ModelSesiRefresh(
        id_pengguna=pengguna.id,
        token_hash=hash_refresh,
        kadaluarsa_pada=kadaluarsa_refresh
    )
    sesi.add(sesi_refresh)

    # Catat audit login berhasil
    audit = ModelCatatanAudit(
        id_toko=pengguna.id_toko,
        id_aktor=pengguna.id,
        aksi="LOGIN_BERHASIL",
        entitas="pengguna",
        id_entitas=pengguna.id,
        rincian=f"Login berhasil sebagai {pengguna.peran} dari IP: {ip_klien}"
    )
    sesi.add(audit)
    await sesi.commit()

    return ResponsToken(
        token_akses=token_jwt,
        tipe_token="bearer",
        kedaluwarsa_dalam_detik=86400,
        id_pengguna=pengguna.id,
        nama_pengguna=pengguna.nama_pengguna,
        nama_lengkap=pengguna.nama_lengkap,
        peran=pengguna.peran,
        id_toko=pengguna.id_toko
    )

@router.get("/profil", response_model=ResponsPengguna)
async def lihat_profil(pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini)):
    """
    Mendapatkan data profil pengguna yang sedang login
    """
    return pengguna

@router.post("/logout")
async def keluar(
    pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Menghapus sesi login pengguna
    """
    audit = ModelCatatanAudit(
        id_toko=pengguna.id_toko,
        id_aktor=pengguna.id,
        aksi="LOGOUT",
        entitas="pengguna",
        id_entitas=pengguna.id,
        rincian=f"Pengguna {pengguna.nama_pengguna} telah logout"
    )
    sesi.add(audit)
    await sesi.commit()
    return {"message": "Berhasil logout"}
