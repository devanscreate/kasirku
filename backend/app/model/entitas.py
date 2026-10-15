import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, BigInteger, Integer, Boolean, DateTime, ForeignKey, Text, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.basis_data import BasisTabel

def waktu_sekarang_utc():
    return datetime.now(timezone.utc)

def buat_uuid():
    return str(uuid.uuid4())

# 1. Tabel Toko (Tenant)
class ModelToko(BasisTabel):
    __tablename__ = "toko"

    id = Column(String(36), primary_key=True, default=buat_uuid)
    nama = Column(String(150), nullable=False)
    alamat = Column(String(255), nullable=True)
    telepon = Column(String(50), nullable=True)
    pengaturan = Column(Text, nullable=True) # JSON: pajak, pembulatan, max_diskon_kasir, cash_diff_threshold, dll
    dibuat_pada = Column(DateTime(timezone=True), default=waktu_sekarang_utc)

# 2. Tabel Pengguna (Kasir, Manajer, Owner)
class ModelPengguna(BasisTabel):
    __tablename__ = "pengguna"

    id = Column(String(36), primary_key=True, default=buat_uuid)
    id_toko = Column(String(36), ForeignKey("toko.id"), nullable=False, index=True)
    nama_pengguna = Column(String(100), nullable=False)
    kata_sandi_hash = Column(String(255), nullable=False)
    nama_lengkap = Column(String(150), nullable=False)
    peran = Column(String(20), nullable=False, default="kasir") # kasir, manajer, owner
    status_aktif = Column(Boolean, default=True, nullable=False)
    dibuat_pada = Column(DateTime(timezone=True), default=waktu_sekarang_utc)

    __table_args__ = (
        UniqueConstraint("id_toko", "nama_pengguna", name="uq_pengguna_toko_nama"),
    )

