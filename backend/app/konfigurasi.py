import os

class Setelan:
    # Nama dan Versi Aplikasi
    NAMA_APLIKASI: str = "Kasirku POS API"
    VERSI_APLIKASI: str = "1.0.0"
    
    # Kunci Rahasia JWT & Enkripsi
    KUNCI_RAHASIA: str = os.getenv("KUNCI_RAHASIA", "kasirku-kunci-rahasia-super-aman-2026-xyz123")
    ALGORITMA_JWT: str = "HS256"
    MENIT_KADALUARSA_AKSES: int = 60 * 24 # 24 jam
    JAM_KADALUARSA_REFRESH: int = 12
    
    # URL Basis Data (Secara bawaan SQLite async, siap diubah ke PostgreSQL via ENV)
    URL_BASIS_DATA: str = os.getenv(
        "DATABASE_URL", 
        "sqlite+aiosqlite:///./kasirku.db"
    )
    
    # Asal domain yang diizinkan (CORS)
    ASAL_DIIZINKAN: list = ["*"]

setelan = Setelan()
