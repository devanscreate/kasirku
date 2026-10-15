import time
from collections import defaultdict
from typing import Dict, List

# Simpan riwayat percobaan gagal di memori: kunci -> list timestamp
_percobaan_gagal: Dict[str, List[float]] = defaultdict(list)

# Batasan: Maksimal 5 kali gagal per 60 detik (F-01 & U01)
MAKS_GAGAL_PER_MENIT = 5
DURASI_JENDELA_DETIK = 60

def periksa_apakah_dibatasi(kunci: str) -> bool:
    """
    Periksa apakah identitas (nama_pengguna + IP) telah melebihi batas percobaan gagal.
    """
    sekarang = time.time()
    daftar_waktu = _percobaan_gagal[kunci]
    
    # Bersihkan riwayat yang sudah di luar jendela 60 detik
    daftar_baru = [t for t in daftar_waktu if sekarang - t < DURASI_JENDELA_DETIK]
    _percobaan_gagal[kunci] = daftar_baru

    return len(daftar_baru) >= MAKS_GAGAL_PER_MENIT

def catat_percobaan_gagal(kunci: str):
    """
    Catat satu kali kegagalan login untuk kunci tertentu.
    """
    sekarang = time.time()
    _percobaan_gagal[kunci].append(sekarang)

def reset_percobaan(kunci: str):
    """
    Reset percobaan gagal jika login berhasil.
    """
    if kunci in _percobaan_gagal:
        del _percobaan_gagal[kunci]
