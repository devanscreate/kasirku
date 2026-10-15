from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class PermintaanBukaShift(BaseModel):
    id: str = Field(..., description="UUID shift yang dihasilkan oleh perangkat kasir")
    kas_awal: int = Field(..., ge=0, description="Uang kas awal di laci kasir")

class PermintaanTutupShift(BaseModel):
    kas_fisik: int = Field(..., ge=0, description="Jumlah uang fisik hasil hitungan kasir")
    catatan: Optional[str] = Field(None, description="Catatan penjelasan jika ada selisih kas")

class ResponsShift(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    id_toko: str
    id_kasir: str
    nama_kasir: Optional[str] = None
    dibuka_pada: datetime
    ditutup_pada: Optional[datetime] = None
    kas_awal: int
    kas_ekspektasi: int
    kas_fisik: Optional[int] = None
    selisih: Optional[int] = None
    status: str
    catatan: Optional[str] = None
    memiliki_penjualan_bermasalah: bool

class RingkasanTutupShift(BaseModel):
    id_shift: str
    kas_awal: int
    total_penjualan_tunai: int
    total_penjualan_qris: int
    total_penjualan_transfer: int
    total_refund_tunai: int
    kas_ekspektasi: int
    kas_fisik: Optional[int] = None
    selisih: Optional[int] = None
    jumlah_transaksi: int
