from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import List

from app.basis_data import dapatkan_sesi_db
from app.model.entitas import (
    ModelReturPenjualan,
    ModelItemRetur,
    ModelPenjualan,
    ModelItemPenjualan,
    ModelProduk,
    ModelPergerakanStok,
    ModelShiftKasir,
    ModelCatatanAudit,
    ModelPengguna,
    waktu_sekarang_utc
)
from app.skema.skema_retur import (
    InputReturPenjualan,
    ResponsReturPenjualan,
    ResponsItemRetur
)
from app.keamanan.autentikasi import dapatkan_pengguna_saat_ini, wajib_peran

router = APIRouter(prefix="/returns", tags=["Retur Penjualan"])

@router.post("", response_model=ResponsReturPenjualan, status_code=status.HTTP_201_CREATED)
async def proses_retur(
    permintaan: InputReturPenjualan,
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-08: Pengajuan Retur Penjualan (Khusus Manajer/Owner, Idempoten berdasarkan UUID)
    """
    # 1. Cek idempotensi
    kueri_ada = select(ModelReturPenjualan).where(
        ModelReturPenjualan.id == permintaan.id
    ).options(selectinload(ModelReturPenjualan.items))
    retur_ada = (await sesi.execute(kueri_ada)).scalar_one_or_none()
    if retur_ada:
        return ResponsReturPenjualan(
            id=retur_ada.id,
            id_penjualan=retur_ada.id_penjualan,
            id_shift=retur_ada.id_shift,
            alasan=retur_ada.alasan,
            metode_pengembalian=retur_ada.metode_pengembalian,
            total_pengembalian=retur_ada.total_pengembalian,
            dibuat_oleh=retur_ada.dibuat_oleh,
            dibuat_pada=retur_ada.dibuat_pada,
            item=retur_ada.items
        )

    # 2. Ambil data transaksi penjualan
    kueri_penjualan = select(ModelPenjualan).where(
        ModelPenjualan.id == permintaan.id_penjualan,
        ModelPenjualan.id_toko == pengguna.id_toko
    ).options(selectinload(ModelPenjualan.items))
    penjualan = (await sesi.execute(kueri_penjualan)).scalar_one_or_none()

    if not penjualan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Transaksi penjualan asal tidak ditemukan."}
        )

    if penjualan.status == "voided":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ALREADY_VOIDED", "message": "Transaksi yang sudah di-void tidak dapat diretur."}
        )

    # 3. Cek shift aktif jika pengembalian tunai
    kueri_shift = select(ModelShiftKasir).where(ModelShiftKasir.id == permintaan.id_shift)
    shift = (await sesi.execute(kueri_shift)).scalar_one_or_none()
    if not shift or shift.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "NO_OPEN_SHIFT", "message": "Shift kasir yang dipilih harus dalam status terbuka untuk mencatat pengeluaran refund."}
        )

    # 4. Ambil riwayat retur sebelumnya untuk transaksi ini
    kueri_retur_lama = select(ModelItemRetur).join(ModelReturPenjualan).where(
        ModelReturPenjualan.id_penjualan == penjualan.id
    )
    items_retur_lama = (await sesi.execute(kueri_retur_lama)).scalars().all()
    kuantitas_teretur: dict[str, int] = {}
    for ir in items_retur_lama:
        kuantitas_teretur[ir.id_produk] = kuantitas_teretur.get(ir.id_produk, 0) + ir.kuantitas

    # Peta item penjualan
    peta_item_penjualan = {it.id_produk: it for it in penjualan.items}

    total_refund_akumulasi = 0
    items_retur_entitas = []

    for it_req in permintaan.item:
        if it_req.id_produk not in peta_item_penjualan:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "INVALID_PRODUCT", "message": f"Produk ID '{it_req.id_produk}' tidak ada dalam transaksi ini."}
            )

        item_asli = peta_item_penjualan[it_req.id_produk]
        sudah_retur = kuantitas_teretur.get(it_req.id_produk, 0)
        sisa_bisa_retur = item_asli.kuantitas - sudah_retur

        if it_req.kuantitas > sisa_bisa_retur:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "RETURN_QTY_EXCEEDED",
                    "message": f"Jumlah retur ({it_req.kuantitas}) melebihi sisa kuota yang bisa diretur ({sisa_bisa_retur}) untuk produk {item_asli.nama_produk_snapshot}."
                }
            )

        # Hitung refund proposional: (subtotal_baris // kuantitas_asli) * qty_retur
        nilai_refund_satuan = item_asli.subtotal_baris // item_asli.kuantitas
        nilai_refund_item = nilai_refund_satuan * it_req.kuantitas
        total_refund_akumulasi += nilai_refund_item

        entitas_item = ModelItemRetur(
            id_retur=permintaan.id,
            id_produk=it_req.id_produk,
            kuantitas=it_req.kuantitas,
            apakah_stok_kembali=it_req.apakah_stok_kembali,
            jumlah_pengembalian=nilai_refund_item
        )
        items_retur_entitas.append(entitas_item)

        # Jika restock (barang bagus): tambahkan stok dan catat pergerakan stok
        if it_req.apakah_stok_kembali:
            kueri_prod = select(ModelProduk).where(ModelProduk.id == it_req.id_produk)
            produk_db = (await sesi.execute(kueri_prod)).scalar_one_or_none()
            if produk_db:
                produk_db.stok += it_req.kuantitas
                pergerakan = ModelPergerakanStok(
                    id_toko=pengguna.id_toko,
                    id_produk=produk_db.id,
                    perubahan_stok=it_req.kuantitas,
                    tipe="return",
                    id_referensi=permintaan.id,
                    alasan=f"Retur struk {penjualan.nomor_struk}: {permintaan.alasan}",
                    dibuat_oleh=pengguna.id
                )
                sesi.add(pergerakan)

    # Simpan entitas retur
    retur_baru = ModelReturPenjualan(
        id=permintaan.id,
        id_penjualan=penjualan.id,
        id_shift=permintaan.id_shift,
        alasan=permintaan.alasan,
        metode_pengembalian=permintaan.metode_pengembalian,
        total_pengembalian=total_refund_akumulasi,
        dibuat_oleh=pengguna.id,
        dibuat_pada=waktu_sekarang_utc()
    )
    sesi.add(retur_baru)
    for ir_entitas in items_retur_entitas:
        sesi.add(ir_entitas)

    # Periksa apakah seluruh transaksi sudah diretur sepenuhnya
    total_qty_asli = sum(it.kuantitas for it in penjualan.items)
    total_qty_retur_total = sum(kuantitas_teretur.values()) + sum(it.kuantitas for it in permintaan.item)

    if total_qty_retur_total >= total_qty_asli:
        penjualan.status = "refunded"
    else:
        penjualan.status = "partially_refunded"

    audit = ModelCatatanAudit(
        id_toko=pengguna.id_toko,
        id_aktor=pengguna.id,
        aksi="RETUR_PENJUALAN",
        entitas="retur",
        id_entitas=retur_baru.id,
        rincian=f"Retur struk {penjualan.nomor_struk} senilai Rp {total_refund_akumulasi:,} diproses oleh {pengguna.nama_pengguna}. Alasan: {permintaan.alasan}"
    )
    sesi.add(audit)
    await sesi.commit()

    return ResponsReturPenjualan(
        id=retur_baru.id,
        id_penjualan=retur_baru.id_penjualan,
        id_shift=retur_baru.id_shift,
        alasan=retur_baru.alasan,
        metode_pengembalian=retur_baru.metode_pengembalian,
        total_pengembalian=retur_baru.total_pengembalian,
        dibuat_oleh=retur_baru.dibuat_oleh,
        dibuat_pada=retur_baru.dibuat_pada,
        item=items_retur_entitas
    )

@router.get("", response_model=List[ResponsReturPenjualan])
async def daftar_retur(
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Mengambil riwayat semua retur penjualan toko
    """
    kueri = select(ModelReturPenjualan).join(ModelPenjualan).where(
        ModelPenjualan.id_toko == pengguna.id_toko
    ).order_by(ModelReturPenjualan.dibuat_pada.desc()).options(selectinload(ModelReturPenjualan.items))

    daftar = (await sesi.execute(kueri)).scalars().all()
    return daftar
