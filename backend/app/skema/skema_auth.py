from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class PermintaanLogin(BaseModel):
    nama_pengguna: str = Field(..., min_length=1, max_length=100)
    kata_sandi: str = Field(..., min_length=1)

class ResponsToken(BaseModel):
    token_akses: str
    tipe_token: str = "bearer"
    kedaluwarsa_dalam_detik: int
    id_pengguna: str
    nama_pengguna: str
    nama_lengkap: str
    peran: str
    id_toko: str

class ResponsPengguna(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    id_toko: str
    nama_pengguna: str
    nama_lengkap: str
    peran: str
    status_aktif: bool
    dibuat_pada: datetime

class PermintaanBuatPengguna(BaseModel):
    nama_pengguna: str = Field(..., min_length=3, max_length=100)
    kata_sandi: str = Field(..., min_length=6)
    nama_lengkap: str = Field(..., min_length=1, max_length=150)
    peran: str = Field("kasir", pattern="^(kasir|manajer|owner)$")

class PermintaanUbahPengguna(BaseModel):
    nama_lengkap: Optional[str] = None
    kata_sandi: Optional[str] = None
    peran: Optional[str] = None
    status_aktif: Optional[bool] = None
