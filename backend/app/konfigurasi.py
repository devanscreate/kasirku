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

    # Setelan S3 Object Storage (RustFS / MinIO / AWS S3)
    S3_ENDPOINT: str = os.getenv("S3_ENDPOINT", "localhost:9000")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "admin")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "password123")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "kasirku")
    S3_SECURE: bool = os.getenv("S3_SECURE", "false").lower() in ("true", "1", "t")
    S3_PUBLIC_BASE_URL: str = os.getenv("S3_PUBLIC_BASE_URL", "http://localhost:9000/kasirku")

setelan = Setelan()
