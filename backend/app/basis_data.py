from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.konfigurasi import setelan

# Inisialisasi engine async SQLAlchemy
mesin_db = create_async_engine(
    setelan.URL_BASIS_DATA,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False} if "sqlite" in setelan.URL_BASIS_DATA else {}
)

# Pembuat sesi async
PembuatSesiAsync = async_sessionmaker(
    bind=mesin_db,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession
)

# Basis deklaratif untuk model ORM
BasisTabel = declarative_base()

# Dependensi FastAPI untuk injeksi sesi basis data
async def dapatkan_sesi_db():
    async with PembuatSesiAsync() as sesi:
        try:
            yield sesi
        finally:
            await sesi.close()
