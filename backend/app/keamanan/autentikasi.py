import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.konfigurasi import setelan
from app.basis_data import dapatkan_sesi_db
from app.model.entitas import ModelPengguna

# Inisialisasi Argon2 Password Hasher
try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    _hasher = PasswordHasher()
    
    def buat_hash_kata_sandi(kata_sandi: str) -> str:
        return _hasher.hash(kata_sandi)

    def verifikasi_kata_sandi(kata_sandi: str, hash_disimpan: str) -> bool:
        try:
            return _hasher.verify(hash_disimpan, kata_sandi)
        except Exception:
            return False
except Exception:
    import hashlib
    # Fallback aman
    def buat_hash_kata_sandi(kata_sandi: str) -> str:
        return hashlib.sha256((kata_sandi + setelan.KUNCI_RAHASIA).encode()).hexdigest()

    def verifikasi_kata_sandi(kata_sandi: str, hash_disimpan: str) -> bool:
        return buat_hash_kata_sandi(kata_sandi) == hash_disimpan

skema_bearer = HTTPBearer(auto_error=False)

def buat_token_akses(data: dict, masa_berlaku_menit: int = None) -> str:
    """
    Buat JWT token akses bertanda tangan
    """
    ke_enkripsi = data.copy()
    if masa_berlaku_menit:
        kedaluwarsa = datetime.now(timezone.utc) + timedelta(minutes=masa_berlaku_menit)
    else:
        kedaluwarsa = datetime.now(timezone.utc) + timedelta(minutes=setelan.MENIT_KADALUARSA_AKSES)
        
    ke_enkripsi.update({"exp": kedaluwarsa})
    token = jwt.encode(ke_enkripsi, setelan.KUNCI_RAHASIA, algorithm=setelan.ALGORITMA_JWT)
    return token

def dekode_token_akses(token: str) -> dict:
    """
    Validasi dan decode payload JWT
    """
    try:
        payload = jwt.decode(token, setelan.KUNCI_RAHASIA, algorithms=[setelan.ALGORITMA_JWT])
        return payload
    except jwt.PyJWTError:
        return None

async def dapatkan_pengguna_saat_ini(
    kredensial: HTTPAuthorizationCredentials = Depends(skema_bearer),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
) -> ModelPengguna:
    """
    Dependensi untuk mengambil data pengguna yang sedang login dari header Bearer token
    """
    if not kredensial:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Autentikasi diperlukan untuk mengakses sumber daya ini"}
        )

    payload = dekode_token_akses(kredensial.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Token tidak valid atau telah kedaluwarsa"}
        )

    id_pengguna = payload["sub"]
    kueri = select(ModelPengguna).where(
        ModelPengguna.id == id_pengguna,
        ModelPengguna.status_aktif == True
    )
    hasil = await sesi.execute(kueri)
    pengguna = hasil.scalar_one_or_none()

    if not pengguna:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Pengguna tidak ditemukan atau telah dinonaktifkan"}
        )

    return pengguna

def wajib_peran(*peran_diizinkan: str):
    """
    Penegakan RBAC di sisi server sesuai Tabel Hak Akses Bagian 3 pada PRD.
    Contoh: @router.get("/laporan", dependencies=[Depends(wajib_peran("manajer", "owner"))])
    """
    async def verifikasi_peran(pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini)):
        if pengguna.peran not in peran_diizinkan:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": f"Akses ditolak. Peran '{pengguna.peran}' tidak memiliki izin."}
            )
        return pengguna
    return verifikasi_peran