# 3. Tabel Sesi Refresh Token
class ModelSesiRefresh(BasisTabel):
    __tablename__ = "sesi_refresh"

    id = Column(String(36), primary_key=True, default=buat_uuid)
    id_pengguna = Column(String(36), ForeignKey("pengguna.id"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True)
    kadaluarsa_pada = Column(DateTime(timezone=True), nullable=False)
    dibuat_pada = Column(DateTime(timezone=True), default=waktu_sekarang_utc)

# 4. Tabel Produk
class ModelProduk(BasisTabel):
    __tablename__ = "produk"

    id = Column(String(36), primary_key=True, default=buat_uuid)
    id_toko = Column(String(36), ForeignKey("toko.id"), nullable=False, index=True)
    sku = Column(String(100), nullable=False)
    barcode = Column(String(100), nullable=True, index=True)
    nama = Column(String(200), nullable=False)
    kategori = Column(String(100), nullable=True)
    foto = Column(Text, nullable=True) # Data foto thumbnail terkompresi / compact WebP base64
    harga = Column(BigInteger, nullable=False, default=0) # Integer Rupiah tanpa desimal
    harga_modal = Column(BigInteger, nullable=False, default=0)
    stok = Column(Integer, nullable=False, default=0)
    min_stok = Column(Integer, nullable=False, default=5)
    status_aktif = Column(Boolean, default=True, nullable=False)
    apakah_dihapus = Column(Boolean, default=False, nullable=False) # Soft delete
    diperbarui_pada = Column(DateTime(timezone=True), default=waktu_sekarang_utc, onupdate=waktu_sekarang_utc, index=True)

    __table_args__ = (
        UniqueConstraint("id_toko", "sku", name="uq_produk_toko_sku"),
        Index("idx_produk_toko_update", "id_toko", "diperbarui_pada"),
    )

# 5. Tabel Riwayat Perubahan Harga
class ModelRiwayatHarga(BasisTabel):
    __tablename__ = "riwayat_harga"

    id = Column(String(36), primary_key=True, default=buat_uuid)
    id_produk = Column(String(36), ForeignKey("produk.id"), nullable=False, index=True)
    harga_lama = Column(BigInteger, nullable=False)
    harga_baru = Column(BigInteger, nullable=False)
    diubah_oleh = Column(String(36), ForeignKey("pengguna.id"), nullable=True)
    diubah_pada = Column(DateTime(timezone=True), default=waktu_sekarang_utc)

# 6. Tabel Shift Kasir
class ModelShiftKasir(BasisTabel):
    __tablename__ = "shift_kasir"

    id = Column(String(36), primary_key=True) # UUID buatan klien
    id_toko = Column(String(36), ForeignKey("toko.id"), nullable=False, index=True)
    id_kasir = Column(String(36), ForeignKey("pengguna.id"), nullable=False, index=True)
    dibuka_pada = Column(DateTime(timezone=True), default=waktu_sekarang_utc)
    ditutup_pada = Column(DateTime(timezone=True), nullable=True)
    kas_awal = Column(BigInteger, nullable=False, default=0)
    kas_ekspektasi = Column(BigInteger, nullable=False, default=0)
    kas_fisik = Column(BigInteger, nullable=True)
    selisih = Column(BigInteger, nullable=True)
    status = Column(String(20), nullable=False, default="open") # open, closed
    catatan = Column(Text, nullable=True)
    memiliki_penjualan_bermasalah = Column(Boolean, default=False)

    kasir = relationship("ModelPengguna", foreign_keys=[id_kasir])

# 7. Tabel Penjualan
class ModelPenjualan(BasisTabel):
    __tablename__ = "penjualan"

    id = Column(String(36), primary_key=True) # UUID buatan klien (idempoten)
    id_toko = Column(String(36), ForeignKey("toko.id"), nullable=False, index=True)
    id_shift = Column(String(36), ForeignKey("shift_kasir.id"), nullable=False, index=True)
    id_kasir = Column(String(36), ForeignKey("pengguna.id"), nullable=False, index=True)
    nomor_struk = Column(String(100), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="completed") # completed, voided, partially_refunded, refunded
    subtotal = Column(BigInteger, nullable=False, default=0)
    diskon = Column(BigInteger, nullable=False, default=0)
    pajak = Column(BigInteger, nullable=False, default=0)
    pembulatan = Column(BigInteger, nullable=False, default=0)
    total = Column(BigInteger, nullable=False, default=0)
    waktu_transaksi = Column(DateTime(timezone=True), nullable=False, index=True) # waktu pada perangkat klien
    waktu_sinkron = Column(DateTime(timezone=True), default=waktu_sekarang_utc)
    hash_payload = Column(String(64), nullable=False)
    flag = Column(Text, nullable=True) # JSON: negative_stock, price_mismatch, total_mismatch, clock_skew
    
    # Kolom Void
    dibatalkan_oleh = Column(String(36), ForeignKey("pengguna.id"), nullable=True)
    dibatalkan_pada = Column(DateTime(timezone=True), nullable=True)
    alasan_batal = Column(Text, nullable=True)

    items = relationship("ModelItemPenjualan", back_populates="penjualan", cascade="all, delete-orphan")
    pembayaran = relationship("ModelPembayaran", back_populates="penjualan", cascade="all, delete-orphan")
    kasir = relationship("ModelPengguna", foreign_keys=[id_kasir])

    __table_args__ = (
        UniqueConstraint("id_toko", "nomor_struk", name="uq_penjualan_toko_struk"),
        Index("idx_penjualan_toko_waktu", "id_toko", "waktu_transaksi"),
    )

# 8. Tabel Item Penjualan
class ModelItemPenjualan(BasisTabel):
    __tablename__ = "item_penjualan"

    id = Column(String(36), primary_key=True, default=buat_uuid)
    id_penjualan = Column(String(36), ForeignKey("penjualan.id"), nullable=False, index=True)
    id_produk = Column(String(36), ForeignKey("produk.id"), nullable=False, index=True)
    nama_produk_snapshot = Column(String(200), nullable=False)
    harga_snapshot = Column(BigInteger, nullable=False)
    kuantitas = Column(Integer, nullable=False)
    alokasi_diskon = Column(BigInteger, nullable=False, default=0)
    subtotal_baris = Column(BigInteger, nullable=False)

    penjualan = relationship("ModelPenjualan", back_populates="items")
    produk = relationship("ModelProduk")

# 9. Tabel Pembayaran
class ModelPembayaran(BasisTabel):
    __tablename__ = "pembayaran"

    id = Column(String(36), primary_key=True, default=buat_uuid)
    id_penjualan = Column(String(36), ForeignKey("penjualan.id"), nullable=False, index=True)
    metode = Column(String(50), nullable=False) # tunai, qris, transfer
    jumlah = Column(BigInteger, nullable=False)
    diterima = Column(BigInteger, nullable=False)
    kembalian = Column(BigInteger, nullable=False, default=0)

    penjualan = relationship("ModelPenjualan", back_populates="pembayaran")

# 10. Tabel Retur Penjualan
class ModelReturPenjualan(BasisTabel):
    __tablename__ = "retur_penjualan"

    id = Column(String(36), primary_key=True) # UUID buatan klien (idempoten)
    id_penjualan = Column(String(36), ForeignKey("penjualan.id"), nullable=False, index=True)
    id_shift = Column(String(36), ForeignKey("shift_kasir.id"), nullable=False, index=True)
    alasan = Column(Text, nullable=False)
    metode_pengembalian = Column(String(50), nullable=False) # tunai, transfer
    total_pengembalian = Column(BigInteger, nullable=False)
    dibuat_oleh = Column(String(36), ForeignKey("pengguna.id"), nullable=False)
    dibuat_pada = Column(DateTime(timezone=True), default=waktu_sekarang_utc)

    items = relationship("ModelItemRetur", back_populates="retur", cascade="all, delete-orphan")

# 11. Tabel Item Retur
class ModelItemRetur(BasisTabel):
    __tablename__ = "item_retur"

    id = Column(String(36), primary_key=True, default=buat_uuid)
    id_retur = Column(String(36), ForeignKey("retur_penjualan.id"), nullable=False, index=True)
    id_produk = Column(String(36), ForeignKey("produk.id"), nullable=False)
    kuantitas = Column(Integer, nullable=False)
    apakah_stok_kembali = Column(Boolean, default=True, nullable=False) # restock (jika barang tidak rusak)
    jumlah_pengembalian = Column(BigInteger, nullable=False)

    retur = relationship("ModelReturPenjualan", back_populates="items")

# 12. Tabel Pergerakan Stok (Audit Ledger Stok)
class ModelPergerakanStok(BasisTabel):
    __tablename__ = "pergerakan_stok"

    id = Column(String(36), primary_key=True, default=buat_uuid)
    id_toko = Column(String(36), ForeignKey("toko.id"), nullable=False, index=True)
    id_produk = Column(String(36), ForeignKey("produk.id"), nullable=False, index=True)
    perubahan_stok = Column(Integer, nullable=False) # delta (+ / -)
    tipe = Column(String(30), nullable=False) # initial, sale, void, return, receive, adjust, opname
    id_referensi = Column(String(36), nullable=True) # id_penjualan, id_retur, dll
    alasan = Column(String(255), nullable=True)
    dibuat_oleh = Column(String(36), ForeignKey("pengguna.id"), nullable=True)
    dibuat_pada = Column(DateTime(timezone=True), default=waktu_sekarang_utc, index=True)

    __table_args__ = (
        Index("idx_pergerakan_produk_waktu", "id_produk", "dibuat_pada"),
    )

# 13. Tabel Catatan Audit (Append-Only)
class ModelCatatanAudit(BasisTabel):
    __tablename__ = "catatan_audit"

    id = Column(String(36), primary_key=True, default=buat_uuid)
    id_toko = Column(String(36), ForeignKey("toko.id"), nullable=False, index=True)
    id_aktor = Column(String(36), ForeignKey("pengguna.id"), nullable=True)
    aksi = Column(String(100), nullable=False)
    entitas = Column(String(50), nullable=False)
    id_entitas = Column(String(36), nullable=True)
    rincian = Column(Text, nullable=True)
    dibuat_pada = Column(DateTime(timezone=True), default=waktu_sekarang_utc)
