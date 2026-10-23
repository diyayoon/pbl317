"""Utilitas upload aman. Implementasi lengkap digunakan mulai Tahap 3."""

from pathlib import Path
from uuid import uuid4

from werkzeug.utils import secure_filename

EKSTENSI_GAMBAR = {"jpg", "jpeg", "png", "webp"}
EKSTENSI_DOKUMEN = {"pdf"}


def ekstensi_file_diizinkan(nama_file: str, ekstensi_diizinkan: set[str]) -> bool:
    """Mengecek ekstensi file tanpa mempercayai nama file asli."""
    if "." not in nama_file:
        return False
    ekstensi = nama_file.rsplit(".", 1)[1].lower()
    return ekstensi in ekstensi_diizinkan


def nama_file_aman(nama_file: str) -> str:
    """Membuat nama acak agar file tidak bentrok dan sulit ditebak."""
    nama_aman = secure_filename(nama_file)
    ekstensi = Path(nama_aman).suffix.lower()
    return f"{uuid4().hex}{ekstensi}"
