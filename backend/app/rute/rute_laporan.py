from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import json
import csv
import io

from app.basis_data import dapatkan_sesi_db
from app.model.entitas import (
    ModelPenjualan,
    ModelItemPenjualan,
    ModelPembayaran,
    ModelReturPenjualan,
    ModelProduk,
    ModelShiftKasir,
    ModelPengguna
)
from app.skema.skema_laporan import (
    RingkasanHarian,
    LaporanPerProduk,
    LaporanPerMetodeBayar,
    LaporanPerKasir,
    LaporanStokMenipis,
    LaporanTransaksiBerflag
)
from app.keamanan.autentikasi import dapatkan_pengguna_saat_ini, wajib_peran

router = APIRouter(prefix="/reports", tags=["Laporan Bisnis & Analitik"])

@router.get("/summary", response_model=RingkasanHarian)
async def ringkasan_harian(
    dari_tanggal: Optional[datetime] = Query(None),
    sampai_tanggal: Optional[datetime] = Query(None),
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-12: Ringkasan pendapatan harian dan omzet bersih
    Definisi: Omzet bersih = Σ total sale (completed & partially_refunded) - Σ refund. Sale voided tidak dihitung.
    """
    kondisi_penjualan = [
        ModelPenjualan.id_toko == pengguna.id_toko,
        ModelPenjualan.status.in_(["completed", "partially_refunded"])
    ]
    if dari_tanggal:
        kondisi_penjualan.append(ModelPenjualan.waktu_transaksi >= dari_tanggal)
    if sampai_tanggal:
        kondisi_penjualan.append(ModelPenjualan.waktu_transaksi <= sampai_tanggal)

    # Ambil transaksi valid
    kueri = select(ModelPenjualan).where(and_(*kondisi_penjualan))
    daftar_penjualan = (await sesi.execute(kueri)).scalars().all()

    total_subtotal = sum(p.subtotal for p in daftar_penjualan)
    total_diskon = sum(p.diskon for p in daftar_penjualan)
    total_pajak = sum(p.pajak for p in daftar_penjualan)
    total_kotor = sum(p.total for p in daftar_penjualan)

    # Ambil refund dalam periode
    kondisi_retur = []
    id_penjualan_list = [p.id for p in daftar_penjualan]
    if id_penjualan_list:
        kondisi_retur.append(ModelReturPenjualan.id_penjualan.in_(id_penjualan_list))
    else:
        kondisi_retur.append(ModelReturPenjualan.id == "") # kosong

    kueri_refund = select(func.coalesce(func.sum(ModelReturPenjualan.total_pengembalian), 0)).where(
        and_(*kondisi_retur)
    )
    total_refund = (await sesi.execute(kueri_refund)).scalar_one()

    # Hitung voided
    kondisi_void = [
        ModelPenjualan.id_toko == pengguna.id_toko,
        ModelPenjualan.status == "voided"
    ]
    if dari_tanggal:
        kondisi_void.append(ModelPenjualan.waktu_transaksi >= dari_tanggal)
    if sampai_tanggal:
        kondisi_void.append(ModelPenjualan.waktu_transaksi <= sampai_tanggal)

    kueri_void = select(func.count(ModelPenjualan.id)).where(and_(*kondisi_void))
    total_void = (await sesi.execute(kueri_void)).scalar_one()

    # Hitung retur transaksi count
    total_transaksi_retur = sum(1 for p in daftar_penjualan if p.status == "partially_refunded")

    omzet_bersih = total_kotor - total_refund

    tgl_mulai_str = dari_tanggal.strftime("%Y-%m-%d %H:%M") if dari_tanggal else "Awal"
    tgl_selesai_str = sampai_tanggal.strftime("%Y-%m-%d %H:%M") if sampai_tanggal else "Sekarang"

    return RingkasanHarian(
        tanggal_mulai=tgl_mulai_str,
        tanggal_selesai=tgl_selesai_str,
        total_omzet_kotor=total_kotor,
        total_diskon=total_diskon,
        total_pajak=total_pajak,
        total_refund=total_refund,
        omzet_bersih=omzet_bersih,
        total_transaksi_berhasil=len(daftar_penjualan),
        total_transaksi_batal=total_void,
        total_transaksi_retur=total_transaksi_retur
    )

@router.get("/products", response_model=List[LaporanPerProduk])
async def laporan_per_produk(
    dari_tanggal: Optional[datetime] = Query(None),
    sampai_tanggal: Optional[datetime] = Query(None),
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-12: Laporan penjualan per produk terlaris
    """
    kondisi = [
        ModelPenjualan.id_toko == pengguna.id_toko,
        ModelPenjualan.status.in_(["completed", "partially_refunded"])
    ]
    if dari_tanggal:
        kondisi.append(ModelPenjualan.waktu_transaksi >= dari_tanggal)
    if sampai_tanggal:
        kondisi.append(ModelPenjualan.waktu_transaksi <= sampai_tanggal)

    kueri = select(
        ModelItemPenjualan.id_produk,
        ModelItemPenjualan.nama_produk_snapshot,
        func.sum(ModelItemPenjualan.kuantitas).label("total_qty"),
        func.sum(ModelItemPenjualan.subtotal_baris).label("total_nominal")
    ).join(ModelPenjualan, ModelItemPenjualan.id_penjualan == ModelPenjualan.id).where(
        and_(*kondisi)
    ).group_by(
        ModelItemPenjualan.id_produk,
        ModelItemPenjualan.nama_produk_snapshot
    ).order_by(func.sum(ModelItemPenjualan.kuantitas).desc())

    hasil = (await sesi.execute(kueri)).all()

    laporan = []
    for baris in hasil:
        # Cari SKU produk
        kueri_p = select(ModelProduk.sku).where(ModelProduk.id == baris[0])
        sku = (await sesi.execute(kueri_p)).scalar_one_or_none() or "-"

        laporan.append(LaporanPerProduk(
            id_produk=baris[0],
            nama_produk=baris[1],
            sku=sku,
            total_kuantitas=baris[2] or 0,
            total_pendapatan=baris[3] or 0
        ))
    return laporan

@router.get("/payments", response_model=List[LaporanPerMetodeBayar])
async def laporan_per_metode_bayar(
    dari_tanggal: Optional[datetime] = Query(None),
    sampai_tanggal: Optional[datetime] = Query(None),
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-12: Laporan penjualan per metode bayar (Tunai, QRIS, Transfer)
    """
    kondisi = [
        ModelPenjualan.id_toko == pengguna.id_toko,
        ModelPenjualan.status.in_(["completed", "partially_refunded"])
    ]
    if dari_tanggal:
        kondisi.append(ModelPenjualan.waktu_transaksi >= dari_tanggal)
    if sampai_tanggal:
        kondisi.append(ModelPenjualan.waktu_transaksi <= sampai_tanggal)

    kueri = select(
        ModelPembayaran.metode,
        func.sum(ModelPembayaran.jumlah).label("total_nominal"),
        func.count(ModelPembayaran.id).label("jumlah_transaksi")
    ).join(ModelPenjualan, ModelPembayaran.id_penjualan == ModelPenjualan.id).where(
        and_(*kondisi)
    ).group_by(ModelPembayaran.metode)

    hasil = (await sesi.execute(kueri)).all()
    return [
        LaporanPerMetodeBayar(
            metode=baris[0],
            total_nominal=baris[1] or 0,
            jumlah_transaksi=baris[2] or 0
        ) for baris in hasil
    ]

@router.get("/cashiers", response_model=List[LaporanPerKasir])
async def laporan_per_kasir(
    dari_tanggal: Optional[datetime] = Query(None),
    sampai_tanggal: Optional[datetime] = Query(None),
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-12: Rekapitulasi performa penjualan per kasir
    """
    kondisi = [
        ModelPenjualan.id_toko == pengguna.id_toko,
        ModelPenjualan.status.in_(["completed", "partially_refunded"])
    ]
    if dari_tanggal:
        kondisi.append(ModelPenjualan.waktu_transaksi >= dari_tanggal)
    if sampai_tanggal:
        kondisi.append(ModelPenjualan.waktu_transaksi <= sampai_tanggal)

    kueri = select(
        ModelPenjualan.id_kasir,
        ModelPengguna.nama_lengkap,
        func.count(ModelPenjualan.id).label("total_transaksi"),
        func.sum(ModelPenjualan.total).label("total_omzet")
    ).join(ModelPengguna, ModelPenjualan.id_kasir == ModelPengguna.id).where(
        and_(*kondisi)
    ).group_by(ModelPenjualan.id_kasir, ModelPengguna.nama_lengkap)

    hasil = (await sesi.execute(kueri)).all()
    return [
        LaporanPerKasir(
            id_kasir=b[0],
            nama_kasir=b[1],
            total_transaksi=b[2] or 0,
            total_omzet=b[3] or 0
        ) for b in hasil
    ]

@router.get("/low-stock", response_model=List[LaporanStokMenipis])
async def laporan_stok_menipis(
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-12: Laporan produk dengan stok menipis (stok <= min_stok)
    """
    kueri = select(ModelProduk).where(
        ModelProduk.id_toko == pengguna.id_toko,
        ModelProduk.apakah_dihapus == False,
        ModelProduk.status_aktif == True,
        ModelProduk.stok <= ModelProduk.min_stok
    ).order_by(ModelProduk.stok.asc())

    hasil = (await sesi.execute(kueri)).scalars().all()
    return [
        LaporanStokMenipis(
            id_produk=p.id,
            nama_produk=p.nama,
            sku=p.sku,
            stok_sekarang=p.stok,
            min_stok=p.min_stok,
            kategori=p.kategori
        ) for p in hasil
    ]

@router.get("/flagged", response_model=List[LaporanTransaksiBerflag])
async def laporan_transaksi_berflag(
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-12: Transaksi berflag anomali (negative_stock, price_mismatch, total_mismatch, clock_skew)
    """
    kueri = select(ModelPenjualan).where(
        ModelPenjualan.id_toko == pengguna.id_toko,
        ModelPenjualan.flag.is_not(None),
        ModelPenjualan.flag != "{}",
        ModelPenjualan.flag != ""
    ).order_by(ModelPenjualan.waktu_transaksi.desc())

    hasil = (await sesi.execute(kueri)).scalars().all()
    
    laporan = []
    for s in hasil:
        kueri_k = select(ModelPengguna.nama_lengkap).where(ModelPengguna.id == s.id_kasir)
        nama_kasir = (await sesi.execute(kueri_k)).scalar_one_or_none() or "Kasir"

        laporan.append(LaporanTransaksiBerflag(
            id=s.id,
            nomor_struk=s.nomor_struk,
            nama_kasir=nama_kasir,
            total=s.total,
            waktu_transaksi=s.waktu_transaksi,
            flag=json.loads(s.flag) if s.flag else {},
            status=s.status
        ))
    return laporan

@router.get("/export/csv")
async def ekspor_laporan_csv(
    tipe: str = Query("penjualan", pattern="^(penjualan|produk|stok_menipis)$"),
    dari_tanggal: Optional[datetime] = Query(None),
    sampai_tanggal: Optional[datetime] = Query(None),
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-12: Ekspor data laporan ke format CSV
    """
    output = io.StringIO()
    penulis = csv.writer(output)

    if tipe == "penjualan":
        penulis.writerow(["Nomor Struk", "Waktu Transaksi", "Total", "Status", "Flags"])
        kueri = select(ModelPenjualan).where(ModelPenjualan.id_toko == pengguna.id_toko)
        if dari_tanggal:
            kueri = kueri.where(ModelPenjualan.waktu_transaksi >= dari_tanggal)
        if sampai_tanggal:
            kueri = kueri.where(ModelPenjualan.waktu_transaksi <= sampai_tanggal)
        for row in (await sesi.execute(kueri.order_by(ModelPenjualan.waktu_transaksi.desc()))).scalars().all():
            penulis.writerow([row.nomor_struk, row.waktu_transaksi.isoformat(), row.total, row.status, row.flag or ""])
    elif tipe == "produk":
        penulis.writerow(["SKU", "Barcode", "Nama Produk", "Kategori", "Harga", "Harga Modal", "Stok", "Min Stok"])
        kueri = select(ModelProduk).where(ModelProduk.id_toko == pengguna.id_toko, ModelProduk.apakah_dihapus == False)
        for p in (await sesi.execute(kueri.order_by(ModelProduk.nama.asc()))).scalars().all():
            penulis.writerow([p.sku, p.barcode or "", p.nama, p.kategori or "", p.harga, p.harga_modal, p.stok, p.min_stok])
    elif tipe == "stok_menipis":
        penulis.writerow(["SKU", "Nama Produk", "Stok Sekarang", "Min Stok", "Kategori"])
        kueri = select(ModelProduk).where(
            ModelProduk.id_toko == pengguna.id_toko,
            ModelProduk.apakah_dihapus == False,
            ModelProduk.stok <= ModelProduk.min_stok
        )
        for p in (await sesi.execute(kueri)).scalars().all():
            penulis.writerow([p.sku, p.nama, p.stok, p.min_stok, p.kategori or ""])

    konten_csv = output.getvalue()
    return Response(
        content=konten_csv,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=laporan_{tipe}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"}
    )
