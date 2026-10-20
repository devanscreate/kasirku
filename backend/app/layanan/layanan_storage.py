import io
import re
import base64
import uuid
import logging
from typing import Optional, Tuple
from minio import Minio
from minio.error import S3Error

from app.konfigurasi import setelan

logger = logging.getLogger("kasirku.storage")

def _buat_klien_s3() -> Tuple[Minio, str]:
    """
    Menginisialisasi klien MinIO / S3 yang terhubung ke RustFS Object Storage.
    """
    raw_endpoint = setelan.S3_ENDPOINT.strip()
    secure = setelan.S3_SECURE

    if raw_endpoint.startswith("https://"):
        raw_endpoint = raw_endpoint[len("https://"):]
        secure = True
    elif raw_endpoint.startswith("http://"):
        raw_endpoint = raw_endpoint[len("http://"):]
        secure = False

    klien = Minio(
        raw_endpoint,
        access_key=setelan.S3_ACCESS_KEY,
        secret_key=setelan.S3_SECRET_KEY,
        secure=secure
    )
    bucket = setelan.S3_BUCKET
    return klien, bucket

def pastikan_bucket_tersedia() -> bool:
    """
    Memeriksa keberadaan bucket di RustFS, dan membuatnya jika belum ada.
    """
    try:
        klien, bucket = _buat_klien_s3()
        if not klien.bucket_exists(bucket):
            klien.make_bucket(bucket)
            logger.info(f"Bucket '{bucket}' berhasil dibuat di RustFS.")
        return True
    except Exception as e:
        logger.warning(f"Gagal memeriksa/membuat bucket '{setelan.S3_BUCKET}' di RustFS: {e}")
        return False

def unggah_berkas_bytes(
    berkas_bytes: bytes, 
    nama_objek: str, 
    tipe_konten: str = "image/webp"
) -> str:
    """
    Mengunggah berkas biner (bytes) ke RustFS Object Storage.
    Mengembalikan URL publik yang dapat diakses oleh browser.
    """
    klien, bucket = _buat_klien_s3()

    # Pastikan bucket ada
    try:
        if not klien.bucket_exists(bucket):
            klien.make_bucket(bucket)
    except Exception as e:
        logger.debug(f"Pengecekan bucket: {e}")

    stream_data = io.BytesIO(berkas_bytes)
    klien.put_object(
        bucket_name=bucket,
        object_name=nama_objek,
        data=stream_data,
        length=len(berkas_bytes),
        content_type=tipe_konten
    )

    url_publik = f"{setelan.S3_PUBLIC_BASE_URL.rstrip('/')}/{nama_objek}"
    return url_publik

def proses_dan_unggah_foto(
    foto_input: Optional[str], 
    awalan: str = "produk"
) -> Optional[str]:
    """
    Mendeteksi apakah foto_input berupa Data URI Base64 (data:image/...).
    Jika ya, dikonversi menjadi berkas biner dan diunggah ke RustFS Object Storage.
    Jika sudah berupa URL (http:// atau https://), dikembalikan apa adanya.
    Jika RustFS tidak dapat dijangkau, fallback aman tetap mengembalikan data asli.
    """
    if not foto_input or not isinstance(foto_input, str):
        return None

    # Jika sudah berupa URL publik (mis. http://localhost:9000/kasirku/produk/...)
    if foto_input.startswith("http://") or foto_input.startswith("https://"):
        return foto_input

    # Jika berupa Data URI Base64: data:image/webp;base64,...
    pola_base64 = re.match(r"^data:(image\/[a-zA-Z0-9\+\-\.]+);base64,(.+)$", foto_input, re.DOTALL)
    if pola_base64:
        tipe_konten = pola_base64.group(1).lower()
        string_base64 = pola_base64.group(2)

        # Tentukan ekstensi
        ekstensi = ".webp"
        if "jpeg" in tipe_konten or "jpg" in tipe_konten:
            ekstensi = ".jpg"
        elif "png" in tipe_konten:
            ekstensi = ".png"
        elif "svg" in tipe_konten:
            ekstensi = ".svg"
        elif "gif" in tipe_konten:
            ekstensi = ".gif"

        try:
            berkas_bytes = base64.b64decode(string_base64)
            nama_unik = f"{awalan}/{uuid.uuid4().hex}{ekstensi}"
            url_s3 = unggah_berkas_bytes(berkas_bytes, nama_unik, tipe_konten)
            logger.info(f"Foto berhasil disimpan ke RustFS S3: {url_s3}")
            return url_s3
        except Exception as e:
            logger.error(f"Gagal mengunggah foto ke RustFS: {e}. Menggunakan fallback data asli.")
            return foto_input

    return foto_input

def hapus_berkas_s3(url_berkas: Optional[str]):
    """
    Menghapus objek dari RustFS jika url_berkas berasal dari bucket yang sama.
    """
    if not url_berkas or not isinstance(url_berkas, str):
        return

    base_url = setelan.S3_PUBLIC_BASE_URL.rstrip('/')
    if url_berkas.startswith(base_url):
        nama_objek = url_berkas[len(base_url):].lstrip('/')
        if nama_objek:
            try:
                klien, bucket = _buat_klien_s3()
                klien.remove_object(bucket, nama_objek)
                logger.info(f"Objek '{nama_objek}' berhasil dihapus dari RustFS.")
            except Exception as e:
                logger.warning(f"Gagal menghapus objek '{nama_objek}' dari RustFS: {e}")
