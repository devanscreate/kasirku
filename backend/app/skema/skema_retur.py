from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

class InputItemRetur(BaseModel):
    id_produk: str
    kuantitas: int = Field(..., gt=0)
    apakah_stok_kembali: bool = True # true jika barang bagus dimasukkan lagi ke stok, false jika barang rusak

class InputReturPenjualan(BaseModel):
    id: str = Field(..., description="UUID retur buatan klien (idempoten)")
    id_penjualan: str
    id_shift: str = Field(..., description="Shift aktif untuk pencatatan pengeluaran refund")
    alasan: str = Field(..., min_length=3)
    metode_pengembalian: str = Field(..., pattern="^(tunai|transfer)$")
    item: List[InputItemRetur] = Field(..., min_length=1)

class ResponsItemRetur(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    id_produk: str
    kuantitas: int
    apakah_stok_kembali: bool
    jumlah_pengembalian: int

class ResponsReturPenjualan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    id_penjualan: str
    id_shift: str
    alasan: str
    metode_pengembalian: str
    total_pengembalian: int
    dibuat_oleh: str
    dibuat_pada: datetime
    item: List[ResponsItemRetur] = []
