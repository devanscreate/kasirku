from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class InputItemPenjualan(BaseModel):
    id_produk: str
    nama_produk_snapshot: str
    harga_snapshot: int = Field(..., ge=0)
    kuantitas: int = Field(..., gt=0)
    alokasi_diskon: int = Field(0, ge=0)
    subtotal_baris: int = Field(..., ge=0)

class InputPembayaran(BaseModel):
    metode: str = Field(..., pattern="^(tunai|qris|transfer)$")
    jumlah: int = Field(..., ge=0)
    diterima: int = Field(..., ge=0)
    kembalian: int = Field(0, ge=0)

class InputPenjualan(BaseModel):
    id: str = Field(..., description="UUID transaksi yang dihasilkan di perangkat klien")
    id_shift: str
    nomor_struk: str
    subtotal: int = Field(..., ge=0)
    diskon: int = Field(0, ge=0)
    pajak: int = Field(0, ge=0)
    pembulatan: int = Field(0)
    total: int = Field(..., ge=0)
    waktu_transaksi: datetime
    item: List[InputItemPenjualan] = Field(..., min_length=1)
    pembayaran: List[InputPembayaran] = Field(..., min_length=1)

class ResponsItemPenjualan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    id_produk: str
    nama_produk_snapshot: str
    harga_snapshot: int
    kuantitas: int
    alokasi_diskon: int
    subtotal_baris: int

class ResponsPembayaran(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    metode: str
    jumlah: int
    diterima: int
    kembalian: int

class ResponsPenjualan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    id_toko: str
    id_shift: str
    id_kasir: str
    nama_kasir: Optional[str] = None
    nomor_struk: str
    status: str
    subtotal: int
    diskon: int
    pajak: int
    pembulatan: int
    total: int
    waktu_transaksi: datetime
    waktu_sinkron: Optional[datetime] = None
    flag: Optional[Dict[str, Any]] = None
    alasan_batal: Optional[str] = None
    dibatalkan_pada: Optional[datetime] = None
    item: List[ResponsItemPenjualan] = []
    pembayaran: List[ResponsPembayaran] = []

class PermintaanVoid(BaseModel):
    alasan: str = Field(..., min_length=5, description="Alasan pembatalan transaksi minimal 5 karakter")
