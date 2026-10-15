from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class RingkasanHarian(BaseModel):
    tanggal_mulai: str
    tanggal_selesai: str
    total_omzet_kotor: int
    total_diskon: int
    total_pajak: int
    total_refund: int
    omzet_bersih: int
    total_transaksi_berhasil: int
    total_transaksi_batal: int
    total_transaksi_retur: int

class LaporanPerProduk(BaseModel):
    id_produk: str
    nama_produk: str
    sku: str
    total_kuantitas: int
    total_pendapatan: int

class LaporanPerMetodeBayar(BaseModel):
    metode: str
    total_nominal: int
    jumlah_transaksi: int

class LaporanPerKasir(BaseModel):
    id_kasir: str
    nama_kasir: str
    total_transaksi: int
    total_omzet: int

class LaporanStokMenipis(BaseModel):
    id_produk: str
    nama_produk: str
    sku: str
    stok_sekarang: int
    min_stok: int
    kategori: Optional[str] = None

class LaporanTransaksiBerflag(BaseModel):
    id: str
    nomor_struk: str
    nama_kasir: str
    total: int
    waktu_transaksi: datetime
    flag: Dict[str, Any]
    status: str
