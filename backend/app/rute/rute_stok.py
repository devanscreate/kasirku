from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List

from app.basis_data import dapatkan_sesi_db
from app.model.entitas import (
    ModelProduk,
    ModelPergerakanStok,
    ModelCatatanAudit,
    ModelPengguna,
    waktu_sekarang_utc
)
from app.skema.skema_stok import (
    PermintaanTerimaStok,
    PermintaanSesuaikanStok,
    PermintaanOpnameStok,
    ResponsPergerakanStok
)
from app.keamanan.autentikasi import dapatkan_pengguna_saat_ini, wajib_peran

router = APIRouter(prefix="/stock", tags=["Manajemen Stok"])

@router.post("/receive", response_model=ResponsPergerakanStok, status_code=status.HTTP_201_CREATED)
async def terima_barang_masuk(
    permintaan: PermintaanTerimaStok,
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-11: Penerimaan barang masuk dari supplier (receive)
    """
    kueri = select(ModelProduk).where(
        ModelProduk.id == permintaan.id_produk,
        ModelProduk.id_toko == pengguna.id_toko,
        ModelProduk.apakah_dihapus == False
    )
    produk = (await sesi.execute(kueri)).scalar_one_or_none()
    if not produk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Produk tidak ditemukan"}
        )

    # Tambah stok dan opsional perbarui harga modal
    produk.stok += permintaan.kuantitas
    if permintaan.harga_modal is not None:
        produk.harga_modal = permintaan.harga_modal
    produk.diperbarui_pada = waktu_sekarang_utc()

    pergerakan = ModelPergerakanStok(
        id_toko=pengguna.id_toko,
        id_produk=produk.id,
        perubahan_stok=permintaan.kuantitas,
        tipe="receive",
        alasan=permintaan.catatan or "Penerimaan barang dari supplier",
        dibuat_oleh=pengguna.id,
        dibuat_pada=waktu_sekarang_utc()
    )
    sesi.add(pergerakan)

    audit = ModelCatatanAudit(
        id_toko=pengguna.id_toko,
        id_aktor=pengguna.id,
        aksi="TERIMA_BARANG",
        entitas="produk",
        id_entitas=produk.id,
        rincian=f"Penerimaan {permintaan.kuantitas} unit {produk.nama} oleh {pengguna.nama_pengguna}"
    )
    sesi.add(audit)
    await sesi.commit()
    await sesi.refresh(pergerakan)

    return ResponsPergerakanStok(
        id=pergerakan.id,
        id_toko=pergerakan.id_toko,
        id_produk=pergerakan.id_produk,
        nama_produk=produk.nama,
        perubahan_stok=pergerakan.perubahan_stok,
        tipe=pergerakan.tipe,
        id_referensi=pergerakan.id_referensi,
        alasan=pergerakan.alasan,
        dibuat_oleh=pengguna.nama_lengkap,
        dibuat_pada=pergerakan.dibuat_pada
    )

@router.post("/adjust", response_model=ResponsPergerakanStok, status_code=status.HTTP_201_CREATED)
async def sesuaikan_stok(
    permintaan: PermintaanSesuaikanStok,
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-11: Penyesuaian stok delta (+/-) dengan alasan wajib (rusak, hilang, koreksi)
    """
    kueri = select(ModelProduk).where(
        ModelProduk.id == permintaan.id_produk,
        ModelProduk.id_toko == pengguna.id_toko,
        ModelProduk.apakah_dihapus == False
    )
    produk = (await sesi.execute(kueri)).scalar_one_or_none()
    if not produk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Produk tidak ditemukan"}
        )

    produk.stok += permintaan.perubahan_stok
    produk.diperbarui_pada = waktu_sekarang_utc()

    pergerakan = ModelPergerakanStok(
        id_toko=pengguna.id_toko,
        id_produk=produk.id,
        perubahan_stok=permintaan.perubahan_stok,
        tipe="adjust",
        alasan=permintaan.alasan,
        dibuat_oleh=pengguna.id,
        dibuat_pada=waktu_sekarang_utc()
    )
    sesi.add(pergerakan)

    audit = ModelCatatanAudit(
        id_toko=pengguna.id_toko,
        id_aktor=pengguna.id,
        aksi="SESUAIKAN_STOK",
        entitas="produk",
        id_entitas=produk.id,
        rincian=f"Penyesuaian stok {produk.nama} ({permintaan.perubahan_stok:+d}) oleh {pengguna.nama_pengguna}. Alasan: {permintaan.alasan}"
    )
    sesi.add(audit)
    await sesi.commit()
    await sesi.refresh(pergerakan)

    return ResponsPergerakanStok(
        id=pergerakan.id,
        id_toko=pergerakan.id_toko,
        id_produk=pergerakan.id_produk,
        nama_produk=produk.nama,
        perubahan_stok=pergerakan.perubahan_stok,
        tipe=pergerakan.tipe,
        id_referensi=pergerakan.id_referensi,
        alasan=pergerakan.alasan,
        dibuat_oleh=pengguna.nama_lengkap,
        dibuat_pada=pergerakan.dibuat_pada
    )

