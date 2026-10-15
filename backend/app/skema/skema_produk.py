from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class PermintaanBuatProduk(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100)
    barcode: Optional[str] = None
    nama: str = Field(..., min_length=1, max_length=200)
    kategori: Optional[str] = None
    foto: Optional[str] = None
    harga: int = Field(..., ge=0, description="Harga jual dalam satuan rupiah integer")
    harga_modal: int = Field(0, ge=0, description="Harga pokok / modal")
    stok_awal: int = Field(0, description="Stok awal produk saat pertama dibuat")
    min_stok: int = Field(5, ge=0)
    status_aktif: bool = True

class PermintaanUbahProduk(BaseModel):
    sku: Optional[str] = None
    barcode: Optional[str] = None
    nama: Optional[str] = None
    kategori: Optional[str] = None
    foto: Optional[str] = None
    harga: Optional[int] = Field(None, ge=0)
    harga_modal: Optional[int] = Field(None, ge=0)
    min_stok: Optional[int] = Field(None, ge=0)
    status_aktif: Optional[bool] = None

class ResponsProduk(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    id_toko: str
    sku: str
    barcode: Optional[str] = None
    nama: str
    kategori: Optional[str] = None
    foto: Optional[str] = None
    harga: int
    harga_modal: int
    stok: int
    min_stok: int
    status_aktif: bool
    apakah_dihapus: bool
    diperbarui_pada: datetime

class ResponsSinkronKatalog(BaseModel):
    produk: List[ResponsProduk]
    kursor_berikutnya: Optional[str] = None
    waktu_server: datetime
