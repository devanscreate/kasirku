from fastapi import APIRouter, Depends, HTTPException, status, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import hashlib
import json

from app.basis_data import dapatkan_sesi_db
from app.model.entitas import (
    ModelPenjualan,
    ModelItemPenjualan,
    ModelPembayaran,
    ModelProduk,
    ModelPergerakanStok,
    ModelShiftKasir,
    ModelCatatanAudit,
    ModelPengguna,
    waktu_sekarang_utc
)
from app.skema.skema_penjualan import (
    InputPenjualan,
    ResponsPenjualan,
    PermintaanVoid
)
from app.keamanan.autentikasi import dapatkan_pengguna_saat_ini, wajib_peran

router = APIRouter(prefix="/sales", tags=["Penjualan & Outbox Sync"])

def hitung_hash_transaksi(data: InputPenjualan) -> str:
    """
    Menghitung hash SHA-256 dari payload transaksi untuk verifikasi integritas & idempotensi
    """
    representasi = {
        "id": data.id,
        "id_shift": data.id_shift,
        "nomor_struk": data.nomor_struk,
        "total": data.total,
        "items": [
            {"id_produk": i.id_produk, "qty": i.kuantitas, "harga": i.harga_snapshot}
            for i in sorted(data.item, key=lambda x: x.id_produk)
        ]
    }
    teks_json = json.dumps(representasi, sort_keys=True)
    return hashlib.sha256(teks_json.encode()).hexdigest()

