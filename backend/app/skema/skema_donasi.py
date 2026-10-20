from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class InputSetorDonasi(BaseModel):
    nomor_hp: str = Field(..., min_length=4, max_length=30, description="Nomor HP pembeli")
    nama_pelanggan: Optional[str] = Field(None, max_length=150, description="Nama pelanggan (opsional)")
    nominal: int = Field(..., gt=0, description="Nominal donasi kembalian dalam Rupiah (e.g. 100, 200, 300, 400)")
    nomor_struk: Optional[str] = Field(None, description="Nomor struk transaksi belanja")
    id_penjualan: Optional[str] = Field(None, description="ID transaksi penjualan")
    id_shift: Optional[str] = Field(None, description="ID shift kasir aktif")

class InputCairkanDonasi(BaseModel):
    nomor_hp: str = Field(..., min_length=4, max_length=30, description="Nomor HP pembeli")
    nominal: int = Field(..., gt=0, description="Nominal yang dicairkan dalam Rupiah")
    tipe: str = Field("tunai", description="Pilihan pencairan: 'tunai' (cash) atau 'potong_belanja'")
    id_shift: Optional[str] = Field(None, description="ID shift kasir yang memproses")
    catatan: Optional[str] = Field(None, description="Catatan pencairan")

class ItemRiwayatDonasi(BaseModel):
    id: str
    tipe: str
    nominal: int
    nomor_struk: Optional[str] = None
    catatan: Optional[str] = None
    dibuat_pada: datetime

    class Config:
        from_attributes = True

class ResponsSaldoPelanggan(BaseModel):
    nomor_hp: str
    nama_pelanggan: Optional[str] = None
    total_saldo: int
    total_donasi_bulan_ini: int
    jumlah_transaksi: int
    riwayat: List[ItemRiwayatDonasi] = []

class ItemPelangganDonasi(BaseModel):
    nomor_hp: str
    nama_pelanggan: Optional[str] = None
    total_saldo: int
    total_donasi_bulan_ini: int
    terakhir_transaksi: Optional[datetime] = None

class RingkasanDonasiToko(BaseModel):
    total_donasi_terkumpul: int
    total_dicairkan: int
    saldo_aktif_keseluruhan: int
    jumlah_pelanggan_aktif: int