@router.post("/opname", response_model=ResponsPergerakanStok, status_code=status.HTTP_201_CREATED)
async def opname_stok_fisik(
    permintaan: PermintaanOpnameStok,
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-11: Stock opname fisik, mencocokkan stok fisik nyata dengan sistem
    """
    kueri = select(ModelProduk).where(
        ModelProduk.id == permintaan.id_produk,
        ModelProduk.id_toko == pengguna.id_toko,
        ModelProduk.apakah_dihapus == False
    )
    produk = (await sesi.execute(kueri)).scalar_one_or_none()
    if not produk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Produk tidak ditemukan"}
        )

    delta = permintaan.stok_fisik - produk.stok
    produk.stok = permintaan.stok_fisik
    produk.diperbarui_pada = waktu_sekarang_utc()

    pergerakan = ModelPergerakanStok(
        id_toko=pengguna.id_toko,
        id_produk=produk.id,
        perubahan_stok=delta,
        tipe="opname",
        alasan=permintaan.alasan or "Opname stok fisik toko",
        dibuat_oleh=pengguna.id,
        dibuat_pada=waktu_sekarang_utc()
    )
    sesi.add(pergerakan)

    audit = ModelCatatanAudit(
        id_toko=pengguna.id_toko,
        id_aktor=pengguna.id,
        aksi="OPNAME_STOK",
        entitas="produk",
        id_entitas=produk.id,
        rincian=f"Opname stok {produk.nama} diset menjadi {permintaan.stok_fisik} (selisih: {delta:+d}) oleh {pengguna.nama_pengguna}"
    )
    sesi.add(audit)
    await sesi.commit()
    await sesi.refresh(pergerakan)

    return ResponsPergerakanStok(
        id=pergerakan.id,
        id_toko=pergerakan.id_toko,
        id_produk=pergerakan.id_produk,
        nama_produk=produk.nama,
        perubahan_stok=pergerakan.perubahan_stok,
        tipe=pergerakan.tipe,
        id_referensi=pergerakan.id_referensi,
        alasan=pergerakan.alasan,
        dibuat_oleh=pengguna.nama_lengkap,
        dibuat_pada=pergerakan.dibuat_pada
    )

@router.get("/movements", response_model=List[ResponsPergerakanStok])
async def riwayat_pergerakan_stok(
    id_produk: Optional[str] = Query(None),
    tipe: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Mengambil buku besar (ledger) riwayat pergerakan stok
    """
    kondisi = [ModelPergerakanStok.id_toko == pengguna.id_toko]
    if id_produk:
        kondisi.append(ModelPergerakanStok.id_produk == id_produk)
    if tipe:
        kondisi.append(ModelPergerakanStok.tipe == tipe)

    kueri = select(ModelPergerakanStok).where(and_(*kondisi)).order_by(
        ModelPergerakanStok.dibuat_pada.desc()
    ).limit(limit)

    hasil = (await sesi.execute(kueri)).scalars().all()
    
    # Ambil nama produk untuk kemudahan visualisasi
    daftar_id_produk = list({m.id_produk for m in hasil})
    peta_nama = {}
    if daftar_id_produk:
        kueri_p = select(ModelProduk.id, ModelProduk.nama).where(ModelProduk.id.in_(daftar_id_produk))
        for pid, pnama in (await sesi.execute(kueri_p)).all():
            peta_nama[pid] = pnama

    hasil_format = []
    for m in hasil:
        hasil_format.append(ResponsPergerakanStok(
            id=m.id,
            id_toko=m.id_toko,
            id_produk=m.id_produk,
            nama_produk=peta_nama.get(m.id_produk, "Produk"),
            perubahan_stok=m.perubahan_stok,
            tipe=m.tipe,
            id_referensi=m.id_referensi,
            alasan=m.alasan,
            dibuat_oleh=m.dibuat_oleh,
            dibuat_pada=m.dibuat_pada
        ))
    return hasil_format
