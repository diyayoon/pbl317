"""Ganti password dengan kontrol keamanan (OWASP A07)."""
from flask import current_app
from app.extensions import db
from app.models import User
from app.utils import audit, ratelimit


class LayananAkun:
    @staticmethod
    def ganti_password(user: User, lama: str, baru: str, konfirmasi: str) -> None:
        """Melempar ValueError(pesan) bila gagal. Sesi lain otomatis tercabut (auth_version naik)."""
        kunci = f"u{user.id}"
        if ratelimit.terblokir("ganti_password", kunci, 5, current_app.config["LOGIN_WINDOW_MENIT"]):
            raise ValueError("Terlalu banyak percobaan. Coba lagi beberapa menit lagi.")
        if not user.cek_password(lama[:200]):
            ratelimit.catat("ganti_password", kunci)
            audit.catat("ganti_password_gagal", "user", user.id, "password lama salah", commit=True)
            raise ValueError("Kata sandi saat ini tidak sesuai.")
        if not baru.strip() or not 16 <= len(baru) <= 128:
            raise ValueError("Kata sandi baru harus terdiri dari 16–128 karakter dan tidak hanya spasi.")
        if baru != konfirmasi:
            raise ValueError("Konfirmasi kata sandi baru tidak cocok.")
        if user.cek_password(baru):
            raise ValueError("Kata sandi baru harus berbeda dari kata sandi saat ini.")
        if user.email.split("@")[0].lower() in baru.lower() and len(user.email.split("@")[0]) >= 4:
            raise ValueError("Kata sandi tidak boleh memuat nama email Anda.")
        user.set_password(baru)
        audit.catat("ganti_password", "user", user.id)
        db.session.commit()
        ratelimit.bersihkan("ganti_password", kunci)
