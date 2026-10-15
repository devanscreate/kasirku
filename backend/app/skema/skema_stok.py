from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class PermintaanTerimaStok(BaseModel):
    id_produk: str
    kuantitas: int = Field(..., gt=0, description="Jumlah barang yang diterima dari pemasok")
    harga_modal: Optional[int] = Field(None, ge=0)
    catatan: Optional[str] = None

class PermintaanSesuaikanStok(BaseModel):
    id_produk: str
    perubahan_stok: int = Field(..., description="Delta perubahan stok (+/-)")
    alasan: str = Field(..., min_length=3, description="Alasan penyesuaian (mis: rusak, kedaluwarsa, koreksi)")

class PermintaanOpnameStok(BaseModel):
    id_produk: str
    stok_fisik: int = Field(..., ge=0, description="Hasil hitungan fisik stok di toko")
    alasan: Optional[str] = "Hasil Stock Opname Fisik"

class ResponsPergerakanStok(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    id_toko: str
    id_produk: str
    nama_produk: Optional[str] = None
    perubahan_stok: int
    tipe: str
    id_referensi: Optional[str] = None
    alasan: Optional[str] = None
    dibuat_oleh: Optional[str] = None
    dibuat_pada: datetime
