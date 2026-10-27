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


def simpan_gambar_upload(file, folder, batas_byte: int):
    """Simpan JPG/PNG/WEBP dengan nama acak setelah cek ekstensi dan signature berkas."""
    if not file or not getattr(file, "filename", ""):
        raise ValueError("Pilih foto terlebih dahulu.")
    if not ekstensi_file_diizinkan(file.filename, EKSTENSI_GAMBAR):
        raise ValueError("Foto harus berformat JPG, JPEG, PNG, atau WEBP.")
    data = file.stream.read(int(batas_byte) + 1)
    if not data:
        raise ValueError("Berkas foto kosong.")
    if len(data) > int(batas_byte):
        raise ValueError(f"Ukuran foto maksimal {int(batas_byte) // (1024 * 1024)} MB.")
    ekstensi = file.filename.rsplit(".", 1)[1].lower()
    signature_ok = (
        (ekstensi in {"jpg", "jpeg"} and data.startswith(b"\xff\xd8\xff"))
        or (ekstensi == "png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
        or (ekstensi == "webp" and len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP")
    )
    if not signature_ok:
        raise ValueError("Isi berkas tidak cocok dengan format gambar yang dipilih.")
    from pathlib import Path
    tujuan = Path(folder)
    tujuan.mkdir(parents=True, exist_ok=True)
    nama = nama_file_aman(file.filename)
    path = tujuan / nama
    path.write_bytes(data)
    return path
