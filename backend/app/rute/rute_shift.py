from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional, List

from app.basis_data import dapatkan_sesi_db
from app.model.entitas import (
    ModelShiftKasir,
    ModelPenjualan,
    ModelPembayaran,
    ModelReturPenjualan,
    ModelCatatanAudit,
    ModelPengguna,
    waktu_sekarang_utc
)
from app.skema.skema_shift import (
    PermintaanBukaShift,
    PermintaanTutupShift,
    ResponsShift,
    RingkasanTutupShift
)
from app.keamanan.autentikasi import dapatkan_pengguna_saat_ini, wajib_peran

router = APIRouter(prefix="/shifts", tags=["Shift Kasir"])

@router.post("/open", response_model=ResponsShift)
async def buka_shift(
    permintaan: PermintaanBukaShift,
    pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-02: Buka Shift Kasir (Idempoten berdasarkan UUID shift_id)
    """
    # 1. Cek apakah shift dengan id tersebut sudah ada (Idempotensi pengiriman outbox)
    kueri_id = select(ModelShiftKasir).where(ModelShiftKasir.id == permintaan.id)
    shift_ada = (await sesi.execute(kueri_id)).scalar_one_or_none()
    if shift_ada:
        return ResponsShift(
            id=shift_ada.id,
            id_toko=shift_ada.id_toko,
            id_kasir=shift_ada.id_kasir,
            nama_kasir=pengguna.nama_lengkap,
            dibuka_pada=shift_ada.dibuka_pada,
            ditutup_pada=shift_ada.ditutup_pada,
            kas_awal=shift_ada.kas_awal,
            kas_ekspektasi=shift_ada.kas_ekspektasi,
            kas_fisik=shift_ada.kas_fisik,
            selisih=shift_ada.selisih,
            status=shift_ada.status,
            catatan=shift_ada.catatan,
            memiliki_penjualan_bermasalah=shift_ada.memiliki_penjualan_bermasalah
        )

    # 2. Cek apakah kasir ini sudah punya shift lain yang masih berstatus 'open'
    kueri_aktif = select(ModelShiftKasir).where(
        ModelShiftKasir.id_toko == pengguna.id_toko,
        ModelShiftKasir.id_kasir == pengguna.id,
        ModelShiftKasir.status == "open"
    )
    shift_sedang_buka = (await sesi.execute(kueri_aktif)).scalar_one_or_none()
    if shift_sedang_buka:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "SHIFT_ALREADY_OPEN",
                "message": "Anda masih memiliki shift yang belum ditutup. Silakan lanjutkan shift tersebut atau tutup terlebih dahulu.",
                "shift_id": shift_sedang_buka.id
            }
        )

    shift_baru = ModelShiftKasir(
        id=permintaan.id,
        id_toko=pengguna.id_toko,
        id_kasir=pengguna.id,
        kas_awal=permintaan.kas_awal,
        kas_ekspektasi=permintaan.kas_awal,
        status="open",
        dibuka_pada=waktu_sekarang_utc()
    )
    sesi.add(shift_baru)

    audit = ModelCatatanAudit(
        id_toko=pengguna.id_toko,
        id_aktor=pengguna.id,
        aksi="BUKA_SHIFT",
        entitas="shift",
        id_entitas=shift_baru.id,
        rincian=f"Kasir {pengguna.nama_pengguna} membuka shift dengan modal kas awal Rp {permintaan.kas_awal:,}"
    )
    sesi.add(audit)
    await sesi.commit()
    await sesi.refresh(shift_baru)

    return ResponsShift(
        id=shift_baru.id,
        id_toko=shift_baru.id_toko,
        id_kasir=shift_baru.id_kasir,
        nama_kasir=pengguna.nama_lengkap,
        dibuka_pada=shift_baru.dibuka_pada,
        ditutup_pada=shift_baru.ditutup_pada,
        kas_awal=shift_baru.kas_awal,
        kas_ekspektasi=shift_baru.kas_ekspektasi,
        kas_fisik=shift_baru.kas_fisik,
        selisih=shift_baru.selisih,
        status=shift_baru.status,
        catatan=shift_baru.catatan,
        memiliki_penjualan_bermasalah=shift_baru.memiliki_penjualan_bermasalah
    )

@router.get("/aktif", response_model=Optional[ResponsShift])
async def dapatkan_shift_aktif(
    pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Mengambil data shift kasir yang saat ini sedang terbuka
    """
    kueri = select(ModelShiftKasir).where(
        ModelShiftKasir.id_toko == pengguna.id_toko,
        ModelShiftKasir.id_kasir == pengguna.id,
        ModelShiftKasir.status == "open"
    )
    shift = (await sesi.execute(kueri)).scalar_one_or_none()
    if not shift:
        return None

    return ResponsShift(
        id=shift.id,
        id_toko=shift.id_toko,
        id_kasir=shift.id_kasir,
        nama_kasir=pengguna.nama_lengkap,
        dibuka_pada=shift.dibuka_pada,
        ditutup_pada=shift.ditutup_pada,
        kas_awal=shift.kas_awal,
        kas_ekspektasi=shift.kas_ekspektasi,
        kas_fisik=shift.kas_fisik,
        selisih=shift.selisih,
        status=shift.status,
        catatan=shift.catatan,
        memiliki_penjualan_bermasalah=shift.memiliki_penjualan_bermasalah
    )

@router.get("/{id_shift}/ringkasan", response_model=RingkasanTutupShift)
async def ringkasan_shift(
    id_shift: str,
    pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-09: Ringkasan penjualan dan kalkulasi kas untuk penutupan shift
    """
    kueri_shift = select(ModelShiftKasir).where(ModelShiftKasir.id == id_shift)
    shift = (await sesi.execute(kueri_shift)).scalar_one_or_none()
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Shift tidak ditemukan"}
        )

    # Ambil semua penjualan yang valid (completed atau partially_refunded)
    kueri_penjualan = select(ModelPenjualan).where(
        ModelPenjualan.id_shift == id_shift,
        ModelPenjualan.status.in_(["completed", "partially_refunded"])
    )
    daftar_penjualan = (await sesi.execute(kueri_penjualan)).scalars().all()
    id_penjualan_list = [p.id for p in daftar_penjualan]

    tunai = 0
    qris = 0
    transfer = 0

    if id_penjualan_list:
        kueri_bayar = select(ModelPembayaran).where(ModelPembayaran.id_penjualan.in_(id_penjualan_list))
        daftar_bayar = (await sesi.execute(kueri_bayar)).scalars().all()
        for b in daftar_bayar:
            if b.metode == "tunai":
                tunai += b.jumlah
            elif b.metode == "qris":
                qris += b.jumlah
            elif b.metode == "transfer":
                transfer += b.jumlah

    # Ambil refund tunai pada shift ini
    kueri_retur = select(func.coalesce(func.sum(ModelReturPenjualan.total_pengembalian), 0)).where(
        ModelReturPenjualan.id_shift == id_shift,
        ModelReturPenjualan.metode_pengembalian == "tunai"
    )
    total_refund_tunai = (await sesi.execute(kueri_retur)).scalar_one()

    kas_ekspektasi = shift.kas_awal + tunai - total_refund_tunai

    return RingkasanTutupShift(
        id_shift=shift.id,
        kas_awal=shift.kas_awal,
        total_penjualan_tunai=tunai,
        total_penjualan_qris=qris,
        total_penjualan_transfer=transfer,
        total_refund_tunai=total_refund_tunai,
        kas_ekspektasi=kas_ekspektasi,
        kas_fisik=shift.kas_fisik,
        selisih=shift.selisih,
        jumlah_transaksi=len(daftar_penjualan)
    )

@router.post("/{id_shift}/close", response_model=ResponsShift)
async def tutup_shift(
    id_shift: str,
    permintaan: PermintaanTutupShift,
    pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-09: Tutup shift kasir dan rekonsiliasi uang fisik (Otoritatif dari data server)
    """
    kueri = select(ModelShiftKasir).where(ModelShiftKasir.id == id_shift)
    shift = (await sesi.execute(kueri)).scalar_one_or_none()
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Shift tidak ditemukan"}
        )

    # Idempoten jika sudah closed
    if shift.status == "closed":
        return ResponsShift(
            id=shift.id,
            id_toko=shift.id_toko,
            id_kasir=shift.id_kasir,
            nama_kasir=pengguna.nama_lengkap,
            dibuka_pada=shift.dibuka_pada,
            ditutup_pada=shift.ditutup_pada,
            kas_awal=shift.kas_awal,
            kas_ekspektasi=shift.kas_ekspektasi,
            kas_fisik=shift.kas_fisik,
            selisih=shift.selisih,
            status=shift.status,
            catatan=shift.catatan,
            memiliki_penjualan_bermasalah=shift.memiliki_penjualan_bermasalah
        )

    # Hitung ulang kas ekspektasi dari basis data server secara otoritatif
    kueri_penjualan = select(ModelPenjualan.id).where(
        ModelPenjualan.id_shift == id_shift,
        ModelPenjualan.status.in_(["completed", "partially_refunded"])
    )
    id_penjualan_list = (await sesi.execute(kueri_penjualan)).scalars().all()

    tunai = 0
    if id_penjualan_list:
        kueri_bayar = select(func.coalesce(func.sum(ModelPembayaran.jumlah), 0)).where(
            ModelPembayaran.id_penjualan.in_(id_penjualan_list),
            ModelPembayaran.metode == "tunai"
        )
        tunai = (await sesi.execute(kueri_bayar)).scalar_one()

    kueri_retur = select(func.coalesce(func.sum(ModelReturPenjualan.total_pengembalian), 0)).where(
        ModelReturPenjualan.id_shift == id_shift,
        ModelReturPenjualan.metode_pengembalian == "tunai"
    )
    total_refund_tunai = (await sesi.execute(kueri_retur)).scalar_one()

    kas_ekspektasi = shift.kas_awal + tunai - total_refund_tunai
    selisih = permintaan.kas_fisik - kas_ekspektasi

    shift.kas_ekspektasi = kas_ekspektasi
    shift.kas_fisik = permintaan.kas_fisik
    shift.selisih = selisih
    shift.catatan = permintaan.catatan
    shift.status = "closed"
    shift.ditutup_pada = waktu_sekarang_utc()

    audit = ModelCatatanAudit(
        id_toko=shift.id_toko,
        id_aktor=pengguna.id,
        aksi="TUTUP_SHIFT",
        entitas="shift",
        id_entitas=shift.id,
        rincian=f"Shift {shift.id} ditutup oleh {pengguna.nama_pengguna}. Kas Fisik: {permintaan.kas_fisik:,}, Ekspektasi: {kas_ekspektasi:,}, Selisih: {selisih:,}"
    )
    sesi.add(audit)
    await sesi.commit()
    await sesi.refresh(shift)

    return ResponsShift(
        id=shift.id,
        id_toko=shift.id_toko,
        id_kasir=shift.id_kasir,
        nama_kasir=pengguna.nama_lengkap,
        dibuka_pada=shift.dibuka_pada,
        ditutup_pada=shift.ditutup_pada,
        kas_awal=shift.kas_awal,
        kas_ekspektasi=shift.kas_ekspektasi,
        kas_fisik=shift.kas_fisik,
        selisih=shift.selisih,
        status=shift.status,
        catatan=shift.catatan,
        memiliki_penjualan_bermasalah=shift.memiliki_penjualan_bermasalah
    )
