"""Utilitas unggah gambar yang memvalidasi ekstensi, MIME, signature, dan ukuran."""
from pathlib import Path
from uuid import uuid4

from werkzeug.utils import secure_filename

EKSTENSI_GAMBAR = {"jpg", "jpeg", "png", "webp"}
EKSTENSI_DOKUMEN = {"pdf"}
MIME_GAMBAR = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def ekstensi_file_diizinkan(nama_file: str, ekstensi_diizinkan: set[str]) -> bool:
    """Periksa ekstensi file tanpa mempercayai nama file asli."""
    if not nama_file or "." not in nama_file:
        return False
    return nama_file.rsplit(".", 1)[1].lower() in ekstensi_diizinkan


def nama_file_aman(nama_file: str) -> str:
    """Buat nama acak agar file tidak bentrok dan nama asli tidak terekspos."""
    nama_aman = secure_filename(nama_file)
    ekstensi = Path(nama_aman).suffix.lower()
    return f"{uuid4().hex}{ekstensi}"


def simpan_gambar_upload(file, folder, batas_byte: int) -> Path:
    """Simpan JPG/PNG/WEBP setelah validasi ekstensi, MIME, signature, dan ukuran."""
    if not file or not getattr(file, "filename", ""):
        raise ValueError("Pilih foto terlebih dahulu.")

    if not ekstensi_file_diizinkan(file.filename, EKSTENSI_GAMBAR):
        raise ValueError("Foto harus berformat JPG, JPEG, PNG, atau WEBP.")

    ekstensi = file.filename.rsplit(".", 1)[1].lower()
    mime_diharapkan = MIME_GAMBAR[ekstensi]
    mime_diterima = (getattr(file, "mimetype", "") or "").split(";", 1)[0].strip().lower()
    if mime_diterima != mime_diharapkan:
        raise ValueError("Tipe MIME foto tidak sesuai dengan format file.")

    batas = int(batas_byte)
    if batas <= 0:
        raise ValueError("Batas ukuran foto tidak valid.")

    data = file.stream.read(batas + 1)
    if not data:
        raise ValueError("Berkas foto kosong.")
    if len(data) > batas:
        ukuran_mb = max(1, batas // (1024 * 1024))
        raise ValueError(f"Ukuran foto maksimal {ukuran_mb} MB.")

    signature_ok = (
        (ekstensi in {"jpg", "jpeg"} and data.startswith(b"\xff\xd8\xff"))
        or (ekstensi == "png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
        or (ekstensi == "webp" and len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP")
    )
    if not signature_ok:
        raise ValueError("Isi berkas tidak cocok dengan format gambar yang dipilih.")

    tujuan = Path(folder)
    tujuan.mkdir(parents=True, exist_ok=True)
    path = tujuan / nama_file_aman(file.filename)
    path.write_bytes(data)
    return path