@router.post("", response_model=ResponsPenjualan, status_code=status.HTTP_201_CREATED)
async def simpan_transaksi_penjualan(
    permintaan: InputPenjualan,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-05: Sinkronisasi Transaksi Idempoten dari Outbox Kasir
    Alur paling kritis dalam arsitektur Offline-First
    """
    kunci_idempoten = idempotency_key or permintaan.id
    hash_saat_ini = hitung_hash_transaksi(permintaan)

    # 1. Cek apakah transaksi sudah pernah tersimpan sebelumnya (Idempotensi)
    kueri_cek = select(ModelPenjualan).where(
        ModelPenjualan.id == kunci_idempoten
    ).options(selectinload(ModelPenjualan.items), selectinload(ModelPenjualan.pembayaran))
    
    transaksi_lama = (await sesi.execute(kueri_cek)).scalar_one_or_none()
    if transaksi_lama:
        if transaksi_lama.hash_payload == hash_saat_ini:
            # Idempoten: kembalikan 200 OK dengan data yang sudah tersimpan tanpa memproses ulang stok (F-05 & U06)
            response.status_code = status.HTTP_200_OK
            return ResponsPenjualan(
                id=transaksi_lama.id,
                id_toko=transaksi_lama.id_toko,
                id_shift=transaksi_lama.id_shift,
                id_kasir=transaksi_lama.id_kasir,
                nama_kasir=pengguna.nama_lengkap,
                nomor_struk=transaksi_lama.nomor_struk,
                status=transaksi_lama.status,
                subtotal=transaksi_lama.subtotal,
                diskon=transaksi_lama.diskon,
                pajak=transaksi_lama.pajak,
                pembulatan=transaksi_lama.pembulatan,
                total=transaksi_lama.total,
                waktu_transaksi=transaksi_lama.waktu_transaksi,
                waktu_sinkron=transaksi_lama.waktu_sinkron,
                flag=json.loads(transaksi_lama.flag) if transaksi_lama.flag else {},
                item=transaksi_lama.items,
                pembayaran=transaksi_lama.pembayaran
            )
        else:
            # Terjadi konflik payload dengan ID yang sama
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "IDEMPOTENCY_CONFLICT", "message": "ID transaksi ini sudah ada namun memiliki data muatan yang berbeda."}
            )

    # 2. Verifikasi keberadaan Shift
    kueri_shift = select(ModelShiftKasir).where(ModelShiftKasir.id == permintaan.id_shift)
    shift = (await sesi.execute(kueri_shift)).scalar_one_or_none()
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "VALIDATION_ERROR", "message": f"Shift ID '{permintaan.id_shift}' tidak ditemukan di sistem."}
        )

    # 3. Urutkan item berdasarkan id_produk ASC untuk mencegah kebuntuan (Deadlock Prevention - U07)
    item_terurut = sorted(permintaan.item, key=lambda x: x.id_produk)
    id_produk_list = [i.id_produk for i in item_terurut]

    kueri_produk = select(ModelProduk).where(
        ModelProduk.id.in_(id_produk_list),
        ModelProduk.id_toko == pengguna.id_toko
    )
    daftar_produk_db = {p.id: p for p in (await sesi.execute(kueri_produk)).scalars().all()}

    # Validasi keberadaan produk
    for it in item_terurut:
        if it.id_produk not in daftar_produk_db:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "VALIDATION_ERROR", "message": f"Produk ID '{it.id_produk}' tidak ditemukan di katalog."}
            )

    # Inisialisasi Bendera Anomali (Flags)
    flags = {}
    waktu_server_sekarang = waktu_sekarang_utc()

    # Periksa Clock Skew (|sold_at - server_now| > 10 menit)
    selisih_waktu = abs((waktu_server_sekarang - permintaan.waktu_transaksi).total_seconds())
    if selisih_waktu > 600:
        flags["clock_skew"] = {
            "selisih_detik": int(selisih_waktu),
            "waktu_klien": permintaan.waktu_transaksi.isoformat(),
            "waktu_server": waktu_server_sekarang.isoformat()
        }

    # Hitung ulang total server untuk deteksi ketidaksesuaian
    subtotal_hitung = 0
    ada_harga_berbeda = False

    for it in item_terurut:
        prod = daftar_produk_db[it.id_produk]
        subtotal_hitung += (it.harga_snapshot * it.kuantitas) - it.alokasi_diskon
        if it.harga_snapshot != prod.harga:
            ada_harga_berbeda = True

    if ada_harga_berbeda:
        flags["price_mismatch"] = True

    total_hitung = subtotal_hitung - permintaan.diskon + permintaan.pajak + permintaan.pembulatan - (permintaan.potongan_donasi or 0)
    if abs(total_hitung - permintaan.total) > 1: # toleransi pembulatan rupiah
        flags["total_mismatch"] = {
            "total_klien": permintaan.total,
            "total_server": total_hitung
        }

    # 4. Potong Stok secara Atomik & Catat Pergerakan Stok
    ada_stok_negatif = False
    for it in item_terurut:
        prod = daftar_produk_db[it.id_produk]
        prod.stok -= it.kuantitas
        if prod.stok < 0:
            ada_stok_negatif = True

        # Catat Ledger Pergerakan Stok
        pergerakan = ModelPergerakanStok(
            id_toko=pengguna.id_toko,
            id_produk=prod.id,
            perubahan_stok=-it.kuantitas,
            tipe="sale",
            id_referensi=kunci_idempoten,
            alasan=f"Penjualan struk {permintaan.nomor_struk}",
            dibuat_oleh=pengguna.id,
            dibuat_pada=waktu_server_sekarang
        )
        sesi.add(pergerakan)

    if ada_stok_negatif:
        flags["negative_stock"] = True

    # 5. Simpan Entitas Penjualan
    penjualan_baru = ModelPenjualan(
        id=kunci_idempoten,
        id_toko=pengguna.id_toko,
        id_shift=permintaan.id_shift,
        id_kasir=pengguna.id,
        nomor_struk=permintaan.nomor_struk,
        status="completed",
        subtotal=permintaan.subtotal,
        diskon=permintaan.diskon,
        pajak=permintaan.pajak,
        pembulatan=permintaan.pembulatan,
        total=permintaan.total,
        waktu_transaksi=permintaan.waktu_transaksi,
        waktu_sinkron=waktu_server_sekarang,
        hash_payload=hash_saat_ini,
        flag=json.dumps(flags) if flags else None
    )
    sesi.add(penjualan_baru)

    # 6. Simpan Item Penjualan
    for it in item_terurut:
        item_baris = ModelItemPenjualan(
            id_penjualan=penjualan_baru.id,
            id_produk=it.id_produk,
            nama_produk_snapshot=it.nama_produk_snapshot,
            harga_snapshot=it.harga_snapshot,
            kuantitas=it.kuantitas,
            alokasi_diskon=it.alokasi_diskon,
            subtotal_baris=it.subtotal_baris
        )
        sesi.add(item_baris)

    # 7. Simpan Pembayaran
    for bayar in permintaan.pembayaran:
        bayar_baris = ModelPembayaran(
            id_penjualan=penjualan_baru.id,
            metode=bayar.metode,
            jumlah=bayar.jumlah,
            diterima=bayar.diterima,
            kembalian=bayar.kembalian
        )
        sesi.add(bayar_baris)

    # Jika ada flag anomali, beri tanda pada shift
    if flags:
        shift.memiliki_penjualan_bermasalah = True

    await sesi.commit()

    # Ambil ulang dengan relasi lengkap
    kueri_lengkap = select(ModelPenjualan).where(
        ModelPenjualan.id == penjualan_baru.id
    ).options(selectinload(ModelPenjualan.items), selectinload(ModelPenjualan.pembayaran))
    hasil_akhir = (await sesi.execute(kueri_lengkap)).scalar_one()

    return ResponsPenjualan(
        id=hasil_akhir.id,
        id_toko=hasil_akhir.id_toko,
        id_shift=hasil_akhir.id_shift,
        id_kasir=hasil_akhir.id_kasir,
        nama_kasir=pengguna.nama_lengkap,
        nomor_struk=hasil_akhir.nomor_struk,
        status=hasil_akhir.status,
        subtotal=hasil_akhir.subtotal,
        diskon=hasil_akhir.diskon,
        pajak=hasil_akhir.pajak,
        pembulatan=hasil_akhir.pembulatan,
        total=hasil_akhir.total,
        waktu_transaksi=hasil_akhir.waktu_transaksi,
        waktu_sinkron=hasil_akhir.waktu_sinkron,
        flag=flags,
        item=hasil_akhir.items,
        pembayaran=hasil_akhir.pembayaran
    )

@router.get("", response_model=List[ResponsPenjualan])
async def daftar_penjualan(
    dari_tanggal: Optional[datetime] = Query(None),
    sampai_tanggal: Optional[datetime] = Query(None),
    nomor_struk: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Mengambil daftar transaksi penjualan (Manajer/Owner melihat semua, Kasir melihat miliknya)
    """
    kondisi = [ModelPenjualan.id_toko == pengguna.id_toko]

    if pengguna.peran == "kasir":
        kondisi.append(ModelPenjualan.id_kasir == pengguna.id)

    if dari_tanggal:
        kondisi.append(ModelPenjualan.waktu_transaksi >= dari_tanggal)
    if sampai_tanggal:
        kondisi.append(ModelPenjualan.waktu_transaksi <= sampai_tanggal)
    if nomor_struk:
        kondisi.append(ModelPenjualan.nomor_struk.ilike(f"%{nomor_struk}%"))
    if status:
        kondisi.append(ModelPenjualan.status == status)

    kueri = select(ModelPenjualan).where(and_(*kondisi)).order_by(
        ModelPenjualan.waktu_transaksi.desc()
    ).options(selectinload(ModelPenjualan.items), selectinload(ModelPenjualan.pembayaran))

    daftar = (await sesi.execute(kueri)).scalars().all()
    
    hasil = []
    for s in daftar:
        hasil.append(ResponsPenjualan(
            id=s.id,
            id_toko=s.id_toko,
            id_shift=s.id_shift,
            id_kasir=s.id_kasir,
            nomor_struk=s.nomor_struk,
            status=s.status,
            subtotal=s.subtotal,
            diskon=s.diskon,
            pajak=s.pajak,
            pembulatan=s.pembulatan,
            total=s.total,
            waktu_transaksi=s.waktu_transaksi,
            waktu_sinkron=s.waktu_sinkron,
            flag=json.loads(s.flag) if s.flag else {},
            alasan_batal=s.alasan_batal,
            dibatalkan_pada=s.dibatalkan_pada,
            item=s.items,
            pembayaran=s.pembayaran
        ))
    return hasil

@router.get("/{id_penjualan}", response_model=ResponsPenjualan)
async def detail_penjualan(
    id_penjualan: str,
    pengguna: ModelPengguna = Depends(dapatkan_pengguna_saat_ini),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    Mengambil detail satu transaksi penjualan
    """
    kueri = select(ModelPenjualan).where(
        ModelPenjualan.id == id_penjualan,
        ModelPenjualan.id_toko == pengguna.id_toko
    ).options(selectinload(ModelPenjualan.items), selectinload(ModelPenjualan.pembayaran))

    transaksi = (await sesi.execute(kueri)).scalar_one_or_none()
    if not transaksi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Transaksi tidak ditemukan"}
        )

    return ResponsPenjualan(
        id=transaksi.id,
        id_toko=transaksi.id_toko,
        id_shift=transaksi.id_shift,
        id_kasir=transaksi.id_kasir,
        nomor_struk=transaksi.nomor_struk,
        status=transaksi.status,
        subtotal=transaksi.subtotal,
        diskon=transaksi.diskon,
        pajak=transaksi.pajak,
        pembulatan=transaksi.pembulatan,
        total=transaksi.total,
        waktu_transaksi=transaksi.waktu_transaksi,
        waktu_sinkron=transaksi.waktu_sinkron,
        flag=json.loads(transaksi.flag) if transaksi.flag else {},
        alasan_batal=transaksi.alasan_batal,
        dibatalkan_pada=transaksi.dibatalkan_pada,
        item=transaksi.items,
        pembayaran=transaksi.pembayaran
    )

@router.post("/{id_penjualan}/void", response_model=ResponsPenjualan)
async def batalkan_transaksi_void(
    id_penjualan: str,
    permintaan: PermintaanVoid,
    pengguna: ModelPengguna = Depends(wajib_peran("manajer", "owner")),
    sesi: AsyncSession = Depends(dapatkan_sesi_db)
):
    """
    F-07: Void Transaksi (Khusus Manajer/Owner).
    Hanya bisa dilakukan jika shift transaksi tersebut MASIH TERBUKA.
    Mengembalikan stok produk secara atomik dan mencatat audit log.
    """
    kueri = select(ModelPenjualan).where(
        ModelPenjualan.id == id_penjualan,
        ModelPenjualan.id_toko == pengguna.id_toko
    ).options(selectinload(ModelPenjualan.items), selectinload(ModelPenjualan.pembayaran))

    transaksi = (await sesi.execute(kueri)).scalar_one_or_none()
    if not transaksi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Transaksi tidak ditemukan"}
        )

    if transaksi.status == "voided":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ALREADY_VOIDED", "message": "Transaksi ini sudah dibatalkan sebelumnya."}
        )

    # Periksa apakah shift transaksi ini masih terbuka
    kueri_shift = select(ModelShiftKasir).where(ModelShiftKasir.id == transaksi.id_shift)
    shift = (await sesi.execute(kueri_shift)).scalar_one_or_none()
    if not shift or shift.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "SHIFT_CLOSED",
                "message": "Shift untuk transaksi ini sudah ditutup. Pembatalan setelah tutup shift harus menggunakan prosedur Retur (F-08)."
            }
        )

    # Kembalikan stok untuk setiap item terurut id_produk ASC
    item_terurut = sorted(transaksi.items, key=lambda x: x.id_produk)
    for it in item_terurut:
        kueri_prod = select(ModelProduk).where(ModelProduk.id == it.id_produk)
        prod = (await sesi.execute(kueri_prod)).scalar_one_or_none()
        if prod:
            prod.stok += it.kuantitas
            pergerakan = ModelPergerakanStok(
                id_toko=pengguna.id_toko,
                id_produk=prod.id,
                perubahan_stok=it.kuantitas,
                tipe="void",
                id_referensi=transaksi.id,
                alasan=f"Void struk {transaksi.nomor_struk}: {permintaan.alasan}",
                dibuat_oleh=pengguna.id
            )
            sesi.add(pergerakan)

    # Perbarui status transaksi
    transaksi.status = "voided"
    transaksi.dibatalkan_oleh = pengguna.id
    transaksi.dibatalkan_pada = waktu_sekarang_utc()
    transaksi.alasan_batal = permintaan.alasan

    audit = ModelCatatanAudit(
        id_toko=pengguna.id_toko,
        id_aktor=pengguna.id,
        aksi="VOID_TRANSAKSI",
        entitas="penjualan",
        id_entitas=transaksi.id,
        rincian=f"Transaksi {transaksi.nomor_struk} senilai Rp {transaksi.total:,} di-void oleh {pengguna.nama_pengguna}. Alasan: {permintaan.alasan}"
    )
    sesi.add(audit)
    await sesi.commit()

    return ResponsPenjualan(
        id=transaksi.id,
        id_toko=transaksi.id_toko,
        id_shift=transaksi.id_shift,
        id_kasir=transaksi.id_kasir,
        nomor_struk=transaksi.nomor_struk,
        status=transaksi.status,
        subtotal=transaksi.subtotal,
        diskon=transaksi.diskon,
        pajak=transaksi.pajak,
        pembulatan=transaksi.pembulatan,
        total=transaksi.total,
        waktu_transaksi=transaksi.waktu_transaksi,
        waktu_sinkron=transaksi.waktu_sinkron,
        flag=json.loads(transaksi.flag) if transaksi.flag else {},
        alasan_batal=transaksi.alasan_batal,
        dibatalkan_pada=transaksi.dibatalkan_pada,
        item=transaksi.items,
        pembayaran=transaksi.pembayaran
    )
