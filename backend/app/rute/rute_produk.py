from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import Optional, List
from datetime import datetime, timezone
import csv
import io

from app.basis_data import dapatkan_sesi_db
from app.model.entitas import (
    ModelProduk,
    ModelRiwayatHarga,
    ModelPergerakanStok,
    ModelCatatanAudit,
    ModelPengguna,
    waktu_sekarang_utc
)
from app.skema.skema_produk import (
    PermintaanBuatProduk,
    PermintaanUbahProduk,
    ResponsProduk,
    ResponsSinkronKatalog
)
from app.keamanan.autentikasi import dapatkan_pengguna_saat_ini, wajib_peran
from app.layanan.layanan_storage import (
    proses_dan_unggah_foto,
    hapus_berkas_s3,
    unggah_berkas_bytes
)
import os
import uuid

router = APIRouter(tags=["Produk & Sinkronisasi"])

@router.get("/sync/products", response_model=ResponsSinkronKatalog)
async def sinkron_katalog(
    since: Optional[datetime] = Query(None, description="Ambil produk yang diubah sejak waktu ini"),
    limit: int = Query(500, le=1000),
    cursor: Optional[str] = Query(None),
    pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-03: Sinkronisasi katalog produk untuk IndexedDB (Dexie) di frontend.
    Mengembalikan data produk yang berubah urut diperbarui_pada, id.
    """
    kondisi = [ModelProduk.id_toko == pengguna.id_toko]
    if since:
        kondisi.append(ModelProduk.diperbarui_pada >= since)

    kueri = select(ModelProduk).where(and_(*kondisi)).order_by(
        ModelProduk.diperbarui_pada.asc(),
        ModelProduk.id.asc()
    ).limit(limit + 1)

    hasil = await sesi.execute(kueri)
    daftar_produk = list(hasil.scalars().all())

    kursor_berikutnya = None
    if len(daftar_produk) > limit:
        item_terakhir = daftar_produk[limit - 1]
        kursor_berikutnya = item_terakhir.id
        daftar_produk = daftar_produk[:limit]

    return ResponsSinkronKatalog(
        produk=daftar_produk,
        kursor_berikutnya=kursor_berikutnya,
        waktu_server=waktu_sekarang_utc()
    )

@router.get("/products", response_model=List[ResponsProduk])
async def daftar_produk(
    cari: Optional[str] = Query(None),
    kategori: Optional[str] = Query(None),
    termasuk_nonaktif: bool = Query(False),
    pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Mengambil daftar produk toko aktif
    """
    kondisi = [
        ModelProduk.id_toko == pengguna.id_toko,
        ModelProduk.apakah_dihapus == False
    ]
    if not termasuk_nonaktif:
        kondisi.append(ModelProduk.status_aktif == True)
    if kategori:
        kondisi.append(ModelProduk.kategori == kategori)
    if cari:
        pola = f"%{cari}%"
        kondisi.append(or_(
            ModelProduk.nama.ilike(pola),
            ModelProduk.sku.ilike(pola),
            ModelProduk.barcode.ilike(pola)
        ))

    kueri = select(ModelProduk).where(and_(*kondisi)).order_by(ModelProduk.nama.asc())
    hasil = await sesi.execute(kueri)
    return hasil.scalars().all()

@router.post("/products", response_model=ResponsProduk, status_code=status.HTTP_201_CREATED)
async def tambah_produk(
    permintaan: PermintaanBuatProduk,
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-10: Tambah produk baru (Manajer/Owner)
    """
    # Cek keunikan SKU dalam toko
    kueri_sku = select(ModelProduk).where(
        ModelProduk.id_toko == pengguna.id_toko,
        ModelProduk.sku == permintaan.sku,
        ModelProduk.apakah_dihapus == False
    )
    ada_sku = (await sesi.execute(kueri_sku)).scalar_one_or_none()
    if ada_sku:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DUPLICATE_SKU", "message": f"SKU '{permintaan.sku}' sudah digunakan pada produk lain."}
        )

    # Cek keunikan Barcode jika diisi
    if permintaan.barcode:
        kueri_barcode = select(ModelProduk).where(
            ModelProduk.id_toko == pengguna.id_toko,
            ModelProduk.barcode == permintaan.barcode,
            ModelProduk.apakah_dihapus == False
        )
        ada_barcode = (await sesi.execute(kueri_barcode)).scalar_one_or_none()
        if ada_barcode:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "DUPLICATE_BARCODE", "message": f"Barcode '{permintaan.barcode}' sudah digunakan pada produk lain."}
            )

    # Proses dan unggah foto ke RustFS S3 jika dikirim sebagai Base64
    foto_s3 = proses_dan_unggah_foto(permintaan.foto, awalan="produk")

    produk_baru = ModelProduk(
        id_toko=pengguna.id_toko,
        sku=permintaan.sku,
        barcode=permintaan.barcode,
        nama=permintaan.nama,
        kategori=permintaan.kategori,
        foto=foto_s3,
        harga=permintaan.harga,
        harga_modal=permintaan.harga_modal,
        stok=permintaan.stok_awal,
        min_stok=permintaan.min_stok,
        status_aktif=permintaan.status_aktif,
        diperbarui_pada=waktu_sekarang_utc()
    )
    sesi.add(produk_baru)
    await sesi.flush()

    # Jika stok awal > 0, catat pergerakan stok awal
    if permintaan.stok_awal > 0:
        pergerakan = ModelPergerakanStok(
            id_toko=pengguna.id_toko,
            id_produk=produk_baru.id,
            perubahan_stok=permintaan.stok_awal,
            tipe="initial",
            alasan="Stok awal produk baru",
            dibuat_oleh=pengguna.id
        )
        sesi.add(pergerakan)

    # Catat audit
    audit = ModelCatatanAudit(
        id_toko=pengguna.id_toko,
        id_aktor=pengguna.id,
        aksi="TAMBAH_PRODUK",
        entitas="produk",
        id_entitas=produk_baru.id,
        rincian=f"Produk {produk_baru.nama} (SKU: {produk_baru.sku}) dibuat oleh {pengguna.nama_pengguna}"
    )
    sesi.add(audit)
    await sesi.commit()
    await sesi.refresh(produk_baru)
    return produk_baru

@router.put("/products/{id_produk}", response_model=ResponsProduk)
async def ubah_produk(
    id_produk: str,
    permintaan: PermintaanUbahProduk,
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-10: Ubah data produk. Jika harga berubah, catat riwayat harga.
    """
    kueri = select(ModelProduk).where(
        ModelProduk.id == id_produk,
        ModelProduk.id_toko == pengguna.id_toko,
        ModelProduk.apakah_dihapus == False
    )
    produk = (await sesi.execute(kueri)).scalar_one_or_none()
    if not produk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Produk tidak ditemukan"}
        )

    # Periksa perubahan harga untuk dicatat di riwayat harga
    if permintaan.harga is not None and permintaan.harga != produk.harga:
        riwayat = ModelRiwayatHarga(
            id_produk=produk.id,
            harga_lama=produk.harga,
            harga_baru=permintaan.harga,
            diubah_oleh=pengguna.id
        )
        sesi.add(riwayat)
        produk.harga = permintaan.harga

    if permintaan.sku is not None and permintaan.sku != produk.sku:
        produk.sku = permintaan.sku
    if permintaan.barcode is not None:
        produk.barcode = permintaan.barcode
    if permintaan.nama is not None:
        produk.nama = permintaan.nama
    if permintaan.kategori is not None:
        produk.kategori = permintaan.kategori
    if permintaan.foto is not None:
        if permintaan.foto != produk.foto:
            foto_s3 = proses_dan_unggah_foto(permintaan.foto, awalan="produk")
            if produk.foto and produk.foto != foto_s3:
                hapus_berkas_s3(produk.foto)
            produk.foto = foto_s3
    if permintaan.harga_modal is not None:
        produk.harga_modal = permintaan.harga_modal
    if permintaan.min_stok is not None:
        produk.min_stok = permintaan.min_stok
    if permintaan.status_aktif is not None:
        produk.status_aktif = permintaan.status_aktif

    produk.diperbarui_pada = waktu_sekarang_utc()

    audit = ModelCatatanAudit(
        id_toko=pengguna.id_toko,
        id_aktor=pengguna.id,
        aksi="UBAH_PRODUK",
        entitas="produk",
        id_entitas=produk.id,
        rincian=f"Produk {produk.nama} diubah oleh {pengguna.nama_pengguna}"
    )
    sesi.add(audit)
    await sesi.commit()
    await sesi.refresh(produk)
    return produk

@router.delete("/products/{id_produk}")
async def hapus_produk(
    id_produk: str,
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-10: Soft delete produk agar data riwayat transaksi tetap utuh
    """
    kueri = select(ModelProduk).where(
        ModelProduk.id == id_produk,
        ModelProduk.id_toko == pengguna.id_toko,
        ModelProduk.apakah_dihapus == False
    )
    produk = (await sesi.execute(kueri)).scalar_one_or_none()
    if not produk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Produk tidak ditemukan"}
        )

    produk.apakah_dihapus = True
    produk.status_aktif = False
    produk.diperbarui_pada = waktu_sekarang_utc()

    audit = ModelCatatanAudit(
        id_toko=pengguna.id_toko,
        id_aktor=pengguna.id,
        aksi="HAPUS_PRODUK",
        entitas="produk",
        id_entitas=produk.id,
        rincian=f"Produk {produk.nama} (SKU: {produk.sku}) dihapus secara soft-delete oleh {pengguna.nama_pengguna}"
    )
    sesi.add(audit)
    await sesi.commit()
    return {"message": "Produk berhasil dihapus"}

@router.post("/products/import")
async def impor_produk_csv(
    berkas: UploadFile = File(...),
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-10: Impor produk massal via CSV dengan validasi dan upsert berbasis SKU
    Format CSV: sku, barcode, nama, kategori, harga, harga_modal, stok, min_stok
    """
    konten = await berkas.read()
    teks = konten.decode("utf-8-sig", errors="ignore")
    pembaca_csv = csv.DictReader(io.StringIO(teks))

    jumlah_sukses = 0
    baris_gagal = []

    for index_baris, baris in enumerate(pembaca_csv, start=2):
        sku = baris.get("sku", "").strip()
        nama = baris.get("nama", "").strip()
        if not sku or not nama:
            baris_gagal.append({"baris": index_baris, "pesan": "SKU dan Nama wajib diisi"})
            continue

        try:
            harga = int(float(baris.get("harga", 0)))
            harga_modal = int(float(baris.get("harga_modal", 0)))
            stok = int(float(baris.get("stok", 0)))
            min_stok = int(float(baris.get("min_stok", 5)))
        except ValueError:
            baris_gagal.append({"baris": index_baris, "pesan": "Format angka harga/stok tidak valid"})
            continue

        barcode = baris.get("barcode", "").strip() or None
        kategori = baris.get("kategori", "").strip() or None

        # Cek apakah produk dengan SKU tersebut sudah ada
        kueri_cek = select(ModelProduk).where(
            ModelProduk.id_toko == pengguna.id_toko,
            ModelProduk.sku == sku,
            ModelProduk.apakah_dihapus == False
        )
        produk_ada = (await sesi.execute(kueri_cek)).scalar_one_or_none()

        if produk_ada:
            produk_ada.nama = nama
            produk_ada.barcode = barcode
            produk_ada.kategori = kategori
            produk_ada.harga = harga
            produk_ada.harga_modal = harga_modal
            produk_ada.min_stok = min_stok
            produk_ada.diperbarui_pada = waktu_sekarang_utc()
        else:
            produk_baru = ModelProduk(
                id_toko=pengguna.id_toko,
                sku=sku,
                barcode=barcode,
                nama=nama,
                kategori=kategori,
                harga=harga,
                harga_modal=harga_modal,
                stok=stok,
                min_stok=min_stok,
                status_aktif=True,
                diperbarui_pada=waktu_sekarang_utc()
            )
            sesi.add(produk_baru)
            await sesi.flush()
            if stok > 0:
                pergerakan = ModelPergerakanStok(
                    id_toko=pengguna.id_toko,
                    id_produk=produk_baru.id,
                    perubahan_stok=stok,
                    tipe="initial",
                    alasan="Impor CSV stok awal",
                    dibuat_oleh=pengguna.id
                )
                sesi.add(pergerakan)

        jumlah_sukses += 1

    await sesi.commit()
    return {
        "status": "sukses",
        "jumlah_diimpor": jumlah_sukses,
        "baris_gagal": baris_gagal
    }

@router.post("/storage/upload")
async def unggah_foto_langsung(
    berkas: UploadFile = File(...),
    pengguna: ModelPengguna = Depends(wajib_peran("kasir", "manajer", "owner"))
):
    """
    Mengunggah berkas gambar langsung ke Object Storage RustFS.
    Mengembalikan URL publik S3.
    """
    konten = await berkas.read()
    tipe_konten = berkas.content_type or "image/webp"
    ekstensi = os.path.splitext(berkas.filename or "")[1] or ".webp"
    nama_objek = f"produk/{uuid.uuid4().hex}{ekstensi}"
    url_publik = unggah_berkas_bytes(konten, nama_objek, tipe_konten)
    return {
        "url": url_publik,
        "nama_objek": nama_objek,
        "ukuran_bytes": len(konten)
    }
