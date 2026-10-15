from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.basis_data import dapatkan_sesi_db

router = APIRouter(tags=["Pemeriksaan Kesehatan (Health Checks)"])

@router.get("/health", status_code=status.HTTP_200_OK)
async def periksa_kesehatan():
    """
    F-14: Liveness probe untuk monitoring kontainer & orchestrator
    """
    return {
        "status": "sehat",
        "layanan": "Kasirku POS API",
        "pesan": "Layanan aktif berjalan"
    }

@router.get("/ready", status_code=status.HTTP_200_OK)
async def periksa_kesiapan(sesi: AsyncSession = Depends(dapatkan_sesi_db)):
    """
    F-14: Readiness probe yang memverifikasi koneksi ke basis data
    """
    try:
        await sesi.execute(text("SELECT 1"))
        return {
            "status": "siap",
            "basis_data": "terhubung",
            "pesan": "Aplikasi siap menerima permintaan lalu lintas data"
        }
    except Exception as e:
        return {
            "status": "belum_siap",
            "basis_data": "terputus",
            "kesalahan": str(e)
        }
