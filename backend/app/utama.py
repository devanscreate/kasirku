from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager

from app.konfigurasi import setelan
from app.basis_data import mesin_db, BasisTabel, PembuatSesiAsync
from app.data_awal import inisialisasi_data_awal

from app.rute.rute_auth import router as rute_auth
from app.rute.rute_produk import router as rute_produk
from app.rute.rute_shift import router as rute_shift
from app.rute.rute_penjualan import router as rute_penjualan
from app.rute.rute_retur import router as rute_retur
from app.rute.rute_stok import router as rute_stok
from app.rute.rute_laporan import router as rute_laporan
from app.rute.rute_pengaturan import router as rute_pengaturan
from app.rute.rute_kesehatan import router as rute_kesehatan
from app.rute.rute_donasi import router as rute_donasi

@asynccontextmanager
async def masa_hidup_aplikasi(app: FastAPI):
    # Buat tabel secara otomatis pada startup jika belum ada
    async with mesin_db.begin() as koneksi:
        await koneksi.run_sync(BasisTabel.metadata.create_all)
        # Migrasi skema ringan: pastikan kolom foto tersedia di tabel produk
        try:
            from sqlalchemy import text
            await koneksi.execute(text("ALTER TABLE produk ADD COLUMN foto TEXT"))
        except Exception:
            pass # Kolom sudah ada

    # Inisialisasi data toko, user default, dan katalog produk demo
    async with PembuatSesiAsync() as sesi:
        await inisialisasi_data_awal(sesi)

    # Pastikan bucket RustFS S3 tersedia
    from app.layanan.layanan_storage import pastikan_bucket_tersedia
    pastikan_bucket_tersedia()

    yield

    # Tutup koneksi engine database saat shutdown
    await mesin_db.dispose()

aplikasi = FastAPI(
    title=setelan.NAMA_APLIKASI,
    version=setelan.VERSI_APLIKASI,
    description="Backend API POS Ringan & Offline-First dengan Idempotensi Outbox dan Row Locking",
    lifespan=masa_hidup_aplikasi
)

# Konfigurasi CORS
aplikasi.add_middleware(
    CORSMiddleware,
    allow_origins=setelan.ASAL_DIIZINKAN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Format Error Seragam Sesuai Bagian 9 PRD: {code, message, details}
@aplikasi.exception_handler(RequestValidationError)
async def penanganan_error_validasi(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Struktur atau tipe data yang dikirimkan tidak valid",
            "details": exc.errors()
        }
    )

# Pendaftaran Rute dengan Prefix /api/v1
aplikasi.include_router(rute_auth, prefix="/api/v1")
aplikasi.include_router(rute_produk, prefix="/api/v1")
aplikasi.include_router(rute_shift, prefix="/api/v1")
aplikasi.include_router(rute_penjualan, prefix="/api/v1")
aplikasi.include_router(rute_retur, prefix="/api/v1")
aplikasi.include_router(rute_stok, prefix="/api/v1")
aplikasi.include_router(rute_laporan, prefix="/api/v1")
aplikasi.include_router(rute_pengaturan, prefix="/api/v1")
aplikasi.include_router(rute_donasi, prefix="/api/v1")
aplikasi.include_router(rute_kesehatan, prefix="/api/v1")

# Rute langsung untuk Docker / Caddy Health Check
aplikasi.include_router(rute_kesehatan)

@aplikasi.get("/")
async def beranda():
    return {
        "nama": setelan.NAMA_APLIKASI,
        "versi": setelan.VERSI_APLIKASI,
        "status": "online",
        "dokumentasi": "/docs"
    }
